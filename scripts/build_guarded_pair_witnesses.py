"""Dense full-approach partner queries and moving-triangle local witnesses."""
import argparse
from pathlib import Path
import shutil
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from convex_partner_surface import candidates
from rig_asset import RigAsset,array
from rig_clip_import import AnimationSampler
from paired_surface_witness import moving_gap


def query(points,target,faces,band=.005,maximum=64):
    ids,broadphase=candidates(points,target,padding=band)
    mesh=trimesh.Trimesh(target,faces,process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent:raise ValueError('Closed wound partner mesh required')
    depth=[]
    for start in range(0,len(ids),32):depth.extend(trimesh.proximity.signed_distance(mesh,points[ids[start:start+32]]))
    depth=np.asarray(depth)
    if not np.isfinite(depth).all():raise ValueError('Nonfinite partner distance')
    near=np.flatnonzero(depth>=-band);selected=near[np.argsort(-depth[near],kind='stable')[:maximum]]
    chosen=ids[selected];distances=depth[selected]
    if len(chosen):
        closest,distance,triangle_ids=trimesh.proximity.closest_point(mesh,points[chosen])
        triangle_nodes=faces[triangle_ids];triangles=target[triangle_nodes]
        bary=trimesh.triangles.points_to_barycentric(triangles,closest)
        # Signed distance is positive inside this closed target mesh.
        delta=points[chosen]-closest;normals=delta/np.maximum(distance[:,None],1e-14)
        normals*=np.where(distances>0,-1,1)[:,None]
        on_surface=distance<1e-12;normals[on_surface]=mesh.face_normals[triangle_ids[on_surface]]
        gaps=moving_gap(points[chosen],triangles,bary,normals)
        np.testing.assert_allclose(gaps,-distances,atol=1e-8,rtol=0)
        records=[dict(vertex=int(v),target_triangle=int(t),target_vertices=tn.tolist(),barycentric=b.tolist(),normal=n.tolist(),
                      gap_m=float(g),source_position_m=p.tolist(),target_position_m=q.tolist())
                 for v,t,tn,b,n,g,p,q in zip(chosen,triangle_ids,triangle_nodes,bary,normals,gaps,points[chosen],closest)]
    else:records=[]
    return dict(vertices_checked=len(points),broadphase=broadphase,near_band_vertices=len(near),selected_witnesses=len(records),
        maximum_depth_m=float(max(0.,depth.max(initial=0))),vertices_over_5mm=int((depth>.005).sum()),records=records)


def run(output):
    output=Path(output).resolve();study=ROOT/'reports/paired-guarded-temporal-v4';result=read(study/'result.json');request=read(study/'request.json')
    geometry=ROOT/'reports/paired-guarded-geometry-v1/geometry/verification.json';geometry_proof=read(geometry)
    adapter=ROOT/'reports/paired-guarded-geometry-v1/adapter';adapter_protocol=read(adapter/'protocol.json')
    if result['status']!='complete' or result['request_sha256']!=sha256(study/'request.json'):raise ValueError('Completed guarded pair required')
    if geometry_proof['request_sha256']!=sha256(geometry.parent/'request.json'):raise ValueError('Geometry proof changed')
    geometry_request=read(geometry.parent/'request.json')
    if geometry_request['protocol_sha256']!=sha256(adapter/'protocol.json') or geometry_request['result_sha256']!=sha256(adapter/'result.json'):
        raise ValueError('Audited adapter changed')
    inputs={**adapter_protocol['inputs'],str(geometry):sha256(geometry),str(geometry.parent/'request.json'):sha256(geometry.parent/'request.json')}
    inputs[str(adapter/'protocol.json')]=sha256(adapter/'protocol.json');inputs[str(adapter/'result.json')]=sha256(adapter/'result.json')
    for name,digest in geometry_proof['artifacts'].items():inputs[str(geometry.parent/name)]=digest
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Bound source changed')
    if output.exists():raise ValueError('Preserve prior witness population')
    output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    methods=['build_guarded_pair_witnesses.py','paired_surface_witness.py','convex_partner_surface.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','strep.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    frames=np.arange(63,77.001,.25);scene=read(ROOT/adapter_protocol['source_scene'])['scene'];actors=[];faces=None
    for actor in ['A','B']:
        path=study/actor/'candidate.glb';rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
        current_faces=array(rig.document,rig.binary,rig.document['meshes'][0]['primitives'][0]['indices']).reshape(-1,3)
        if faces is not None:np.testing.assert_array_equal(faces,current_faces)
        faces=current_faces;placement=scene['actors'][actor]['transform']
        actors.append((rig,sampler,Rotation.from_quat(placement['rotation_xyzw']).as_matrix(),np.asarray(placement['translation_m'])))
    protocol=dict(at=now(),inputs=inputs,implementation={n:sha256(snapshot/n) for n in methods},frames=frames.tolist(),
        seed=1301,near_band_m=.005,maximum_witnesses_per_direction=64,penetration_screen_m=.005,
        intended_control_knots=[63,66,70,74,75],contact_frame=75,quality_approved=False,
        scope='Complete vertex eligibility and signed-distance query at all approach quarter frames, with a bounded deepest/nearby subset retained as local moving-triangle witnesses. Both actors must move in the residual. Frozen normals/barycentric locations are local approximations; refresh and full skin validation required after fitting. No new animation or cleared collision claim.')
    save(output/'request.json',protocol);rows=[];bindings={}
    for number,frame in enumerate(frames):
        points=[rig.vertices(sampler.sample(frame/30))@r.T+shift for rig,sampler,r,shift in actors]
        directions=[dict(source=a,target=b,**query(points[a],points[b],faces)) for a,b in [(0,1),(1,0)]]
        row=dict(frame=float(frame),directions=directions,floor_depth_m=[max(0.,-float(p[:,1].min())) for p in points])
        path=output/f'frame-{number:03d}.json';save(path,row);bindings[path.name]=sha256(path)
        rows.append(dict(frame=float(frame),maximum_depth_m=max(d['maximum_depth_m'] for d in directions),witnesses=sum(d['selected_witnesses'] for d in directions)))
        save(output/'progress.json',dict(status='running',completed=number+1,total=len(frames),frame=float(frame)))
        if (number+1)%10==0:print(dict(completed=number+1,total=len(frames)),flush=True)
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Input changed during extraction')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Extraction method changed')
    save(output/'result.json',dict(at=now(),status='complete',request_sha256=sha256(output/'request.json'),rows=rows,artifacts=bindings,quality_approved=False))
    save(output/'progress.json',dict(status='complete'));print(dict(frames=len(rows),witnesses=sum(r['witnesses'] for r in rows)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
    with threadpool_limits(limits=1):run(a.output)
