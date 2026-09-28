"""Frozen linear clearance planes from independently measured partner overlap.

These are local approximations at a reference pair, not a global collision model.
"""
import argparse
import numpy as np
import trimesh
from strep import ROOT,read,save,sha256,now
from floor_contact import Surface
from build_soma_preview import ASSET
from scene_constraints import pose,transform_motion,vector


def surface_cuts(points,target_vertices,faces,max_cuts=64):
    points=np.asarray(points);target_vertices=np.asarray(target_vertices)
    mesh=trimesh.Trimesh(target_vertices,faces,process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent:raise ValueError('Closed partner mesh required')
    ids=np.flatnonzero(np.all((points>=target_vertices.min(0)-1e-7)&(points<=target_vertices.max(0)+1e-7),axis=1))
    if not len(ids):return []
    distance=trimesh.proximity.signed_distance(mesh,points[ids]);penetrating=np.flatnonzero(distance>1e-5)
    selected=penetrating[np.argsort(distance[penetrating])[::-1][:max_cuts]];vertices=ids[selected]
    if not len(vertices):return []
    closest,_,triangles=trimesh.proximity.closest_point(mesh,points[vertices])
    outward=closest-points[vertices];outward/=np.linalg.norm(outward,axis=1,keepdims=True)
    return [dict(vertex=int(v),point_m=p.tolist(),normal=n.tolist(),reference_depth_m=float(d),partner_triangle=int(t))
        for v,p,n,d,t in zip(vertices,closest,outward,distance[selected],triangles)]


def load_cuts(scene,actor_id,skin):
    path=(ROOT/scene['partner_cut_file']).resolve()
    if not path.is_relative_to(ROOT.resolve()) or sha256(path)!=scene.get('partner_cut_sha256'):raise ValueError('Partner cut path/hash mismatch')
    data=read(path)
    if data.get('schema_version')!=1 or data['frame_count']!=scene['frame_count']:raise ValueError('Partner cut clock/schema mismatch')
    if data['placements']!={n:e['transform'] for n,e in scene['actors'].items()}:raise ValueError('Partner cut actor placements changed')
    records=data['actors'][actor_id]
    for c in records:
        if type(c['frame'])!=int or not 0<=c['frame']<scene['frame_count']:raise ValueError('Invalid cut frame')
        if type(c['vertex'])!=int or not 0<=c['vertex']<len(skin['bind_vertices']):raise ValueError('Invalid cut vertex')
        vector(c['point_m'],3,'cut point');normal=vector(c['normal'],3,'cut normal')
        if abs(np.linalg.norm(normal)-1)>1e-6:raise ValueError('Cut normal must be unit length')
    return records,dict(file=scene['partner_cut_file'],sha256=sha256(path),reference_sources=data['reference_sources'],reference_scene_sha256=data['reference_scene_sha256'])


def build(scene_path,audit_path,output,max_cuts=64):
    data=read(scene_path);scene=data.get('scene',data);audit=read(audit_path)
    if audit['scene_sha256']!=sha256(scene_path):raise ValueError('Audit does not describe this scene file')
    if max_cuts<1 or max_cuts>1024:raise ValueError('Invalid maximum cuts')
    skin=dict(np.load(ASSET));surface=Surface(skin);actors={};sources={}
    for name,entry in scene['actors'].items():
        path=(ROOT/entry['motion']).resolve()
        if not path.is_relative_to(ROOT.resolve()):raise ValueError('Motion escapes project')
        sources[name]=sha256(path)
        if sources[name]!=audit['sources'][name]:raise ValueError('Audited motion changed')
        actors[name]=transform_motion(dict(np.load(path)),entry['transform'])
    result={name:[] for name in actors}
    for pair in audit['pairs']:
        for frame in pair['frames']:
            if frame['max_depth_m']<=1e-5:continue
            f=frame['frame'];world={name:surface.vertices(actors[name]['rotations'][f],actors[name]['positions'][f]) for name in pair['actors']}
            for direction in frame['directions']:
                source,target=direction['source'],direction['target']
                if direction['max_depth_m']<=1e-5:continue
                p,r=pose(scene['actors'][source]['transform'])
                cuts=surface_cuts(world[source],world[target],skin['faces'],max_cuts)
                for cut in cuts:
                    cut.update(frame=f,partner=target,point_m=((np.array(cut['point_m'])-p)@r).tolist(),normal=(np.array(cut['normal'])@r).tolist())
                result[source].extend(cuts)
            print('Cut frame',f,{n:len(c) for n,c in result.items()},flush=True)
    save(output,dict(schema_version=1,created_at=now(),frame_count=scene['frame_count'],actors=result,max_cuts_per_actor_frame=max_cuts,
        placements={n:e['transform'] for n,e in scene['actors'].items()},reference_sources=sources,reference_scene_sha256=sha256(scene_path),audit_sha256=sha256(audit_path),builder_sha256=sha256(__file__),
        scope='Frozen outward clearance halfspaces at penetrating reference vertices in actor-native coordinates. Re-audit after fitting; moving partner surfaces and newly penetrating vertices are not represented by these local cuts.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene');p.add_argument('audit');p.add_argument('--output',required=True);p.add_argument('--max-cuts',type=int,default=64);a=p.parse_args();build(a.scene,a.audit,a.output,a.max_cuts)
