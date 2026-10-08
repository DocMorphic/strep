"""Hand-frame fitting and frozen partner surface cuts with hard edit budgets.

Object tracks and optional partner clearance planes are frozen. No joint partner,
self-collision, anatomy or dynamics solve; independent geometry audit required.
"""
import numpy as np
import torch
from scipy.ndimage import gaussian_filter1d
from floor_contact import Surface,reconstruct
from inspect_motion import skeleton_metadata
from support_contact_v5 import infer_support,bounded_rotation,bounded_lift,rodrigues,contact_losses,correction_basis,CONFIG as BASE_CONFIG
from scene_solver_context import context_primitives
CONFIG={**BASE_CONFIG,'iterations':100,'partner_clearance_m':.002,'partner_penalty':10000.,'outer_stages':3,'penalty_growth':4.,'point_tolerance_m':.005,'normal_tolerance_degrees':10.,'authored_slide_weight':1.,'fade_contact_weight':6.,'orientation_weight':5.,'object_collision_weight':10000.,'object_clearance_m':.002,'object_uniform_stride':48,'object_near_samples':48}


def select_inferred_supports(contacts, requested):
    """Select existing active inference without overriding explicit/disabled intent."""
    if not isinstance(requested,(list,tuple)) or any(not isinstance(name,str) for name in requested) or len(set(requested))!=len(requested):
        raise ValueError('Distinct inferred support region names required')
    for name in requested:
        if name not in contacts:raise ValueError('Unknown inferred support region: '+name)
        row=contacts[name]
        if row.get('provenance','inferred')!='inferred':
            raise ValueError('Cannot replace authored or disabled support: '+name)
        if not np.any(row['active']):raise ValueError('No active inferred support: '+name)
    return [name in requested for name in contacts]


def normalized_support_residual(point_violation, tolerance):
    """Dimensionless residual with the same feasible set and original tolerance."""
    scale=torch.as_tensor(tolerance,dtype=point_violation.dtype,device=point_violation.device)
    if not torch.isfinite(scale).all() or (scale<=0).any():raise ValueError('Positive finite support tolerance required')
    return point_violation/scale


def inequality_merit(g,multiplier,penalty):
    """PHR inequality merit for g <= 0; multipliers held fixed per subproblem."""
    return (torch.relu(multiplier+penalty*g).square()-multiplier.square())/(2*penalty)


def object_clearance_target(margin):
    """Optional stricter solver target; acceptance CONFIG remains unchanged."""
    if type(margin) not in [int,float] or not np.isfinite(margin) or margin<0:
        raise ValueError('Object clearance margin must be finite and nonnegative')
    return CONFIG['object_clearance_m']+margin


def object_constraint_residuals(vertex_violations,mode):
    """Same feasible set, either a maximum row or one row per vertex."""
    if mode not in ['maximum','per_vertex']:raise ValueError('Unknown object constraint mode')
    if vertex_violations.ndim!=2 or min(vertex_violations.shape)<1:raise ValueError('Nonempty frame by vertex residuals required')
    return vertex_violations.amax(1) if mode=='maximum' else vertex_violations


def object_constraint_merit(residuals,multipliers,penalty,mode):
    if mode not in ['maximum','per_vertex']:raise ValueError('Unknown object constraint mode')
    expected=1 if mode=='maximum' else 2
    if residuals.ndim!=expected or multipliers.shape!=residuals.shape:raise ValueError('Object multiplier layout mismatch')
    merits=inequality_merit(residuals,multipliers,penalty)
    # Sum, rather than mean, keeps a single violating vertex at its original
    # weight. Multiple violations deliberately contribute multiple penalties.
    return merits.mean() if mode=='maximum' else merits.sum(1).mean()


def relative_track_speed(points,targets,fps=30):
    return torch.linalg.vector_norm(torch.diff(points-targets,dim=0)*fps,dim=-1)


def torch_box_depth(points,position,rotation,size,clearance=0.):
    local=torch.einsum('fvi,fij->fvj',points-position[:,None,:],rotation)
    return torch.relu((size/2+clearance-local.abs()).amin(-1))


def torch_primitive_depth(points,position,rotation,geometry,clearance=0.):
    """Preserve box-face inflation; use Euclidean sphere/cylinder clearance."""
    if geometry.shape=='box':
        size=torch.as_tensor(geometry.dimensions,dtype=points.dtype,device=points.device)
        return torch_box_depth(points,position,rotation,size,clearance)
    return torch.relu(torch_primitive_clearance_violation(points,position,rotation,geometry,clearance))


def torch_primitive_clearance_violation(points,position,rotation,geometry,clearance):
    """Signed violation of the existing inflated primitive (negative outside)."""
    if geometry.shape=='sphere':
        return geometry.dimensions[0]+clearance-torch.linalg.vector_norm(points-position[:,None,:],dim=-1)
    if geometry.shape=='cylinder':
        local=torch.einsum('fvi,fij->fvj',points-position[:,None,:],rotation)
        q=torch.stack([torch.linalg.vector_norm(local[..., [0,2]],dim=-1)-geometry.dimensions[0],local[...,1].abs()-geometry.dimensions[1]/2],dim=-1)
        return clearance-torch.linalg.vector_norm(torch.relu(q),dim=-1)-torch.minimum(q.amax(-1),q.new_tensor(0.))
    size=torch.as_tensor(geometry.dimensions,dtype=points.dtype,device=points.device)
    local=torch.einsum('fvi,fij->fvj',points-position[:,None,:],rotation)
    buffer=clearance[...,None] if torch.is_tensor(clearance) and clearance.ndim else clearance
    return (size/2+buffer-local.abs()).amin(-1)


def finger_rotation_budgets(names):
    result={}
    for side in ['Left','Right']:
        for finger in ['Thumb','Index','Middle','Ring','Pinky']:
            for joint in range(1,4 if finger=='Thumb' else 5):
                name=side+'Hand'+finger+str(joint)
                if name not in names:raise ValueError('Native finger chain is missing')
                result[names.index(name)]=float((8 if finger=='Thumb' else 5) if joint==1 else 12)
    return result


