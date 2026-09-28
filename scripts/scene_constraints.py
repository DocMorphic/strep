"""Shared-clock scene targets for objects and multiple humanoid actors.

Scene transforms and trajectories are authored fixtures, not model predictions.
Collision diagnostics use skin vertices inside oriented boxes, not mesh/mesh CCD.
"""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from strep import ROOT,sha256
from inspect_motion import skeleton_metadata,validate_motion
from floor_contact import Surface


def vector(value,n,label):
    if not isinstance(value,list) or len(value)!=n or any(type(x) not in [float,int] or not np.isfinite(x) for x in value):raise ValueError('Invalid '+label)
    return np.array(value,dtype=float)


def pose(value):
    if not isinstance(value,dict) or set(value)-{'translation_m','rotation_xyzw','frame'}:raise ValueError('Invalid pose fields')
    p=vector(value.get('translation_m'),3,'translation')
    q=vector(value.get('rotation_xyzw'),4,'rotation')
    if abs(np.linalg.norm(q)-1)>1e-5:raise ValueError('Scene quaternion must have unit length')
    return p,Rotation.from_quat(q).as_matrix()


def sample_object(obj,frames):
    if obj.get('shape')!='box':raise ValueError('Only oriented box geometry is implemented')
    size=vector(obj.get('size_m'),3,'box dimensions')
    if np.any(size<=0):raise ValueError('Box dimensions must be positive')
    keys=obj.get('keyframes')
    if not isinstance(keys,list) or not keys:raise ValueError('Object needs a pose track')
    indices=[k.get('frame') for k in keys]
    if any(type(i)!=int for i in indices) or indices[0]!=0 or any(b<=a for a,b in zip(indices,indices[1:])) or indices[-1]>=frames:raise ValueError('Invalid object keyframe times')
    if len(keys)>1 and indices[-1]!=frames-1:raise ValueError('Animated object track must cover the clip')
    sampled=[pose(k) for k in keys]
    if len(keys)==1:return np.repeat(sampled[0][0][None],frames,0),np.repeat(sampled[0][1][None],frames,0)
    times=np.arange(frames);positions=np.stack([np.interp(times,indices,[p[axis] for p,_ in sampled]) for axis in range(3)],1)
    rotations=Slerp(indices,Rotation.from_matrix(np.stack([r for _,r in sampled])))(times).as_matrix()
    return positions,rotations


def transform_motion(motion,transform):
    p,r=pose(transform)
    return dict(positions=np.einsum('ij,fkj->fki',r,motion['posed_joints'])+p,
                rotations=np.einsum('ij,fkjl->fkil',r,motion['global_rot_mats']))


def joint_point(actor,joint,offset):
    names,_,_=skeleton_metadata(77)
    if joint not in names:raise ValueError('Unknown joint '+str(joint))
    j=names.index(joint);offset=vector(offset,3,'joint-local offset')
    return actor['positions'][:,j]+np.einsum('fij,j->fi',actor['rotations'][:,j],offset)


def effector_track(actor,effector,skin=None):
    if 'surface_vertex' in effector:
        if skin is None:raise ValueError('Surface contact requires skin geometry')
        from palm_contacts import surface_track
        return surface_track(actor,skin,effector['surface_vertex'])
    return joint_point(actor,effector.get('joint'),effector.get('offset_m'))


def target_track(target,actors,objects,frames,skin=None):
    space=target.get('space')
    if space=='world':return np.repeat(vector(target.get('point_m'),3,'world target')[None],frames,0)
    if space=='object':
        name=target.get('object')
        if name not in objects:raise ValueError('Unknown target object')
        p,r=objects[name];point=vector(target.get('point_m'),3,'object-local target')
        return p+np.einsum('fij,j->fi',r,point)
    if space=='actor':
        name=target.get('actor')
        if name not in actors:raise ValueError('Unknown target actor')
        return effector_track(actors[name],target,skin)
    raise ValueError('Unknown scene target space')


def box_vertex_depth(vertices,position,rotation,size):
    local=(vertices-position)@rotation
    distance=np.asarray(size)/2-np.abs(local)
    return np.maximum(0,distance.min(-1))


