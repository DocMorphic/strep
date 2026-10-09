"""Independent complete native-load arithmetic replay, without the producer.

Checks archived outputs against recorded poses/settings; not a force sensor,
musculoskeletal model, derivative accuracy bound, or animation-quality review.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation


def verify(capture,report,prop):
    def require(value,message):
        if not value:raise ValueError(message)
    def same(actual,expected):
        a=np.asarray(actual,dtype=float);e=np.asarray(expected,dtype=float)
        require(a.shape==e.shape and np.isfinite(a).all() and np.isfinite(e).all() and np.allclose(a,e,rtol=1e-12,atol=1e-12),'Complete native-load numeric population changed')
    require(report['schema']=='strep-native-prop-load-v1' and report['prop']==prop and all(v[k] is False for v in [capture,report] for k in ['quality_approved','release_approved']) and not capture['faults'],'Unapproved successful capture/report required')
    fps=capture['physics_fps'];n=capture['last_tick']+1;rows=capture['records'];body=capture['bodies'][prop];d=report['diagnostic']
    require(type(fps) is int and fps in (60,120,240) and type(capture['last_tick']) is int and 3<=n<=14401 and len(rows)==n==report['records']==d['frame_count'] and report['last_tick']==n-1 and report['physics_fps']==d['fps']==fps,'Complete source clock/population required')
    require(body==report['body_settings'] and body['center_of_mass_policy']=='custom_zero_body_origin' and body['center_of_mass_mode']==1 and body['center_of_mass_local_m']==[0,0,0],'Bound custom-zero COM settings required')
    mass=body['mass_kg'];inertia=np.diag(body['inertia_diagonal']);require(type(mass) in (int,float) and np.isfinite(mass) and mass>0 and inertia.shape==(3,3) and np.isfinite(inertia).all() and np.all(np.diag(inertia)>0),'Positive finite native mass/inertia required')
    eigen=np.sort(np.diag(inertia));require(eigen[-1]<=eigen[0]+eigen[1]+1e-12,'Physical body inertia required')
    same(d['inertia_body_kg_m2'],inertia);require(d['mass_kg']==mass and d['physical_approval'] is None,'Source mass and no physical approval required')
    p=[];r=[];g=[];v=[];spin=[];steps=[];states=[];labels=[];phases=[]
    for i,row in enumerate(rows):
        require(type(row['tick']) is int and row['tick']==i and row['session']==0 and row['transport']=='live' and not row['failure'] and abs(row['source_time_s']-i/fps)<=1e-12,'Uninterrupted source clock required')
        state=row['props'][prop];pose=np.asarray(state['pose'],dtype=float)
        require(pose.shape==(4,4) and np.isfinite(pose).all() and np.array_equal(pose[3],[0,0,0,1]),'Finite native matrix required')
        inverse=state['inverse_mass'];inverse_inertia=np.asarray(state['inverse_inertia'],dtype=float)
        require(type(inverse) in (int,float) and np.isfinite(inverse) and abs(inverse-1/mass)<=max(1e-10,1e-6/mass)
            and inverse_inertia.shape==(3,) and np.isfinite(inverse_inertia).all() and np.allclose(inverse_inertia,1/np.diag(inertia),rtol=1e-6,atol=1e-10),'Native-precision inverse mass/inertia mismatch')
        require(abs(state['step_s']-1/fps)<=1e-9,'Native timestep changed')
        mode=row['modes'][prop];members=row['members'][prop];ownership=(mode,tuple(sorted(members)))
        require(mode in ('held','released') and (mode=='held')==bool(members) and len(members)==len(set(members)),'Explicit source support population required')
        if not states or ownership!=states[-1]:phases.append(dict(id='ownership-'+str(len(phases)),start_frame=i,end_frame_exclusive=i+1,support_assumption='supported' if mode=='held' else 'unknown'))
        else:phases[-1]['end_frame_exclusive']=i+1
        labels.append(len(phases)-1);states.append(ownership);p.append(pose[:3,3]);r.append(pose[:3,:3]);g.append(state['gravity']);v.append(state['velocity']);spin.append(state['spin']);steps.append(state['step_s'])
    p=np.array(p);r=np.array(r);g=np.array(g);v=np.array(v);spin=np.array(spin);labels=np.array(labels);frames=np.arange(1,n-1)
    require(all(a.shape==(n,3) and np.isfinite(a).all() for a in [p,g,v,spin]) and np.allclose(r.transpose(0,2,1)@r,np.eye(3),atol=2e-6,rtol=0) and np.allclose(np.linalg.det(r),1,atol=2e-6,rtol=0),'Finite rigid native trajectory required')
    # Rotation.from_matrix orthogonalizes the accepted engine-precision basis.
    r=Rotation.from_matrix(r).as_matrix();dt=1/fps
    adjacent=Rotation.from_matrix(r[1:]@r[:-1].transpose(0,2,1)).as_rotvec()
    require(np.all(np.linalg.norm(adjacent,axis=1)<np.pi-1e-6),'Ambiguous sampled angular change')
    w=(adjacent[1:]+adjacent[:-1])/(2*dt);alpha=(adjacent[1:]-adjacent[:-1])/dt**2
    a=(p[2:]-2*p[1:-1]+p[:-2])/dt**2;force=mass*(a-g[1:-1]);iw=r[1:-1]@inertia@r[1:-1].transpose(0,2,1)
    torque=np.einsum('fij,fj->fi',iw,alpha)+np.cross(w,np.einsum('fij,fj->fi',iw,w))
    valid=(labels[:-2]==labels[1:-1])&(labels[1:-1]==labels[2:]);held=valid&np.array([s[0]=='held' for s in states[1:-1]])
    require(d['sample_frames']==frames.tolist() and d['same_phase_stencil']==valid.tolist() and d['excluded_boundary_frames']==frames[~valid].tolist(),'Complete samples and support boundaries required')
    same(d['gravity_m_s2'],g);same(report['actual_native_steps_s'],steps)
    for field,expected in [('acceleration_world_m_s2',a),('angular_velocity_world_rad_s',w),('angular_acceleration_world_rad_s2',alpha),('required_non_gravity_force_world_N',force),('required_torque_about_com_world_Nm',torque)]:same(d[field],expected)
    require(report['ownership']==[dict(mode=m,members=list(s)) for m,s in states] and len(d['phases'])==len(phases),'Complete ownership phase population required')
    for index,(phase,saved) in enumerate(zip(phases,d['phases'])):
        require(all(saved[k]==value for k,value in phase.items()) and saved['free_flight_residual_applicable'] is False,'Unknown release support cannot imply free flight')
        indices=np.flatnonzero(valid&(labels[1:-1]==index));require(saved['interior_samples']==len(indices),'Complete phase interiors required')
        for field,values in [('required_non_gravity_force_N',force),('required_torque_about_com_Nm',torque)]:
            stats=saved[field]
            if not len(indices):require(stats is None,'Empty phase has no load aggregate');continue
            norms=np.linalg.norm(values[indices],axis=1);peak=int(np.argmax(norms))
            same([stats['max'],stats['p95'],stats['mean']],[norms[peak],np.percentile(norms,95),np.mean(norms)])
            # Separate SO(3) reconstructions can reorder machine-precision ties.
            # Require an original phase frame whose reconstructed value is maximal.
            require(type(stats['peak_frame']) is int and stats['peak_frame'] in frames[indices],'Peak must name an original phase frame')
            claimed=int(np.flatnonzero(frames[indices]==stats['peak_frame'])[0]);same(norms[claimed],norms[peak])
    velocity=(p[2:]-p[:-2])/(2*dt)-v[1:-1];angular=w-spin[1:-1]
    same(report['sampled_com_velocity_minus_body_velocity_world_m_s'],velocity);same(report['sampled_angular_velocity_minus_body_spin_world_rad_s'],angular)
    require(report['held_interior_samples']==int(held.sum()),'Complete held interiors required')
    for name,values in [('held_com_velocity_disagreement_max_m_s',velocity),('held_spin_disagreement_max_rad_s',angular)]:
        if held.any():same(report[name],np.linalg.norm(values[held],axis=1).max())
        else:require(report[name] is None,'Empty held interior has no velocity aggregate')
    return dict(records=n,central_samples=len(frames),ownership_phases=len(phases),excluded_boundaries=frames[~valid].tolist(),held_interiors=int(held.sum()),quality_approved=False,release_approved=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('capture',type=Path);parser.add_argument('report',type=Path);parser.add_argument('--prop',required=True);args=parser.parse_args()
    inputs={p:p.read_bytes() for p in [args.capture,args.report]}
    capture=json.loads(inputs[args.capture]);report=json.loads(inputs[args.report]);result=verify(capture,report,args.prop)
    if any(p.read_bytes()!=data for p,data in inputs.items()):raise ValueError('Replay inputs changed')
    result['input_sha256']={str(p):hashlib.sha256(data).hexdigest() for p,data in inputs.items()}
    result['verifier_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();print(json.dumps(result))
