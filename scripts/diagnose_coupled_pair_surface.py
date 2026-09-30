"""Separate a retained witness's linearization, moving-plane and mesh errors."""
import argparse
from pathlib import Path
import shutil
import numpy as np
import trimesh
from strep import ROOT, read, save, sha256, now
from coupled_pair_problem import PairProblem
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler
from paired_surface_witness import moving_gap


def run(study, witnesses, output, frame, source, vertex):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Preserve previous diagnostic')
    problem = PairProblem(witnesses)
    result, request = read(study/'result.json'), read(study/'request.json')
    solver = read(study/'solver.json')
    if result['status'] != 'complete' or result['selected'] is None or result['request_sha256'] != sha256(study/'request.json') or result['solver_sha256'] != sha256(study/'solver.json'):
        raise ValueError('Completed bound selected proposal required')
    inputs = {**problem.inputs, **request['inputs']}
    for name in ['result.json','request.json','solver.json','linearization.npz','manifest.json']:
        inputs[str(study/name)] = sha256(study/name)
    if solver['linearization_sha256'] != inputs[str(study/'linearization.npz')]:
        raise ValueError('Linearization changed')
    for entry in read(study/'manifest.json')['cases']:
        inputs[str(study/entry['path'])] = entry['sha256']
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Bound input changed')
    if frame not in problem.request['frames'] or source not in [0,1]:
        raise ValueError('Declared time and actor required')
    points = {}; faces = None
    for variant in ['input','candidate']:
        points[variant] = []
        for actor in problem.actors:
            rig = RigAsset.load(study/variant/(actor['name']+'.glb'))
            world = AnimationSampler(rig.document, rig.binary, 0).sample(frame/30)
            points[variant].append(rig.vertices(world)@actor['rotation'].T+actor['translation'])
            f = array(rig.document, rig.binary, rig.document['meshes'][0]['primitives'][0]['indices']).reshape(-1,3)
            if faces is not None:
                np.testing.assert_array_equal(faces, f)
            faces = f
    if not 0 <= vertex < len(points['candidate'][source]):
        raise ValueError('Valid vertex required')
    selected = []
    offset = 0
    for group in problem.groups:
        for index, row in enumerate(group['rows']):
            if row['frame'] == frame and row['source'] == source and row['vertex'] == vertex:
                selected.append((offset+index,row))
        offset += len(group['rows'])
    queries = {}
    for variant, pair in points.items():
        mesh = trimesh.Trimesh(pair[1-source],faces,process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('Closed wound target required')
        point = pair[source][vertex:vertex+1]
        closest, distance, triangle = trimesh.proximity.closest_point(mesh,point)
        signed = trimesh.proximity.signed_distance(mesh,point)
        queries[variant] = dict(signed_gap_m=-float(signed[0]),closest_triangle=int(triangle[0]),closest_position_m=closest[0].tolist(),distance_m=float(distance[0]))
    diagnostic = dict(frame=frame,source=source,vertex=vertex,in_fitting_witnesses=bool(selected),queries=queries)
    if selected:
        if len(selected) != 1:
            raise ValueError('Duplicate witness')
        index,row=selected[0]
        controls=np.array(solver['controls'])*result['selected']['factor']
        parts=np.split(controls,[problem.sizes[0]])
        sample=int(round((frame-61)*4));ideal=[]
        for actor,part in zip(problem.actors,parts):
            world=actor['model'].world(part)[sample]
            ideal.append(actor['rig'].vertices(world)@actor['rotation'].T+actor['translation'])
        gaps={}
        for variant,pair in {**points,'ideal':ideal}.items():
            gaps[variant]=float(moving_gap(pair[source][vertex:vertex+1],pair[1-source][row['target_vertices']][None],np.array(row['barycentric'])[None],np.array(row['normal'])[None])[0])
        with np.load(study/'linearization.npz',allow_pickle=False) as linear:
            predicted=float(linear['gaps'][index]+linear['gap_jacobian'][index]@controls)
            np.testing.assert_allclose(linear['gaps'][index],gaps['input'],atol=1e-10,rtol=0)
        # A full separation-vector norm retains tangential movement omitted by
        # projection onto the old normal. Its distance to this fixed barycentric
        # surface point upper-bounds distance to the closest point on that mesh.
        derivatives=[]
        for number,actor in enumerate(problem.actors):
            _,jac=actor['model'].world_pair(np.zeros(actor['model'].size))
            if number==source:
                value=actor['skin'].derivative(jac,np.array([sample]),np.array([vertex]))[0]
            else:
                value=-np.einsum('n,nid->id',row['barycentric'],actor['skin'].derivative(jac,np.full(3,sample),np.array(row['target_vertices'])))
            derivatives.append(actor['rotation']@value)
        vector_jacobian=np.concatenate(derivatives,axis=1)
        separations={variant:pair[source][vertex]-np.asarray(row['barycentric'])@pair[1-source][row['target_vertices']] for variant,pair in points.items()}
        predicted_vector=separations['input']+vector_jacobian@controls
        predicted_distance=float(np.linalg.norm(predicted_vector))
        diagnostic.update(witness_triangle=row['target_triangle'],per_time_depth_cap_m=row['cap'],predicted_gap_m=predicted,moving_plane_gaps_m=gaps,
            nonlinear_plane_error_m=gaps['ideal']-predicted,serialization_plane_error_m=gaps['candidate']-gaps['ideal'],
            signed_distance_minus_moving_plane_m=queries['candidate']['signed_gap_m']-gaps['candidate'],
            predicted_full_vector_distance_m=predicted_distance,exported_fixed_barycentric_distance_m=float(np.linalg.norm(separations['candidate'])),
            predicted_full_vector_cap_excess_m=max(0.,predicted_distance-row['cap']))
    for path,digest in inputs.items():
        if sha256(path)!=digest:
            raise ValueError('Input changed during diagnostic')
    output.mkdir();shutil.copyfile(__file__,output/'implementation.py')
    save(output/'verification.json',dict(at=now(),inputs=inputs,implementation_sha256=sha256(__file__),diagnostic=diagnostic,quality_approved=False,
        scope='Fresh signed distance and closest-feature query for one declared retained vertex at one time. Local error attribution only; complete geometry review remains separate.'))
    print(diagnostic,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['study','witnesses','output']:p.add_argument(name,type=Path)
    p.add_argument('--frame',type=float,required=True);p.add_argument('--source',type=int,choices=[0,1],required=True);p.add_argument('--vertex',type=int,required=True)
    a=p.parse_args();run(a.study,a.witnesses,a.output,a.frame,a.source,a.vertex)
