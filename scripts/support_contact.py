"""Experimental clip-wide support fitting. Inferred contacts are not annotations.

Preserves rigid bones, root heading/XZ, fingers, duration and predicted labels.
Does not model anatomical limits, forces, self-collision, objects or partners.
"""
import numpy as np
import torch
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation
from floor_contact import Surface, reconstruct
from inspect_motion import skeleton_metadata

CONFIG = dict(fps=30, contact_height_m=.025, contact_speed_m_s=.2,
              minimum_contact_intervals=3, fade_frames=2, iterations=120,
              clearance_m=.002, max_root_lift_m=.22, max_rotation_degrees=40,
              collision_weight=10000., contact_weight=300., pose_weight=.1,
              temporal_weight=200., velocity_weight=10., slide_weight=10.)


def regions(skin):
    surface=Surface(skin); names=surface.names
    dominant=surface.indices[np.arange(len(surface.indices)),surface.weights.argmax(1)]
    result=dict(surface.regions)
    for name,bones in {'Torso':['Hips','Spine1','Spine2','Chest'], 'Head':['Head','Neck1','Neck2']}.items():
        result[name]=np.flatnonzero(np.isin(dominant,[names.index(b) for b in bones]))
    for side in ['Left','Right']:
        for name,bone in [('Knee','Shin'),('Elbow','ForeArm')]:
            j=names.index(side+bone)
            near=np.linalg.norm(skin['bind_vertices']-skin['bind_rig_transform'][j,:3,3],axis=1)<.13
            result[side+name]=np.flatnonzero((dominant==j)&near)
    return result


def intervals(mask):
    edges=np.diff(np.r_[False,mask,False].astype(int))
    return list(zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))


def infer_support(base,skin):
    """Fixed baseline geometry; retain only consecutive low/slow intervals."""
    surface=Surface(skin); out={}
    for name,ids in regions(skin).items():
        verts=np.array([surface.vertices(r,p,ids) for r,p in zip(base['global_rot_mats'],base['posed_joints'])])
        h=verts[:,:,1].min(1); speed=np.linalg.norm(np.diff(verts.mean(1)[:,[0,2]],axis=0),axis=1)*CONFIG['fps']
        mask=(h[:-1]<CONFIG['contact_height_m'])&(h[1:]<CONFIG['contact_height_m'])&(speed<CONFIG['contact_speed_m_s'])
        spans=[(int(a),int(b)) for a,b in intervals(mask) if b-a>=CONFIG['minimum_contact_intervals']]
        active=np.zeros(len(h),bool)
        for a,b in spans:active[a:b+1]=True
        weight=gaussian_filter1d(active.astype(float),CONFIG['fade_frames'],mode='nearest')
        lowest=verts[:,:,1].argmin(1)
        targets=verts[np.arange(len(h)),lowest].copy();targets[:,1]=np.maximum(targets[:,1],CONFIG['clearance_m'])
        out[name]=dict(vertex_ids=ids[lowest], targets=targets, weights=weight,
                       spans=spans, active=active, height=h, speed=speed)
    return out


def rodrigues(v):
    # sinc form has finite derivatives at zero, unlike an axis normalization.
    x,y,z=v.unbind(-1); zero=torch.zeros_like(x)
    k=torch.stack([zero,-z,y,z,zero,-x,-y,x,zero],-1).reshape(*v.shape[:-1],3,3)
    angle=torch.linalg.vector_norm(v,dim=-1)
    return torch.eye(3,dtype=v.dtype)+torch.sinc(angle/torch.pi)[...,None,None]*k+.5*torch.sinc(angle/(2*torch.pi))[...,None,None]**2*(k@k)


