"""Complete sampled net load from native SDK poses, never character capacity.

The current SDK explicitly fixes COM at body origin. Require that native startup
setting; preserve all ownership boundaries and use every recorded gravity value.
"""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from object_dynamics import diagnose


def require(value,message):
    if not value:raise ValueError(message)


def vector(value,shape,label):
    a=np.asarray(value,dtype=float)
    require(a.shape==shape and np.isfinite(a).all(),'Complete finite '+label+' required')
    return a


def measure(run,prop):
    require(run['faults']==[] and run['quality_approved'] is False and run['release_approved'] is False,'Successful unapproved native capture required')
    fps=run['physics_fps'];last=run['last_tick'];records=run['records'];body=run['bodies'][prop]
    require(type(fps) is int and fps in (60,120,240) and type(last) is int and 2<=last<=14400 and len(records)==last+1,'Complete bounded native clock required')
    require(body['center_of_mass_policy']=='custom_zero_body_origin' and type(body['center_of_mass_mode']) is int
        and body['center_of_mass_mode']==1 and np.array_equal(vector(body['center_of_mass_local_m'],(3,),'COM'),np.zeros(3)),'Native custom-zero COM setting required; do not guess a mesh origin')
    mass=body['mass_kg'];require(type(mass) in (int,float) and np.isfinite(mass) and mass>0,'Positive native mass required')
    inertia=vector(body['inertia_diagonal'],(3,),'body inertia');require((inertia>0).all(),'Positive native body inertia required')
    poses=[];gravity=[];velocities=[];spins=[];steps=[];states=[];phases=[]
    for tick,row in enumerate(records):
        require(type(row['tick']) is int and row['tick']==tick and type(row['session']) is int and row['session']==0
            and row['transport']=='live' and not row['failure'],'Complete uninterrupted live capture required')
        clock=row['source_time_s'];require(type(clock) in (int,float) and np.isfinite(clock) and abs(clock-tick/fps)<=1e-12,'Source clock must match every native tick')
        state=row['props'][prop];pose=vector(state['pose'],(4,4),'native pose');r=pose[:3,:3]
        require(np.array_equal(pose[3],[0,0,0,1]) and np.allclose(r.T@r,np.eye(3),rtol=0,atol=2e-6)
            and abs(np.linalg.det(r)-1)<=2e-6,'Rigid native body frame required')
        inverse=state['inverse_mass'];require(type(inverse) in (int,float) and np.isfinite(inverse) and abs(inverse-1/mass)<=max(1e-10,1e-6/mass),'Native inverse mass changed')
        require(np.allclose(vector(state['inverse_inertia'],(3,),'inverse inertia'),1/inertia,rtol=1e-6,atol=1e-10),'Native inertia changed')
        step=state['step_s'];require(type(step) in (int,float) and np.isfinite(step) and abs(step-1/fps)<=1e-9,'Native physics step changed')
        mode=row['modes'][prop];members=row['members'][prop]
        require(mode in ('held','released') and isinstance(members,list) and all(isinstance(v,str) and v for v in members)
            and len(set(members))==len(members) and (bool(members)==(mode=='held')),'Explicit matching ownership/support required')
        ownership=(mode,tuple(sorted(members)))
        if not states or ownership!=states[-1]:
            phases.append(dict(id='ownership-'+str(len(phases)),start_frame=tick,end_frame_exclusive=tick+1,support_assumption='supported' if mode=='held' else 'unknown'))
        else:phases[-1]['end_frame_exclusive']=tick+1
        states.append(ownership);poses.append(pose);steps.append(step)
        gravity.append(vector(state['gravity'],(3,),'body gravity'))
        velocities.append(vector(state['velocity'],(3,),'body velocity'));spins.append(vector(state['spin'],(3,),'body angular velocity'))
    poses=np.array(poses);q=Rotation.from_matrix(poses[:,:3,:3]).as_quat();positions=poses[:,:3,3]
    report=diagnose(positions,q,fps=fps,mass_kg=mass,inertia_body_kg_m2=np.diag(inertia),gravity_m_s2=gravity,phases=phases)
    differences=(positions[2:]-positions[:-2])*fps/2-np.array(velocities)[1:-1]
    spin_difference=np.array(report['angular_velocity_world_rad_s'])-np.array(spins)[1:-1]
    valid=np.array(report['same_phase_stencil'],dtype=bool)
    held=valid&np.array([s[0]=='held' for s in states[1:-1]])
    def maximum(value):return float(np.linalg.norm(value[held],axis=1).max()) if held.any() else None
    return dict(schema='strep-native-prop-load-v1',prop=prop,records=len(records),physics_fps=fps,last_tick=last,
        body_settings=copy.deepcopy(body),clock_basis='source_time_s = tick / physics_fps; actual native step retained separately',actual_native_steps_s=steps,
        ownership=[dict(mode=mode,members=list(members)) for mode,members in states],diagnostic=report,
        sampled_com_velocity_minus_body_velocity_world_m_s=differences.tolist(),sampled_angular_velocity_minus_body_spin_world_rad_s=spin_difference.tolist(),
        held_interior_samples=int(held.sum()),held_com_velocity_disagreement_max_m_s=maximum(differences),held_spin_disagreement_max_rad_s=maximum(spin_difference),
        com_provenance='Native startup custom-zero COM setting, enforced by the bound SDK. Poses are body origins; no inferred geometry COM or per-tick COM sensor.',
        scope='Sampled trajectory required net non-gravity force and COM torque. Held poses may be driven despite zero recorded velocity. No hand-force allocation, grip/friction feasibility, ground balance, character strength/fatigue, effort realism or physical approval. Boundary samples retained but excluded from phase aggregates; released phases are unknown, never inferred free flight.',
        quality_approved=False,release_approved=False)
