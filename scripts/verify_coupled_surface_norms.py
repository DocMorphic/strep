"""Replay retained surface cones through complete CPU-skinned source/GLB meshes."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from coupled_pair_problem import PairProblem
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def run(study,witnesses,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve previous vector review')
    problem=PairProblem(witnesses);request=read(study/'request.json');result=read(study/'result.json');solver=read(study/'solver.json')
    if result['status']!='complete' or result['selected'] is None or result['request_sha256']!=sha256(study/'request.json') or result['solver_sha256']!=sha256(study/'solver.json'):
        raise ValueError('Completed selected proposal required')
    if not request['penetrating_surface_norms'] or solver['surface_norms_sha256']!=sha256(study/'surface-norms.npz') or solver['linearization_sha256']!=sha256(study/'linearization.npz'):
        raise ValueError('Matching saved surface norms required')
    inputs={**problem.inputs,**request['inputs']}
    for name in ['request.json','result.json','solver.json','surface-norms.npz','linearization.npz','manifest.json']:
        inputs[str(study/name)]=sha256(study/name)
    for entry in read(study/'manifest.json')['cases']:inputs[str(study/entry['path'])]=entry['sha256']
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Bound review input changed')
    output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    methods=['verify_coupled_surface_norms.py','coupled_pair_problem.py','coupled_pair_proposal.py','coupled_surface_norms.py','paired_approach_basis.py',
             'paired_guarded_temporal.py','paired_temporal_neighbor.py','paired_surface_witness.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','strep.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    protocol=dict(at=now(),inputs=inputs,implementation={name:sha256(snapshot/name) for name in methods},directional_probe_seed=7403,derivative_step_radians=1e-6,
        scope='All retained penetrating witnesses replayed through full RigAsset CPU skins, independently of the selected-vertex BoundSkin evaluator. Two coupled directional derivative checks per row, actual exported distances and local nonlinear error. Not a full collision or continuous-time certificate.')
    save(output/'request.json',protocol)
    with np.load(study/'surface-norms.npz',allow_pickle=False) as archive:surface=dict(archive)
    with np.load(study/'linearization.npz',allow_pickle=False) as archive:linear=dict(archive)
    np.testing.assert_array_equal(surface['witness_indices'],np.flatnonzero(linear['gaps']<0))
    np.testing.assert_array_equal(surface['radii'],linear['depth_caps'][surface['witness_indices']])
    all_records=[row for group in problem.groups for row in group['rows']]
    records=[all_records[index] for index in surface['witness_indices']]
    by_time={frame:[] for frame in sorted({r['frame'] for r in records})}
    for index,row in enumerate(records):by_time[row['frame']].append((index,row))
    def evaluate(worlds,rigs):
        values=np.empty((len(records),3))
        for frame,rows in by_time.items():
            sample=int(round((frame-61)*4))
            points=[rig.vertices(world[sample])@actor['rotation'].T+actor['translation'] for rig,world,actor in zip(rigs,worlds,problem.actors)]
            for index,row in rows:
                weights=np.maximum(np.array(row['barycentric']),0);weights/=weights.sum()
                target=sum(weight*points[row['target']][vertex] for weight,vertex in zip(weights,row['target_vertices']))
                values[index]=points[row['source']][row['vertex']]-target
        return values
    def worlds(controls):
        return [actor['model'].world(part) for actor,part in zip(problem.actors,np.split(controls,[problem.sizes[0]]))]
    rigs=[actor['rig'] for actor in problem.actors]
    source=evaluate(worlds(np.zeros(problem.size)),rigs)
    source_error=float(np.abs(source-surface['vectors']).max());np.testing.assert_allclose(source,surface['vectors'],atol=1e-10,rtol=0)
    arrays=dict(source=source);probes=[];rng=np.random.default_rng(protocol['directional_probe_seed'])
    for index in range(2):
        direction=rng.normal(size=problem.size);direction/=np.linalg.norm(direction);step=protocol['derivative_step_radians']
        numerical=(evaluate(worlds(direction*step),rigs)-evaluate(worlds(-direction*step),rigs))/(2*step)
        expected=surface['jacobians']@direction
        error=float(np.abs(numerical-expected).max());np.testing.assert_allclose(numerical,expected,atol=1e-7,rtol=0)
        arrays[f'probe_{index}']=numerical;arrays[f'jacobian_{index}']=expected
        probes.append(dict(direction=direction.tolist(),maximum_error_m_per_radian=error))
        print(dict(probe=index,maximum_error=error),flush=True)
    controls=np.array(solver['controls'])*result['selected']['factor']
    ideal=evaluate(worlds(controls),rigs);prediction=surface['vectors']+surface['jacobians']@controls
    exported_rigs=[RigAsset.load(study/'candidate'/(actor['name']+'.glb')) for actor in problem.actors]
    exported_worlds=[]
    for rig in exported_rigs:
        sampler=AnimationSampler(rig.document,rig.binary,0)
        exported_worlds.append(np.array([sampler.sample(frame/30) for frame in problem.frames]))
    exported=evaluate(exported_worlds,exported_rigs)
    arrays.update(ideal=ideal,affine=prediction,exported=exported);np.savez_compressed(output/'vectors.npz',**arrays)
    predicted_norm=np.linalg.norm(prediction,axis=1);ideal_norm=np.linalg.norm(ideal,axis=1);actual_norm=np.linalg.norm(exported,axis=1)
    excess=actual_norm-surface['radii'];largest=np.argsort(excess)[-10:][::-1]
    details=[dict(frame=records[i]['frame'],source=records[i]['source'],vertex=records[i]['vertex'],cap_m=float(surface['radii'][i]),
                  affine_m=float(predicted_norm[i]),ideal_m=float(ideal_norm[i]),exported_m=float(actual_norm[i]),excess_m=float(excess[i])) for i in largest]
    summary=dict(at=now(),request_sha256=sha256(output/'request.json'),vectors_sha256=sha256(output/'vectors.npz'),rows=len(records),source_vector_max_error_m=source_error,
        derivative_checks=2*len(records),probes=probes,maximum_affine_cap_excess_m=float(max(0.,(predicted_norm-surface['radii']).max())),
        maximum_exported_cap_excess_m=float(max(0.,excess.max())),exported_excesses_over_1e_6=int((excess>1e-6).sum()),
        maximum_nonlinear_norm_error_m=float(np.abs(ideal_norm-predicted_norm).max()),maximum_serialization_norm_error_m=float(np.abs(actual_norm-ideal_norm).max()),
        largest=details,quality_approved=False)
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed during replay')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed during replay')
    save(output/'verification.json',summary);print({k:v for k,v in summary.items() if k not in ['probes','largest']},flush=True)


if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['study','witnesses','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    with threadpool_limits(limits=1):run(a.study,a.witnesses,a.output)
