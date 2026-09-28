"""Version 5 clip-wide support fitting with explicit contacts and hard edit budgets.

Preserves rigid bones, root heading/XZ, fingers, duration and predicted labels.
Does not model anatomical limits, forces, self-collision, objects or partners.
"""
import numpy as np
import torch
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import make_interp_spline
from scipy.spatial.transform import Rotation
from floor_contact import Surface, reconstruct
from inspect_motion import skeleton_metadata

CONFIG = dict(fps=30, contact_height_m=.025, contact_speed_m_s=.2,
              minimum_contact_intervals=3, fade_frames=2, iterations=160, knot_spacing_frames=6,
              clearance_m=.002, max_root_lift_m=.22, max_rotation_degrees=40,
              collision_weight=10000., contact_weight=300., explicit_contact_weight=300., pose_weight=.1,
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


def bounded_rotation(parameters,limit):
    """Smooth map into the open rotation-vector ball, with finite zero gradient."""
    return limit*parameters/torch.sqrt(1+parameters.square().sum(-1,keepdim=True))


def bounded_lift(parameters,limit):
    return limit*torch.sigmoid(parameters)


def contact_losses(errors,weights,explicit_mask):
    """Keep a one-frame authored target from being diluted by long foot supports.

    Each authored region has equal weight after averaging its active frames.
    Inferred supports retain their original aggregate normalization separately.
    """
    totals=weights.sum(0)
    per_region=(errors*weights).sum(0)/totals.clamp_min(1e-12)
    active=explicit_mask & (totals>0)
    explicit=(per_region*active).sum()/active.sum().clamp_min(1)
    inferred_weights=weights*(~explicit_mask)
    inferred=(errors*inferred_weights).sum()/inferred_weights.sum().clamp_min(1)
    return inferred,explicit


def correction_basis(frames,spacing):
    """Cubic interpolation of sparse edit controls; output rotations stay bounded."""
    if type(frames)!=int or frames<3 or type(spacing)!=int or spacing<1:raise ValueError('Invalid correction clock')
    knots=np.unique(np.r_[np.arange(0,frames,spacing),frames-1])
    return make_interp_spline(knots,np.eye(len(knots)),k=min(3,len(knots)-1))(np.arange(frames)),knots


def refine(base,previous,skin,progress=None,raw=None,contact_spec=None):
    torch.set_num_threads(2)
    names,parents,_=skeleton_metadata(77); surface=Surface(skin)
    contacts=infer_support(base,skin)
    if contact_spec is not None:
        from contact_spec import apply_overrides
        contacts=apply_overrides(contacts,base,skin,contact_spec,CONFIG['fade_frames'],CONFIG['clearance_m'])
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
    basis,knots=correction_basis(T,CONFIG['knot_spacing_frames']);basis=tensor(basis)
    delta=torch.zeros((len(knots),len(editable),3),dtype=dtype,requires_grad=True)
    def smooth_delta():return torch.einsum('fk,kjd->fjd',basis,delta)
    initial_lift=tensor(previous['root_positions'][:,1]-base['root_positions'][:,1])
    unit=(initial_lift/CONFIG['max_root_lift_m']).clamp(1e-4,1-1e-4)
    lift_parameters=torch.logit(unit).clone().requires_grad_()
    lookup={j:i for i,j in enumerate(editable)}
    reference=tensor((base if raw is None else raw)['posed_joints'])
    def fk():
        change=rodrigues(bounded_rotation(smooth_delta(),np.deg2rad(CONFIG['max_rotation_degrees'])));r=[];p=[];locals=[]
        lift=bounded_lift(lift_parameters,CONFIG['max_root_lift_m'])
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
    explicit_mask=torch.tensor([c.get('provenance')=='explicit' for c in contacts.values()])
    ci=torch.tensor(np.stack([[mapping[v] for v in c['vertex_ids']] for c in contacts.values()],1))
    def vertices(r,p):
        return (((r[:,inds]@bind[None,:,:,:,None]).squeeze(-1)+p[:,inds])*weights[None,:,:,None]).sum(2)
    baseline_vertices=vertices(tensor(base['global_rot_mats']),tensor(base['posed_joints']))
    frame_indices=torch.arange(T-1)[:,None]; patch_indices=ci[:-1]
    original_slide=torch.linalg.vector_norm((baseline_vertices[frame_indices+1,patch_indices]-baseline_vertices[frame_indices,patch_indices])[...,[0,2]]*30,dim=-1)
    optimizer=torch.optim.LBFGS([delta,lift_parameters],lr=.8,max_iter=CONFIG['iterations'],history_size=12,line_search_fn='strong_wolfe',tolerance_grad=1e-8,tolerance_change=1e-11)
    calls=0;last={}
    def closure():
        nonlocal calls,last
        optimizer.zero_grad();r,p,_=fk();v=vertices(r,p)
        selected_contact=v[torch.arange(T)[:,None],ci]
        contact=((selected_contact-targets)**2).sum(-1)
        inferred_loss,explicit_loss=contact_losses(contact,cw,explicit_mask)
        displacement=p-reference
        velocity=torch.linalg.vector_norm(torch.diff(displacement,dim=0)*30,dim=-1)
        slide=torch.linalg.vector_norm((v[frame_indices+1,patch_indices]-v[frame_indices,patch_indices])[...,[0,2]]*30,dim=-1)
        terms=dict(collision=torch.relu(CONFIG['clearance_m']-v[:,:,1]).square().amax(1).mean()*CONFIG['collision_weight'],
            contact=inferred_loss*CONFIG['contact_weight'],
            authored_contact=explicit_loss*CONFIG['explicit_contact_weight'],
            pose=bounded_rotation(smooth_delta(),np.deg2rad(CONFIG['max_rotation_degrees'])).square().mean()*CONFIG['pose_weight'],
            temporal=torch.diff(displacement,n=2,dim=0).square().sum(-1).mean()*CONFIG['temporal_weight'],
            velocity=torch.relu(velocity-1.2).square().amax()*CONFIG['velocity_weight'],
            slide=(torch.relu(slide-original_slide-.02).square()*cw[:-1]).sum()/cw[:-1].sum().clamp_min(1)*CONFIG['slide_weight'])
        loss=sum(terms.values());loss.backward();calls+=1
        last={k:float(v.detach()) for k,v in terms.items()}
        if progress and calls%20==0:progress(dict(evaluations=calls,loss=float(loss.detach()),terms=last))
        return loss
    optimizer.step(closure)
    closure() # Record the accepted point, not the last line-search trial.
    with torch.no_grad():
        _,_,local=fk()
        lift=bounded_lift(lift_parameters,CONFIG['max_root_lift_m'])
        actual_delta=bounded_rotation(smooth_delta(),np.deg2rad(CONFIG['max_rotation_degrees']))
    shifted={k:v.copy() for k,v in base.items()};shifted['root_positions'][:,1]+=lift.detach().numpy()
    result=reconstruct(shifted,local.detach().numpy().copy(),parents);result.pop('smooth_root_pos',None)
    recipe=dict(config=CONFIG,correction_knots=knots.tolist(),parameterization='Cubic edit controls, bounded after interpolation; v5',applied=True,evaluations=calls,objective=last,selected_vertices=len(selected),
        root_lift_m=lift.detach().tolist(), max_rotation_delta_degrees=float(torch.linalg.vector_norm(actual_delta,dim=-1).max()*180/torch.pi),
        contact_spec=contact_spec,hard_bounds=True,
        contact_normalization='Per explicit region, independently of inferred support duration; v3',
        support={k:dict(spans=c['spans'],active_frames=int(c['active'].sum()),provenance=c.get('provenance','inferred')) for k,c in contacts.items()},
        scope='Hard root/rotation budgets with soft clip-wide contact constraints; candidate only until full-mesh and regression checks pass. No certified support or dynamics.')
    return result,recipe
