"""Export and retain bounded feedback proposals for a saved stationary-pin edit.

This adapter is experimental. It never replaces the source or approves quality.
The caller owns the worker lock; the command-line entry point acquires it.
"""
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation

from strep import ROOT, read, save, sha256, now


def verify_original_bounds(source, candidate, max_lift, max_degrees, held):
    """All limits are relative to the original source, not the fitted seed."""
    for value, limit, name in [(max_lift, None, 'root'), (max_degrees, 180, 'rotation')]:
        if type(value) not in (int, float) or not np.isfinite(value) or value <= 0 or (limit and value > limit):
            raise ValueError('Invalid original '+name+' budget')
    if not np.array_equal(candidate['root_positions'][:, [0, 2]], source['root_positions'][:, [0, 2]]):
        raise ValueError('Root XZ changed')
    lift = candidate['root_positions'][:, 1].astype(float)-source['root_positions'][:, 1]
    if not np.isfinite(lift).all() or lift.min() < 0 or lift.max() > max_lift:
        raise ValueError('Original root budget exceeded')
    relative = source['local_rot_mats'].transpose(0, 1, 3, 2) @ candidate['local_rot_mats']
    if not np.isfinite(relative).all():
        raise ValueError('Nonfinite rotations')
    angle = float(np.rad2deg(Rotation.from_matrix(relative.reshape(-1, 3, 3)).magnitude()).max())
    if angle > max_degrees+1e-6:
        raise ValueError('Original rotation budget exceeded')
    for key in ['root_positions', 'posed_joints', 'local_rot_mats', 'global_rot_mats']:
        if candidate[key][held].tobytes() != source[key][held].tobytes():
            raise ValueError('Held source pose changed: '+key)
    return dict(minimum_root_lift_m=float(lift.min()), maximum_root_lift_m=float(lift.max()),
                maximum_rotation_delta_degrees=angle)


