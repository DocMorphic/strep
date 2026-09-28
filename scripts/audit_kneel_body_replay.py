"""Audit unchanged clearance candidates against phases, pose guides and engine import."""
import argparse
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from audit_generation_guides import audit as guide_audit
from compare_kneel_origins import verified
from compare_kneel_timing import pause_measures
from inspect_kneel_phases import inspect
from motion_window_dynamics import measure
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from run_godot_rig_import import run as engine
from strep import ROOT, now, read, save, sha256


def run(plan, raw_audit, study, output):
    if output.exists():
        raise ValueError('Preserve earlier audits')
    protocol = read(plan/'protocol.json')
    audit_protocol = read(plan/'audit-implementation.json')
    for path, digest in audit_protocol['implementation'].items():
        if sha256(ROOT/path) != digest:
            raise ValueError('Prepared auditor dependency changed: '+path)
    raw_completion, raw_rows = verified(raw_audit)
    if sha256(raw_audit/'completion.json') != protocol['source_audit_completion_sha256']:
        raise ValueError('Different source audit')
    if read(study/'pipeline.json')['status'] != 'complete':
        raise ValueError('Require completed clearance replay')
    summary = read(study/'summary.json')
    if summary['config'] != protocol['config'] or summary['mesh_sha256'] != protocol['skin_sha256']:
        raise ValueError('Clearance configuration or skin changed')
    if any(digest != protocol['implementation']['scripts/'+name] for name,digest in summary['implementation_hashes'].items()):
        raise ValueError('Clearance implementation differs from protocol')
    if [r['id'] for r in summary['trials']] != protocol['population'] or [r['id'] for r in raw_rows] != protocol['population']:
        raise ValueError('Incomplete or changed population')
    for path, digest in protocol['implementation'].items():
        if sha256(ROOT/path) != digest:
            raise ValueError('Replay implementation changed')
    output.mkdir(parents=True)
    inputs = {str(path):sha256(path) for path in [plan/'protocol.json',plan/'audit-implementation.json',study/'summary.json',
              study/'pipeline.json',raw_audit/'completion.json']}
    rows, cases = [], []
    save(output/'pipeline.json',dict(status='measuring',at=now()))
    with threadpool_limits(limits=1):
        for trial, raw_row in zip(summary['trials'],raw_rows):
            take = study/'takes'/trial['id']
            for name, digest in trial['hashes'].items():
                path = take/name
                if sha256(path) != digest:
                    raise ValueError('Clearance artifact changed: '+str(path))
                inputs[str(path)] = digest
            source = ROOT/ 'reports' / trial['source_collection'] / 'takes' / trial['source_original_id']
            raw_npz = source/'motion.npz'
            if sha256(raw_npz) != trial['source_sha256'] or sha256(take/'raw/motion.npz') != sha256(raw_npz):
                raise ValueError('Raw copy differs from unchanged source')
            if sha256(source/'generation-record.json') != sha256(take/'generation-record.json'):
                raise ValueError('Copied source generation record differs')
            for path in [raw_npz,source/'generation-record.json']:
                inputs[str(path)]=sha256(path)
            compiled = read(source/'generation-record.json')['constraints']
            for variant, folder in [('raw',take/'raw'),('limb-only',take/'limb'),('body-candidate',take)]:
                name = trial['id']+'-'+variant
                phase = inspect(folder/'motion.npz',output/name/'posture.json')
                with np.load(folder/'motion.npz',allow_pickle=False) as z:
                    motion = dict(z)
                dynamics = measure(motion)
                guides = guide_audit(motion,compiled)
                guides['root_path_kind'] = 'model_smooth_root' if 'smooth_root_pos' in motion else 'edited_pelvis_xz_fallback'
                guides['root_path_comparison_note'] = 'Do not compare smoothed-root error directly with a pelvis-XZ fallback. Joint/hip guide errors are reconstructed from each variant.'
                save(output/name/'guide-audit.json',guides)
                rig = RigAsset.load(folder/'soma.glb')
                sampler = AnimationSampler(rig.document,rig.binary,0)
                depths = []
                for frame in np.arange(0,trial['frames']-.5,.5):
                    vertices = rig.vertices(sampler.sample(float(frame/30)))
                    depths.append(dict(frame=float(frame),depth_m=max(0.,-float(vertices[:,1].min()))))
                save(output/name/'mesh-floor.json',dict(samples=depths,source_sha256=sha256(folder/'soma.glb')))
                floor = max(r['depth_m'] for r in depths)
                if variant=='raw' and abs(floor-raw_row['mesh_floor_max_m'])>1e-9:
                    raise ValueError('Raw mesh diagnostic differs from prior audit')
                rows.append(dict(id=trial['id'],variant=variant,condition=raw_row['condition'],seed=raw_row['seed'],
                    order_proxy=phase['upright_kneel_upright_proxy_present'],starts_upright=phase['sustained_upright_start'],
                    ends_upright=phase['sustained_upright_end'],pause=pause_measures(phase,motion),dynamics=dynamics,
                    guides=guides,floor_max_m=floor,body_correction=trial['body_correction'] if variant=='body-candidate' else None,
                    original_method_flags=trial['flags'] if variant=='body-candidate' else trial['limb_trial']['flags'] if variant=='limb-only' else trial['raw_flags'],
                    native_sha256=sha256(folder/'motion.npz'),glb_sha256=sha256(folder/'soma.glb'),
                    details={n:sha256(output/name/n) for n in ['posture.json','guide-audit.json','mesh-floor.json']},
                    human_review=None,quality_approved=False))
                if variant!='raw':
                    cases.append(dict(id=name,path=str((folder/'soma.glb').resolve()),sha256=sha256(folder/'soma.glb'),
                                      fps=30,frames=trial['frames'],sample_by_time=True))
                save(output/'results.json',dict(rows=rows))
    save(output/'manifest.json',dict(cases=cases))
    save(output/'pipeline.json',dict(status='engine',at=now()))
    engine(output,output/'engine')
    proof=read(output/'engine/verification.json')
    if [(c['id'],c['frames'],c['source_sha256']) for c in proof['checks']] != [(c['id'],c['frames'],c['sha256']) for c in cases]:
        raise ValueError('Engine evidence missing or different')
    for path,digest in inputs.items():
        if sha256(path)!=digest:
            raise ValueError('Input changed during audit')
    save(output/'completion.json',dict(at=now(),inputs=inputs,results_sha256=sha256(output/'results.json'),
        engine_sha256=sha256(output/'engine/verification.json'),engine_actor_frames=sum(c['frames'] for c in cases),
        auditor_sha256=sha256(__file__),quality_approved=False,human_review=None,
        scope='Eight development sources, each raw/limb/body. Sixteen new exports checked in Godot; raw files already verified by source audit. Fixed phase rules, full mesh half-frame samples and existing method flags; no support, action or realism approval.'))
    save(output/'pipeline.json',dict(status='complete',at=now()))
    print(dict(variants=len(rows),engine_actor_frames=sum(c['frames'] for c in cases)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['plan','raw_audit','study','output']:
        p.add_argument(name,type=Path)
    a=p.parse_args()
    run(a.plan.resolve(),a.raw_audit.resolve(),a.study.resolve(),a.output.resolve())
