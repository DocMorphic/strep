"""Fixed-input development trial with an audit-derived enriched fitting clock."""
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
from contact_witness_clock import enrich
from compare_partner_paths import load as load_audit


def run(source, output, wait_for):
    source, output, wait_for = [Path(p).resolve() for p in [source, output, wait_for]]
    if output.exists():
        raise ValueError('Preserve previous trial')
    recipe = read(source/'request.json')
    initial = read(source/'initial-parameters.json')
    prior = read(wait_for/'request.json')
    previous_study=Path(prior['study'])
    previous_request=read(previous_study/'request.json')
    if Path(previous_request['source_study']).resolve()!=source or previous_request['source_request_sha256']!=sha256(source/'request.json'):
        raise ValueError('The audited predecessor must share the original strict initializer')
    strict_audit=ROOT/'reports/bounded-surface-path-completion-v1'
    strict=load_audit(strict_audit);screen=load_audit(wait_for)
    comparison=ROOT/'reports/partner-path-comparison-v1'
    compared=read(comparison/'summary.json')
    if compared['strict_completion_sha256']!=strict['completion_sha256'] or compared['screen_completion_sha256']!=screen['completion_sha256']:
        raise ValueError('Witness comparison does not bind these completed audits')
    if compared['curves_sha256']!=sha256(comparison/'curves.json'):
        raise ValueError('Witness curves changed')
    curves=read(comparison/'curves.json')
    if curves!={'raw':strict['variants']['raw']['curve'],'strict':strict['variants']['candidate']['curve'],'screen':screen['variants']['candidate']['curve']}:
        raise ValueError('Witness curves disagree with full exported geometry')
    plan=enrich(recipe['frames'],curves,threshold=SCREEN['max_sample_penetration_m'])
    if not plan['added_frames']:raise ValueError('No new witnesses; do not duplicate the prior experiment')
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
        'run_enriched_surface_path.py','contact_witness_clock.py','compare_partner_paths.py','screen_path_guard.py','refine_screen_path.py',
        'fast_bounded_path.py','fast_path_skin.py','verify_palm_region.py','audit_paired_guides.py'})
    for name in names:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    for name in ['initial-parameters.json','scene.json','palm-region.json','A-source-local.npz','B-source-local.npz']:
        shutil.copyfile(source/name, output/name)
    request = copy.deepcopy(recipe)
    request.update(at=now(), pid=os.getpid(), created=psutil.Process().create_time(),
        method='audit_enriched_screen_preserving_steps', frames=plan['frames'],
        witness_comparison=str(comparison), witness_summary_sha256=sha256(comparison/'summary.json'),
        witness_curves_sha256=sha256(comparison/'curves.json'), sampling_plan=plan,
        source_study=str(source), source_request_sha256=sha256(source/'request.json'),
        source_initial_parameters_sha256=sha256(source/'initial-parameters.json'),
        wait_for=str(wait_for), wait_request_sha256=sha256(wait_for/'request.json'),
        derivative_benchmark=str(benchmark), derivative_completion_sha256=sha256(benchmark/'completion.json'),
        implementation={n:sha256(output/'implementation'/n) for n in names},
        selection_screen=SCREEN, quality_approved=False,
        scope='Same seed, raw/authored-finger inputs, original initializer, basis, edit limits, selection thresholds and three-iteration budget as prior screen-preserving development trial. Fitting clock adds every audited failure and adjacent half-frames from raw/strict/screen results. This uses prior development failures, not held-out evidence. Full independent exported 299-sample and engine audits remain required; root and existing floor failures remain unchanged.')
    save(output/'request.json', request)
    def phase(status, **details):
        save(output/'pipeline.json', dict(status=status, at=now(), quality_approved=False, **details))
        print(status, details, flush=True)
    try:
        from audit_paired_guides import await_owner
        phase('checking_completed_predecessor')
        await_owner(prior, 'pid', 'created', wait_for, {'complete'})
        if sha256(wait_for/'request.json') != request['wait_request_sha256'] or sha256(source/'request.json') != request['source_request_sha256']:
            raise ValueError('Comparison source changed while waiting')
        for name, digest in request['implementation'].items():
            if sha256(output/'implementation'/name) != digest or sha256(ROOT/'scripts'/name) != digest:
                raise ValueError('Frozen implementation changed: '+name)
        if sha256(comparison/'summary.json')!=request['witness_summary_sha256'] or sha256(comparison/'curves.json')!=request['witness_curves_sha256']:
            raise ValueError('Witness evidence changed')
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
    p.add_argument('--wait-for',type=Path,required=True);a=p.parse_args();run(a.source,a.output,a.wait_for)
