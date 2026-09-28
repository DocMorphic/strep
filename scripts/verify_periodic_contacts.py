"""Independently decoded periodic correction, bounds, all-source patch and package audit."""
import io
import json
import zipfile
import hashlib
import numpy as np
from scipy.spatial.transform import Rotation
from urllib.request import urlopen
from strep import ROOT,read,save,sha256
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def decode(path,frames):
    rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
    poses=np.array([sampler.sample(float(np.float32(f/30))) for f in range(frames)])
    return rig,poses,sampler


def metrics(rig,poses,sampler,review):
    points=[rig.vertices(w) for w in poses];floor=max(max(0.,-float(v[:,1].min())) for v in points)
    half=max(max(0.,-float(rig.vertices(sampler.sample((f+.5)/30))[:,1].min())) for f in range(len(poses)-1))
    speeds=[];errors=[];per=[]
    for t in review['authored_targets']:
        active={e['frame'] for e in t['output_frames'] if e['weight']>0}
        track=np.array([v[t['vertices']].mean(axis=0) for v in points])
        for f in active:
            errors.append(float(np.linalg.norm(track[f]-t['target_position_m'])))
            if f+1 in active:speeds.append(float(np.linalg.norm((track[f+1]-track[f])[[0,2]])*30))
    return dict(floor_depth_max_m=floor,half_frame_floor_max_m=half,all_positive_source_target_error_max_m=max(errors,default=None),all_positive_source_target_speed_p95_m_s=float(np.percentile(speeds,95)) if speeds else None,all_positive_source_target_speed_max_m_s=max(speeds,default=None),support_velocity_steps=len(speeds))


def verify(job):
    folder=ROOT/'reports/rig-jobs'/job;spec=read(folder/'contact-spec.json');result=read(folder/'result.json');out=folder/'corrected';p=read(out/'timeline.json')['period_frames'];n=p+1;root=spec['root_node']
    rig,before,b_sampler=decode(folder/'transfer/character.glb',n);changed,after,a_sampler=decode(out/'character.glb',n)
    cycle=np.array(read(out/'timeline.json')['cycle_transform']);repeat,repeated,r_sampler=decode(out/'repeated/character.glb',3*p+1)
    descendants=[]
    for node in range(len(rig.parents)):
        ancestor=node
        while ancestor>=0 and ancestor!=root:ancestor=rig.parents[ancestor]
        if ancestor==root:descendants.append(node)
    repeat_error=0.;closure=0.
    for f in range(3*p+1):
        expected=after[f%p].copy();expected[descendants]=np.linalg.matrix_power(cycle,f//p)@expected[descendants]
        repeat_error=max(repeat_error,float(np.abs(expected-repeated[f]).max()))
        if f==p:closure=float(np.abs(expected-after[-1]).max())
    assert max(repeat_error,closure)<1e-5
    def local(w):
        m=w.copy()
        for node,parent in enumerate(rig.parents):
            if parent>=0:m[:,node]=np.linalg.inv(w[:,parent])@w[:,node]
        return m
    a,b=local(after),local(before);editable={e['node'] for e in spec['edit_joints'].values()};untouched=set(range(len(rig.parents)))-editable-{root}
    untouched_error=float(np.abs(a[:,sorted(untouched)]-b[:,sorted(untouched)]).max());assert untouched_error<1e-5
    for node in editable:assert np.max(np.abs(a[:,node,:3,3]-b[:,node,:3,3]))<1e-6
    shifts=after[:,root,:3,3]-before[:,root,:3,3];limits=spec['limits']
    root_step=float(np.linalg.norm(np.diff(shifts,axis=0),axis=1).max());root_h=float(np.linalg.norm(shifts[:,[0,2]],axis=1).max());root_v=float(np.abs(shifts[:,1]).max())
    assert root_step<=limits['root_step_m']+1e-6 and root_h<=limits['root_horizontal_m']+1e-6 and root_v<=limits['root_vertical_m']+1e-6
    joints={}
    for role,entry in spec['edit_joints'].items():
        node=entry['node'];delta=b[:,node,:3,:3].transpose(0,2,1)@a[:,node,:3,:3];angles=np.degrees(Rotation.from_matrix(delta).magnitude());steps=np.degrees(Rotation.from_matrix(delta[:-1].transpose(0,2,1)@delta[1:]).magnitude())
        assert angles.max()<=entry['limit_degrees']+1e-4 and steps.max()<=limits['joint_step_degrees']+1e-4
        joints[role]=dict(max_edit_deg=float(angles.max()),max_step_deg=float(steps.max()),seam_step_deg=float(steps[-1]))
    review=read(folder/'transfer/contact-review.json');quality={label:metrics(r,w,s,review) for label,r,w,s in [('before',rig,before,b_sampler),('after',changed,after,a_sampler)]}
    # Independent target residuals from explicit specification, including terminal constraints.
    errors=[]
    for c in spec['contacts']:
        for f in range(c['start_frame'],c['end_frame_exclusive']):errors.append(np.linalg.norm(changed.vertices(after[f])[spec['patches'][c['patch']]['vertices']].mean(axis=0)-c['target_position_m']))
    audit=read(out/'audit.json');assert abs(max(errors)-audit['after']['patch_contact_error_max_m'])<1e-5
    assert read(out/'events.json')==read(folder/'transfer/events.json')
    for path,poses in [(out,after),(out/'repeated',repeated)]:
        rt=read(path/'root-motion.json');assert np.max(np.abs(np.array(rt['positions_m'])-poses[:,root,:3,3]))<1e-5
    package=urlopen('http://127.0.0.1:8768'+result['package']).read();assert hashlib.sha256(package).hexdigest()==result['package_sha256']
    with zipfile.ZipFile(io.BytesIO(package)) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name!='README.txt':assert z.read(name)==(folder/name).read_bytes()
        entries=len(z.namelist())
    for variant in result['variants'].values():assert hashlib.sha256(urlopen('http://127.0.0.1:8768'+variant['glb']).read()).hexdigest()==variant['sha256']
    return dict(job=job,closure_error=closure,repeated_transform_error=repeat_error,untouched_local_error=untouched_error,root_step_m=root_step,root_seam_step_m=float(np.linalg.norm(shifts[-1]-shifts[-2])),joint_bounds=joints,quality=quality,explicit_contact_error_m=float(max(errors)),solver=audit['periodic_solver'],flags=audit['flags'],package_entries=entries)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('study');args=p.parse_args();out=ROOT/args.study
    checks={k:verify(v) for k,v in read(out/'cases.json').items()};save(out/'verification.json',dict(checks=checks,scope='Decoded GLBs, untouched local transforms, correction bounds including seam, original positive-weight patch errors/speeds, integer and half-frame floor, root/event tracks, packages and HTTP. Not naturalness or physics approval.'));print(json.dumps(checks))