def bounded_edit_rotations(parameters,limits,body_count,physical_fingers=False):
    if physical_fingers:
        parameters=torch.cat([parameters[:,:body_count],parameters[:,body_count:]/limits[:,body_count:]],dim=1)
    return bounded_rotation(parameters,limits)


def solver_stage_count(requested):
    count=CONFIG['outer_stages'] if requested is None else requested
    if type(count)!=int or not 1<=count<=12:raise ValueError('Outer stage count must be an integer from 1 to 12')
    return count


def solver_iteration_count(requested):
    count=CONFIG['iterations'] if requested is None else requested
    if type(count)!=int or not 1<=count<=1000:raise ValueError('Iterations must be an integer from 1 to 1000')
    return count


def object_sampling_layout(selected,vertex_count,full):
    """Extend object coverage without changing the existing floor sample."""
    if type(full)!=bool:raise ValueError('Explicit full-skin boolean required')
    raw=np.asarray(sorted(selected))
    if raw.dtype.kind not in 'iu' or type(vertex_count)!=int or vertex_count<=0:
        raise ValueError('Integer vertex identities required')
    original=raw.astype(int)
    if not len(original) or original[0]<0 or original[-1]>=vertex_count or len(np.unique(original))!=len(original):
        raise ValueError('Valid distinct source samples required')
    ids=np.arange(vertex_count) if full else original
    return ids,np.searchsorted(ids,original)


