"""Generate each scene actor from its fitted contact poses, then audit the scene.

Actors share an authored clock/placement, not a joint scene-aware model. Source
poses may have known collision defects; target validity and generated contact
accuracy remain separate measurements.
"""
import argparse
import copy
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now, source_check
from action_requests import validate_batch, request_digest, conditioning_texts
from generation_constraints import EFFECTORS, compile_guides
from scene_constraints import evaluate, pose, effector_track
from build_soma_preview import ASSET


def actor_guides(scene, name):
    """Combine simultaneous effectors, avoiding conflicting implicit root guides."""
    entry=scene['actors'][name]; path=(ROOT/entry['motion']).resolve()
    if not path.is_relative_to(ROOT.resolve()) or sha256(path)!=entry.get('source_sha256'):
        raise ValueError('Scene actor source hash mismatch')
    translation, rotation=pose(entry['transform'])
    if abs(translation[1])>1e-6 or not np.allclose(rotation[:,1],[0,1,0],atol=1e-6):
        raise ValueError('Generation currently requires ground-level yaw-only actor placement')
    frames={}
    for contact in scene['contacts']:
        if contact['actor']!=name:continue
        joint=contact['effector'].get('joint')
        if joint not in EFFECTORS:raise ValueError('Generation scene guides currently support hand/foot contacts only')
        a,b=contact['start_frame'],contact['end_frame']
        if type(a)!=int or type(b)!=int or not 0<=a<=b<scene['frame_count']:raise ValueError('Contact frame outside scene')
        for frame in range(a,b+1):frames.setdefault(frame,set()).add(joint)
    if not frames:raise ValueError('Scene actor needs at least one hand/foot contact pose')
    groups={}
    for frame,joints in sorted(frames.items()):groups.setdefault(tuple(sorted(joints)),[]).append(frame)
    return [dict(type='end-effector',joint_names=list(joints),motion=entry['motion'],sha256=entry['source_sha256'],
                 source_frames=indices,frame_indices=indices) for joints,indices in groups.items()]


def requests(scene, plan):
    if set(plan)!=set(scene['actors']):raise ValueError('Provide a prompt schedule and seeds for every scene actor')
    result=[]
    for i,(name,settings) in enumerate(plan.items()):
        if set(settings)!={'segments','seeds'}:raise ValueError('Actor plan requires segments and seeds')
        if sum(round(s['duration_s']*30) for s in settings['segments'])!=scene['frame_count']:
            raise ValueError('Prompt schedule must match the shared scene clock')
        for mode in ['baseline','guided']:
            value=dict(id=f'actor-{i}-{mode}',label=f'Actor {name} · {mode}',**copy.deepcopy(settings))
            if mode=='guided':value['generation_constraints']=actor_guides(scene,name)
            result.append(value)
    batch=validate_batch(dict(schema_version=1,requests=result))
    for value in batch['requests']:compile_guides(value)
    return batch


def import_baseline_cache(batch, cache):
    """Extract exact tensor rows from the validated original v0 cache."""
    import torch
    from safetensors.torch import save_file, load_file
    from embedding_cache import CachedEncoder
    from action_encoder import ActionEncoder
    from profile_encoder import text_hash, revisions
    source=ROOT/'models/prompt-cache-v0-offload/manifest.json'; encoder=CachedEncoder(source)
    texts=conditioning_texts(batch)
    if not set(texts)<=set(encoder.texts):raise ValueError('Scene prompt is not in original cache; encode the actual new prompt instead')
    cache=Path(cache);cache.mkdir()
    entries={}
    for text in texts:
        features,_=encoder([text]);features=features.contiguous()
        filename=text_hash(text)+'.safetensors';save_file({'features':features},str(cache/filename))
        if not torch.equal(features,load_file(str(cache/filename))['features']):raise ValueError('Imported conditioning changed')
        entries[text]=dict(file=filename,sha256=sha256(cache/filename))
    save(cache/'manifest.json',dict(status='complete',request_sha256=request_digest(batch),kimodo_commit=source_check(),
        encoder_revisions=revisions(),entries=entries,
        loader_hashes={n:sha256(ROOT/'scripts'/n) for n in ['action_encoder.py','offload_encoder.py','streamed_encoder.py']},
        qualification='Original BF16 base/FP32 adapters with experimental disk offloading; full 8B resident equivalence untested.',
        reuse_provenance=dict(source=str(source),manifest_sha256=sha256(source),tensor_sha256=encoder.metadata['tensor_sha256'],
            original_loader_hashes=encoder.metadata['loader_source_sha256'],imported_at=now(),importer_sha256=sha256(__file__),
            reason='Exact requested text rows extracted without re-encoding or numeric conversion. loader_hashes above identify the current cache reader configuration, not the original encoder invocation.')))
    ActionEncoder(cache,batch)


