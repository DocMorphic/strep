"""Same signed-distance vertex test, bounded to 32 query points per call."""
import itertools
import numpy as np
import trimesh
import rtree
from strep import ROOT,sha256
from floor_contact import Surface
from scene_constraints import transform_motion


def penetration(source_vertices,target_vertices,target_faces,tolerance_m=.005):
    source=np.asarray(source_vertices,dtype=float);target=np.asarray(target_vertices,dtype=float)
    if not np.isfinite(source).all() or not np.isfinite(target).all():raise ValueError('Non-finite surface')
    mesh=trimesh.Trimesh(target,target_faces,process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent:raise ValueError('Partner signed distance requires a closed consistently wound mesh')
    candidates=np.flatnonzero(np.all((source>=target.min(0)-1e-7)&(source<=target.max(0)+1e-7),axis=1))
    result=dict(vertices_checked=len(source),broadphase_candidates=len(candidates),max_depth_m=0.,vertices_over_tolerance=0,deepest_vertex=None)
    for start in range(0,len(candidates),32):
        selected=candidates[start:start+32]
        depths=np.maximum(0,trimesh.proximity.signed_distance(mesh,source[selected]))
        if not np.isfinite(depths).all():raise ValueError('Non-finite signed distance')
        i=int(depths.argmax());value=float(depths[i])
        result['vertices_over_tolerance']+=int(np.sum(depths>tolerance_m))
        if value>result['max_depth_m']:
            result['max_depth_m']=value;result['deepest_vertex']=int(selected[i])
    return result


def audit(scene,skin,frames=None,tolerance_m=.005,progress=None):
    selected=list(range(scene['frame_count'])) if frames is None else sorted(set(frames))
    if not selected or any(type(f)!=int or not 0<=f<scene['frame_count'] for f in selected):raise ValueError('Invalid audit frames')
    if not np.isfinite(tolerance_m) or tolerance_m<=0:raise ValueError('Invalid tolerance')
    actors={};sources={};surface=Surface(skin);pairs=[]
    for name,entry in scene['actors'].items():
        path=(ROOT/entry['motion']).resolve()
        if not path.is_relative_to(ROOT.resolve()):raise ValueError('Motion escapes project')
        actors[name]=transform_motion(dict(np.load(path,allow_pickle=False)),entry['transform']);sources[name]=sha256(path)
        if entry.get('source_sha256') and sources[name]!=entry['source_sha256']:raise ValueError('Source changed')
    for left,right in itertools.combinations(actors,2):
        records=[]
        for f in selected:
            vertices={name:surface.vertices(actors[name]['rotations'][f],actors[name]['positions'][f]) for name in [left,right]}
            directions=[]
            for source,target in [(left,right),(right,left)]:
                measurement=penetration(vertices[source],vertices[target],skin['faces'],tolerance_m)
                vertex=measurement['deepest_vertex']
                measurement['dominant_bone']=surface.names[surface.indices[vertex,surface.weights[vertex].argmax()]] if vertex is not None else None
                directions.append(dict(source=source,target=target,**measurement))
            records.append(dict(frame=f,directions=directions,max_depth_m=max(m['max_depth_m'] for m in directions)))
            if progress:progress(dict(pair=[left,right],frames_checked=len(records),frames_total=len(selected),max_depth_m=max(r['max_depth_m'] for r in records)))
        pairs.append(dict(actors=[left,right],max_depth_m=max(r['max_depth_m'] for r in records),frames_over_tolerance=sum(r['max_depth_m']>tolerance_m for r in records),frames=records))
    return dict(scene_id=scene['id'],sources=sources,frame_count=scene['frame_count'],frames_checked=selected,tolerance_m=tolerance_m,pairs=pairs,
        query_batch_vertices=32,dependencies=dict(trimesh=trimesh.__version__,rtree=rtree.__version__),
        scope='All skin vertices in both directions at listed discrete frames, against closed partner triangle meshes; query batching changes memory use, not selection or tolerance. No edge-only triangle intersections, continuous-time, self-collision or collision-free certification; self-intersections can make inside/outside ambiguous.')
