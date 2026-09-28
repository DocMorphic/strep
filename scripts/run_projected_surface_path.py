"""Serialized matched trial using independently checked projected distances."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now


def run(source, output, wait_for, benchmark):
    source, output, wait_for, benchmark = [Path(p).resolve() for p in [source, output, wait_for, benchmark]]
    if output.exists():
        raise ValueError('Preserve previous trial')
    recipe = read(source/'request.json')
    initial = read(source/'initial-parameters.json')
    prior = read(wait_for/'request.json')
    if Path(prior['study']).resolve()!=source or prior['study_request_sha256']!=sha256(source/'request.json'):
        raise ValueError('Prerequisite audit must cover the matched enriched source')
    benchmark_request=read(benchmark/'request.json')
    if Path(benchmark_request['source']).resolve()!=source or benchmark_request['source_request_sha256']!=sha256(source/'request.json') or benchmark_request['initial_sha256']!=sha256(source/'initial-parameters.json') or benchmark_request['frames']!=recipe['frames']:
        raise ValueError('Projection proof inputs differ')
    for name,digest in recipe['implementation'].items():
        if sha256(source/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:
            raise ValueError('Matched source implementation changed: '+name)
    output.mkdir(); (output/'implementation').mkdir()
    names = sorted(set(recipe['implementation']) | {
        'run_projected_surface_path.py','projected_temporal_surface.py','refine_projected_path.py',
        'unique_fractional_skin.py','batched_fractional_skin.py','batched_bounded_path.py'})
    for name in names:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    for name in ['initial-parameters.json','scene.json','palm-region.json','A-source-local.npz','B-source-local.npz']:
        shutil.copyfile(source/name, output/name)
    request = copy.deepcopy(recipe)
    request.update(at=now(), pid=os.getpid(), created=psutil.Process().create_time(),
        method='projected_fractional_surface_distances',
        matched_study=str(source), matched_request_sha256=sha256(source/'request.json'),
        matched_initial_parameters_sha256=sha256(source/'initial-parameters.json'),
        wait_for=str(wait_for), wait_request_sha256=sha256(wait_for/'request.json'),
        projection_benchmark=str(benchmark), projection_request_sha256=sha256(benchmark/'request.json'),
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False,
        scope='Same raw/authored-finger sources, original initializer, 30-time clock, basis, edit limits, objective, selection screens and solver budgets as the enriched trial. Changes only derivative evaluation: batched local fractional differences and sparse fixed-normal skin projection; integer skin path unchanged. Separate measured numerical proof required before fitting. Full export/engine/299-sample geometry must follow. No physical or quality approval.')
    save(output/'request.json', request)
    def phase(status, **details):
        save(output/'pipeline.json', dict(status=status, at=now(), quality_approved=False, **details))
        print(status, details, flush=True)
    try:
        from audit_paired_guides import await_owner
        phase('waiting_for_exact_projection_proof')
        await_owner(benchmark_request,'pid','created',benchmark,{'complete'})
        if sha256(benchmark/'request.json')!=request['projection_request_sha256']:raise ValueError('Projection proof request changed')
        proof=read(benchmark/'completion.json');rows=read(benchmark/'results.json')['rows']
        if proof['results_sha256']!=sha256(benchmark/'results.json') or proof['initial_history_sha256']!=sha256(benchmark/'initial-history.json'):raise ValueError('Projection evidence changed')
        if [r['frame'] for r in rows]!=recipe['frames'] or proof['frames']!=len(rows) or proof['comparisons']!=4*len(rows):raise ValueError('Incomplete projection proof')
        if proof['constraints']!=sum(r['constraints'] for r in rows):raise ValueError('Projection constraint population differs')
        for row in rows:
            if sha256(benchmark/'surfaces'/row['correspondences_file'])!=row['correspondences_sha256']:raise ValueError('Frozen correspondences changed')
            if len(row['checks'])!=4:raise ValueError('Projection comparison population differs')
            if {(c['variant'],c['margin_m']) for c in row['checks']}!={(v,m) for v in ['initializer','small_perturbation'] for m in [.001,.003]}:raise ValueError('Incomplete projection states/margins')
            if any(not 0<=c['value_error_m']<=1e-11 or not 0<=c['derivative_max_element_error']<=2e-6 for c in row['checks']):raise ValueError('Projection mismatch')
        for name,digest in benchmark_request['implementation'].items():
            if sha256(benchmark/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Projection implementation changed: '+name)
        save(output/'projection-proof.json',dict(at=now(),completion_sha256=sha256(benchmark/'completion.json'),results_sha256=proof['results_sha256'],quality_approved=False))
        phase('waiting_for_exact_enriched_full_audit')
        await_owner(prior,'pid','created',wait_for,{'complete'})
        if sha256(wait_for/'request.json')!=request['wait_request_sha256'] or sha256(source/'request.json')!=request['matched_request_sha256']:raise ValueError('Comparison source changed while waiting')
        for name,digest in request['implementation'].items():
            if sha256(output/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Frozen implementation changed: '+name)
        if sha256(output/'initial-parameters.json')!=request['matched_initial_parameters_sha256']:raise ValueError('Initializer changed')
        if sha256(output/'palm-region.json')!=recipe['palm_region_sha256'] or sha256(recipe['source_scene'])!=recipe['source_scene_sha256']:raise ValueError('Scene/contact patch changed')
        from rig_asset import RigAsset, array
        from paired_palm_region import RegionActor
        from unique_fractional_skin import UniqueBoundedPathFitter
        from refine_projected_path import refine
        scene = read(recipe['source_scene'])['scene']; patches = read(output/'palm-region.json')
        actors=[]
        for label in ['A','B']:
            src=recipe['sources'][label]; path=Path(src['raw_glb']); local_path=output/f'{label}-source-local.npz'
            if sha256(path) != src['raw_glb_sha256'] or sha256(local_path) != src['local_npz_sha256']:
                raise ValueError('Animation source changed')
            rig=RigAsset.load(path); local=np.load(local_path,allow_pickle=False)['authored_finger_local']
            primitive=rig.document['meshes'][0]['primitives'][0]
            actor_faces=array(rig.document,rig.binary,primitive['indices']).reshape(-1,3)
            if actors and not np.array_equal(faces,actor_faces):
                raise ValueError('Contact solver requires matching triangle topology')
            faces=actor_faces
            actors.append(RegionActor(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],faces,
                scene['actors'][label]['transform'],patch=patches[label]))
        fitter=UniqueBoundedPathFitter(actors)
        for name, value in [('basis',fitter.matrix),('control_bounds',fitter.bounds),('control_radii',fitter.control_radii)]:
            if not np.array_equal(np.asarray(initial[name]),value):
                raise ValueError('Matched-input control protocol changed: '+name)
        controls=np.asarray(initial['controls'],dtype=float)
        phase('initial_surface_samples')
        def progress(history):
            save(output/'history.json',dict(iterations=history,quality_approved=False))
            phase('refining',completed_iterations=len(history)-1,
                peak_depth_m=max(c['max_depth_m'] for s in history[-1]['window'] for c in s['collision']))
        with threadpool_limits(limits=1):
            result,history=refine(fitter,controls,faces,request['frames'],iterations=recipe['iterations'],progress=progress,restoration=True)
        save(output/'parameters.json',dict(controls=result.tolist(),trajectory_values=fitter.values(result).tolist(),
            control_bounds=fitter.bounds.tolist(),control_radii=fitter.control_radii.tolist(),basis=fitter.matrix.tolist(),
            minimum_constraint_slack=float(fitter.step_pair(result)[0].min()),quality_approved=False))
        phase('complete_pending_export_and_full_geometry')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc())
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--wait-for',type=Path,required=True);p.add_argument('--benchmark',type=Path,required=True);a=p.parse_args();run(a.source,a.output,a.wait_for,a.benchmark)
