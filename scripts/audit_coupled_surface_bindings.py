"""Fresh closest-feature queries for worst and tight retained partner witnesses."""
import argparse
from pathlib import Path
import shutil
import numpy as np
import trimesh
from strep import read,save,sha256,now
from coupled_pair_problem import PairProblem
from coupled_continuation_checkpoint import checkpoint
from rig_asset import RigAsset,array
from rig_clip_import import AnimationSampler


def run(study,witnesses,output):
    study,output=Path(study).resolve(),Path(output).resolve();state=checkpoint(study);problem=PairProblem(witnesses)
    if output.exists():raise ValueError('Preserve earlier binding audit')
    result=state['result'];selected=result['selected'];parent=study/Path(selected['actors'][0]['path']).parent
    vector_path=parent/'witness-vectors.npz'
    if sha256(vector_path)!=selected['witness_vectors_sha256']:raise ValueError('Selected vectors changed')
    with np.load(vector_path,allow_pickle=False) as archive:saved=archive['vectors']
    records=[row for group in problem.groups for row in group['rows']];caps=np.array([row['cap'] for row in records])
    with np.load(state['origin']/'linearization.npz',allow_pickle=False) as archive:inside=archive['gaps']<0
    ids=np.flatnonzero(inside);norms=np.linalg.norm(saved,axis=1)
    selected_ids=sorted(set(ids[np.argsort(norms[ids])[-12:]].tolist()+ids[np.argsort((norms-caps)[ids])[-6:]].tolist()))
    inputs={**state['inputs'],**problem.inputs,str(vector_path):sha256(vector_path)};actors=[];faces=None
    for actor,entry in zip(problem.actors,selected['actors']):
        path=study/'candidate'/(actor['name']+'.glb');inputs[str(path)]=entry['sha256'];rig=RigAsset.load(path)
        current_faces=array(rig.document,rig.binary,rig.document['meshes'][0]['primitives'][0]['indices']).reshape(-1,3)
        if faces is not None:np.testing.assert_array_equal(faces,current_faces)
        faces=current_faces;actors.append((rig,AnimationSampler(rig.document,rig.binary,0),actor))
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Binding audit input changed')
    rows=[]
    for frame in sorted({records[i]['frame'] for i in selected_ids}):
        points=[rig.vertices(sampler.sample(frame/30))@actor['rotation'].T+actor['translation'] for rig,sampler,actor in actors]
        meshes=[trimesh.Trimesh(p,faces,process=False) for p in points]
        if not all(mesh.is_watertight and mesh.is_winding_consistent for mesh in meshes):raise ValueError('Closed wound meshes required')
        for index in selected_ids:
            row=records[index]
            if row['frame']!=frame:continue
            source,target=row['source'],row['target'];point=points[source][row['vertex']:row['vertex']+1]
            weights=np.maximum(row['barycentric'],0);weights=weights/weights.sum()
            fixed=point[0]-weights@points[target][row['target_vertices']]
            np.testing.assert_allclose(fixed,saved[index],atol=1e-10,rtol=0)
            closest,distance,triangle=trimesh.proximity.closest_point(meshes[target],point)
            signed=float(trimesh.proximity.signed_distance(meshes[target],point)[0]);depth=max(0.,signed)
            if depth>np.linalg.norm(fixed)+1e-8:raise ValueError('Nearest-depth upper bound contradicted')
            rows.append(dict(index=index,frame=frame,source=source,vertex=row['vertex'],fixed_distance_m=float(np.linalg.norm(fixed)),
                projected_depth_m=max(0.,-float(fixed@np.array(row['normal']))),actual_depth_m=depth,nearest_distance_m=float(distance[0]),
                cap_m=row['cap'],original_triangle=row['target_triangle'],current_triangle=int(triangle[0]),
                binding_point_drift_m=float(np.linalg.norm(closest[0]-(point[0]-fixed))),fixed_distance_overestimate_m=float(np.linalg.norm(fixed)-depth)))
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed during binding audit')
    output.mkdir();shutil.copyfile(__file__,output/'implementation.py')
    summary=dict(at=now(),inputs=inputs,implementation_sha256=sha256(__file__),rows=rows,queried_witnesses=len(rows),
        closest_triangle_changes=sum(r['original_triangle']!=r['current_triangle'] for r in rows),
        maximum_binding_point_drift_m=max(r['binding_point_drift_m'] for r in rows),maximum_distance_overestimate_m=max(r['fixed_distance_overestimate_m'] for r in rows),
        quality_approved=False,scope='Declared worst 12 retained distances plus six tightest retained rows, deduplicated. Fresh point-to-complete-mesh queries diagnose stale closest-feature bindings; this is not a whole-scene collision audit or a changed fitting method.')
    save(output/'verification.json',summary);print({k:v for k,v in summary.items() if k not in ['inputs','rows']},flush=True)


if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['study','witnesses','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    with threadpool_limits(limits=1):run(a.study,a.witnesses,a.output)