def run(source_folder, seed_folder, checked_plan, output, *, max_lift, max_degrees, progress=None):
    """Produce a separate selected candidate while retaining every trial export."""
    import torch
    from threadpoolctl import threadpool_limits
    from build_soma_preview import ASSET
    from contact_timing_job import validate_options, verify_source
    from root_height_feasibility import RootHeightProblem
    from held_pose_preservation import restore_locked_pose
    from inspect_motion import validate_motion, skeleton_metadata
    from export_feedback_repair import repair, rate_layout, exported_measurements
    from evaluate_body_contact import evaluate
    from run_body_contact import export_motion
    from audit_checked_contact import audit
    from kimodo.skeleton import SOMASkeleton77

    source_folder, seed_folder, checked_plan, output = map(
        lambda p: Path(p).resolve(), [source_folder, seed_folder, checked_plan, output])
    if not output.is_relative_to((ROOT/'reports').resolve()):
        raise ValueError('Keep experimental repair output under reports')
    paths = [source_folder/n for n in ['motion.npz', 'soma.glb', 'raw/motion.npz', 'limb/motion.npz']]
    paths += [seed_folder/'motion.npz', ASSET]
    paths += [checked_plan/n for n in ['bound-contact-spec.json', 'rate-reference.json', 'edit-request.json']]
    inputs = {str(p): sha256(p) for p in paths}
    methods = {p.name: sha256(p) for p in (ROOT/'scripts').iterdir() if p.suffix in ['.py', '.gd']}
    source, seed, raw, limb = [dict(np.load(p)) for p in
        [source_folder/'motion.npz', seed_folder/'motion.npz', source_folder/'raw/motion.npz', source_folder/'limb/motion.npz']]
    for motion in [source, seed, raw, limb]:
        validate_motion(motion, 30)
    if any(m['root_positions'].shape != source['root_positions'].shape for m in [seed, raw, limb]):
        raise ValueError('Original, seed and history clocks differ')
    skin = dict(np.load(ASSET))
    # Decode the supplied preview: a matching rate JSON does not bind a GLB.
    source_check = verify_source(source_folder/'soma.glb', source, skin)
    spec = read(checked_plan/'bound-contact-spec.json')
    reference = read(checked_plan/'rate-reference.json')
    options = read(checked_plan/'edit-request.json')['options']
    validate_options(options, spec, len(source['root_positions']))
    window = options['edit_window']
    held = np.ones(len(source['root_positions']), bool)
    held[window[0]+int(window[0]>0):window[1]+int(window[1]==len(held)-1)] = False
    seed = restore_locked_pose(source, seed, held)
    verify_original_bounds(source, seed, max_lift, max_degrees, held)
    _, parents, _ = skeleton_metadata(source['posed_joints'].shape[1])
    output.mkdir(parents=True, exist_ok=False)
    import psutil
    process = psutil.Process()
    save(output/'worker.json', dict(pid=process.pid, created=process.create_time()))
    save(output/'pipeline.json', dict(status='preparing', quality_approved=False))
    (output/'implementation').mkdir()
    for name in methods:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'inputs.json', inputs)
    save(output/'source-validation.json', source_check)
    save(output/'protocol.json', dict(created_at=now(), implementation=methods, edit_window=window,
        max_root_lift_m=max_lift, max_rotation_degrees=max_degrees, fps=30,
        reference='Original source; retained seed supplies poses only', quality_approved=False))

    def phase(status, **fields):
        save(output/'pipeline.json', dict(status=status, at=now(), quality_approved=False, **fields))
        if progress:
            progress(dict(status=status, **fields))

    old_threads = torch.get_num_threads()
    try:
        with threadpool_limits(limits=1):
            torch.set_num_threads(2)
            problem = RootHeightProblem(source, seed, parents, skin, spec, window, max_lift)
            if problem.point_rate.record() != reference:
                raise ValueError('Original rate reference differs from saved check')
            blocks = rate_layout(problem)
            save(output/'rate-layout.json', blocks)

            def inspect(coordinates, label):
                phase('exporting', proposal=label)
                destination = output/label
                candidate = {k: v.astype(seed[k].dtype) for k, v in problem.motion(coordinates).items()}
                validate_motion(candidate, 30)
                budgets = verify_original_bounds(source, candidate, max_lift, max_degrees, held)
                for key in ['local_rot_mats', 'global_rot_mats']:
                    if candidate[key].tobytes() != seed[key].tobytes():
                        raise ValueError('Root repair changed seed rotations')
                serial = problem.reference_residuals(candidate)
                evaluation, body = evaluate(raw, limb, candidate, skin, dict(applied=True))
                validation = export_motion(destination, candidate, skin, SOMASkeleton77(), evaluation['after']['per_frame_max_depth_m'])
                exported = audit(source_folder/'soma.glb', destination/'soma.glb', spec, window, reference)
                peaks, slacks = exported_measurements(exported, blocks)
                save(destination/'checked-export-audit.json', exported)
                save(destination/'body-evaluation.json', dict(evaluation=evaluation, body=body))
                save(destination/'validation.json', validation)
                save(destination/'budgets.json', budgets)
                save(destination/'serialized-proxy.json', dict(minimum_slack=float(serial.min()), violations=int((serial < 0).sum())))
                return dict(path=destination, peaks=peaks, slacks=slacks, serial=serial, flags=evaluation['flags'])

            _, selected, report = repair(problem, inspect, progress=lambda row: phase('searching', progress=row))
            report['selected_export'] = selected['path'].name
            report['flags'] = list(selected['flags'])
            save(output/'solver.json', report)
            shutil.copytree(selected['path'], output/'candidate')
            for path, digest in inputs.items():
                if sha256(Path(path)) != digest:
                    raise ValueError('Repair input changed: '+path)
            for name, digest in methods.items():
                if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest:
                    raise ValueError('Repair method changed: '+name)
            phase('complete', export_and_native_screen=report['export_and_native_screen'], flags=report['flags'])
            save(output/'completion.json', dict(export_and_native_screen=report['export_and_native_screen'],
                flags=report['flags'], quality_approved=False, engine_import=None,
                files={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file()}))
            return report
    except BaseException as exc:
        phase('failed', error=str(exc))
        raise
    finally:
        torch.set_num_threads(old_threads)


if __name__ == '__main__':
    import argparse
    from action_worker_lock import worker_lock
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--seed', required=True, type=Path)
    parser.add_argument('--checked-plan', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--max-root-lift-m', required=True, type=float)
    parser.add_argument('--max-rotation-degrees', required=True, type=float)
    args = parser.parse_args()
    with worker_lock():
        run(args.source, args.seed, args.checked_plan, args.output,
            max_lift=args.max_root_lift_m, max_degrees=args.max_rotation_degrees,
            progress=lambda row: print(row['status'], row.get('proposal', ''), flush=True))
