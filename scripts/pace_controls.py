"""Real asset retiming and explicit root/contact exports; no pose modification."""
import copy
import numpy as np
from gltf_tools import accessor,append_accessor


def retime_glb(document,binary,target_speed):
    if not np.isfinite(target_speed) or target_speed<=0:raise ValueError('Speed must be positive and finite')
    result=copy.deepcopy(document);buffer=bytearray(binary)
    animation=result['animations'][0]
    root=next(i for i,n in enumerate(result['nodes']) if n.get('name')=='Hips')
    channel=next(c for c in animation['channels'] if c['target']=={'node':root,'path':'translation'})
    sampler=animation['samplers'][channel['sampler']]
    original_times=accessor(document,binary,sampler['input'])
    positions=accessor(document,binary,sampler['output'])
    native_speed=float((positions[-1,2]-positions[0,2])/(original_times[-1]-original_times[0]))
    if native_speed<=0:raise ValueError('Expected positive forward travel')
    ratio=target_speed/native_speed
    indices={}
    for item in animation['samplers']:
        old=item['input']
        if old not in indices:
            indices[old]=append_accessor(result,buffer,accessor(document,binary,old)/ratio,'SCALAR')
        item['input']=indices[old]
    times=original_times/ratio
    result['asset']['generator']='strep pace controls v1'
    result.setdefault('extras',{})['pace']={'target_speed_m_s':target_speed,'native_speed_m_s':native_speed,
        'time_scale':ratio,'method':'Uniform key-time scaling; all pose keys, skinning and stride unchanged.'}
    return result,buffer,{'native_speed_m_s':native_speed,'time_scale':ratio,'effective_fps':30*ratio,
        'duration_s':float(times[-1]),'cycle_displacement_m':((positions[-1]-positions[0])/4).tolist()}


def contact_intervals(contacts,times,names):
    """Half-open intervals over frame segments; final pose closes the clip."""
    contacts=np.asarray(contacts,dtype=bool);times=np.asarray(times)
    if len(contacts)!=len(times) or len(times)<2 or not np.all(np.diff(times)>0):raise ValueError('Invalid contact timeline')
    result=[]
    for j,name in enumerate(names):
        active=contacts[:-1,j];start=None
        for i in range(len(active)+1):
            on=i<len(active) and active[i]
            if on and start is None:start=i
            if not on and start is not None:
                result.append({'joint':name,'start_s':float(times[start]),'end_s':float(times[i]),
                    'start_frame':start,'end_frame_exclusive':i,'clipped_at_start':start==0,'clipped_at_end':i==len(active),
                    'source':'model_predicted_contact'})
                start=None
    return sorted(result,key=lambda x:(x['start_s'],x['joint']))


def foot_surface_measurements(motion,skin,displacement,rules):
    """Foot-only LBS with all 8 influences; stable lowest-patch velocity proxy."""
    vertices=skin['bind_vertices'];weights=skin['lbs_weights'];joints=skin['lbs_indices']
    names=list(skin['rig_joint_names']);inverse=np.linalg.inv(skin['bind_rig_transform'])
    n=len(motion['posed_joints']);transforms=np.broadcast_to(np.eye(4),(n,77,4,4)).copy()
    transforms[:,:,:3,:3]=motion['global_rot_mats'];transforms[:,:,:3,3]=motion['posed_joints']
    transforms=transforms@inverse;all_speeds=[];minimum=1e9;counts=[]
    for side,offset in [('Left',0),('Right',3)]:
        bones=[names.index(side+n) for n in ['Foot','ToeBase','ToeEnd']]
        membership=np.sum(weights*np.isin(joints,bones),axis=1)
        selected=np.flatnonzero(membership>.99)
        if len(selected)<10:raise ValueError('Foot surface selection too small')
        points=np.c_[vertices[selected],np.ones(len(selected))]
        posed=np.array([np.sum(np.einsum('vwij,vj->vwi',t[joints[selected]],points)[:,:,:3]*weights[selected,:,None],axis=1) for t in transforms])
        minimum=min(minimum,float(posed[:,:,1].min()))
        patch=(posed[:,:,1]<=posed[:,:,1].min(axis=1,keepdims=True)+rules['lowest_patch_band_m']) & (posed[:,:,1]<=rules['near_floor_height_m'])
        contact=motion['foot_contacts'][:,offset:offset+3].any(axis=1)
        next_pos=np.concatenate([posed[1:],posed[:1]+displacement])
        mask=patch & np.roll(patch,-1,axis=0) & contact[:,None] & np.roll(contact,-1)[:,None]
        speeds=np.linalg.norm((next_pos-posed)[:,:,[0,2]],axis=-1)*30
        all_speeds.extend(speeds[mask].tolist());counts.append({'side':side,'vertices':len(selected),'samples':int(mask.sum())})
    return {'minimum_foot_surface_y_m':minimum,'maximum_foot_penetration_m':max(0,-minimum),
        'native_patch_speed_p95_m_s':float(np.percentile(all_speeds,95)) if all_speeds else None,
        'patch_samples':len(all_speeds),'regions':counts,
        'scope':'Foot-dominated mesh vertices (>99% weight); lowest 5 mm patch within 3 cm of floor, persistent across adjacent predicted support samples. Rolling feet and wrong contact labels can bias this proxy. No independent stance, body collisions or dynamics.'}
