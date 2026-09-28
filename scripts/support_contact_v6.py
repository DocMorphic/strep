"""Oriented scene contact fitting with cubic edit controls and sampled box clearance.

Object tracks are frozen. No partner/self collision, anatomy or dynamics solve.
"""
import numpy as np
import torch
from scipy.ndimage import gaussian_filter1d
from floor_contact import Surface,reconstruct
from inspect_motion import skeleton_metadata
from support_contact_v5 import infer_support,bounded_rotation,bounded_lift,rodrigues,contact_losses,correction_basis,CONFIG as BASE_CONFIG
from scene_solver_context import box_signed_distance
CONFIG={**BASE_CONFIG,'iterations':200,'orientation_weight':5.,'object_collision_weight':10000.,'object_clearance_m':.002,'object_uniform_stride':48,'object_near_samples':48}


def torch_box_depth(points,position,rotation,size,clearance=0.):
    local=torch.einsum('fvi,fij->fvj',points-position[:,None,:],rotation)
    return torch.relu((size/2+clearance-local.abs()).amin(-1))


def refine(base,previous,skin,progress=None,raw=None,contact_spec=None,scene_context=None):
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
    context=scene_context or dict(frame_count=T,boxes=[],normals=[])
    if context['frame_count']!=T:raise ValueError('Scene context clock mismatch')
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
    normal_faces=[]
    for c in context['normals']:
        faces=skin['faces'][np.any(skin['faces']==c['surface_vertex'],axis=1)]
        if not len(faces):raise ValueError('Contact normal has no surface triangles')
        normal_faces.append(faces);selected.update(faces.reshape(-1).tolist())
    if context['boxes']:
        selected.update(range(0,len(skin['bind_vertices']),CONFIG['object_uniform_stride']))
        for source in [base,previous]:
            for f,(r,p) in enumerate(zip(source['global_rot_mats'],source['posed_joints'])):
                points=surface.vertices(r,p)
                for box in context['boxes']:
                    distances=box_signed_distance(points,np.array(box['positions_m'][f]),np.array(box['rotations'][f]),box['size_m'])
                    selected.update(np.argsort(distances)[:CONFIG['object_near_samples']].tolist())
    selected=np.array(sorted(selected)); mapping={v:i for i,v in enumerate(selected)}
    normal_constraints=[]
    for c,faces in zip(context['normals'],normal_faces):
        indices=torch.tensor([[mapping[int(i)] for i in face] for face in faces])
        mask=np.zeros(T);mask[c['start_frame']:c['end_frame']+1]=1
        normal_constraints.append((indices,tensor(c['directions']),tensor(gaussian_filter1d(mask,CONFIG['fade_frames'],mode='nearest'))))
    objects=[(tensor(b['positions_m']),tensor(b['rotations']),tensor(b['size_m'])) for b in context['boxes']]

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
        if normal_constraints:
            normal_loss=[]
            for triangles,desired,weight in normal_constraints:
                points=v[:,triangles]
                normal=torch.linalg.cross(points[:,:,1]-points[:,:,0],points[:,:,2]-points[:,:,0]).sum(1)
                normal=normal/torch.linalg.vector_norm(normal,dim=-1,keepdim=True).clamp_min(1e-12)
                normal_loss.append((((normal-desired)**2).sum(-1)*weight).sum()/weight.sum().clamp_min(1e-12))
            terms['orientation']=torch.stack(normal_loss).mean()*CONFIG['orientation_weight']
        if objects:
            terms['object_collision']=torch.stack([torch_box_depth(v,op,orr,size,CONFIG['object_clearance_m']).square().amax(1).mean() for op,orr,size in objects]).mean()*CONFIG['object_collision_weight']
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
    recipe=dict(config=CONFIG,correction_knots=knots.tolist(),parameterization='Cubic edit controls with oriented surface contact and sampled box clearance; v6',applied=True,evaluations=calls,objective=last,selected_vertices=len(selected),
        root_lift_m=lift.detach().tolist(), max_rotation_delta_degrees=float(torch.linalg.vector_norm(actual_delta,dim=-1).max()*180/torch.pi),
        contact_spec=contact_spec,scene_context=scene_context,hard_bounds=True,normal_constraints=len(normal_constraints),object_constraints=len(objects),
        contact_normalization='Per explicit region, independently of inferred support duration; v3',
        support={k:dict(spans=c['spans'],active_frames=int(c['active'].sum()),provenance=c.get('provenance','inferred')) for k,c in contacts.items()},
        scope='Hard root/rotation budgets with soft clip-wide contact constraints; candidate only until full-mesh and regression checks pass. Sampled box clearance and oriented surface points only; no partner/self collision, anatomy or dynamics certification.')
    return result,recipe
