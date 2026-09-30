"""Check the coupled approach model against actual skin and signed-distance queries."""
import argparse
from pathlib import Path
import shutil
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb
from rig_asset import RigAsset,array
from paired_approach_basis import ApproachActor,BoundSkin
from paired_surface_witness import moving_gap,moving_gap_jacobian


def run(witnesses,output,frame=66.):
    witnesses,output=Path(witnesses).resolve(),Path(output).resolve();request=read(witnesses/'request.json')
    if output.exists():raise ValueError('Preserve previous derivative check')
    index=request['frames'].index(frame);row_path=witnesses/f'frame-{index:03d}.json';row=read(row_path)
    if row['frame']!=frame:raise ValueError('Witness clock mismatch')
    inputs={**request['inputs'],str(row_path):sha256(row_path),str(witnesses/'request.json'):sha256(witnesses/'request.json')}
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Witness input changed')
    study=ROOT/'reports/paired-guarded-temporal-v4';scene=read(ROOT/'reports/paired-pose-posture-v1/body_fit_posture-seed-1301.json')['scene']
    output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    methods=['verify_paired_approach_basis.py','paired_approach_basis.py','paired_guarded_temporal.py','paired_temporal_neighbor.py','paired_surface_witness.py','rig_clip_import.py','rig_asset.py','gltf_tools.py','strep.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    protocol=dict(at=now(),inputs=inputs,frame=frame,implementation={n:sha256(snapshot/n) for n in methods},
        seed=4207,difference_step_radians=1e-6,witnesses_per_direction=3,quality_approved=False)
    save(output/'request.json',protocol);actors=[];identities=[]
    names=['LeftShoulder','LeftArm','LeftForeArm','LeftHand'];frames=np.asarray(request['frames']);sample=index
    for actor in ['A','B']:
        rig=RigAsset.load(study/actor/'candidate.glb');reference,binary=read_glb(study/actor/'input.glb')
        model=ApproachActor(rig.document,rig.binary,reference,binary,names,frames)
        zero=np.zeros(model.size);world,jacobian=model.world_pair(zero);skin=BoundSkin(rig)
        placement=scene['actors'][actor]['transform'];rotation=Rotation.from_quat(placement['rotation_xyzw']).as_matrix();translation=np.asarray(placement['translation_m'])
        error=float(np.abs(world-model.base.reference_world).max())
        if error>1e-12:raise ValueError('Zero controls changed the current candidate')
        ids=np.arange(len(rig.primitives[0]['positions']));skin_error=float(np.abs(skin.evaluate(world,np.full(len(ids),sample),ids)-rig.vertices(world[sample])).max())
        if skin_error>1e-12:raise ValueError('Subset skin evaluator changed the skin')
        identities.append(dict(actor=actor,zero_world_error=error,skin_error=skin_error,controls=model.size))
        actors.append(dict(model=model,rig=rig,skin=skin,world=world,jacobian=jacobian,rotation=rotation,translation=translation))
    faces=array(actors[0]['rig'].document,actors[0]['rig'].binary,actors[0]['rig'].document['meshes'][0]['primitives'][0]['indices']).reshape(-1,3)
    random=np.random.default_rng(4207);directions=[random.normal(size=a['model'].size) for a in actors]
    directions=[v/np.linalg.norm(v) for v in directions];records=[];step=1e-6
    for direction in row['directions']:
        source,target=direction['source'],direction['target'];a,b=actors[source],actors[target];chosen=direction['records'][:3]
        if len(chosen)!=3:raise ValueError('Three deep witnesses per direction required')
        ids=np.array([r['vertex'] for r in chosen]);triangle_nodes=np.array([r['target_vertices'] for r in chosen]);bary=np.array([r['barycentric'] for r in chosen]);normals=np.array([r['normal'] for r in chosen])
        sf=np.full(len(ids),sample);tf=np.full(triangle_nodes.size,sample)
        points=a['skin'].evaluate(a['world'],sf,ids)@a['rotation'].T+a['translation']
        triangle_points=(b['skin'].evaluate(b['world'],tf,triangle_nodes.ravel())@b['rotation'].T+b['translation']).reshape(-1,3,3)
        gaps=moving_gap(points,triangle_points,bary,normals)
        np.testing.assert_allclose(gaps,[r['gap_m'] for r in chosen],atol=1e-8,rtol=0)
        jp=np.einsum('ij,njd->nid',a['rotation'],a['skin'].derivative(a['jacobian'],sf,ids))
        jq=np.einsum('ij,njd->nid',b['rotation'],b['skin'].derivative(b['jacobian'],tf,triangle_nodes.ravel())).reshape(-1,3,3,b['model'].size)
        jac=moving_gap_jacobian(jp,jq,bary,normals);predicted=jac@np.r_[directions[source],directions[target]]
        plane=[];mesh=[]
        for sign in [-1,1]:
            wa=a['model'].world(sign*step*directions[source]);wb=b['model'].world(sign*step*directions[target])
            p=a['skin'].evaluate(wa,sf,ids)@a['rotation'].T+a['translation']
            tri=(b['skin'].evaluate(wb,tf,triangle_nodes.ravel())@b['rotation'].T+b['translation']).reshape(-1,3,3)
            plane.append(moving_gap(p,tri,bary,normals))
            target_points=b['rig'].vertices(wb[sample])@b['rotation'].T+b['translation']
            mesh.append(-trimesh.proximity.signed_distance(trimesh.Trimesh(target_points,faces,process=False),p))
        plane_difference=(plane[1]-plane[0])/(2*step);mesh_difference=(mesh[1]-mesh[0])/(2*step)
        plane_error=float(np.abs(predicted-plane_difference).max());mesh_error=float(np.abs(predicted-mesh_difference).max())
        if plane_error>1e-6 or mesh_error>1e-4:raise ValueError(f'Coupled derivative discrepancy: plane={plane_error}, mesh={mesh_error}')
        records.append(dict(source=source,target=target,vertices=ids.tolist(),predicted=predicted.tolist(),
            plane_difference=plane_difference.tolist(),mesh_difference=mesh_difference.tolist(),plane_error=plane_error,mesh_error=mesh_error,
            source_jacobian_norm=float(np.linalg.norm(jac[:,:a['model'].size])),target_jacobian_norm=float(np.linalg.norm(jac[:,a['model'].size:]))))
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Input changed during verification')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed during verification')
    save(output/'verification.json',dict(at=now(),request_sha256=sha256(output/'request.json'),identities=identities,records=records,quality_approved=False,
        scope='Zero-control pose/skin agreement and six local coupled derivative checks at one collision time on the real meshes. No new correction, no optimizer acceptance and no global collision certificate. Witness extraction may still be running; this report binds the inspected frame independently.'))
    print(dict(identities=identities,maximum_plane_error=max(r['plane_error'] for r in records),maximum_mesh_error=max(r['mesh_error'] for r in records)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('witnesses',type=Path);p.add_argument('output',type=Path);p.add_argument('--frame',type=float,default=66.);a=p.parse_args()
    with threadpool_limits(limits=1):run(a.witnesses,a.output,a.frame)
