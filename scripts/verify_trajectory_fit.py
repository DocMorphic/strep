"""Independent decoded-GLB trajectory/contact comparison; no optimizer imports."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_rig_clearance import verify as verify_bounds, localize


def summary(values):
    values=np.asarray(values)
    return dict(count=int(values.size),maximum=float(values.max()) if values.size else None,p95=float(np.percentile(values,95)) if values.size else None)


def energy(world,points,local,original_world,original_points,original_local,spec,request,supports,cfg):
    # Independent scalar sum: each velocity edge and acceleration center once.
    root=spec['root_node'];nodes=[e['node'] for e in spec['edit_joints'].values()]
    shift=world[:,root,:3,3]-original_world[:,root,:3,3]
    delta=original_local[:,nodes,:3,:3].transpose(0,1,3,2)@local[:,nodes,:3,:3]
    vectors=Rotation.from_matrix(delta.reshape(-1,3,3)).as_rotvec()
    obj=spec['objective'];terms={}
    terms['floor']=float(np.sum((np.minimum(points[:,:,1],0)*obj['floor_weight'])**2))
    terms['height']=sum(float(np.sum(((points[:,p['vertices'],1].min(axis=1)-np.array(request['targets_m'][side]))*12)**2)) for side,p in spec['patches'].items())
    terms['prior']=float(np.sum((shift*obj['root_prior'])**2)+np.sum((vectors*obj['rotation_prior_m_per_radian'])**2))
    terms['free_horizontal']=0.;terms['support_position']=0.;terms['support_velocity']=0.
    for side,patch in spec['patches'].items():
        active=np.zeros(len(world),bool)
        for c in supports:
            if c['side']==side:active[c['start_frame']:c['end_frame_exclusive']]=True
        ids=patch['vertices'];d=points[:,ids][:,:,[0,2]]-original_points[:,ids][:,:,[0,2]]
        terms['free_horizontal']+=float(np.sum(d[~active]**2)*cfg['free_horizontal_weight']**2/len(ids))
    for c in supports:
        a,b=c['start_frame'],c['end_frame_exclusive'];p=points[a:b][:,c['vertices']].mean(axis=1)
        terms['support_position']+=float(np.sum((p-c['target_position_m'])**2)*cfg['support_position_weight']**2)
        terms['support_velocity']+=float(np.sum(np.diff(p,axis=0)**2)*cfg['support_velocity_weight']**2)
    terms['rotation_acceleration']=float(np.sum(np.diff(local[:,nodes,:3,:3],n=2,axis=0)**2)*cfg['rotation_acceleration_weight']**2)
    terms['root_acceleration']=float(np.sum(np.diff(world[:,root,:3,3],n=2,axis=0)**2)*cfg['root_acceleration_weight']**2)
    return dict(total=sum(terms.values()),terms=terms)


def verify(folder,mode):
    folder=Path(folder);bounds=verify_bounds(folder)
    spec=read(folder/'spec.json');envelope=np.array(read(folder/'request.json')['envelope']);count=len(envelope)
    supports=read(folder/'support-targets.json')['supports'];cfg=read(folder/'trajectory-settings.json')
    nodes=[e['node'] for e in spec['edit_joints'].values()];metrics={};matrices={};rotations={};skin={}
    for stage in ['input','candidate']:
        rig=RigAsset.load(folder/stage/'character.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
        world=np.array([sampler.sample(float(np.float32(f/30))) for f in range(count)])
        points=np.array([rig.vertices(w) for w in world]);local=localize(world,rig.parents)
        r=local[:,nodes,:3,:3];rotations[stage]=r;skin[stage]=points;matrices[stage]=world
        steps=np.degrees(Rotation.from_matrix((r[:-1].transpose(0,1,3,2)@r[1:]).reshape(-1,3,3)).magnitude()).reshape(count-1,-1)
        # Angular velocities are expressed in each local joint's parent frame.
        omega=Rotation.from_matrix((r[1:]@r[:-1].transpose(0,1,3,2)).reshape(-1,3,3)).as_rotvec().reshape(count-1,-1,3)*30
        acceleration=np.linalg.norm(np.diff(omega,axis=0),axis=2)*30
        root=world[:,spec['root_node'],:3,3];rootacc=np.linalg.norm(np.diff(root,n=2,axis=0),axis=1)*900
        contacts=[]
        for entry in supports:
            a,b=entry['start_frame'],entry['end_frame_exclusive'];ids=entry['vertices']
            p=points[a:b][:,ids].mean(axis=1);errors=np.linalg.norm(p-np.array(entry['target_position_m']),axis=1)
            velocity=np.diff(p,axis=0)*30;editable=envelope[a:b]>0;fixed=~editable
            contacts.append(dict(positions_m=p.tolist(),target_position_m=entry['target_position_m'],side=entry['side'],start_frame=a,end_frame_exclusive=b,vertices=len(ids),error_m=summary(errors),editable_error_m=summary(errors[editable]),frozen_error_m=summary(errors[fixed]),speed_m_s=summary(np.linalg.norm(velocity,axis=1)),horizontal_speed_m_s=summary(np.linalg.norm(velocity[:,[0,2]],axis=1)),editable_horizontal_speed_m_s=summary(np.linalg.norm(velocity[:,[0,2]],axis=1)[editable[:-1]&editable[1:]])))
        metrics[stage]=dict(contacts=contacts,edited_joint_step_degrees=summary(steps),angular_acceleration_rad_s2=summary(acceleration),editable_angular_acceleration_rad_s2=summary(acceleration[envelope[1:-1]>0]),root_acceleration_m_s2=summary(rootacc),editable_root_acceleration_m_s2=summary(rootacc[envelope[1:-1]>0]),rotation_matrix_acceleration_squared_sum=float(np.sum(np.diff(r,n=2,axis=0)**2)),root_acceleration_squared_sum_m2=float(np.sum(np.diff(root,n=2,axis=0)**2)))
        metrics[stage]['floor']=bounds['metrics'][stage]
    request=read(folder/'request.json')
    for stage in ['input','candidate']:
        metrics[stage]['trajectory_energy']=energy(matrices[stage],skin[stage],localize(matrices[stage],rig.parents),matrices['input'],skin['input'],localize(matrices['input'],rig.parents),spec,request,supports,cfg)
    if mode=='trajectory':assert metrics['candidate']['trajectory_energy']['total']<=metrics['input']['trajectory_energy']['total']+1e-4
    def step(r):return Rotation.from_matrix((r[:-1].transpose(0,1,3,2)@r[1:]).reshape(-1,3,3)).magnitude().reshape(count-1,-1)
    regression=np.degrees(step(rotations['candidate'])-step(rotations['input']))
    limits_pass=bool(regression.max()<=cfg['rotation_step_allowance_degrees']+1e-4)
    if mode=='trajectory':assert limits_pass,regression.max()
    records=read(folder/'solver.json')
    assert all(r['cost_after']<=r['cost_before']+1e-9 for r in records)
    conflicts=[]
    for c in supports:
        a,b=c['start_frame'],c['end_frame_exclusive']
        h=np.asarray(request['targets_m'][c['side']])[a:b]
        lower=np.maximum(0,(h-c['target_position_m'][1])/2)
        frozen=[]
        for frame in range(a,b):
            if envelope[frame]==0:
                error=float(np.linalg.norm(skin['input'][frame,c['vertices']].mean(axis=0)-c['target_position_m']))
                if error>spec['screen']['contact_error_m']:frozen.append(dict(frame=frame,error_m=error))
        conflicts.append(dict(side=c['side'],start_frame=a,end_frame_exclusive=b,height_and_support_minimax_error_lower_bound_m=float(lower.max()),frozen_frames_failing_contact=frozen))
    result=dict(target_conflicts=conflicts,created_at=now(),mode=mode,checks_passed=True,quality_approved=False,support_targets_confirmed=False,glb_sha256=sha256(folder/'candidate/character.glb'),input_sha256=sha256(folder/'input/character.glb'),max_adjacent_joint_step_increase_degrees=float(regression.max()),joint_step_allowance_passed=limits_pass,solver_unsuccessful_subproblems=sum(not x['success'] for x in records),solver=read(folder/'fit-summary.json')['convergence'],metrics=metrics,scope='All decoded frames and independent clearance/bound/half-frame checks. Contact groups are unconfirmed explicit drafts. Angular acceleration is local-parent-frame finite difference; no dynamics or semantic approval.')
    save(folder/'trajectory-verification.json',result);return result


def run(out):
    out=Path(out);rows=[];manifest=[]
    for case in read(out/'design.json')['cases']:
        for mode in read(out/'design.json')['modes']:
            folder=out/case/mode;row=verify(folder,mode);row['case']=case;rows.append(row)
            count=read(folder/'spec.json')['frames']
            for stage in ['input','candidate']:
                p=folder/stage/'character.glb';manifest.append(dict(id=case+'-'+mode+'-'+stage,path=p.relative_to(out).as_posix(),sha256=sha256(p),frames=count,fps=30))
    for case in read(out/'design.json')['cases']:
        matched=[r for r in rows if r['case']==case];assert len({r['input_sha256'] for r in matched})==1
    save(out/'verification.json',dict(cases=rows,verifier_sha256=sha256(__file__),quality_approved=False));save(out/'manifest.json',dict(cases=manifest))
    print('Verified',len(rows),'fits and',len(manifest),'GLBs',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
