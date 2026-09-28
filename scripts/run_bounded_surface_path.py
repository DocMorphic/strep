"""Scene-aware timed arm trial with widened coverage and exact norm budgets.

First declared development seed, never a held-out evaluation. Preserve all
iterations; full decoded coverage, engine import and quality checks follow.
"""
import argparse
import os
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler
from verify_rig_clearance import localize
from paired_palm_region import RegionActor
from bounded_path_trajectory import BoundedPathFitter
from refine_hand_trajectory import refine


def run(output, seed=1301):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Preserve earlier path trial')
    if seed not in [1301, 2089, 3253, 4099, 5101]:
        raise ValueError('Choose a recorded development seed')
    study = ROOT/'reports/paired-pose-posture-v1'
    pose_study = ROOT/'reports/bounded-wrist-pose-v2'
    summary = ROOT/'reports/paired-pose-posture-summary-v1'
    summary_data = read(summary/'summary.json')
    if read(pose_study/'pipeline.json')['status'] != 'complete':
        raise ValueError('Incomplete pose initializer')
    proof = read(study/'preservation-verification.json')
    if sha256(study/'manifest.json') != proof['manifest_sha256']:
        raise ValueError('Changed source manifest')
    source_scene = study/f'raw-seed-{seed}.json'
    scene = read(source_scene)['scene']
    patch_path = ROOT/'reports/paired-pose-posture-audit-v1/palm-region.json'
    patches = read(patch_path)
    actors, sources, initial = [], {}, []
    for label in ['A', 'B']:
        folder = study/f'seed-{seed}'/label
        glb, posture = folder/'raw/character.glb', folder/'body_fit_posture/character.glb'
        for path in [glb, posture]:
            if sha256(path) != proof['files'][str(path)]:
                raise ValueError('Changed source clip')
        rig, hand_rig = RigAsset.load(glb), RigAsset.load(posture)
        sampler = AnimationSampler(rig.document, rig.binary, 0)
        hand_sampler = AnimationSampler(hand_rig.document, hand_rig.binary, 0)
        times = np.arange(150, dtype=np.float32)/30
        local = localize(np.asarray([sampler.sample(float(t)) for t in times]), rig.parents)
        hand_local = localize(np.asarray([hand_sampler.sample(float(t)) for t in times]), hand_rig.parents)
        names = [n.get('name') for n in rig.document['nodes']]
        if names != [n.get('name') for n in hand_rig.document['nodes']] or not np.array_equal(rig.parents, hand_rig.parents):
            raise ValueError('Different finger rig mapping')
        fingers = [i for i, name in enumerate(names) if name and name.startswith('LeftHand') and name[-1:].isdigit()]
        raw_local = local.copy()
        local[:, fingers, :3, :3] = hand_local[:, fingers, :3, :3]
        primitive = rig.document['meshes'][0]['primitives'][0]
        faces = array(rig.document, rig.binary, primitive['indices']).reshape(-1, 3)
        actor = RegionActor(rig, local, 'LeftHand', scene['contacts'][0]['effector']['surface_vertex'], faces,
                            scene['actors'][label]['transform'], patch=patches[label])
        row = next(r for r in read(pose_study/'results.json')['rows'] if (r['seed'], r['actor']) == (seed, label))
        if row['source_glb_sha256'] != sha256(glb) or row['fit']['edited_nodes'] != actor.nodes:
            raise ValueError('Pose/source mapping mismatch')
        if not row['fit']['targets_matched']:
            raise ValueError('This trial requires a matched event initializer; retain failed pose separately')
        pose_path = pose_study/f'{seed}-{label}/pose.npz'
        if sha256(pose_path) != row['pose_sha256']:
            raise ValueError('Changed event initializer')
        initial.extend(np.asarray(row['fit']['rotation_vectors_rad']).ravel())
        actors.append(actor)
        sources[label] = dict(raw_glb=str(glb), raw_glb_sha256=sha256(glb), posture_glb=str(posture), posture_glb_sha256=sha256(posture),
                              event_pose=str(pose_path), event_pose_sha256=sha256(pose_path), finger_nodes=fingers)
        sources[label]['local_data'] = (raw_local, local)
    fitter = BoundedPathFitter(actors)
    controls = fitter.expand(np.asarray(initial))
    if fitter.step_pair(controls)[0].min() < -1e-7:
        raise ValueError('Initializer violates path limits')
    # Fixed broad clock, half-frame event neighbors and recorded failure peaks.
    selected = [r for r in summary_data['rows'] if r['id'].endswith(f'-seed-{seed}')]
    frames = sorted(set(range(45, 106, 5)) | {74.5, 75.5} | {r['peak_frame'] for r in selected})
    output.mkdir()
    (output/'implementation').mkdir()
    scripts = ['run_bounded_surface_path.py', 'bounded_path_trajectory.py', 'paired_hand_trajectory.py',
               'paired_hand_fit.py', 'paired_hand_clearance.py', 'paired_palm_region.py', 'refine_hand_trajectory.py',
               'elastic_hand_step.py', 'rig_asset.py', 'rig_clip_import.py', 'target_rig_contact.py', 'rig_clearance_fit.py',
               'verify_rig_clearance.py']
    for name in scripts:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    for label in sources:
        raw_local, local = sources[label].pop('local_data')
        np.savez_compressed(output/f'{label}-source-local.npz', raw_local=raw_local, authored_finger_local=local)
        sources[label]['local_npz_sha256'] = sha256(output/f'{label}-source-local.npz')
    save(output/'request.json', dict(at=now(), pid=os.getpid(), created=psutil.Process().create_time(), seed=seed,
         source_scene=str(source_scene), source_scene_sha256=sha256(source_scene), sources=sources,
         source_summary_sha256=sha256(summary/'summary.json'), pose_results_sha256=sha256(pose_study/'results.json'),
         palm_region_sha256=sha256(patch_path), frames=frames, knots=fitter.knots, envelope_frames=[45, 75, 105],
         joint_edit_degrees=[15, 25, 35, 30], adjacent_rotation_vector_edit_degrees=5,
         iterations=3, inner_max_iterations=60, component_trust_degrees=5, safeguard_trials=8,
         restoration=True, restoration_slack_is_acceptance_tolerance=False,
         implementation={n:sha256(output/'implementation'/n) for n in scripts}, quality_approved=False,
         scope='First declared development seed with matched event initialization. Authored finger layer preserved separately; only arm controls optimized. All selected approach/recovery samples included. These sparse fitting frames are NOT a full collision audit. Root, legs and unresolved floor failures preserved. No anatomical, semantic, continuous or human certification.'))
    save(output/'scene.json', dict(scene=scene))
    save(output/'palm-region.json', patches)
    save(output/'initial-parameters.json', dict(controls=controls.tolist(), control_bounds=fitter.bounds.tolist(), control_radii=fitter.control_radii.tolist(), basis=fitter.matrix.tolist()))
    try:
        save(output/'pipeline.json', dict(status='initial_surface_samples', quality_approved=False))
        def progress(history):
            save(output/'history.json', dict(iterations=history, quality_approved=False))
            save(output/'pipeline.json', dict(status='refining', completed_iterations=len(history)-1, quality_approved=False))
            print('Iteration', len(history)-1, 'peak_depth_m', max(c['max_depth_m'] for s in history[-1]['window'] for c in s['collision']), flush=True)
        with threadpool_limits(limits=1):
            result, history = refine(fitter, controls, faces, frames, iterations=3, progress=progress, restoration=True)
        save(output/'parameters.json', dict(controls=result.tolist(), trajectory_values=fitter.values(result).tolist(),
             control_bounds=fitter.bounds.tolist(), control_radii=fitter.control_radii.tolist(), basis=fitter.matrix.tolist(),
             minimum_constraint_slack=float(fitter.step_pair(result)[0].min()), quality_approved=False))
        save(output/'pipeline.json', dict(status='complete_pending_export_and_full_geometry', quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json', dict(status='failed', error=str(exc), traceback=traceback.format_exc(), quality_approved=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--seed', type=int, default=1301)
    args = parser.parse_args()
    run(args.output, args.seed)
