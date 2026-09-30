"""Attribute exported motion changes across every seed/actor in a staged study.

Reuses only hash-bound historical geometry/engine evidence. New measurements
are joint motion at quarter frames; they do not revalidate mesh collisions.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from audit_scene_joint_rates import compare_rates


METHODS=('raw','body_fit','body_fit_posture')
EDGES=(('raw','body_fit'),('body_fit','body_fit_posture'),('raw','body_fit_posture'))


def validate_population(manifest,request,engine):
    seeds=request['seeds']
    if not seeds or len(set(seeds))!=len(seeds) or request['methods']!=list(METHODS):
        raise ValueError('Distinct seeds and complete ordered correction stages required')
    expected={f'{m}-seed-{seed}' for seed in seeds for m in METHODS}
    scenes=manifest['scenes']
    if len(scenes)!=len(expected) or {s['id'] for s in scenes}!=expected:
        raise ValueError('Missing or duplicate stage/seed scene')
    keys=[(r['scene_id'],r['actor']) for r in engine]
    if len(keys)!=2*len(expected) or set(keys)!={(s,a) for s in expected for a in ['A','B']}:
        raise ValueError('Missing or duplicate engine actor evidence')
    if any(r['frames']!=150 for r in engine):
        raise ValueError('Unexpected engine frame count')
    return expected


def phase_windows(frame_count,event,posture):
    a,b,c,d=posture
    if frame_count!=150 or not 0<a<b==c==event<d<frame_count-1:
        raise ValueError('This staged audit requires the declared single-event posture clock')
    return dict(whole_clip=[0,frame_count-1],before=[0,a],approach=[a,event],event=[event-2,event+2],
                release=[event,d],after=[d,frame_count-1],entry_join=[a-2,a+2],exit_join=[d-2,d+2])


def run(study,geometry_summary,output):
    study,geometry_summary,output=[Path(p).resolve() for p in (study,geometry_summary,output)]
    if output.exists():raise ValueError('Preserve earlier stage audit')
    request=read(study/'request.json');manifest=read(study/'manifest.json')
    engine=read(study/'engine-audit/verification.json')['checks'];summary=read(geometry_summary)
    expected=validate_population(manifest,request,engine)
    verified=summary['verified_files']
    for file,digest in verified.items():
        if sha256(file)!=digest:raise ValueError('Historical evidence changed: '+file)
    for path in [study/'request.json',study/'manifest.json',study/'engine-audit/verification.json']:
        if verified.get(str(path))!=sha256(path):raise ValueError('Summary does not bind this population')
    if len(summary['rows'])!=len(expected) or {r['id'] for r in summary['rows']}!=expected:
        raise ValueError('Incomplete historical geometry population')
    for name,digest in request['implementation'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Original method snapshot changed')
    for file,row in manifest['assets'].items():
        if sha256(study/file)!=row['sha256']:raise ValueError('Study asset changed')
    output.mkdir(parents=True);snapshot=output/'implementation';snapshot.mkdir()
    methods=['audit_paired_stage_rates.py','audit_scene_joint_rates.py','rig_clip_import.py','gltf_tools.py','rig_asset.py','strep.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    inputs=dict(verified);inputs[str(geometry_summary)]=sha256(geometry_summary)
    protocol=dict(at=now(),study=study.relative_to(ROOT).as_posix(),geometry_summary=geometry_summary.relative_to(ROOT).as_posix(),
        seeds=request['seeds'],methods=list(METHODS),comparisons=[list(e) for e in EDGES],subdivisions=4,fps=30,frames=150,
        inputs=inputs,implementation={n:sha256(snapshot/n) for n in methods},quality_approved=False,
        scope='All retained development seeds and both actors, 597 decoded samples per clip. Per-joint stage/phase rate diagnostics; positive changes are not automatically quality failures. Reuse only matching prior geometry/engine evidence, without claiming fresh dense surface tests or new generation.')
    save(output/'protocol.json',protocol);rows=[];bindings=[]
    scene_index={s['id']:s for s in manifest['scenes']};engine_index={(r['scene_id'],r['actor']):r for r in engine}
    for seed in request['seeds']:
        for actor in ['A','B']:
            tracks={};reference_transform=None;reference_contact=None;names=None
            for method in METHODS:
                sid=f'{method}-seed-{seed}';entry=scene_index[sid];scene_path=study/entry['variants']['palm'];scene=read(scene_path)['scene']
                if scene['id']!=sid or set(scene['actors'])!={'A','B'} or scene['frame_count']!=150 or scene['fps']!=30 or len(scene['contacts'])!=1:
                    raise ValueError('Scene population or clock changed')
                record=scene['actors'][actor];transform=record['transform'];contact=scene['contacts'][0]
                if reference_transform is not None and (transform!=reference_transform or contact!=reference_contact):raise ValueError('Stage placement or authored contact changed')
                reference_transform,reference_contact=transform,contact
                if contact['start_frame']!=contact['end_frame']:raise ValueError('Point event required for this stage population')
                windows=phase_windows(150,contact['start_frame'],request['posture_frames'])
                path=study/record['preview_glb'];motion=ROOT/record['motion'];proof=engine_index[(sid,actor)]
                if verified.get(str(path))!=sha256(path) or verified.get(str(scene_path))!=sha256(scene_path) or sha256(motion)!=record['source_sha256']:
                    raise ValueError('Stage source is not bound to historical proof')
                if proof['glb_sha256']!=sha256(path) or proof['source_sha256']!=sha256(motion):raise ValueError('Engine clip identity changed')
                doc,binary=read_glb(path);sampler=AnimationSampler(doc,binary,0);joints=doc['skins'][0]['joints']
                current_names=[doc['nodes'][j]['name'] for j in joints]
                if len(joints)!=77 or names is not None and current_names!=names or abs(sampler.duration-149/30)>1e-5:raise ValueError('Clip skeleton or duration changed')
                names=current_names;world=Rotation.from_quat(transform['rotation_xyzw']).as_matrix();shift=np.array(transform['translation_m'])
                tracks[method]=np.array([sampler.sample(t/120)[joints,:3,3]@world.T+shift for t in range(597)])
                bindings.append(dict(seed=seed,actor=actor,method=method,glb_sha256=sha256(path),scene_sha256=sha256(scene_path),samples=597))
            np.savez(output/f'seed-{seed}-{actor}-positions.npz',**tracks)
            comparisons=[]
            for before,after in EDGES:
                rates=compare_rates(tracks[before],tracks[after],names,windows)
                file=output/f'seed-{seed}-{actor}-{before}-to-{after}.json'
                save(file,dict(seed=seed,actor=actor,before=before,after=after,rates=rates,quality_approved=False))
                compact={metric:[{k:v for k,v in w.items() if k!='joints'} for w in values['windows']] for metric,values in rates.items()}
                comparisons.append(dict(before=before,after=after,file=file.name,sha256=sha256(file),summary=compact))
            rows.append(dict(seed=seed,actor=actor,positions_sha256=sha256(output/f'seed-{seed}-{actor}-positions.npz'),comparisons=comparisons))
            save(output/'progress.json',dict(status='running',completed_actors=len(rows),total_actors=2*len(request['seeds'])));print(dict(seed=seed,actor=actor,completed=len(rows)),flush=True)
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Evidence changed during audit')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Auditor changed during measurement')
    save(output/'result.json',dict(at=now(),status='complete',protocol_sha256=sha256(output/'protocol.json'),actors=len(rows),clips=len(bindings),
        decoded_actor_samples=sum(r['samples'] for r in bindings),bindings=bindings,rows=rows,historical_geometry=summary['rows'],
        historical_engine_actor_frames=summary['engine_actor_frames'],new_engine_actor_frames=0,quality_approved=False))
    save(output/'progress.json',dict(status='complete',completed_actors=len(rows)));print('Stage motion audit complete',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('geometry_summary',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.study,args.geometry_summary,args.output)
