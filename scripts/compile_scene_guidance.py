"""Freeze authored scene tracks in the generated actor's explicit native frame.

Reference partners remain supplied source motion, not jointly sampled actors.
Compilation never approves feasibility, contact anatomy or physical quality.
"""
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from strep import ROOT,sha256
from scene_constraints import pose,sample_object,transform_motion,target_track,effector_track,vector
from object_geometry import scene_geometry
from inspect_motion import validate_motion


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def compile_scene_guidance(scene,actor,skin,*,project_root=ROOT,origin_xz_m=(0.,0.)):
    original=scene;scene=copy.deepcopy(scene);source_digest=digest(scene);root=Path(project_root).resolve()
    frames=scene.get('frame_count');actors=scene.get('actors');objects=scene.get('objects',{});contacts=scene.get('contacts',[])
    if scene.get('schema_version')!=1 or scene.get('fps')!=30 or type(frames) is not int or not 3<=frames<=300 or not isinstance(actors,dict) or not 1<=len(actors)<=10 or actor not in actors:
        raise ValueError('Complete SOMA scene at30fps, one selected actor and3-300 frames required')
    if not isinstance(objects,dict) or len(objects)>16 or not isinstance(contacts,list) or len(contacts)>64:raise ValueError('Complete bounded object/contact populations required')
    if any(not isinstance(k,str) or not k or len(k)>64 for k in [*actors,*objects]):raise ValueError('Bounded distinct actor/object names required')
    if len({c['id'] for c in contacts})!=len(contacts):raise ValueError('Distinct original contact identities required')
    names=list(map(str,skin['rig_joint_names']));vertices=len(skin['bind_vertices']);faces=np.asarray(skin['faces'])
    if len(names)!=77 or not vertices or faces.ndim!=2 or not len(faces) or faces.shape[1]!=3 or faces.dtype.kind not in 'iu' or faces.min()<0 or faces.max()>=vertices:raise ValueError('Complete native SOMA77 skin and topology required')
    origin=np.asarray(origin_xz_m,dtype=float)
    if origin.shape!=(2,) or not np.isfinite(origin).all():raise ValueError('Explicit finite canonical-origin XZ offset required')
    placement,rotation=pose(actors[actor]['transform']);placement=placement+rotation@np.array([origin[0],0.,origin[1]])
    references={};pins={};source_actors={}
    for name,entry in actors.items():
        path=(root/entry['motion']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha256(path)!=entry.get('source_sha256'):raise ValueError('Pinned reference motion inside project required')
        pins[str(path)]=sha256(path)
        with np.load(path,allow_pickle=False) as z:motion={k:z[k] for k in ['posed_joints','local_rot_mats','global_rot_mats','root_positions','foot_contacts']}
        actual_names,_,_=validate_motion(motion,30)
        if actual_names!=names or len(motion['root_positions'])!=frames:raise ValueError('Full reference rig order and clock must match')
        references[name]=transform_motion(motion,entry['transform']);source_actors[name]=dict(motion=entry['motion'],sha256=pins[str(path)],transform=entry['transform'])
    trajectories={name:sample_object(obj,frames) for name,obj in objects.items()};primitives=[]
    for name,obj in objects.items():
        p,r=trajectories[name];primitives.append(dict(id=name,geometry=scene_geometry(obj).record(),positions_m=((p-placement)@rotation).tolist(),rotations=(rotation.T@r).tolist()))
    floor=scene.get('floor',dict(normal_world=[0.,1.,0.],offset_m=0.));n=vector(floor.get('normal_world'),3,'floor normal');offset=floor.get('offset_m')
    if abs(np.linalg.norm(n)-1)>1e-6 or type(offset) not in (int,float) or not np.isfinite(offset):raise ValueError('Finite unit world floor plane required')
    def direction(request):
        d=vector(request.get('direction'),3,'contact direction')
        if abs(np.linalg.norm(d)-1)>1e-6:raise ValueError('Unit contact direction required')
        if request.get('space')=='world':world=np.tile(d,(frames,1))
        elif request.get('space')=='object' and request.get('object') in trajectories:world=np.einsum('fij,j->fi',trajectories[request['object']][1],d)
        else:raise ValueError('Explicit world/object orientation target required')
        return world@rotation
    compiled=[]
    for c in contacts:
        owner=c.get('actor');target=c.get('target',{});partner=target.get('space')=='actor' and target.get('actor')==actor
        if owner not in actors or target.get('space')=='actor' and target.get('actor') not in actors:raise ValueError('All original contact actors must exist')
        if target.get('space')=='object' and target.get('object') not in objects:raise ValueError('All original contact objects must exist')
        a,b=c['start_frame'],c['end_frame']
        if type(a) is not int or type(b) is not int or not 0<=a<=b<frames:raise ValueError('Original contact interval outside complete clock')
        if owner!=actor and not partner:continue
        if 'region_contact' in c:raise ValueError('Distributed regions require their own energy; cannot reduce them to a point')
        if owner==actor and partner:raise ValueError('Self-contact needs a dynamic same-sample target; cannot freeze it as a reference')
        effector=target if partner else c['effector'];vertex=effector.get('surface_vertex')
        if type(vertex) is not int or not 0<=vertex<vertices:raise ValueError('Explicit native skin contact vertex required')
        world=effector_track(references[owner],c['effector'],skin) if partner else target_track(target,references,trajectories,frames,skin)
        tolerance=c.get('tolerance_m',.03)
        if type(tolerance) not in (int,float) or not np.isfinite(tolerance) or tolerance<=0:raise ValueError('Positive original contact tolerance required')
        row=dict(id=c['id'],source_actor=owner,reciprocal_point=partner,vertex=vertex,start_frame=a,end_frame=b,targets_m=((world[a:b+1]-placement)@rotation).tolist(),tolerance_m=tolerance,
            target_provenance='fixed reference partner track' if partner or target['space']=='actor' else 'authored world/object track',effector_metadata=copy.deepcopy(effector))
        if not partner and c.get('normal_target'):
            row['normal_directions']=direction(c['normal_target'])[a:b+1].tolist();adjacent=faces[np.any(faces==vertex,axis=1)]
            if not len(adjacent):raise ValueError('Contact normal needs its actual adjacent skin triangles')
            row['normal_faces']=adjacent.tolist()
        if not partner and c.get('tangent_target'):
            if 'normal_directions' not in row:raise ValueError('A tangent requires an explicit normal')
            hand=effector.get('joint');knuckles=[hand+f+'2' for f in ['Index','Middle','Ring','Pinky']] if hand in ['LeftHand','RightHand'] else []
            if not knuckles or any(k not in names for k in knuckles):raise ValueError('Hand tangent requires actual wrist/knuckle mappings')
            td=direction(c['tangent_target'])[a:b+1]
            if np.max(abs(np.sum(td*np.asarray(row['normal_directions']),axis=1)))>1e-6:raise ValueError('Authored normal and tangent must be orthogonal')
            row.update(tangent_directions=td.tolist(),hand_joint=names.index(hand),knuckle_joints=[names.index(k) for k in knuckles])
        compiled.append(row)
    if any(sha256(p)!=h for p,h in pins.items()) or digest(original)!=source_digest:raise ValueError('Scene or pinned references changed during compilation')
    return dict(schema='strep-authored-scene-guidance-v1',scene_id=scene.get('id'),scene_sha256=source_digest,actor=actor,frames=frames,fps=30,vertices=vertices,joint_names=names,
        actor_placement_m=placement.tolist(),actor_rotation=rotation.tolist(),explicit_origin_xz_m=origin.tolist(),floor_normal=(n@rotation).tolist(),floor_offset_m=float(offset-n@placement),
        primitives=primitives,contacts=compiled,all_original_contact_ids=[c['id'] for c in contacts],reference_actors=source_actors,reference_source_sha256=pins,partner_collision_evaluated=False,
        quality_approved=False,release_approved=False,scope='Complete authored primitive tracks and selected actor skin contacts/orientation intervals in explicit native coordinates, retaining original scene digest/contact identities and all reference source hashes. Reciprocal points use supplied fixed partner motion, not jointly sampled motion. All supplied objects retained. No partner triangle/self/continuous collision, forces, attachment, feasibility, semantics or human approval.')