def refine(base,previous,skin,progress=None,raw=None,contact_spec=None,scene_context=None,*,finger_edits=False,physical_finger_parameters=False,release_endpoint_guards=False,object_inequalities=False,outer_stage_count=None,region_fitting=None,iteration_count=None,full_object_skin=False,object_constraint_mode="maximum",warm_start=None,object_clearance_margin_m=0.,export_rate_guard=False,export_acceleration_margin_fraction=0.,skin_backend="gather",root_coordinate_mode="legacy",shared_pose=False,preserve_support_regions=(),edit_window=None,export_point_rate_guard=False,authored_point_scaling="metres",export_floor_guard=False,export_point_position_guard=False,native_body_references=None,native_support_references=None,root_optimizer_scale_m=1.,constraint_restore_steps=0,intentional_object_contacts=False,object_subframe_divisions=1,object_sample_margin_m=0.,point_numerical_margin_m=0.):
    from point_numerical_headroom import validate_margin,working_limits
    validate_margin(point_numerical_margin_m)
    if point_numerical_margin_m and (contact_spec is None or region_fitting is not None):raise ValueError('Point numerical headroom requires an explicit point specification and no distributed fitter')
    if type(object_subframe_divisions) is not int or not 1<=object_subframe_divisions<=8:raise ValueError('Object playback divisions must be 1–8')
    if type(object_sample_margin_m) not in (int,float) or not np.isfinite(object_sample_margin_m) or not 0<=object_sample_margin_m<=.001:raise ValueError('Finite numerical object margin in [0,1mm] required')
    if (object_subframe_divisions>1 or object_sample_margin_m) and not object_inequalities:raise ValueError('Object playback guards require object inequalities')
    if type(intentional_object_contacts)!=bool:raise ValueError('Explicit intentional object contact boolean required')
    if intentional_object_contacts and (not object_inequalities or region_fitting is not None or scene_context is None or 'intentional_object_clearance' not in scene_context):
        raise ValueError('Intentional object contact requires compiled point-contact policy and object inequalities')
    if not intentional_object_contacts and scene_context is not None and 'intentional_object_clearance' in scene_context:
        raise ValueError('Intentional clearance policy requires its explicit correction mode')
    if type(constraint_restore_steps) is not int or not 0<=constraint_restore_steps<=20:
        raise ValueError('Constraint restoration steps must be an integer in [0,20]')
    if constraint_restore_steps and (root_coordinate_mode!='physical_box' or not all([export_rate_guard,export_point_rate_guard,export_floor_guard,export_point_position_guard]) or native_support_references is None or scene_context is not None or finger_edits or region_fitting is not None or release_endpoint_guards or shared_pose or preserve_support_regions or object_inequalities):
        raise ValueError('Constraint restoration requires stationary body contacts, physical_box, all export guards and native support references')
    if authored_point_scaling not in ["metres","tolerance"]:raise ValueError("Unknown authored point scaling")
    if root_coordinate_mode not in ["legacy","scaled_initial","physical_box"]:raise ValueError("Unknown root coordinate mode")
    if type(root_optimizer_scale_m) not in (int,float) or not np.isfinite(root_optimizer_scale_m) or root_optimizer_scale_m<=0:
        raise ValueError('Positive finite root optimizer scale required')
    if root_coordinate_mode!='physical_box' and root_optimizer_scale_m!=1.:
        raise ValueError('Root optimizer scaling requires physical_box coordinates')
    if object_constraint_mode not in ["maximum","per_vertex"]:raise ValueError("Unknown object constraint mode")
    if object_constraint_mode!="maximum" and not object_inequalities:raise ValueError("Per-vertex constraints require object inequalities")
    if skin_backend not in ["gather","sparse"]:raise ValueError("Unknown skin backend")
    if type(shared_pose)!=bool:raise ValueError('Explicit shared-pose boolean required')
    if shared_pose:
        if edit_window is not None:raise ValueError('Shared pose does not support a local edit window')
        from shared_pose_diagnostic import require_repeated_motion,shared_basis
        count=require_repeated_motion(base)
        for track in [previous,raw,warm_start]:
            if track is not None:require_repeated_motion(track,count)
        if release_endpoint_guards:raise ValueError('Shared pose does not support release guards')
    object_clearance=object_clearance_target(object_clearance_margin_m)
    stage_count=solver_stage_count(outer_stage_count)
    iterations=solver_iteration_count(iteration_count)
    if physical_finger_parameters and not finger_edits:raise ValueError('Physical finger parameters require finger controls')
    torch.set_num_threads(2)
    names,parents,_=skeleton_metadata(77); surface=Surface(skin)
    contacts=infer_support(base,skin)
    guards=[];effective_spec=contact_spec
    if release_endpoint_guards:
        from scene_release_guards import extend_solver_spec
        if contact_spec is None or scene_context is None or 'release_guards' not in scene_context:raise ValueError('Compiled release guards required')
        guards=scene_context['release_guards'];effective_spec=extend_solver_spec(contact_spec,guards)
    if contact_spec is not None:
        from contact_spec import apply_overrides
        contacts=apply_overrides(contacts,base,skin,effective_spec,CONFIG['fade_frames'],CONFIG['clearance_m'])
    # Small body set; facial, finger and toe articulation remain unchanged.
    editable=[names.index(n) for n in ['Spine1','Spine2','Chest','Neck1','Neck2','Head',
        'LeftShoulder','LeftArm','LeftForeArm','LeftHand','RightShoulder','RightArm','RightForeArm','RightHand',
        'LeftLeg','LeftShin','LeftFoot','RightLeg','RightShin','RightFoot']]
    body_count=len(editable);fingers=finger_rotation_budgets(names) if finger_edits else {}
    editable.extend(fingers)
    limits=[CONFIG['max_rotation_degrees']]*body_count+list(fingers.values())
    T=len(base['root_positions']); dtype=torch.float64
    context=scene_context or dict(frame_count=T,boxes=[],normals=[])
    if context['frame_count']!=T:raise ValueError('Scene context clock mismatch')
    primitive_records=context_primitives(context)
    def tensor(x):return torch.as_tensor(np.asarray(x),dtype=dtype)
    rotation_limits=tensor(np.deg2rad(limits))[None,:,None] if finger_edits else np.deg2rad(CONFIG['max_rotation_degrees'])
    def bounded_edits(values):return bounded_edit_rotations(values,rotation_limits,body_count,physical_finger_parameters)
    offsets=np.zeros_like(base['posed_joints'],dtype=float)
    for j,p in enumerate(parents):
        if p>=0:offsets[:,j]=np.einsum('fji,fj->fi',base['global_rot_mats'][:,p],base['posed_joints'][:,j]-base['posed_joints'][:,p])
    offsets=tensor(offsets); initial=tensor(previous['local_rot_mats']);root=tensor(base['root_positions'])
    basis,knots=shared_basis(T) if shared_pose else correction_basis(T,CONFIG['knot_spacing_frames']);basis=tensor(basis)
    delta=torch.zeros((len(knots),len(editable),3),dtype=dtype,requires_grad=True)
    initialization=None
    if warm_start is not None:
        from scene_fit_initialization import recover_controls
        if not np.array_equal(previous['local_rot_mats'],base['local_rot_mats']):raise ValueError('Warm starts require the original clip as the rotation reference')
        controls,initialization=recover_controls(base['local_rot_mats'],warm_start['local_rot_mats'],editable,np.deg2rad(limits),body_count,physical_finger_parameters,basis.detach().numpy())
        with torch.no_grad():delta.copy_(tensor(controls))
    localization=None;control_transform=None;seed_controls=None;outside_keys=None
    if edit_window is not None:
        from localized_spline import localized_controls
        if not np.array_equal(previous['local_rot_mats'],base['local_rot_mats']):
            raise ValueError('Localized fitting requires the original rotation reference')
        transform,outside,localization=localized_controls(basis.detach().numpy(),edit_window)
        outside_keys=torch.as_tensor(outside,dtype=torch.bool)
        control_transform=tensor(transform);seed_controls=delta.detach().clone()
        delta=torch.zeros((transform.shape[1],len(editable),3),dtype=dtype,requires_grad=True)
    def smooth_delta():
        controls=delta if control_transform is None else seed_controls+torch.einsum('kr,rjd->kjd',control_transform,delta)
        return torch.einsum('fk,kjd->fjd',basis,controls)
    initial_lift=tensor((previous if warm_start is None else warm_start)['root_positions'][:,1]-base['root_positions'][:,1])
    if shared_pose:initial_lift=initial_lift[:1]
    root_coordinates=None
    if root_coordinate_mode in ['legacy','physical_box']:
        unit=(initial_lift/CONFIG['max_root_lift_m']).clamp(1e-4,1-1e-4)
        lift_parameters=torch.logit(unit).clone().requires_grad_()
        if root_coordinate_mode=='physical_box':lift_parameters=bounded_lift(lift_parameters,CONFIG['max_root_lift_m']).detach().clone().requires_grad_()
    else:
        from bounded_root_coordinates import BoundedRootCoordinates
        root_coordinates=BoundedRootCoordinates(initial_lift,CONFIG['max_root_lift_m'])
        lift_parameters=root_coordinates.initial_parameters().requires_grad_()
    def root_lift():
        value=lift_parameters if root_coordinate_mode=='physical_box' else (bounded_lift(lift_parameters,CONFIG['max_root_lift_m']) if root_coordinates is None else root_coordinates(lift_parameters))
        if outside_keys is not None:value=torch.where(outside_keys,initial_lift,value)
        return value.expand(T) if shared_pose else value
    lookup={j:i for i,j in enumerate(editable)}
    reference=tensor((base if raw is None else raw)['posed_joints'])
    def fk():
        change=rodrigues(bounded_edits(smooth_delta()));r=[];p=[];locals=[]
        lift=root_lift()
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
    selected=set() if region_fitting is None else set(region_fitting.selected)
    for r,p in zip(base['global_rot_mats'],base['posed_joints']):
        heights=surface.vertices(r,p)[:,1]
        selected.update(np.argsort(heights)[:32].tolist())
    for c in contacts.values():selected.update(c['vertex_ids'].tolist())
    normal_faces=[]
    for c in context['normals']:
        faces=skin['faces'][np.any(skin['faces']==c['surface_vertex'],axis=1)]
        if not len(faces):raise ValueError('Contact normal has no surface triangles')
        normal_faces.append(faces);selected.update(faces.reshape(-1).tolist())
    if primitive_records:
        selected.update(range(0,len(skin['bind_vertices']),CONFIG['object_uniform_stride']))
        for source in [base,previous]:
            for f,(r,p) in enumerate(zip(source['global_rot_mats'],source['posed_joints'])):
                points=surface.vertices(r,p)
                for geometry,obj in primitive_records:
                    distances=geometry.distance_gradient(points,np.array(obj['positions_m'][f]),np.array(obj['rotations'][f]))[0]
                    selected.update(np.argsort(distances)[:CONFIG['object_near_samples']].tolist())
    for cut in context.get('partner_cuts',[]):selected.add(cut['vertex'])
    selected,floor_indices=object_sampling_layout(selected,len(skin['bind_vertices']),full_object_skin)
    contact_policy=None
    if intentional_object_contacts:
        from intentional_object_clearance import validate as validate_contact_policy,validate_constraints,margin_tracks
        contact_policy=validate_contact_policy(context['intentional_object_clearance'],skin,primitive_records)
        validate_constraints(contact_policy,effective_spec,primitive_records)
        if contact_policy['frame_count']!=T:raise ValueError('Intentional contact clock differs from clip')
        original_floor_vertices=selected[floor_indices].copy()
        selected=np.unique(np.concatenate([selected,*[np.asarray(c['region_vertices'],dtype=int) for c in contact_policy['contacts']]]))
        floor_indices=np.searchsorted(selected,original_floor_vertices)
    floor_indices=torch.tensor(floor_indices,dtype=torch.long)
    mapping={v:i for i,v in enumerate(selected)}
    if region_fitting is not None:region_fitting.bind(mapping)
    normal_constraints=[]
    for c,faces in zip(context['normals'],normal_faces):
        indices=torch.tensor([[mapping[int(i)] for i in face] for face in faces])
        mask=np.zeros(T);mask[c['start_frame']:c['end_frame']+1]=1
        for guard in guards:
            if guard['contact_id']==c['id']:mask[guard['frame']]=1
        normal_constraints.append((indices,tensor(c['directions']),tensor(mask)))
    objects=[(tensor(b['positions_m']),tensor(b['rotations']),geometry,
        (tensor(margin_tracks(contact_policy,b['id'],selected,object_clearance)) if contact_policy is not None else object_clearance)+object_sample_margin_m) for geometry,b in primitive_records]
    subframe_clock=None;subframe_objects=[]
    if object_subframe_divisions>1:
        if not objects:raise ValueError('Object playback guards need declared geometry')
        from object_subframe_constraints import clock as playback_clock,poses as playback_poses,linear as playback_linear,rotations as playback_rotations
        left,fraction=playback_clock(T,object_subframe_divisions,device=root.device);subframe_clock=(left,fraction)
        subframe_objects=[(playback_linear(op,left,fraction),playback_rotations(orr,left,fraction),geometry,
            playback_linear(margin,left,fraction) if torch.is_tensor(margin) else margin) for op,orr,geometry,margin in objects]

    inds=skin['lbs_indices'][selected];weights=tensor(skin['lbs_weights'][selected])
    bind=tensor(np.einsum('vwij,vj->vwi',surface.inverse[inds],surface.points[selected])[:,:,:3])
    targets=torch.stack([tensor(c['targets']) for c in contacts.values()],1)
    cw=torch.stack([tensor(c['weights']) for c in contacts.values()],1)
    explicit_mask=torch.tensor([c.get('provenance')=='explicit' for c in contacts.values()])
    active=torch.stack([tensor(c['active']) for c in contacts.values()],1)*explicit_mask
    from contact_spec import solver_point_tolerances
    point_tolerance=tensor(solver_point_tolerances(contacts,effective_spec,T,CONFIG['point_tolerance_m'])) if region_fitting is None else tensor(region_fitting.point_tolerances(contacts,T,CONFIG['point_tolerance_m']))
    unbuffered_point_tolerance=point_tolerance
    point_headroom=None
    if point_numerical_margin_m:
        limits,point_headroom=working_limits(point_tolerance.detach().cpu().numpy(),active.detach().cpu().numpy().astype(bool),point_numerical_margin_m)
        point_tolerance=tensor(limits)
    preserved_mask=torch.tensor(select_inferred_supports(contacts,preserve_support_regions))
    preserved_active=torch.stack([tensor(c['active']) for c in contacts.values()],1)*preserved_mask
    preserved_multiplier=torch.zeros_like(active)
    point_multiplier=torch.zeros_like(active)
    normal_multiplier=[torch.zeros(T,dtype=dtype) for _ in normal_constraints]
    tangent_multiplier=[torch.zeros(T,dtype=dtype) for _ in normal_constraints]
    cuts=context.get('partner_cuts',[])
    cut_frames=torch.tensor([c['frame'] for c in cuts],dtype=torch.long)
    cut_vertices=torch.tensor([mapping[c['vertex']] for c in cuts],dtype=torch.long)
    cut_points=tensor([c['point_m'] for c in cuts]).reshape(-1,3)
    cut_normals=tensor([c['normal'] for c in cuts]).reshape(-1,3)
    cut_multiplier=torch.zeros(len(cuts),dtype=dtype);cut_penalty=CONFIG['partner_penalty']
    last_cuts=None;last_tangents=[]
    last_objects=[];object_observation_count=T+(0 if subframe_clock is None else len(subframe_clock[0]));object_multiplier=[torch.zeros(object_observation_count if object_constraint_mode=="maximum" else (object_observation_count,len(selected)),dtype=dtype) for _ in objects]
    object_penalty=2*CONFIG['object_collision_weight']
    point_penalty=CONFIG['explicit_contact_weight'];normal_penalty=CONFIG['orientation_weight']
    stage_records=[];last_point=None;last_normals=[]
    ci=torch.tensor(np.stack([[mapping[v] for v in c['vertex_ids']] for c in contacts.values()],1))
    sparse_skin=None
    if skin_backend=="sparse":
        from linear_skin_operator import LinearSkinOperator
        sparse_skin=LinearSkinOperator(torch.as_tensor(inds,dtype=torch.long),weights,bind,len(names))
    def vertices(r,p):
        if sparse_skin is not None:return sparse_skin(r,p)
        return (((r[:,inds]@bind[None,:,:,:,None]).squeeze(-1)+p[:,inds])*weights[None,:,:,None]).sum(2)
    baseline_vertices=vertices(tensor(base['global_rot_mats']),tensor(base['posed_joints']))
    frame_indices=torch.arange(T-1)[:,None]; patch_indices=ci[:-1]
    original_slide=torch.linalg.vector_norm((baseline_vertices[frame_indices+1,patch_indices]-baseline_vertices[frame_indices,patch_indices])[...,[0,2]]*30,dim=-1)
    if region_fitting is not None and region_fitting.witness_mode=='stage_refresh':
        with torch.no_grad():
            initial_r,initial_p,_=fk()
            region_fitting.initialize_witnesses(vertices(initial_r,initial_p))
    rate_objective=None
    if type(export_rate_guard)!=bool:raise ValueError('Explicit export-rate guard boolean required')
    if export_rate_guard:
        from export_rate_objective import ExportRateObjective
        rate_objective=ExportRateObjective(tensor(base['global_rot_mats']),tensor(base['posed_joints']),parents,export_acceleration_margin_fraction)
    elif export_acceleration_margin_fraction!=0:
        raise ValueError('Acceleration margin requires the export-rate guard')
    point_rate_objective=None
    if type(export_point_rate_guard)!=bool:raise ValueError('Explicit point-rate guard boolean required')
    if export_point_rate_guard:
        from export_point_rate_objective import ExportPointRateObjective
        point_rate_objective=ExportPointRateObjective(tensor(base['global_rot_mats']),tensor(base['posed_joints']),parents,skin,contact_spec,edit_window)
    floor_objective=None
    if type(export_floor_guard)!=bool:raise ValueError('Explicit floor guard boolean required')
    if export_floor_guard:
        from export_floor_objective import ExportFloorObjective
        floor_objective=ExportFloorObjective(tensor(base['global_rot_mats']),tensor(base['posed_joints']),parents,skin)
    position_objective=None
    if type(export_point_position_guard)!=bool:raise ValueError('Explicit point-position guard boolean required')
    if export_point_position_guard:
        if region_fitting is not None or release_endpoint_guards:raise ValueError('Sampled stationary pins do not replace regional or release-guard constraints')
        from export_point_position_objective import ExportPointPositionObjective
        position_objective=ExportPointPositionObjective(tensor(base['global_rot_mats']),tensor(base['posed_joints']),parents,skin,contact_spec,
            tolerance=CONFIG['point_tolerance_m'],scaling=authored_point_scaling,penalty=CONFIG['explicit_contact_weight'])
    body_objective=None
    if native_body_references is not None:
        from native_body_objective import NativeBodyObjective
        if not isinstance(native_body_references,dict) or not native_body_references:raise ValueError('Named native body reference motions required')
        body_objective=NativeBodyObjective({name:tensor(motion['posed_joints']) for name,motion in native_body_references.items()})
    support_objective=None
    if native_support_references is not None:
        from native_support_objective import NativeSupportObjective
        support_objective=NativeSupportObjective(native_support_references,skin)
    calls=0;last={}
    def closure():
        nonlocal calls,last,last_point,last_normals,last_cuts,last_tangents,last_objects
        optimizer.zero_grad();r,p,local_keys=fk();v=vertices(r,p)
        selected_contact=v[torch.arange(T)[:,None],ci]
        contact=((selected_contact-targets)**2).sum(-1)
        inferred_loss,explicit_loss=contact_losses(contact,cw,explicit_mask)
        point_g=torch.linalg.vector_norm(selected_contact-targets,dim=-1)-point_tolerance
        point_residual=normalized_support_residual(point_g,point_tolerance) if authored_point_scaling=="tolerance" else point_g
        point_merit=inequality_merit(point_residual,point_multiplier,point_penalty)
        _,point_loss=contact_losses(point_merit,active,explicit_mask)
        preserved_loss=None
        if preserved_mask.any():
            merit=inequality_merit(normalized_support_residual(point_g,point_tolerance),preserved_multiplier,point_penalty)
            _,preserved_loss=contact_losses(merit,preserved_active,preserved_mask)
        fade_weights=(cw-active).clamp_min(0)*explicit_mask
        _,fade_loss=contact_losses(contact,fade_weights,explicit_mask)
        moving_weights=active[1:]*active[:-1]*(ci[1:]==ci[:-1])
        relative_slide=relative_track_speed(selected_contact,targets)
        _,moving_loss=contact_losses(torch.relu(relative_slide-.03).square(),moving_weights,explicit_mask)
        last_point=point_g.detach();last_normals=[];last_tangents=[]
        displacement=p-reference
        velocity=torch.linalg.vector_norm(torch.diff(displacement,dim=0)*30,dim=-1)
        slide=torch.linalg.vector_norm((v[frame_indices+1,patch_indices]-v[frame_indices,patch_indices])[...,[0,2]]*30,dim=-1)
        terms=dict(collision=torch.relu(CONFIG['clearance_m']-v[:,floor_indices,1]).square().amax(1).mean()*CONFIG['collision_weight'],
            contact=inferred_loss*CONFIG['contact_weight'],
            authored_contact=point_loss if position_objective is None else position_objective.loss(r,p),authored_fade=fade_loss*CONFIG['fade_contact_weight'],authored_slide=moving_loss*CONFIG['authored_slide_weight'],
            pose=bounded_edits(smooth_delta())[:,:body_count].square().mean()*CONFIG['pose_weight'],
            temporal=torch.diff(displacement,n=2,dim=0).square().sum(-1).mean()*CONFIG['temporal_weight'],
            velocity=torch.relu(velocity-1.2).square().amax()*CONFIG['velocity_weight'],
            slide=(torch.relu(slide-original_slide-.02).square()*(cw[:-1]*(~explicit_mask))).sum()/(cw[:-1]*(~explicit_mask)).sum().clamp_min(1)*CONFIG['slide_weight'])
        if body_objective is not None:terms['native_body']=body_objective.loss(p)
        if support_objective is not None:terms['native_support']=support_objective.loss(r,p)
        if preserved_loss is not None:terms['preserved_support']=preserved_loss
        if region_fitting is not None:terms['distributed_region']=region_fitting.loss(v)
        if rate_objective is not None:terms['export_rates']=rate_objective.loss(r,p)
        if point_rate_objective is not None:terms['export_point_rates']=point_rate_objective.loss(r,p)
        if floor_objective is not None:terms['export_floor']=floor_objective.loss(r,p)
        if finger_edits:
            terms['finger_pose']=bounded_edits(smooth_delta())[:,body_count:].square().mean()*CONFIG['pose_weight']
        if normal_constraints:
            normal_loss=[];tangent_loss=[]
            for ni,(triangles,desired,weight) in enumerate(normal_constraints):
                points=v[:,triangles]
                normal=torch.linalg.cross(points[:,:,1]-points[:,:,0],points[:,:,2]-points[:,:,0]).sum(1)
                normal=normal/torch.linalg.vector_norm(normal,dim=-1,keepdim=True).clamp_min(1e-12)
                g=torch.linalg.vector_norm(normal-desired,dim=-1)-2*np.sin(np.deg2rad(CONFIG['normal_tolerance_degrees'])/2)
                normal_loss.append((inequality_merit(g,normal_multiplier[ni],normal_penalty)*weight).sum()/weight.sum().clamp_min(1e-12))
                last_normals.append(g.detach())
                tc=context['normals'][ni]
                if 'tangent_directions' in tc:
                    direction=p[:,tc['knuckle_joints']].mean(1)-p[:,tc['hand_joint']]
                    tangent=direction-normal*(direction*normal).sum(-1,keepdim=True)
                    tangent=tangent/torch.linalg.vector_norm(tangent,dim=-1,keepdim=True).clamp_min(1e-12)
                    tg=torch.linalg.vector_norm(tangent-tensor(tc['tangent_directions']),dim=-1)-2*np.sin(np.deg2rad(CONFIG['normal_tolerance_degrees'])/2)
                    tangent_loss.append((inequality_merit(tg,tangent_multiplier[ni],normal_penalty)*weight).sum()/weight.sum().clamp_min(1e-12))
                    last_tangents.append(tg.detach())
                else:last_tangents.append(torch.zeros(T,dtype=dtype))
            terms['orientation']=torch.stack(normal_loss).mean()
            if tangent_loss:terms['hand_tangent']=torch.stack(tangent_loss).mean()
        if objects:
            if object_inequalities:
                violations=[object_constraint_residuals(torch_primitive_clearance_violation(v,op,orr,geometry,margin),object_constraint_mode) for op,orr,geometry,margin in objects]
                if subframe_clock is not None:
                    left,fraction=subframe_clock
                    between_r,between_p=playback_poses(local_keys,offsets,p[:,0],parents,left,fraction)
                    between_vertices=vertices(between_r,between_p)
                    between=[object_constraint_residuals(torch_primitive_clearance_violation(between_vertices,op,orr,geometry,margin),object_constraint_mode) for op,orr,geometry,margin in subframe_objects]
                    violations=[torch.cat([key,intermediate],dim=0) for key,intermediate in zip(violations,between)]
                terms['object_collision']=torch.stack([object_constraint_merit(g,m,object_penalty,object_constraint_mode) for g,m in zip(violations,object_multiplier)]).mean()
                last_objects=[g.detach() for g in violations]
            else:
                terms['object_collision']=torch.stack([torch_primitive_depth(v,op,orr,geometry,margin).square().amax(1).mean() for op,orr,geometry,margin in objects]).mean()*CONFIG['object_collision_weight']
        if cuts:
            signed=((v[cut_frames,cut_vertices]-cut_points)*cut_normals).sum(-1)
            g=CONFIG['partner_clearance_m']-signed
            terms['partner_cut']=inequality_merit(g,cut_multiplier,cut_penalty).mean()
            last_cuts=g.detach()
        loss=sum(terms.values());loss.backward();calls+=1
        last={k:float(v.detach()) for k,v in terms.items()}
        if progress and calls%20==0:progress(dict(evaluations=calls,loss=float(loss.detach()),terms=last))
        return loss
    for stage in range(stage_count):
        if root_coordinate_mode=='physical_box':
            from box_root_optimizer import BoxRootOptimizer
            optimizer=BoxRootOptimizer(delta,lift_parameters,CONFIG['max_root_lift_m'],iterations,root_scale_m=root_optimizer_scale_m)
        else:
            optimizer=torch.optim.LBFGS([delta,lift_parameters],lr=.8,max_iter=iterations,history_size=12,line_search_fn='strong_wolfe',tolerance_grad=1e-8,tolerance_change=1e-11)
        optimizer.step(closure)
        closure() # Recompute at accepted parameters before multiplier updates.
        stage_records.append(dict(stage=stage,point_penalty=point_penalty,normal_penalty=normal_penalty,objective=last.copy(),
            max_active_point_violation_m=float(torch.relu(last_point)[active.bool()].max()) if active.any() else 0.,
            max_partner_cut_violation_m=float(torch.relu(last_cuts).max()) if cuts else 0.,max_active_tangent_chord_violation=max([float(torch.relu(g)[c[2].bool()].max()) for g,c in zip(last_tangents,normal_constraints)]+[0.]),
            max_active_normal_chord_violation=max([float(torch.relu(g)[c[2].bool()].max()) for g,c in zip(last_normals,normal_constraints)]+[0.])))
        if preserved_mask.any():stage_records[-1]['max_preserved_support_violation_m']=float(torch.relu(last_point)[preserved_active.bool()].max())
        if root_coordinate_mode=='physical_box':stage_records[-1]['optimizer']=optimizer.summary
        if object_inequalities:
            stage_records[-1].update(object_penalty=object_penalty,max_sampled_object_clearance_violation_m=max([float(torch.relu(g).max()) for g in last_objects]+[0.]))
        if region_fitting is not None:stage_records[-1]['regional_constraints']=region_fitting.stage_diagnostics()
        if rate_objective is not None:stage_records[-1]['export_rates']=rate_objective.record()
        if point_rate_objective is not None:stage_records[-1]['export_point_rates']=point_rate_objective.record()
        if floor_objective is not None:stage_records[-1]['export_floor']=floor_objective.record()
        if position_objective is not None:stage_records[-1]['export_point_positions']=position_objective.record()
        if body_objective is not None:stage_records[-1]['native_body']=body_objective.record()
        if support_objective is not None:stage_records[-1]['native_support']=support_objective.record()
        if stage+1<stage_count:
            if body_objective is not None:body_objective.advance_stage(CONFIG['penalty_growth'])
            if support_objective is not None:support_objective.advance_stage(CONFIG['penalty_growth'])
            if rate_objective is not None:rate_objective.advance_stage(CONFIG['penalty_growth'])
            if point_rate_objective is not None:point_rate_objective.advance_stage(CONFIG['penalty_growth'])
            if floor_objective is not None:floor_objective.advance_stage(CONFIG['penalty_growth'])
            if position_objective is not None:position_objective.advance_stage(CONFIG['penalty_growth'])
            if region_fitting is not None:region_fitting.advance_stage(CONFIG['penalty_growth'])
            if preserved_mask.any():preserved_multiplier=torch.relu(preserved_multiplier+point_penalty*normalized_support_residual(last_point,point_tolerance))*preserved_active
            point_residual=normalized_support_residual(last_point,point_tolerance) if authored_point_scaling=="tolerance" else last_point
            point_multiplier=torch.relu(point_multiplier+point_penalty*point_residual)*active
            normal_multiplier=[torch.relu(m+normal_penalty*g)*c[2] for m,g,c in zip(normal_multiplier,last_normals,normal_constraints)]
            tangent_multiplier=[torch.relu(m+normal_penalty*g)*c[2] for m,g,c in zip(tangent_multiplier,last_tangents,normal_constraints)]
            if object_inequalities:
                object_multiplier=[torch.relu(m+object_penalty*g) for m,g in zip(object_multiplier,last_objects)]
                object_penalty*=CONFIG['penalty_growth']
            if cuts:cut_multiplier=torch.relu(cut_multiplier+cut_penalty*last_cuts)
            point_penalty*=CONFIG['penalty_growth'];normal_penalty*=CONFIG['penalty_growth'];cut_penalty*=CONFIG['penalty_growth']
    restoration=None
    if constraint_restore_steps:
        from constraint_restoration import restore
        from native_contact_constraints import residuals
        from native_body_objective import NativeBodyObjective
        body_guard=body_objective if body_objective is not None else NativeBodyObjective({name:tensor(motion['posed_joints']) for name,motion in native_support_references.items()})
        def constraints():
            r,p,_=fk()
            return residuals(r,p,position_objective,point_rate_objective,rate_objective,floor_objective,body_guard,support_objective)
        with torch.no_grad():before_constraints=constraints().detach().numpy().copy()
        count=delta.numel();root_count=lift_parameters.numel()
        restoration=restore([delta,lift_parameters],constraints,
            np.r_[np.full(count,-np.inf),np.zeros(root_count)],
            np.r_[np.full(count,np.inf),np.full(root_count,CONFIG['max_root_lift_m'])],
            np.r_[np.full(count,.01),np.full(root_count,.0005)],steps=constraint_restore_steps,
            progress=None if progress is None else lambda record:progress(dict(constraint_restoration=record)))
        restoration.update(rotation_control_trust=.01,root_trust_m=.0005,
            scope='Experimental minimax linearization with full nonlinear stationary pin, point/global rate, full-skin floor, native body and fixed-patch support checks. No newly failing proxy entry or increase in an existing proxy violation accepted. Original root/rotation bounds and held keys remain enforced. Export rounding and human quality require independent review.')
        with torch.no_grad():
            r,p,_=fk()
            after_constraints,labels=residuals(r,p,position_objective,point_rate_objective,rate_objective,floor_objective,body_guard,support_objective,with_labels=True)
        restoration['constraints']=[dict(label=label,before=float(a),after=float(b)) for label,a,b in zip(labels,before_constraints,after_constraints)]
        closure()
    with torch.no_grad():
        _,_,local=fk()
        lift=root_lift()
        actual_delta=bounded_edits(smooth_delta())
    shifted={k:v.copy() for k,v in base.items()};shifted['root_positions'][:,1]+=lift.detach().numpy()
    result=reconstruct(shifted,local.detach().numpy().copy(),parents);result.pop('smooth_root_pos',None)
    if localization is not None:
        from scipy.spatial.transform import Rotation
        seed=base if warm_start is None else warm_start
        outside=outside_keys.numpy()
        relative=seed['local_rot_mats'][outside].transpose(0,1,3,2)@result['local_rot_mats'][outside]
        rotation_error=float(Rotation.from_matrix(relative.reshape(-1,3,3)).magnitude().max()) if outside.any() else 0.
        root_error=float(np.max(np.abs(seed['root_positions'][outside]-result['root_positions'][outside]))) if outside.any() else 0.
        if rotation_error>1e-6 or root_error>1e-7:raise ValueError('Unselected seed motion changed')
        from held_pose_preservation import restore_locked_pose
        result=restore_locked_pose(seed,result,outside)
        localization.update(maximum_outside_seed_rotation_error_rad=0.,maximum_outside_seed_root_error_m=0.,
            reconstruction_outside_rotation_error_rad=rotation_error,reconstruction_outside_root_error_m=root_error,
            held_seed='original' if warm_start is None else 'warm_start',held_pose_arrays_bit_exact=True)
    recipe=dict(localization=localization,config={**CONFIG,'outer_stages':stage_count},correction_knots=knots.tolist(),parameterization='Cubic edit controls with hand tangents and frozen partner clearance cuts; v8',partner_cut_count=len(cuts),stage_records=stage_records,applied=True,evaluations=calls,objective=last,selected_vertices=len(selected),
        root_lift_m=lift.detach().tolist(), max_rotation_delta_degrees=float(torch.linalg.vector_norm(actual_delta,dim=-1).max()*180/torch.pi),
        contact_spec=contact_spec,scene_context=scene_context,hard_bounds=True,normal_constraints=len(normal_constraints),object_constraints=len(objects),
        contact_normalization='Per explicit region, independently of inferred support duration; v3',
        support={k:dict(spans=c['spans'],active_frames=int(c['active'].sum()),provenance=c.get('provenance','inferred')) for k,c in contacts.items()},
        scope='Hard root/rotation budgets with augmented-Lagrangian contact inequalities (not guaranteed feasible); candidate only until full-mesh and regression checks pass. Sampled primitive clearance and oriented surface points only; frozen partner cuts are local approximations, not self/partner collision, anatomy or dynamics certification.')
    if preserved_mask.any():
        recipe['preserved_support']=dict(regions=list(preserve_support_regions),tolerance_m=CONFIG['point_tolerance_m'],
            constraint_normalization='signed point violation divided by original point tolerance',
            scope='Selected inferred source support points, active frames only; augmented inequalities do not guarantee feasibility, a planted sole, balance or force support.')
    if shared_pose:
        recipe['shared_pose']=dict(rotation_control_frames=1,root_control_frames=1,output_frames=T,quality_approved=False)
        recipe['parameterization']='One shared bounded rotation set and root lift; frozen-pose diagnostic only'
    if floor_objective is not None:recipe['export_floor']=floor_objective.record()
    if position_objective is not None:recipe['export_point_positions']=position_objective.record()
    recipe['authored_point_scaling']=authored_point_scaling
    recipe['root_coordinate_mode']=root_coordinate_mode
    recipe['root_optimizer_scale_m']=root_optimizer_scale_m
    if restoration is not None:recipe['constraint_restoration']=restoration
    if root_coordinates is not None:recipe['root_coordinate_reference']=root_coordinates.record()
    if finger_edits:
        recipe['finger_edits']=dict(budgets_degrees={names[j]:v for j,v in fingers.items()},
            parameter_units='physical_radians_before_smooth_bound' if physical_finger_parameters else 'dimensionless_bound_fraction',
            measured_max_degrees={names[j]:float(torch.linalg.vector_norm(actual_delta[:,editable.index(j)],dim=-1).max()*180/torch.pi) for j in fingers},
            scope='Reuses earlier native finger-edit budgets. No anatomical axes/ranges or self-collision constraint; requires independent geometry and temporal review.')
    if release_endpoint_guards:
        recipe['release_endpoint_guards']=dict(guards=guards,solver_contact_spec=effective_spec,
            scope='Target and surface frame enforced at the release boundary as an additional solver key; authored scene contacts/events unchanged. This is not a continuous-time constraint guarantee.')
    if object_inequalities:
        recipe['object_inequalities']=dict(initial_penalty=2*CONFIG['object_collision_weight'],growth=CONFIG['penalty_growth'],mode=object_constraint_mode,
            reduction='sum over vertex constraints, mean over frames and objects' if object_constraint_mode=='per_vertex' else 'maximum vertex constraint, mean over frames and objects',
            scope='Existing inflated geometry and selected skin vertices. Per-vertex mode has separate multipliers and greater total weight when multiple vertices violate. No continuous-time or feasibility guarantee.')
    if region_fitting is not None:recipe['distributed_regions']=region_fitting.record()
    if contact_policy is not None:
        recipe['intentional_object_clearance']=dict(policy=contact_policy,default_margin_m=object_clearance,
            original_floor_vertices=original_floor_vertices.tolist(),
            scope='Complete declared hand/foot skin regions have zero extra buffer only against their named object on contact/release keys. Every selected vertex retains nonpenetration; other regions, objects and times retain the configured buffer. Whole-skin independent checks remain required; no anatomical or force approval.')
    if subframe_clock is not None:
        recipe['object_playback_guard']=dict(divisions=object_subframe_divisions,left_frames=subframe_clock[0].cpu().tolist(),fractions=subframe_clock[1].cpu().tolist(),
            key_samples=T,intermediate_samples=len(subframe_clock[0]),sampled_vertices=len(selected),objects=len(objects),numerical_margin_m=object_sample_margin_m,
            scope='Every adjacent key interval and declared object, shortest local-quaternion interpolation plus linear native offsets/root and hierarchical FK. Same selected skin set. Not float32 export or engine equivalence, full mesh or continuous collision proof.')
    recipe['object_clearance_target_m']=object_clearance
    recipe['object_clearance_margin_m']=object_clearance_margin_m
    if rate_objective is not None:recipe['export_rates']=rate_objective.record()
    if point_rate_objective is not None:recipe['export_point_rates']=point_rate_objective.record()
    if body_objective is not None:recipe['native_body']=body_objective.record()
    if support_objective is not None:recipe['native_support']=support_objective.record()
    recipe['point_tolerance_policy']=dict(default_m=CONFIG['point_tolerance_m'],per_frame_region_limits_m=point_tolerance.detach().cpu().tolist(),
        scope='Explicit point intervals may tighten the existing solver limit; they never relax it. Distributed regions retain their own anchor limits. Numerical convergence still requires independent evaluation.')
    if point_headroom is not None:
        recipe['point_tolerance_policy']['numerical_headroom']=dict(requested_margin_m=point_numerical_margin_m,maximum_fraction=.01,
            per_frame_region_unbuffered_limits_m=unbuffered_point_tolerance.detach().cpu().tolist(),per_frame_region_reserved_m=point_headroom.tolist(),
            scope='Stricter working limits on active explicit keys only. Authored specifications and independent acceptance unchanged. No guaranteed solver, interpolation or export error bound.')
    recipe['initialization']=initialization
    recipe['skin_backend']=skin_backend
    recipe['iterations_per_stage']=iterations
    recipe['object_sampling']=dict(mode='all_vertices' if full_object_skin else 'frozen_subset',
        object_vertices=len(selected),floor_vertices=len(floor_indices),
        scope='Only object coverage changes; original floor sample and contact/edit/acceptance limits retained.')
    return result,recipe
