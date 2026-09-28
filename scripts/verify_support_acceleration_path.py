"""Fresh decoded path metrics and rotation-peak locations; no fitting."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_rig_clearance import localize


def run(folder,output):
    if output.exists():raise ValueError('Preserve earlier audit')
    request=read(folder/'request.json');done=read(folder/'completion.json');results=read(folder/'results.json')['rows']
    if sha256(folder/'request.json')!=done['request_sha256'] or sha256(folder/'results.json')!=done['results_sha256']:raise ValueError('Changed protocol/results')
    if [r['alpha'] for r in results]!=request['fractions']:raise ValueError('Fraction population differs')
    for p,h in request['inputs'].items():
        if sha256(p)!=h:raise ValueError('Changed source')
    for name,h in request['implementation'].items():
        if sha256(folder/'implementation'/name)!=h:raise ValueError('Changed snapshot')
    held=Path(request['held']);prior=Path(request['prior']);proposal=Path(request['proposal'])
    old=read(prior/'verification.json');reference=read(held/'verification.json')
    caps=np.asarray(read(proposal/'request.json')['acceleration_caps_m_s2']);rows=[]
    protected=request.get('protected_joint_track');baseline_local=None
    if protected:
        rig=RigAsset.load(held/'candidate/character.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
        spec=read(held/'spec.json');count=spec['frames'];fps=spec['fps']
        baseline_local=localize(np.array([sampler.sample(float(np.float32(f/fps))) for f in range(count)]),rig.parents)
        initial=np.load(held/'fit.npz',allow_pickle=False)['parameters'];proposal_parameters=np.load(proposal/'fit.npz',allow_pickle=False)['parameters']
        nodes=[x['node'] for x in spec['edit_joints'].values()];start=3+3*nodes.index(protected['node'])
    for i,row in enumerate(results):
        step=folder/f'step-{i:02d}';spec=read(step/'spec.json');fps=spec['fps'];count=spec['frames']
        for name,h in row['files'].items():
            if sha256(step/name)!=h:raise ValueError('Changed diagnostic output')
        rig=RigAsset.load(step/'candidate/character.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
        world=np.array([sampler.sample(float(np.float32(f/fps))) for f in range(count)])
        skin=np.array([rig.vertices(w) for w in world]);local=localize(world,rig.parents)
        protected_error=None
        if protected:
            parameters=np.load(step/'parameters.npz',allow_pickle=False)['parameters']
            expected=(1-row['alpha'])*initial+row['alpha']*proposal_parameters
            expected[:,start:start+3]=initial[:,start:start+3]
            np.testing.assert_allclose(parameters,expected,atol=1e-14,rtol=0)
            protected_error=float(np.abs(local[:,protected['node'],:3,:3]-baseline_local[:,protected['node'],:3,:3]).max())
            if protected_error>1e-6:raise ValueError('Protected joint rotation changed')
        delta=local[:-1,:,:3,:3].transpose(0,1,3,2)@local[1:,:,:3,:3]
        angles=np.degrees(Rotation.from_matrix(delta.reshape(-1,3,3)).magnitude()).reshape(count-1,-1)
        peak_frame,node=np.unravel_index(np.argmax(angles),angles.shape);peak=float(angles[peak_frame,node])
        root=world[:,spec['root_node'],:3,3];root_acc=float(np.linalg.norm(np.diff(root,n=2,axis=0)*fps**2,axis=1).max())
        floor=max(0.,-float(skin[:,:,1].min()))
        for f in range(count-1):floor=max(floor,-float(rig.vertices(sampler.sample((f+.5)/fps))[:,1].min()))
        points=np.stack([skin[:,p['vertices']].mean(axis=1) for p in spec['patches'].values()],axis=1)
        excess=np.maximum(np.linalg.norm(np.diff(points,n=2,axis=0)*fps**2,axis=2)-caps,0);energy=float(np.sum(excess**2))
        proof=read(step/'verification.json');metrics=proof['metrics']['candidate']
        if abs(peak-metrics['local_rotation_step_max_degrees'])>1e-10:raise ValueError('Rotation metric differs')
        np.testing.assert_allclose([root_acc,floor,energy],[row['root_acceleration_m_s2'],row['floor_m'],row['energy']],atol=1e-9,rtol=0)
        guards=dict(floor=floor<=.005,root_acceleration=root_acc<=max(old['metrics'][v]['root_acceleration_max_m_s2'] for v in ['input','candidate'])+1e-5,
            rotation_steps=peak<=max(old['metrics']['input']['local_rotation_step_max_degrees'],reference['metrics']['candidate']['local_rotation_step_max_degrees'])+1e-4,
            acceleration_energy_improves=bool(i and energy<rows[0]['energy']-1e-9))
        annotations=read(step/'input/contacts.json')
        for s,side in enumerate(spec['patches']):
            active=np.zeros(count,bool)
            for interval in annotations['intervals']:
                if interval['joint'] in [side+'Foot',side+'ToeBase']:active[interval['start_frame']:interval['end_frame_exclusive']]=True
            speeds=np.linalg.norm(np.diff(points[:,s][:,[0,2]],axis=0),axis=1)*fps;values=speeds[active[:-1]&active[1:]]
            for label,value in [('max',float(values.max())),('p95',float(np.percentile(values,95)))]:
                key=f'predicted_support_{label}_m_s'
                cap=max(next(v for v in read(p/'traces.json')['variants'] if v['variant']=='candidate')['feet'][side][key] for p in [held,prior])
                guards[f'{side}_{label}']=value<=cap+1e-6
        if guards!=row['guard_checks'] or all(guards.values())!=row['guarded_improvement']:raise ValueError('Guard decision differs')
        rows.append(dict(alpha=row['alpha'],energy=energy,floor_m=floor,root_acceleration_m_s2=root_acc,rotation_peak_degrees=peak,
            protected_joint_max_local_matrix_error=protected_error,
            rotation_peak_step_end=int(peak_frame+1),rotation_peak_node=int(node),rotation_peak_name=rig.document['nodes'][node].get('name',''),
            guard_checks=guards,guarded_improvement=all(guards.values())))
    save(output,dict(at=now(),completion_sha256=sha256(folder/'completion.json'),implementation_sha256=sha256(__file__),rows=rows,
        decoded_integer_poses=sum(read(folder/f'step-{i:02d}/spec.json')['frames'] for i in range(len(rows))),
        quality_approved=False,scope='Fresh decoded whole/half-frame floor, root, rotation, foot acceleration and support guard audit. No engine import, visual review or optimizer success claim.'))
    print([(r['alpha'],r['rotation_peak_name'],r['rotation_peak_step_end'],r['rotation_peak_degrees']) for r in rows])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    with threadpool_limits(limits=1):run(a.folder.resolve(),a.output.resolve())
