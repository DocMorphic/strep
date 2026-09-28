"""Clip-fitted bone-local convex proxies; actual exported skeleton clock.

Regions follow dominant skin weights. Finger/toe/face bones merge into a hand,
foot or head proxy. All eight influences remain in the skin used for fitting.
These rigid envelopes are not a deformable-body or contact-force model.
"""
import itertools
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from strep import ROOT,sha256
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from scene_constraints import pose
from convex_colliders import direction_hull

DIRECTIONS=np.array([x for x in itertools.product([-1.,0.,1.],repeat=3) if any(x)])
DIRECTIONS/=np.linalg.norm(DIRECTIONS,axis=1)[:,None]


def region_name(name):
    for side in ['Left','Right']:
        if name.startswith(side+'Hand'):return side+'Hand'
        if name.startswith(side+'Toe'):return side+'Foot'
    if name in ['HeadEnd','Jaw','LeftEye','RightEye']:return 'Head'
    return name


def fit_actor(path,frames,progress=None):
    rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
    if type(frames)!=int or frames<4 or abs(sampler.duration-(frames-1)/30)>1e-5:raise ValueError('Actor export duration does not match the scene clock')
    if len(rig.primitives)!=1:raise ValueError('Actor proxies currently require the native single-mesh skin')
    primitive=rig.primitives[0]
    if primitive['joints'] is None:raise ValueError('Actor skin required')
    names=[rig.document['nodes'][int(j)].get('name') for j in rig.joints]
    from inspect_motion import skeleton_metadata
    if names!=skeleton_metadata(77)[0]:raise ValueError('Actor proxies currently require native SOMA77')
    assigned=primitive['joints'][np.arange(len(primitive['joints'])),primitive['weights'].argmax(axis=1)]
    labels=np.array([region_name(names[int(i)]) for i in assigned])
    groups={name:np.flatnonzero(labels==name) for name in dict.fromkeys(labels)}
    nodes={name:int(rig.joints[names.index(name)]) for name in groups}
    supports={name:np.full(len(DIRECTIONS),-np.inf) for name in groups}
    # No collision result is used to tune these envelopes. Whole-clip skin is
    # measured before simulation, including authored prefix and retained tail.
    for frame in range(frames):
        matrices=sampler.sample(frame/30);vertices=rig.vertices(matrices)
        for name,ids in groups.items():
            m=matrices[nodes[name]];local=(vertices[ids]-m[:3,3])@m[:3,:3]
            supports[name]=np.maximum(supports[name],(local@DIRECTIONS.T).max(axis=0))
        if progress and frame%30==0:progress(frame,frames)
    parts=[]
    for name in groups:
        points=direction_hull(DIRECTIONS,supports[name]+.001)
        center=(points.min(axis=0)+points.max(axis=0))/2
        parts.append(dict(name=name,node=nodes[name],vertex_ids=groups[name].tolist(),center_local_m=center.tolist(),points_m=(points-center).tolist(),planes_support_m=(supports[name]+.001).tolist()))
    # Whole and half frames: measure assigned-skin misses independently from
    # hull construction. Half-frame samples were not included in the fit.
    missed=0.;excess=0.;worst=None
    for f in np.arange(0,frames-.5,.5):
        matrices=sampler.sample(float(f)/30);vertices=rig.vertices(matrices);tree=cKDTree(vertices)
        for part in parts:
            m=matrices[part['node']];local=(vertices[part['vertex_ids']]-m[:3,3])@m[:3,:3]
            outside=float(max(0.,(local@DIRECTIONS.T-np.array(part['planes_support_m'])).max()))
            if outside>missed:missed=outside;worst=dict(frame=float(f),part=part['name'])
            proxy=(np.array(part['points_m'])+part['center_local_m'])@m[:3,:3].T+m[:3,3]
            excess=max(excess,float(tree.query(proxy)[0].max()))
    report=dict(asset_sha256=sha256(path),frame_count=frames,parts=len(parts),vertices_assigned=len(labels),fitting_margin_m=.001,
        whole_half_frame_skin_outside_plane_max_m=missed,worst_missed_skin=worst,
        proxy_vertex_to_nearest_skin_vertex_max_m=excess,
        scope='26 support directions per dominant-weight region, fitted at whole frames; whole/half-frame assigned skin coverage and proxy-vertex distance to nearest skin vertex. Plane violation underestimates Euclidean outside distance near corners; vertex distances do not bound entire proxy surfaces. No anatomical accuracy, continuous coverage, balance, force or human approval.')
    return rig,sampler,parts,report


def compile_actor_proxies(scene,base,release_frame,*,physics_fps,friction,restitution,progress=None):
    colliders=[];reports=[];frames=scene['frame_count'];steps=(frames-1-release_frame)*(physics_fps//30)
    times=release_frame/30+np.arange(-1,steps+1)/physics_fps
    for actor,entry in scene['actors'].items():
        path=base/entry['preview_glb'];rig,sampler,parts,report=fit_actor(path,frames,progress)
        placement_p,placement_r=pose(entry['transform'])
        matrices=np.array([sampler.sample(float(t)) for t in times])
        for part in parts:
            m=matrices[:,part['node']];r=placement_r@m[:,:3,:3]
            p=(m[:,:3,3]+np.einsum('fij,j->fi',m[:,:3,:3],part['center_local_m']))@placement_r.T+placement_p
            colliders.append(dict(id='actor:'+actor+':'+part['name'],shape='convex',points_m=part['points_m'],positions_m=p.tolist(),
                rotations_xyzw=Rotation.from_matrix(r).as_quat().tolist(),friction=friction,restitution=restitution))
        reports.append(dict(actor=actor,**report,parts_geometry=parts))
    return colliders,dict(actors=reports,actor_motion_responds=False,clock='Actual exported local-TRS interpolation composed through the hierarchy, plus authored world placement; one incoming physics tick before release.')
