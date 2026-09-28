"""Frozen shared-pose conditioning comparison; raw generation stays uncorrected."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT, read, save, sha256, now


SOURCES = ['paired_guide_study.py', 'run_actions.py', 'action_requests.py',
           'generation_constraints.py', 'generate_actions.py', 'export_actions.py',
           'action_encoder.py', 'reuse_action_conditioning.py', 'audit_generation_guides.py',
           'build_soma_preview.py', 'gltf_tools.py', 'inspect_motion.py']


def prepare(output):
    from action_requests import validate_batch
    from generation_constraints import compile_guides
    from reuse_action_conditioning import reuse
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError('Use a new study folder inside the project')
    prior = ROOT / 'reports/breadth-partners-v2'
    entries = [e for e in read(prior / 'protocol.json')['scenes']
               if e['case'] == 'partner_interaction-left-high-five']
    if len(entries) != 5 or len({e['seed'] for e in entries}) != 5:
        raise ValueError('Require the complete five-seed baseline population')
    guide = ROOT / 'reports/paired-palm-region-export-v5'
    proof = read(guide / 'completion-verification.json')
    for relative, digest in proof['files'].items():
        if sha256(guide / relative) != digest:
            raise ValueError('Changed guide evidence: ' + relative)
    scene = read(guide / 'candidate-scene.json')['scene']
    output.mkdir(); (output / 'guides').mkdir(); (output / 'implementation').mkdir()
    for name in SOURCES:
        shutil.copyfile(ROOT / 'scripts' / name, output / 'implementation' / name)
    sources = {}
    for actor in ['A', 'B']:
        source = ROOT / scene['actors'][actor]['motion']
        if sha256(source) != scene['actors'][actor]['source_sha256']:
            raise ValueError('Guide motion changed')
        dest = output / 'guides' / (actor + '.npz'); shutil.copyfile(source, dest)
        sources[actor] = dict(path=dest.relative_to(ROOT).as_posix(), sha256=sha256(dest))
    requests = []; pairs = []
    for method in ['hand', 'body']:
        for entry in entries:
            pair = dict(id=f'{method}-seed-{entry["seed"]}', method=method,
                        seed=entry['seed'], baseline_id=entry['id'], requests={})
            for actor in ['A', 'B']:
                original = entry['sources'][actor]
                for kind in ['motion', 'glb']:
                    if sha256(original['original_' + kind]) != original['original_' + kind + '_sha256']:
                        raise ValueError('Baseline source changed')
                identifier = f'guide-{method}-{actor.lower()}-{entry["seed"]}'
                common = dict(motion=sources[actor]['path'], sha256=sources[actor]['sha256'])
                constraints = [dict(type='fullbody', source_frames=[0, 149], frame_indices=[0, 149], **common),
                               dict(type='left-hand' if method == 'hand' else 'fullbody',
                                    source_frames=[75], frame_indices=[75], **common)]
                request = dict(id=identifier, label=f'Shared {method} guide / actor {actor}',
                               segments=[dict(prompt=original['prompt'], duration_s=5)],
                               seeds=[entry['seed']], generation_constraints=constraints,
                               scene_requirements=['Two actors share a high-five target at frame 75; independently sampled conditioned actors.'])
                # FK/hash validation precedes model loading and protocol freezing.
                compiled, provenance = compile_guides(request)
                save(output / 'guides' / (identifier + '.json'), dict(compiled=compiled, provenance=provenance))
                requests.append(request); pair['requests'][actor] = identifier
            pairs.append(pair)
    batch = validate_batch(dict(schema_version=1, requests=requests)); save(output / 'request.json', batch)
    save(output / 'guide-scene.json', dict(scene=scene))
    save(output / 'baseline-population.json', dict(entries=entries, source_protocol_sha256=sha256(prior / 'protocol.json')))
    shutil.copyfile(ROOT / 'vendor/kimodo/LICENSE', output / 'SOMA-preview-LICENSE.txt')
    protocol = dict(at=now(), planned_pairs=10, planned_actor_clips=20, pairs=pairs,
                    guide_export=str(guide), guide_proof_sha256=sha256(guide / 'completion-verification.json'),
                    request_sha256=sha256(output / 'request.json'), guide_scene_sha256=sha256(output / 'guide-scene.json'),
                    baseline_population_sha256=sha256(output / 'baseline-population.json'), guides=sources,
                    implementation={name:sha256(output / 'implementation' / name) for name in SOURCES},
                    guide_frames=[0,75,149], event_frame=75, audit_window_frames=[60,90], audit_substeps=2,
                    unchanged_generation=dict(diffusion_steps=100,cfg_weight=[2,2],postprocessing=False),
                    contact_screens=dict(point_distance_m=.03,opposing_normals_degrees=15,penetration_m=.005),
                    scope='Development comparison on five existing seeds. A common authored pose fixture from seed1301 is used for every seed. Both methods constrain full-body start/end; event varies between left-hand and full-body channels. Frozen scene placement from guide fixture, no per-result realignment. SOMA30 constraints do not constrain fingers or skin. Guide event itself fails distributed-region contact; it is not ground truth. No training, joint two-person model, independent test set or quality approval.')
    save(output / 'protocol.json', protocol); save(output / 'freeze.json', dict(protocol_sha256=sha256(output / 'protocol.json')))
    job = output / 'generation'; job.mkdir()
    reused = reuse(batch, job / 'conditioning')
    save(output / 'pipeline.json', dict(status='prepared', exact_conditioning_reused=reused, quality_approved=False))
    return protocol


def validate(output):
    protocol = read(output / 'protocol.json')
    if sha256(output / 'protocol.json') != read(output / 'freeze.json')['protocol_sha256']:
        raise ValueError('Protocol changed')
    for name, key in [('request.json','request_sha256'),('guide-scene.json','guide_scene_sha256'),('baseline-population.json','baseline_population_sha256')]:
        if sha256(output / name) != protocol[key]: raise ValueError('Frozen input changed: ' + name)
    for name, digest in protocol['implementation'].items():
        if sha256(ROOT / 'scripts' / name) != digest or sha256(output / 'implementation' / name) != digest:
            raise ValueError('Frozen implementation changed: ' + name)
    for entry in protocol['guides'].values():
        if sha256(ROOT / entry['path']) != entry['sha256']: raise ValueError('Guide changed')
    return protocol


def run(output):
    from run_actions import main
    output = Path(output).resolve(); validate(output)
    if read(output / 'pipeline.json')['status'] != 'prepared': raise ValueError('Inspect existing attempt; never restart blindly')
    owner = psutil.Process()
    save(output / 'runner.json', dict(pid=os.getpid(), created=owner.create_time(), started_at=now()))
    save(output / 'pipeline.json', dict(status='generation', quality_approved=False))
    try:
        main(output / 'request.json', output / 'generation'); protocol = validate(output)
        trials = read(output / 'generation/summary.json')['trials']
        expected = {(r['id'],r['seeds'][0]) for r in read(output / 'request.json')['requests']}
        if {(t['request_id'],t['seed']) for t in trials} != expected or len(trials) != protocol['planned_actor_clips']:
            raise ValueError('Incomplete generation population')
        for take in trials:
            for name,digest in take['hashes'].items():
                if sha256(output / 'generation/takes' / take['id'] / name) != digest: raise ValueError('Output changed')
        save(output / 'pipeline.json',dict(status='generated_pending_scene_audit',finished_at=now(),actor_clips=len(trials),quality_approved=False))
    except BaseException as exc:
        save(output / 'pipeline.json',dict(status='failed',error=str(exc),traceback=traceback.format_exc(),quality_approved=False)); raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run']);parser.add_argument('output',type=Path)
    args=parser.parse_args(); print(prepare(args.output)['planned_actor_clips']) if args.command=='prepare' else run(args.output)