def refine(base,previous,skin,progress=None,raw=None):
    torch.set_num_threads(2)
    names,parents,_=skeleton_metadata(77); surface=Surface(skin)
    contacts=infer_support(base,skin)
    # Small body set; facial, finger and toe articulation remain unchanged.
    editable=[names.index(n) for n in ['Spine1','Spine2','Chest','Neck1','Neck2','Head',
        'LeftShoulder','LeftArm','LeftForeArm','LeftHand','RightShoulder','RightArm','RightForeArm','RightHand',
        'LeftLeg','LeftShin','LeftFoot','RightLeg','RightShin','RightFoot']]
    T=len(base['root_positions']); dtype=torch.float64
    def tensor(x):return torch.as_tensor(np.asarray(x),dtype=dtype)
    offsets=np.zeros_like(base['posed_joints'],dtype=float)
    for j,p in enumerate(parents):
        if p>=0:offsets[:,j]=np.einsum('fji,fj->fi',base['global_rot_mats'][:,p],base['posed_joints'][:,j]-base['posed_joints'][:,p])
    offsets=tensor(offsets); initial=tensor(previous['local_rot_mats']);root=tensor(base['root_positions'])
    delta=torch.zeros((T,len(editable),3),dtype=dtype,requires_grad=True)
    lift=tensor(previous['root_positions'][:,1]-base['root_positions'][:,1]).clone().requires_grad_()
    lookup={j:i for i,j in enumerate(editable)}
    reference=tensor((base if raw is None else raw)['posed_joints'])
    def fk():
        change=rodrigues(delta);r=[];p=[];locals=[]
        for j,parent in enumerate(parents):
            local=initial[:,j] if j not in lookup else initial[:,j]@change[:,lookup[j]]
            locals.append(local)
            if parent<0:
                r.append(local);p.append(root+torch.stack([lift*0,lift,lift*0],-1))
            else:
                r.append(r[parent]@local);p.append(p[parent]+(r[parent]@offsets[:,j,:,None]).squeeze(-1))
        return torch.stack(r,1),torch.stack(p,1),torch.stack(locals,1)
    # Fixed baseline skin points near the floor include penetrating torso areas.
    # Full mesh verification remains independent of this optimization sample.
    selected=set()
    for r,p in zip(base['global_rot_mats'],base['posed_joints']):
        heights=surface.vertices(r,p)[:,1]
        selected.update(np.argsort(heights)[:32].tolist())
    for c in contacts.values():selected.update(c['vertex_ids'].tolist())
    selected=np.array(sorted(selected)); mapping={v:i for i,v in enumerate(selected)}
    inds=skin['lbs_indices'][selected];weights=tensor(skin['lbs_weights'][selected])
    bind=tensor(np.einsum('vwij,vj->vwi',surface.inverse[inds],surface.points[selected])[:,:,:3])
    targets=torch.stack([tensor(c['targets']) for c in contacts.values()],1)
    cw=torch.stack([tensor(c['weights']) for c in contacts.values()],1)
    ci=torch.tensor(np.stack([[mapping[v] for v in c['vertex_ids']] for c in contacts.values()],1))
    def vertices(r,p):
        return (((r[:,inds]@bind[None,:,:,:,None]).squeeze(-1)+p[:,inds])*weights[None,:,:,None]).sum(2)
    baseline_vertices=vertices(tensor(base['global_rot_mats']),tensor(base['posed_joints']))
    frame_indices=torch.arange(T-1)[:,None]; patch_indices=ci[:-1]
    original_slide=torch.linalg.vector_norm((baseline_vertices[frame_indices+1,patch_indices]-baseline_vertices[frame_indices,patch_indices])[...,[0,2]]*30,dim=-1)
    optimizer=torch.optim.LBFGS([delta,lift],lr=.8,max_iter=CONFIG['iterations'],history_size=12,line_search_fn='strong_wolfe',tolerance_grad=1e-8,tolerance_change=1e-11)
    calls=0;last={}
    def closure():
        nonlocal calls,last
        optimizer.zero_grad();r,p,_=fk();v=vertices(r,p)
        selected_contact=v[torch.arange(T)[:,None],ci]
        contact=((selected_contact-targets)**2).sum(-1)
        displacement=p-reference
        velocity=torch.linalg.vector_norm(torch.diff(displacement,dim=0)*30,dim=-1)
        slide=torch.linalg.vector_norm((v[frame_indices+1,patch_indices]-v[frame_indices,patch_indices])[...,[0,2]]*30,dim=-1)
        terms=dict(collision=torch.relu(CONFIG['clearance_m']-v[:,:,1]).square().amax(1).mean()*CONFIG['collision_weight'],
            contact=(contact*cw).sum()/cw.sum().clamp_min(1)*CONFIG['contact_weight'],
            pose=delta.square().mean()*CONFIG['pose_weight'],
            temporal=torch.diff(displacement,n=2,dim=0).square().sum(-1).mean()*CONFIG['temporal_weight'],
            velocity=torch.relu(velocity-1.2).square().amax()*CONFIG['velocity_weight'],
            slide=(torch.relu(slide-original_slide-.02).square()*cw[:-1]).sum()/cw[:-1].sum().clamp_min(1)*CONFIG['slide_weight'],
            budget=(torch.relu(-lift).square()+torch.relu(lift-CONFIG['max_root_lift_m']).square()).mean()*10000+
                   torch.relu(torch.linalg.vector_norm(delta,dim=-1)-np.deg2rad(CONFIG['max_rotation_degrees'])).square().mean()*100)
        loss=sum(terms.values());loss.backward();calls+=1
        last={k:float(v.detach()) for k,v in terms.items()}
        if progress and calls%20==0:progress(dict(evaluations=calls,loss=float(loss.detach()),terms=last))
        return loss
    optimizer.step(closure)
    with torch.no_grad():_,_,local=fk()
    shifted={k:v.copy() for k,v in base.items()};shifted['root_positions'][:,1]+=lift.detach().numpy()
    result=reconstruct(shifted,local.detach().numpy().copy(),parents);result.pop('smooth_root_pos',None)
    recipe=dict(config=CONFIG,applied=True,evaluations=calls,objective=last,selected_vertices=len(selected),
        root_lift_m=lift.detach().tolist(), max_rotation_delta_degrees=float(torch.linalg.vector_norm(delta.detach(),dim=-1).max()*180/torch.pi),
        support={k:dict(spans=c['spans'],active_frames=int(c['active'].sum())) for k,c in contacts.items()},
        scope='Soft clip-wide geometric constraints; candidate only until full-mesh and regression checks pass. No certified support or dynamics.')
    return result,recipe