def prepare(scene_path, plan_path, output, reuse_baseline=False):
    source=read(scene_path);scene=source.get('scene',source);plan=read(plan_path)
    batch=requests(scene,plan)
    skin=dict(np.load(ASSET,allow_pickle=False));source_evaluation=evaluate(scene,skin)
    from audit_scene_orientation import audit
    orientation=audit(scene,skin)
    if any(not c['all_requested_frames_within_tolerance'] for c in source_evaluation['contacts']):
        raise ValueError('Fit source poses to the authored scene contacts before using them as generation guides')
    if any(c['frames_over_tolerance'] or c.get('tangent_frames_over_tolerance',0) for c in orientation['contacts']):
        raise ValueError('Fit source hand orientation to the scene before using it as a generation guide')
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False)
    save(out/'authored-scene.json',scene);save(out/'actor-plan.json',plan);save(out/'request.json',batch)
    save(out/'source-contact-evaluation.json',source_evaluation);save(out/'source-orientation.json',orientation)
    save(out/'freeze.json',dict(created_at=now(),scene_sha256=sha256(out/'authored-scene.json'),plan_sha256=sha256(out/'actor-plan.json'),
        request_sha256=request_digest(batch),compiler_sha256=sha256(__file__),actor_order=list(plan),
        source_file=str(Path(scene_path).resolve()),source_file_sha256=sha256(scene_path),
        scope='Fitted native actor poses used as sparse generation conditions. Independent actor sampling with fixed authored placement/clock; no object/partner awareness, anatomy approval or collision solve. All source and output defects remain reportable.'))
    snapshot=out/'source-snapshot';snapshot.mkdir()
    for name in ['scene_generation.py','generation_constraints.py','generate_actions.py','run_actions.py','audit_generation_guides.py']:
        shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    if reuse_baseline:import_baseline_cache(batch,out/'conditioning')
    print(out,flush=True)


def build(output):
    out=Path(output).resolve();freeze=read(out/'freeze.json');scene=read(out/'authored-scene.json');plan=read(out/'actor-plan.json')
    if sha256(out/'authored-scene.json')!=freeze['scene_sha256'] or sha256(out/'actor-plan.json')!=freeze['plan_sha256']:
        raise ValueError('Authored scene or actor plan changed')
    if request_digest(read(out/'request.json'))!=freeze['request_sha256']:raise ValueError('Generation request changed')
    if read(out/'pipeline.json')['status']!='complete':raise ValueError('Complete generation and exports first')
    if len({len(v['seeds']) for v in plan.values()})!=1:raise ValueError('Each actor needs the same number of seeds for paired scenes')
    skin=dict(np.load(ASSET,allow_pickle=False));manifest=dict(created_at=now(),scenes=[],assets={})
    from audit_scene_orientation import audit
    from run_scene_fit import bundle
    for pair in range(len(next(iter(plan.values()))['seeds'])):
        for mode in ['baseline','guided']:
            candidate=copy.deepcopy(scene);candidate['id']=f'scene-pair-{pair+1}-{mode}';motions={};downloads=[]
            candidate['review_note']='Independent raw checkpoint samples with '+('fitted contact-pose guides.' if mode=='guided' else 'text-only conditioning.')+' Shared authored placement and clock; no joint scene model or collision correction. All candidates unreviewed.'
            candidate.pop('partner_cut_file',None);candidate.pop('partner_cut_sha256',None)
            for i,name in enumerate(freeze['actor_order']):
                seed=plan[name]['seeds'][pair];take=out/'takes'/f'actor-{i}-{mode}-seed-{seed}'
                record=read(take/'generation-record.json')
                if sha256(take/'motion.npz')!=record['npz_sha256']:raise ValueError('Generated actor changed')
                entry=candidate['actors'][name];entry.update(motion=(take/'motion.npz').relative_to(ROOT).as_posix(),
                    preview_glb=(take/'soma.glb').relative_to(out).as_posix(),source_sha256=record['npz_sha256'])
                motions[name]=dict(np.load(take/'motion.npz',allow_pickle=False))
                manifest['assets'][entry['preview_glb']]=dict(sha256=sha256(take/'soma.glb'))
                downloads.append(dict(label=f'Actor {name} · animation ZIP',path=(take/'animation-pack.zip').relative_to(out).as_posix()))
            folder=out/'scenes'/candidate['id'];folder.mkdir(parents=True,exist_ok=False)
            measured=evaluate(candidate,skin);save(folder/'scene.json',bundle(candidate,motions,measured))
            save(folder/'orientation.json',audit(candidate,skin))
            save(folder/'actor-placement.json',{name:entry['transform'] for name,entry in candidate['actors'].items()})
            downloads.append(dict(label='Actor placements',path=(folder/'actor-placement.json').relative_to(out).as_posix()))
            manifest['scenes'].append(dict(id=candidate['id'],label=f'Generated scene pair {pair+1} · {mode}',
                review_note=candidate['review_note'],
                variants=dict(palm=(folder/'scene.json').relative_to(out).as_posix()),
                orientation_file=(folder/'orientation.json').relative_to(out).as_posix(),downloads=downloads))
    manifest['scope']=freeze['scope'];save(out/'manifest.json',manifest)


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('scene');p.add_argument('plan');p.add_argument('output');p.add_argument('--reuse-baseline-cache',action='store_true')
    p=sub.add_parser('build');p.add_argument('output');args=parser.parse_args()
    if args.command=='prepare':prepare(args.scene,args.plan,args.output,args.reuse_baseline_cache)
    else:build(args.output)
