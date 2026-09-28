"""Audit every paired kneel-start trial, retaining semantic and physical failures."""
import argparse
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from action_requests import request_digest, validate_batch
from inspect_kneel_phases import inspect, RULES
from motion_window_dynamics import measure as dynamics
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from run_godot_rig_import import run as engine
from strep import ROOT, now, read, save, sha256


def condition_bindings(protocol, batch, snapshot):
    """Bind labels and guides explicitly, including comparisons with two guided arms."""
    ids = [r['id'] for r in batch['requests']]
    labels = protocol.get('condition_by_request', {'kneel-baseline': 'baseline', 'kneel-upright-start': 'upright-start'})
    if (len(ids) != 2 or set(labels) != set(ids) or len(set(labels.values())) != 2
            or [labels[i] for i in ids] != protocol['conditions']):
        raise ValueError('Explicit paired condition labels do not match requests')
    if any(r['seeds'] != protocol['seed_pairs'] for r in batch['requests']):
        raise ValueError('Paired seed population differs from plan')
    if 'by_request' in snapshot:
        if set(snapshot) != {'by_request'} or set(snapshot['by_request']) != set(ids):
            raise ValueError('Prepared guide map does not match requests')
        guides = {i: snapshot['by_request'][i]['constraints'] for i in ids}
    else:
        if set(ids) != {'kneel-baseline', 'kneel-upright-start'}:
            raise ValueError('Named conditions require an explicit prepared guide map')
        guides = {'kneel-baseline': [], 'kneel-upright-start': snapshot['constraints']}
    if any(not isinstance(v, list) for v in guides.values()):
        raise ValueError('Prepared constraints must be lists')
    return labels, guides


