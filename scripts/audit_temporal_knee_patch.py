"""Decoded dense interpolation and edit-budget audit of the temporal pilot."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from audit_knee_window_bounds import measure
from probe_knee_contact_windows import posture
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from strep import ROOT,now,read,save,sha256


def run(study,output):
    if output.exists():raise ValueError('Preserve earlier audit')
    if read(study/'pipeline.json')['status']!='complete':raise ValueError('Require completed temporal pilot')
    protocol=read(study/'protocol.json');result=read(study/'result.json');spec=read(study/'spec.json')
    for p,d in protocol['implementation'].items():
        if sha256(ROOT/p)!=d:raise ValueError('Frozen pilot implementation changed')
    if sha256(study/'candidate.glb')!=result['candidate_sha256'] or sha256(study/'fit.npz')!=result['fit_sha256']:
        raise ValueError('Pilot output changed')
    proof=read(study/'engine/verification.json')['checks']
    if [(r['id'],r['frames'],r['source_sha256']) for r in proof]!=[(result['case'],180,result['candidate_sha256'])]:
        raise ValueError('Missing all-frame engine evidence')
    with np.load(study/'fit.npz',allow_pickle=False) as z:data=dict(z)
    source=ROOT/'reports/knee-contact-windows-v1'/result['case']
    if sha256(source/'poses.npz')!=protocol['input_pose_sha256'] or sha256(source/'result.json')!=protocol['input_result_sha256']:
        raise ValueError('Window input changed')
    source_record=read(source/'result.json')
    body=ROOT/'reports/kneel-body-clearance-v1/takes'/result['case']/'soma.glb'
    if sha256(body)!=source_record['body_sha256']:raise ValueError('Original body source changed')
    encoded=RigAsset.load(study/'candidate.glb');sampler=AnimationSampler(encoded.document,encoded.binary,0)
    original=RigAsset.load(body);bs=AnimationSampler(original.document,original.binary,0)
    output.mkdir(parents=True);samples=[];tracks={p:dict(before=[],after=[]) for p in spec['patches']}
    first=min(protocol['frames'])-2;last=max(protocol['frames'])+2
    with threadpool_limits(limits=1):
        world=np.array([sampler.sample(f/30) for f in range(180)])
        for f in np.arange(0,179.001,.125):
            points=encoded.vertices(sampler.sample(float(f/30)));before=original.vertices(bs.sample(float(f/30)))
            samples.append(dict(frame=float(f),depth_m=max(0.,-float(points[:,1].min())),before_depth_m=max(0.,-float(before[:,1].min()))))
            if first<=f<=last:
                for name,p in spec['patches'].items():
                    tracks[name]['before'].append(before[p['vertices']].mean(0).tolist());tracks[name]['after'].append(points[p['vertices']].mean(0).tolist())
    before_bounds=measure(data['limb'],data['body'],encoded.parents,spec,data['weights'])
    after_bounds=measure(data['limb'],world,encoded.parents,spec,data['weights'])
    violations=after_bounds['root_step_violations']+[v for values in after_bounds['joint_step_violations'].values() for v in values]
    window_step_failures=[v for v in violations if v['inside_edit_window']]
    center=spec['contacts'][0]['start_frame'];points=encoded.vertices(sampler.sample(center/30))
    errors={c['patch']:float(np.linalg.norm(points[spec['patches'][c['patch']]['vertices']].mean(0)-c['target_position_m'])) for c in spec['contacts']}
    speeds={}
    for name,t in tracks.items():
        a,b=np.array(t['before']),np.array(t['after'])
        speeds[name]=dict(before_peak_m_s=float(np.linalg.norm(np.diff(a,axis=0),axis=1).max()*240),
            after_peak_m_s=float(np.linalg.norm(np.diff(b,axis=0),axis=1).max()*240),
            added_peak_m_s=float(np.linalg.norm(np.diff(b-a,axis=0),axis=1).max()*240))
    mapping={encoded.document['nodes'][n]['name']:n for n in encoded.joints}
    outside=data['weights']==0
    keys=[r for r in samples if r['frame'].is_integer()]
    maximum=max(samples,key=lambda r:r['depth_m'])
    source_inputs=[study/n for n in ['protocol.json','spec.json','result.json','candidate.glb','fit.npz','engine/verification.json']]+[source/'poses.npz',source/'result.json',body]
    save(output/'floor.json',dict(samples=samples));save(output/'patch-tracks.json',dict(start_frame=first,fps=240,tracks=tracks))
    summary=dict(at=now(),inputs={str(p):sha256(p) for p in source_inputs},case=result['case'],sample_count=len(samples),
        floor_worst=maximum,key_floor_max_m=max(r['depth_m'] for r in keys),dense_floor_passed=maximum['depth_m']<=spec['screen']['floor_depth_m'],
        center_contact_errors_m=errors,center_contact_passed=max(errors.values())<=spec['screen']['contact_error_m'],
        before_bounds=before_bounds,after_bounds=after_bounds,window_step_bounds_passed=not window_step_failures,
        global_step_bounds_passed=not violations,window_step_failures=window_step_failures,
        candidate_pose_bounds_passed=not after_bounds['joint_pose_violations'] and after_bounds['root_horizontal_max_m']<=spec['limits']['root_horizontal_m']+1e-6 and after_bounds['root_vertical_max_m']<=spec['limits']['root_vertical_m']+1e-6,
        outside_matrix_max_error=float(np.max(abs(world[outside]-data['body'][outside]))),
        before_posture=posture(data['body'],mapping),after_posture=posture(world,mapping),patch_speeds=speeds,
        details={n:sha256(output/n) for n in ['floor.json','patch-tracks.json']},engine_actor_frames=180,
        quality_approved=False,human_review=None,scope='One development clip. All keys and eighth-frame skin samples; finite sampling is not continuous collision proof. Only the center-frame contact is declared. Unchanged outer source failures remain; no sustained-support, dynamics, visual or release approval.')
    save(output/'verification.json',summary)
    print({k:summary[k] for k in ['floor_worst','key_floor_max_m','dense_floor_passed','center_contact_passed','window_step_bounds_passed','global_step_bounds_passed','candidate_pose_bounds_passed']})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study.resolve(),a.output.resolve())
