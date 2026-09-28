"""Bind a sustained-contact pilot to verified source motion before fitting."""
import argparse
import copy
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from analytic_patch_contact import AnalyticPatchFitter
from compare_reference_temporal_knee import verified_audit
from reference_temporal_patch_frame import evaluate
from temporal_patch_frame import coordinate_bounds, pose_budget_pair
from rig_asset import RigAsset
from rig_transition import localize
from strep import ROOT, now, read, save, sha256


def run(output):
    if output.exists():raise ValueError('Preserve earlier prepared pilots')
    study=ROOT/'reports/knee-contact-reference-v1'
    audited=ROOT/'reports/knee-contact-reference-audit-v1'
    hold=ROOT/'reports/knee-hold-contract-audit-v1'
    verified_audit(audited)
    hold_record=read(hold/'verification.json')
    if sha256(hold/'proposed-spec.json')!=hold_record['proposed_spec_sha256']:
        raise ValueError('Proposed hold contract changed')
    spec=copy.deepcopy(read(hold/'proposed-spec.json'))
    old=read(study/'spec.json')
    for field in ['patches','edit_joints','limits','screen','objective','root_node']:
        if spec[field]!=old[field]:raise ValueError('Unplanned change: '+field)
    if [(c['start_frame'],c['end_frame_exclusive']) for c in spec['contacts']]!=[(60,90),(60,90)]:
        raise ValueError('Expected predeclared knee hold')
    case=read(study/'result.json')['case']
    source_case=next(c for c in read(ROOT/'reports/knee-patch-feasibility-v1/protocol.json')['cases'] if c['id']==case)
    source=Path(source_case['source_glb'])
    if sha256(source)!=source_case['source_glb_sha256']:raise ValueError('Limb source changed')
    rig=RigAsset.load(source)
    spec['glb_sha256']=sha256(source)
    with np.load(study/'fit.npz',allow_pickle=False) as z:data=dict(z)
    frames=np.arange(47,103)
    weights=np.zeros(len(data['body']));weights[frames]=1
    fitter=AnalyticPatchFitter(rig,spec,localize(data['limb'],rig.parents))
    # Warm-start from the verified single-frame candidate; retain body reference.
    initial=data['parameters'].copy();reference=data['reference'].copy()
    if np.max(abs(initial[frames])-coordinate_bounds(fitter))>1e-6:
        raise ValueError('Warm start exceeds coordinate bounds')
    minimum_budget=min(float(pose_budget_pair(fitter,initial[f])[0].min()) for f in frames)
    if minimum_budget < -1e-5:raise ValueError('Warm start exceeds declared pose norms')
    preflight=[]
    with threadpool_limits(limits=1):
        for f in frames:
            neighbors=[initial[f-1],initial[f+1]]
            refs=[reference[f-1],reference[f+1]]
            row=evaluate(fitter,int(f),initial[f],neighbors,reference[f],refs)
            preflight.append(dict(frame=int(f),active_contacts=len(fitter.active[f]),
                objective=row[0],minimum_scaled_constraint=float(row[2].min())))
    # Freeze all inputs; no optimization or candidate export is performed here.
    output.mkdir(parents=True)
    save(output/'spec.json',spec)
    np.savez_compressed(output/'prepared.npz',initial=initial,reference=reference,
        body=data['body'],limb=data['limb'],weights=weights)
    save(output/'preflight.json',dict(rows=preflight,minimum_pose_budget=minimum_budget,
        infeasible_initial_frames=[r['frame'] for r in preflight if r['minimum_scaled_constraint'] < -1e-8]))
    inputs=[source,study/'fit.npz',study/'result.json',audited/'verification.json',
            hold/'verification.json',hold/'proposed-spec.json']
    implementation=['prepare_knee_hold_pilot.py','reference_temporal_patch_frame.py',
        'temporal_patch_frame.py','analytic_patch_contact.py','constrained_patch_pose.py',
        'rig_periodic_contact.py','target_rig_contact.py','rig_clearance_fit.py']
    save(output/'protocol.json',dict(at=now(),status='prepared_not_run',case=case,source_glb=str(source),
        frames=frames.tolist(),hold_frames=dict(start=60,end_exclusive=90),context_frames_per_side=13,
        max_sweeps=4,max_iterations_per_frame=80,
        inputs={str(p):sha256(p) for p in inputs},implementation={f'scripts/{n}':sha256(ROOT/'scripts'/n) for n in implementation},
        prepared_sha256=sha256(output/'prepared.npz'),spec_sha256=sha256(output/'spec.json'),
        contract='Keep the same two knee patch centroids within20mm of their fixed targets for the requested one-second pause. Hard keyframe floor5mm, unchanged pose/edit budgets; explicitly audit between-frame contact and floor, release boundary and unchanged outside motion.',
        scope='First development case only. Fixed material patches are a proposed authoring choice. No fit, convergence, naturalness, force balance or release approval.',quality_approved=False))
    print(dict(prepared_frames=len(frames),contact_frames=sum(bool(fitter.active[f]) for f in frames),
        infeasible_initial_frames=sum(r['minimum_scaled_constraint'] < -1e-8 for r in preflight)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    run(parser.parse_args().output.resolve())
