"""Frozen matched-input experiment, serialized after the strict-path audit."""
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
from screen_path_guard import SCREEN


def run(source, output, wait_for):
    source, output, wait_for = [Path(p).resolve() for p in [source, output, wait_for]]
    if output.exists():
        raise ValueError('Preserve previous trial')
    recipe = read(source/'request.json')
    initial = read(source/'initial-parameters.json')
    prior = read(wait_for/'request.json')
    if prior['study'] != str(source) or prior['study_request_sha256'] != sha256(source/'request.json'):
        raise ValueError('The prerequisite audit must cover the strict comparison source')
    for name, digest in recipe['implementation'].items():
        if sha256(source/'implementation'/name) != digest or sha256(ROOT/'scripts'/name) != digest:
            raise ValueError('Strict source implementation changed: '+name)
    benchmark = ROOT/'reports/fast-path-skin-v1'
    proof = read(benchmark/'completion.json')
    benchmark_request = read(benchmark/'request.json')
    if (proof['comparisons'] != 36 or proof['results_sha256'] != sha256(benchmark/'results.json')
        or benchmark_request['source_request_sha256'] != sha256(source/'request.json')
        or benchmark_request['initial_parameters_sha256'] != sha256(source/'initial-parameters.json')):
        raise ValueError('Missing matching derivative evidence')
    for name, digest in benchmark_request['implementation'].items():
        if sha256(benchmark/'implementation'/name) != digest or sha256(ROOT/'scripts'/name) != digest:
            raise ValueError('Derivative implementation changed: '+name)
    if proof['max_position_error_m'] > 1e-11 or proof['max_derivative_error'] > 2e-6:
        raise ValueError('Derivative equivalence failed')
    output.mkdir(); (output/'implementation').mkdir()
    names = sorted(set(recipe['implementation']) | {
        'run_screen_surface_path.py','screen_path_guard.py','refine_screen_path.py',
        'fast_bounded_path.py','fast_path_skin.py','verify_palm_region.py','audit_paired_guides.py'})
    for name in names:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    for name in ['initial-parameters.json','scene.json','palm-region.json','A-source-local.npz','B-source-local.npz']:
        shutil.copyfile(source/name, output/name)
    request = copy.deepcopy(recipe)
    request.update(at=now(), pid=os.getpid(), created=psutil.Process().create_time(),
        method='screen_preserving_steps_with_analytic_integer_skin',
        source_study=str(source), source_request_sha256=sha256(source/'request.json'),
        source_initial_parameters_sha256=sha256(source/'initial-parameters.json'),
        wait_for=str(wait_for), wait_request_sha256=sha256(wait_for/'request.json'),
        derivative_benchmark=str(benchmark), derivative_completion_sha256=sha256(benchmark/'completion.json'),
        implementation={n:sha256(output/'implementation'/n) for n in names},
        selection_screen=SCREEN, quality_approved=False,
        scope='Same declared seed, raw/authored-finger inputs, initializer, basis, fitting clock and edit/solver budgets as strict v1. Changes: separately verified analytic integer derivatives; passing fitting samples remain at or below the existing 5mm screen, already-failing samples and overall peak cannot worsen, objective cannot worsen, and the measured event palm region and opposing normals must pass. Sparse fitting and accepted steps are not motion approval. Full export, edit-budget, engine and 299-sample geometry checks follow. Root and existing floor failures remain unchanged.')
    save(output/'request.json', request)
    def phase(status, **details):
        save(output/'pipeline.json', dict(status=status, at=now(), quality_approved=False, **details))
        print(status, details, flush=True)
    try:
        from audit_paired_guides import await_owner
        phase('waiting_for_strict_path_full_audit')
        await_owner(prior, 'pid', 'created', wait_for, {'complete'})
        if sha256(wait_for/'request.json') != request['wait_request_sha256'] or sha256(source/'request.json') != request['source_request_sha256']:
            raise ValueError('Comparison source changed while waiting')
        for name, digest in request['implementation'].items():
            if sha256(output/'implementation'/name) != digest or sha256(ROOT/'scripts'/name) != digest:
                raise ValueError('Frozen implementation changed: '+name)
        if sha256(output/'initial-parameters.json') != request['source_initial_parameters_sha256']:
            raise ValueError('Initializer changed')
        if sha256(output/'palm-region.json') != recipe['palm_region_sha256'] or sha256(recipe['source_scene']) != recipe['source_scene_sha256']:
            raise ValueError('Scene/contact patch changed')
        from rig_asset import RigAsset, array
        from paired_palm_region import RegionActor
        from fast_bounded_path import FastBoundedPathFitter
        from refine_screen_path import refine
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
        fitter=FastBoundedPathFitter(actors)
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
            result,history=refine(fitter,controls,faces,recipe['frames'],iterations=recipe['iterations'],progress=progress,restoration=True)
        save(output/'parameters.json',dict(controls=result.tolist(),trajectory_values=fitter.values(result).tolist(),
            control_bounds=fitter.bounds.tolist(),control_radii=fitter.control_radii.tolist(),basis=fitter.matrix.tolist(),
            minimum_constraint_slack=float(fitter.step_pair(result)[0].min()),quality_approved=False))
        phase('complete_pending_export_and_full_geometry')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc())
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--wait-for',type=Path,required=True);a=p.parse_args();run(a.source,a.output,a.wait_for)