def evaluate(scene,skin,project_root=ROOT):
    if scene.get('schema_version')!=1 or scene.get('fps')!=30:raise ValueError('Scene schema/fps mismatch')
    frames=scene.get('frame_count')
    if type(frames)!=int or not 3<=frames<=1800:raise ValueError('Invalid scene duration')
    actors={};provenance={}
    for name,entry in scene['actors'].items():
        path=(Path(project_root)/entry['motion']).resolve()
        if not path.is_relative_to(Path(project_root).resolve()):raise ValueError('Motion escapes project')
        motion=dict(np.load(path,allow_pickle=False));validate_motion(motion,30)
        if len(motion['root_positions'])!=frames:raise ValueError('Actor clock/duration mismatch')
        actors[name]=transform_motion(motion,entry['transform']);provenance[name]=dict(path=entry['motion'],sha256=sha256(path))
    if not actors:raise ValueError('Scene needs an actor')
    objects={name:sample_object(obj,frames) for name,obj in scene.get('objects',{}).items()}
    contacts=[];tracks={};ids=set()
    for c in scene['contacts']:
        if c['id'] in ids:raise ValueError('Duplicate contact id')
        ids.add(c['id']);a,b=c['start_frame'],c['end_frame']
        if type(a)!=int or type(b)!=int or not 0<=a<=b<frames:raise ValueError('Contact interval outside scene')
        if c['actor'] not in actors:raise ValueError('Unknown contact actor')
        effector=c['effector'];actual=effector_track(actors[c['actor']],effector,skin)
        target=target_track(c['target'],actors,objects,frames,skin);errors=np.linalg.norm(actual-target,axis=1)
        tolerance=c.get('tolerance_m',.03)
        if type(tolerance) not in [int,float] or not np.isfinite(tolerance) or tolerance<=0:raise ValueError('Invalid contact tolerance')
        valid=np.flatnonzero(errors[a:b+1]<=tolerance)+a
        contacts.append(dict(id=c['id'],actor=c['actor'],start_frame=a,end_frame=b,effector=effector,
            max_interval_error_m=float(errors[a:b+1].max()),mean_interval_error_m=float(errors[a:b+1].mean()),
            frames_within_tolerance=int(len(valid)),interval_frames=b-a+1,first_valid_frame=int(valid[0]) if len(valid) else None,
            first_valid_offset_from_interval_start_frames=int(valid[0]-a) if len(valid) else None,
            nearest_frame=int(errors.argmin()),nearest_distance_m=float(errors.min()),
            all_requested_frames_within_tolerance=bool(np.all(errors[a:b+1]<=tolerance))))
        tracks[c['id']]=dict(actual_world_m=actual.tolist(),target_world_m=target.tolist(),errors_m=errors.tolist())
    collisions=[];surface=Surface(skin)
    for actor_name,actor in actors.items():
        for object_name,(positions,rotations) in objects.items():
            depths=[]
            for f in range(frames):
                vertices=surface.vertices(actor['rotations'][f],actor['positions'][f])
                depths.append(float(box_vertex_depth(vertices,positions[f],rotations[f],scene['objects'][object_name]['size_m']).max()))
            collisions.append(dict(actor=actor_name,object=object_name,max_skin_vertex_depth_m=max(depths),frames_over_1cm=int(np.sum(np.array(depths)>.01)),per_frame_max_depth_m=depths))
    return dict(scene_id=scene['id'],fps=30,frame_count=frames,sources=provenance,contacts=contacts,contact_tracks=tracks,
        object_collisions=collisions,object_tracks={name:dict(positions_m=p.tolist(),rotations_xyzw=Rotation.from_matrix(r).as_quat().tolist(),provenance=scene['objects'][name].get('trajectory_provenance','authored')) for name,(p,r) in objects.items()},
        partner_collision=None,object_attachment=None,scope='Authored shared-clock transforms and targets; no joint scene-aware generation or interaction correction. Effector offsets are declared proxies. Box tests cover sampled skin vertices only; no triangle intersections, self/partner collision, forces or continuous-time proof.')
