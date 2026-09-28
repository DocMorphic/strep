"""Independently decode prepared-trajectory exports, including every contact interval."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from run_prepared_contact_trajectory import load_plan
from audit_knee_hold_contract import interval_metrics
from audit_knee_window_bounds import measure
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_loop import encode
from strep import ROOT, now, read, save, sha256


def run(plan,study,output):
    if output.exists():raise ValueError('Preserve earlier decoded audits')
    if read(study/'pipeline.json')['status']!='complete':raise ValueError('Require finished fit')
    planned,spec,prepared,_,_,frames=load_plan(plan)
    protocol=read(study/'protocol.json');result=read(study/'result.json')
    for p,digest in protocol['implementation'].items():
        if sha256(ROOT/p)!=digest:raise ValueError('Fitting implementation changed: '+p)
    if (protocol['plan_protocol_sha256']!=sha256(plan/'protocol.json')
        or protocol['prepared_sha256']!=sha256(plan/'prepared.npz')
        or protocol['spec_sha256']!=sha256(plan/'spec.json')
        or sha256(study/'spec.json')!=sha256(plan/'spec.json')):
        raise ValueError('Fit differs from prepared contract')
    for filename,key in [('candidate.glb','candidate_sha256'),('fit.npz','fit_sha256')]:
        if sha256(study/filename)!=result[key]:raise ValueError('Candidate changed')
    with np.load(study/'fit.npz',allow_pickle=False) as z:fit=dict(z)
    for name in prepared:np.testing.assert_array_equal(fit[name],prepared[name])
    outside=prepared['weights']==0
    np.testing.assert_array_equal(fit['world'][outside],prepared['body'][outside])
    proof=read(study/'engine/verification.json')['checks']
    expected=[(planned['case'],spec['frames'],result['candidate_sha256'])]
    if [(r['id'],r['frames'],r['source_sha256']) for r in proof]!=expected:
        raise ValueError('Missing complete matching engine evidence')
    rig=RigAsset.load(study/'candidate.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
    output.mkdir(parents=True);floor=[];samples=[[] for c in spec['contacts']]
    # Re-encode the hash-bound body transforms solely for a matching interpolated
    # numerical reference. This is not a new generation or an engine-approved clip.
    animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}
    _,reference_roundtrip=encode(rig,prepared['body'],animated,spec['root_node'],output/'reference.glb','Audit body reference')
    reference_rig=RigAsset.load(output/'reference.glb')
    reference_sampler=AnimationSampler(reference_rig.document,reference_rig.binary,0)
    tracks={name:dict(before=[],after=[]) for name in spec['patches']};track_frames=[]
    first=max(0,int(frames.min())-2);last=min(spec['frames']-1,int(frames.max())+2)
    with threadpool_limits(limits=1):
        world=np.array([sampler.sample(f/spec['fps']) for f in range(spec['frames'])])
        for frame in np.arange(0,spec['frames']-1+.001,.125):
            points=rig.vertices(sampler.sample(float(frame/spec['fps'])))
            floor.append(dict(frame=float(frame),depth_m=max(0.,-float(points[:,1].min()))))
            if first<=frame<=last:
                baseline=reference_rig.vertices(reference_sampler.sample(float(frame/spec['fps'])))
                track_frames.append(float(frame))
                for name,patch in spec['patches'].items():
                    tracks[name]['before'].append(baseline[patch['vertices']].mean(0).tolist())
                    tracks[name]['after'].append(points[patch['vertices']].mean(0).tolist())
            for index,c in enumerate(spec['contacts']):
                if c['start_frame']<=frame<c['end_frame_exclusive']:
                    center=points[spec['patches'][c['patch']]['vertices']].mean(0)
                    samples[index].append(dict(frame=float(frame),position_m=center.tolist(),
                        error_m=float(np.linalg.norm(center-c['target_position_m']))))
    contacts=[]
    for c,rows in zip(spec['contacts'],samples):
        if len(rows)<2:raise ValueError('This interval audit requires two or more contact samples')
        stats=interval_metrics([r['position_m'] for r in rows],c['target_position_m'],spec['fps']*8,spec['screen']['contact_error_m'])
        contacts.append(dict(patch=c['patch'],start_frame=c['start_frame'],end_frame_exclusive=c['end_frame_exclusive'],
            **stats,worst_error_frame=max(rows,key=lambda r:r['error_m'])['frame']))
    before=measure(prepared['limb'],prepared['body'],rig.parents,spec,prepared['weights'])
    after=measure(prepared['limb'],world,rig.parents,spec,prepared['weights'])
    steps=after['root_step_violations']+[v for rows in after['joint_step_violations'].values() for v in rows]
    peak=max(floor,key=lambda r:r['depth_m'])
    speed_peaks={}
    for name,track in tracks.items():
        speed_peaks[name]={}
        for version in ['before','after']:
            speed=np.linalg.norm(np.diff(track[version],axis=0),axis=1)*spec['fps']*8
            index=int(np.argmax(speed))
            speed_peaks[name][version]=dict(peak_m_s=float(speed[index]),arrival_frame=track_frames[index+1])
    pose_pass=not after['joint_pose_violations'] and after['root_horizontal_max_m']<=spec['limits']['root_horizontal_m']+1e-6 and after['root_vertical_max_m']<=spec['limits']['root_vertical_m']+1e-6
    save(output/'floor.json',dict(samples=floor));save(output/'contact-tracks.json',dict(contacts=spec['contacts'],samples=samples))
    save(output/'window-tracks.json',dict(frames=track_frames,tracks=tracks))
    inputs=[plan/'protocol.json',plan/'prepared.npz',plan/'spec.json',study/'protocol.json',study/'result.json',
            study/'candidate.glb',study/'fit.npz',study/'engine/verification.json']
    summary=dict(at=now(),case=planned['case'],inputs={str(p):sha256(p) for p in inputs},
        auditor_sha256=sha256(Path(__file__)),details={n:sha256(output/n) for n in ['floor.json','contact-tracks.json','window-tracks.json','reference.glb']},
        reference_roundtrip=reference_roundtrip,window_speed_peaks=speed_peaks,
        samples=len(floor),floor_worst=peak,dense_floor_passed=peak['depth_m']<=spec['screen']['floor_depth_m'],
        contacts=contacts,all_interval_contact_samples_passed=all(c['all_contact_samples_passed'] for c in contacts),
        before_bounds=before,after_bounds=after,candidate_pose_bounds_passed=bool(pose_pass),
        window_step_bounds_passed=not any(v['inside_edit_window'] for v in steps),global_step_bounds_passed=not steps,
        outside_matrix_max_error=float(abs(world[outside]-prepared['body'][outside]).max()) if outside.any() else None,
        engine_actor_frames=spec['frames'],quality_approved=False,human_review=None,
        scope='All keys and eighth-frame samples across the exported clip; every declared contact interval is sampled. Finite sampling is not continuous collision proof or a naturalness/force-balance rating. Speeds are diagnostics, not an approved realism threshold.')
    save(output/'verification.json',summary)
    print({k:summary[k] for k in ['floor_worst','dense_floor_passed','all_interval_contact_samples_passed','candidate_pose_bounds_passed','window_step_bounds_passed','global_step_bounds_passed']})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['plan','study','output']:parser.add_argument(n,type=Path)
    a=parser.parse_args();run(a.plan.resolve(),a.study.resolve(),a.output.resolve())