def run(plan, job, output):
    if output.exists():
        raise ValueError('Preserve earlier audits')
    protocol = read(plan / 'protocol.json')
    evaluation = read(plan / 'evaluation-protocol.json')
    if (evaluation['study_protocol_sha256'] != sha256(plan / 'protocol.json')
            or evaluation['rules'] != RULES):
        raise ValueError('Evaluation protocol changed')
    for path, digest in evaluation['implementation'].items():
        if sha256(ROOT / path) != digest:
            raise ValueError('Frozen diagnostic changed: ' + path)
    request = ROOT / protocol['request']
    if sha256(request) != protocol['request_sha256'] or sha256(protocol['source_pose']) != protocol['source_pose_sha256']:
        raise ValueError('Planned request or source pose changed')
    batch = validate_batch(read(request))
    if request_digest(read(job / 'request.json')) != request_digest(batch):
        raise ValueError('Generation request differs from plan')
    if read(job / 'pipeline.json')['status'] != 'complete':
        raise ValueError('Require completed generation and export, including failures')
    summary = read(job / 'summary.json')
    expected = [(r['id'], s) for r in batch['requests'] for s in r['seeds']]
    if [(t['request_id'], t['seed']) for t in summary['trials']] != expected or len(expected) != protocol['clips']:
        raise ValueError('Incomplete or reordered paired population')
    if summary['exporter_sha256'] != protocol['implementation']['scripts/export_actions.py']:
        raise ValueError('Exporter differs from prepared implementation')
    compiled_path = plan / 'compiled-guides.json'
    if sha256(compiled_path) != protocol['compiled_guides_sha256']:
        raise ValueError('Prepared guides changed')
    condition_labels, prepared_guides = condition_bindings(protocol, batch, read(compiled_path))
    encoder_path = job / 'conditioning/manifest.json'
    encoder_record = read(encoder_path)
    if encoder_record['status'] != 'complete' or encoder_record['request_sha256'] != request_digest(batch):
        raise ValueError('Incomplete or mismatched conditioning')
    output.mkdir(parents=True)
    inputs = {str(p): sha256(p) for p in [plan / 'protocol.json', plan / 'evaluation-protocol.json',
               request, job / 'request.json', job / 'summary.json', job / 'pipeline.json', compiled_path, encoder_path]}
    for entry in encoder_record['entries'].values():
        path = job / 'conditioning' / entry['file']
        if sha256(path) != entry['sha256']:
            raise ValueError('Conditioning feature changed')
        inputs[str(path)] = entry['sha256']
    rows, cases, identities = [], [], []
    save(output / 'pipeline.json', dict(status='measuring', at=now()))
    with threadpool_limits(limits=1):
        for trial in summary['trials']:
            take = job / 'takes' / trial['id']
            for filename, digest in trial['hashes'].items():
                if sha256(take / filename) != digest:
                    raise ValueError('Exported asset changed: ' + str(take / filename))
                inputs[str(take / filename)] = digest
            record = read(take / 'generation-record.json')
            if (record['request_sha256'] != request_digest(batch) or record['seed'] != trial['seed']
                    or record['request'] != trial['request'] or record['npz_sha256'] != trial['hashes']['motion.npz']
                    or record['encoder'] != encoder_record
                    or record['generation_script_sha256'] != protocol['implementation']['scripts/generate_actions.py']):
                raise ValueError('Generation provenance differs from exported trial')
            identities.append({k: record[k] for k in ['kimodo_commit', 'checkpoint_revision', 'checkpoint_sha256',
                               'diffusion_steps', 'cfg_type', 'cfg_weight', 'postprocessing']})
            phase = inspect(take / 'motion.npz', output / trial['id'] / 'posture.json')
            with np.load(take / 'motion.npz', allow_pickle=False) as archive:
                motion_dynamics = dynamics(dict(archive))
            save(output / trial['id'] / 'dynamics.json', motion_dynamics)
            rig = RigAsset.load(take / 'soma.glb')
            sampler = AnimationSampler(rig.document, rig.binary, 0)
            floor = []
            for frame in np.arange(0, trial['frames'] - .5, .5):
                vertices = rig.vertices(sampler.sample(float(frame / 30)))
                floor.append(dict(frame=float(frame), depth_m=float(max(0., -vertices[:, 1].min()))))
            save(output / trial['id'] / 'mesh-floor.json', dict(source_sha256=trial['hashes']['soma.glb'],
                 floor_y_m=0., samples=floor, scope='Whole/half-frame decoded mesh samples, not continuous collision.'))
            guide = read(take / 'constraint-audit.json') if record['constraints'] else None
            if record['constraints'] != prepared_guides[trial['request_id']]:
                raise ValueError('Missing or unexpected guide')
            rows.append(dict(id=trial['id'], seed=trial['seed'], condition=condition_labels[trial['request_id']],
                 sustained_upright_start=phase['sustained_upright_start'], sustained_upright_end=phase['sustained_upright_end'],
                 upright_kneel_upright_proxy_present=phase['upright_kneel_upright_proxy_present'],
                 standing_proxy_intervals=phase['standing_proxy_intervals'], kneeling_proxy_intervals=phase['kneeling_proxy_intervals'],
                 mesh_floor_max_m=max(r['depth_m'] for r in floor), mesh_samples=len(floor),
                 foot_speed_proxies=trial['metrics'], generation_flags=trial['flags'], guide_audit=guide,
                 posture_sha256=sha256(output / trial['id'] / 'posture.json'),
                 mesh_floor_sha256=sha256(output / trial['id'] / 'mesh-floor.json'),
                 dynamics=motion_dynamics, dynamics_sha256=sha256(output / trial['id'] / 'dynamics.json'),
                 action_correctness=None, human_review=None, quality_approved=False))
            cases.append(dict(id=trial['id'], path=str(take / 'soma.glb'), sha256=trial['hashes']['soma.glb'],
                              fps=30, frames=trial['frames'], sample_by_time=True))
            save(output / 'results.json', dict(rows=rows))
    if any(identity != identities[0] for identity in identities[1:]):
        raise ValueError('Paired clips used different checkpoint or sampling settings')
    save(output / 'manifest.json', dict(cases=cases))
    save(output / 'pipeline.json', dict(status='engine', at=now()))
    engine(output, output / 'engine')
    proof = read(output / 'engine/verification.json')
    if [(r['id'], r['frames'], r['source_sha256']) for r in proof['checks']] != [
            (r['id'], r['frames'], r['sha256']) for r in cases]:
        raise ValueError('Incomplete engine evidence')
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Source changed during audit')
    pairs = []
    for seed in protocol['seed_pairs']:
        group = {r['condition']: r for r in rows if r['seed'] == seed}
        control_label, variant_label = protocol['conditions']
        base, guided = group[control_label], group[variant_label]
        pairs.append(dict(seed=seed, control_condition=control_label, variant_condition=variant_label,
                          control_order_proxy=base['upright_kneel_upright_proxy_present'],
                          variant_order_proxy=guided['upright_kneel_upright_proxy_present'],
                          mesh_floor_change_m=guided['mesh_floor_max_m'] - base['mesh_floor_max_m']))
    save(output / 'completion.json', dict(at=now(), inputs=inputs, model_and_sampling=identities[0],
         results_sha256=sha256(output / 'results.json'), engine_sha256=sha256(output / 'engine/verification.json'),
         auditor_sha256=sha256(Path(__file__)), paired_comparisons=pairs,
         engine_actor_frames=sum(c['frames'] for c in cases), quality_approved=False,
         scope=f'{len(rows)} native development clips. Fixed posture proxies are not complete action correctness; '
               'no retargeting, collision-free guarantee, independent human rating or cleanup time is established.'))
    save(output / 'pipeline.json', dict(status='complete', at=now()))
    print(dict(clips=len(rows), engine_actor_frames=sum(c['frames'] for c in cases), pairs=pairs))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'job', 'output'):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    run(a.plan.resolve(), a.job.resolve(), a.output.resolve())
