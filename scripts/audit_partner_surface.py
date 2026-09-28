"""Bidirectional skin-vertex penetration into the other actor's closed mesh.

Discrete frames and vertices only: not a continuous triangle/self-collision proof.
"""
import argparse
import itertools
import time
import numpy as np
import trimesh
import rtree
from strep import ROOT,read,save,sha256,now
from floor_contact import Surface
from build_soma_preview import ASSET
from scene_constraints import transform_motion


def penetration(source_vertices,target_vertices,target_faces,tolerance_m=.005):
    source=np.asarray(source_vertices,dtype=float);target=np.asarray(target_vertices,dtype=float)
    if not np.isfinite(source).all() or not np.isfinite(target).all():raise ValueError('Non-finite surface')
    mesh=trimesh.Trimesh(target,target_faces,process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent:raise ValueError('Partner signed distance requires a closed consistently wound mesh')
    candidates=np.flatnonzero(np.all((source>=target.min(0)-1e-7)&(source<=target.max(0)+1e-7),axis=1))
    result=dict(vertices_checked=len(source),broadphase_candidates=len(candidates),max_depth_m=0.,vertices_over_tolerance=0,deepest_vertex=None)
    if len(candidates):
        # Trimesh documents positive signed distance for an interior point.
        depths=np.maximum(0,trimesh.proximity.signed_distance(mesh,source[candidates]))
        if not np.isfinite(depths).all():raise ValueError('Non-finite signed distance')
        deepest=int(depths.argmax());depth=float(depths[deepest])
        result.update(max_depth_m=depth,vertices_over_tolerance=int(np.sum(depths>tolerance_m)),deepest_vertex=int(candidates[deepest]) if depth>0 else None)
    return result


def audit(scene,skin,frames=None,tolerance_m=.005,progress=None):
    selected=list(range(scene['frame_count'])) if frames is None else sorted(set(frames))
    if not selected or any(type(f)!=int or not 0<=f<scene['frame_count'] for f in selected):raise ValueError('Invalid audit frames')
    if not np.isfinite(tolerance_m) or tolerance_m<=0:raise ValueError('Invalid tolerance')
    actors={};sources={};surface=Surface(skin);pairs=[]
    for name,entry in scene['actors'].items():
        path=(ROOT/entry['motion']).resolve()
        if not path.is_relative_to(ROOT.resolve()):raise ValueError('Motion escapes project')
        actors[name]=transform_motion(dict(np.load(path)),entry['transform']);sources[name]=sha256(path)
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
            if progress and len(records)%10==0:progress(dict(pair=[left,right],frames_checked=len(records),frames_total=len(selected),max_depth_m=max(r['max_depth_m'] for r in records)))
        pairs.append(dict(actors=[left,right],max_depth_m=max(r['max_depth_m'] for r in records),frames_over_tolerance=sum(r['max_depth_m']>tolerance_m for r in records),frames=records))
    return dict(scene_id=scene['id'],sources=sources,frame_count=scene['frame_count'],frames_checked=selected,tolerance_m=tolerance_m,pairs=pairs,
        dependencies=dict(trimesh=trimesh.__version__,rtree=rtree.__version__),
        scope='All skin vertices in both directions at listed discrete frames, against closed partner triangle meshes. No edge-only triangle intersections, continuous-time, self-collision or collision-free certification; self-intersections can make inside/outside ambiguous. Tolerance is diagnostic, not animator approval.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene');p.add_argument('--output',required=True);p.add_argument('--frames',nargs='+',type=int);args=p.parse_args()
    d=read(args.scene);start=time.perf_counter();result=audit(d.get('scene',d),dict(np.load(ASSET)),args.frames,progress=lambda r:print(r,flush=True))
    save(args.output,dict(**result,created_at=now(),seconds=time.perf_counter()-start,scene_sha256=sha256(args.scene),auditor_sha256=sha256(__file__)))
    print([(p['actors'],p['max_depth_m'],p['frames_over_tolerance']) for p in result['pairs']])
