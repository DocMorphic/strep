"""Independent Godot import/scrub audit of a completed native support study."""
import argparse
from pathlib import Path
import shutil
import subprocess
import numpy as np
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_spec import validate
from native_engine_clock import audit_clock, compare_poses, clock_echo_matches
from native_godot_payload import payload
from native_leg_floor import foot_region
from paired_approach_basis import BoundSkin
from contact_rate_path import ProjectedSkin

SOURCE_DIR = Path(__file__).resolve().parent
POSE_TOLERANCE = 1e-4


def bind_study(study):
    """Bind completed evidence without trusting selection as engine evidence."""
    study = Path(study).resolve()
    request, result = read(study/'request.json'), read(study/'result.json')
    if read(study/'pipeline.json').get('status') != 'complete' or result.get('status') != 'complete':
        raise ValueError('Completed native support study required')
    files = {}
    def bind(path, digest):
        name = str(Path(path).resolve())
        if name in files and files[name] != digest: raise ValueError('Conflicting support evidence')
        files[name] = digest
    for name, digest in request['inputs'].items(): bind(name, digest)
    for parent, entries in ((study, result['outputs']), (study/'implementation', request['implementation'])):
        for name, digest in entries.items():
            if Path(name).name != name or (parent == study/'implementation' and Path(name).suffix != '.py'):
                raise ValueError('Plain support evidence filenames required')
            bind(parent/name, digest)
    for name in ('request.json', 'result.json', 'pipeline.json'): bind(study/name, sha256(study/name))
    unchanged(files)
    for name in ('input.glb', 'candidate.glb'):
        if files.get(str(study/name)) != sha256(study/name): raise ValueError('Unbound support input/candidate')
    trials = result.get('trials', [])
    if len(trials) != 4 or any(t.get('trial') != i or t.get('status') != 'complete' for i, t in enumerate(trials)):
        raise ValueError('Four ordered completed support trials required')
    if sha256(study/'input.glb') != request['spec']['glb_sha256']:
        raise ValueError('Frozen support source differs from authored draft')
    selected = result.get('selected_trial')
    if selected is not None and (type(selected) is not int or not 0 <= selected < 4):
        raise ValueError('Explicit support selection required')
    if result.get('retained_input') is not (selected is None): raise ValueError('Support retention differs')
    expected = study/('input.glb' if selected is None else f'trial-{selected}.glb')
    if result['candidate_sha256'] != sha256(study/'candidate.glb') or sha256(expected) != result['candidate_sha256']:
        raise ValueError('Selected support candidate binding differs')
    for i, trial in enumerate(trials):
        if files.get(str(study/f'trial-{i}.glb')) != trial['sha256']:
            raise ValueError('Trial GLB binding differs')
    return request, result, files


def unchanged(files):
    for path, digest in files.items():
        if sha256(path) != digest: raise ValueError('Support engine audit evidence changed')


def prepare_cases(study, request, result, output):
    """Input and every proposal, on each clip's full native/fractional clock."""
    source = RigAsset.load(study/'input.glb')
    original = NativeSupportSampler(source.document, source.binary, 0)
    _, rows = validate(request['spec'], source, original, sha256(study/'input.glb'))
    declared = [t for r in rows for t in r['stance_s']+r['edit_s']]
    cases, references = [], []
    for name in ['input']+[f'trial-{i}' for i in range(4)]:
        path = study/f'{name}.glb'; rig = RigAsset.load(path)
        if len(rig.document.get('animations', [])) != 1: raise ValueError('One native animation required')
        sampler = NativeSupportSampler(rig.document, rig.binary, 0)
        times = audit_clock(sampler.duration, [c[2] for c in sampler.channels], declared, rows[0]['stance_s'][0])
        native = payload(rig, sampler, sha256(path))
        names = [rig.document['nodes'][n]['name'] for n in rig.joints]
        cases.append(dict(id=name, path=str(path), frames=len(times), sample_times_s=times.tolist(),
            authoring_seek=True, native_payload=native,
            native_animation_output=str(output/f'{name}-animation.res')))
        references.append((rig, sampler, names))
    return cases, references, rows


def check_case(case, observed, reference, supports):
    """Compare independently decoded bones, then project the original skin."""
    rig, sampler, names = reference
    if observed['id'] != case['id'] or observed['path'] != case['path'] or len(observed['frames']) != case['frames']:
        raise ValueError('Engine case/frame mismatch')
    found_names = observed['bone_names']
    if len(found_names) != len(names) or set(found_names) != set(names):
        raise ValueError('Engine joint names differ')
    if len([n for n in observed['animations'] if n != 'RESET']) != 1 or observed['import_error'] != 0:
        raise ValueError('Ambiguous or failed engine animation import')
    order = [rig.joints[names.index(n)] for n in found_names]
    times = np.asarray(case['sample_times_s'], float)
    if times.shape != (case['frames'],): raise ValueError('Engine requested clock population differs')
    expected = np.array([sampler.sample(float(t)) for t in times])
    errors, bones = [], []
    for t, world, frame in zip(times, expected, observed['frames']):
        if not clock_echo_matches(t, frame['requested_time_s']): raise ValueError('Different engine requested clock')
        row = compare_poses(world[order], frame['bones'])
        errors.append(dict(time_s=float(t), actual_time_s=frame['actual_time_s'], **row))
        bones.append(frame['bones'])
    native_world = expected.copy(); bones = np.asarray(bones, float)
    observed_world = np.broadcast_to(np.eye(4), expected[:, order].shape).copy()
    observed_world[:, :, :3, :3] = bones[:, :, :3, :].transpose(0, 1, 3, 2)
    observed_world[:, :, :3, 3] = bones[:, :, 3, :]
    native_world[:, order] = observed_world
    skin = BoundSkin(rig); contact_rows, height_records = [], []
    for r in supports:
        projection = ProjectedSkin(skin, foot_region(skin, rig.parents, r['chain'][-1]), r['up'], r['offset'])
        mask = (times >= r['stance_s'][0])&(times <= r['stance_s'][1])
        reference_height = projection.evaluate(expected[mask]).min(axis=1)
        engine_height = projection.evaluate(native_world[mask]).min(axis=1)
        passed = bool(engine_height.min() >= -1e-8 and engine_height.max() <= r['maximum_height'])
        contact_rows.append(dict(id=r['id'], samples=int(mask.sum()), minimum_height_m=float(engine_height.min()),
            maximum_lowest_height_m=float(engine_height.max()),
            maximum_source_height_error_m=float(abs(engine_height-reference_height).max()),
            engine_bones_original_skin_support_pass=passed))
        height_records.append(dict(id=r['id'], times_s=times[mask].tolist(),
            source_lowest_heights_m=reference_height.tolist(), engine_bone_lowest_heights_m=engine_height.tolist()))
    maximum = {key: max(r[key] for r in errors) for key in ('position_error_m', 'basis_element_error')}
    duration_error = abs(observed['duration_s']-sampler.duration)
    seek_pass = all(clock_echo_matches(e['time_s'], e['actual_time_s']) for e in errors)
    surfaces = sum(bool(m['weights']) for m in observed['meshes'])
    pose_pass = bool(max(*maximum.values(), duration_error) <= POSE_TOLERANCE and seek_pass
                     and observed['imported_loop_mode'] == 0 and surfaces > 0)
    return dict(id=case['id'], samples=len(errors), bones=len(order), source_sha256=sha256(case['path']),
        **maximum, maximum_seek_time_error_s=max(abs(e['time_s']-e['actual_time_s']) for e in errors),
        duration_error_s=duration_error, seek_clock_pass=seek_pass, imported_skinned_surfaces=surfaces,
        imported_loop_mode=observed['imported_loop_mode'], engine_pose_pass=pose_pass, supports=contact_rows,
        engine_bones_original_skin_support_pass=all(s['engine_bones_original_skin_support_pass'] for s in contact_rows)), errors, height_records


def run(study, output, *, engine=None):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists() or output.parent != ROOT/'reports': raise ValueError('Fresh immediate reports output required')
    request, fitted, files = bind_study(study)
    cases, references, rows = prepare_cases(study, request, fitted, output)
    engine = Path(engine).resolve() if engine is not None else ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    files[str(engine)] = sha256(engine)
    names = ('run_native_support_engine.py', 'native_engine_clock.py', 'native_support_clock.py',
        'native_support_spec.py', 'native_godot_payload.py', 'native_godot_import_audit.gd',
        'native_godot_tracks.gd', 'native_godot_preview.gd', 'native_leg_floor.py',
        'contact_rate_path.py', 'paired_approach_basis.py', 'rig_asset.py', 'rig_clip_import.py',
        'gltf_tools.py', 'strep.py', 'elbow_swivel.py', 'two_bone_waypoint.py',
        'paired_temporal_neighbor.py', 'paired_guarded_temporal.py', 'contact_locked_native.py',
        'timed_rotation_edit.py')
    methods = {SOURCE_DIR/name: sha256(SOURCE_DIR/name) for name in names}
    output.mkdir(); project = output/'project'; project.mkdir(); archive = output/'implementation'; archive.mkdir()
    for path, digest in methods.items():
        target = archive/path.name; shutil.copyfile(path, target); files[str(target)] = digest
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep support clock audit"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', encoding='utf8')
    for name in ('native_godot_import_audit.gd', 'native_godot_tracks.gd', 'native_godot_preview.gd'):
        target = project/('audit.gd' if name == 'native_godot_import_audit.gd' else name)
        shutil.copyfile(SOURCE_DIR/name, target); files[str(target)] = methods[SOURCE_DIR/name]
    save(output/'request.json', dict(at=now(), study=str(study), inputs=files, cases=cases,
        pose_tolerance=POSE_TOLERANCE, native_tracks=True, authoring_seek=True,
        fit_selected_trial=fitted['selected_trial'], retained_input=fitted['retained_input'],
        support_scope='Original GLB skin driven by observed engine bone transforms; not imported/GPU skin or contact forces'))
    save(output/'pipeline.json', dict(status='processing'))
    try:
        unchanged(files)
        with (output/'engine.log').open('w', encoding='utf8') as log:
            completed = subprocess.run([str(engine), '--headless', '--path', str(project), '--script', 'audit.gd', '--',
                str(output/'request.json'), str(output/'engine-output.json')], stdout=log, stderr=subprocess.STDOUT,
                timeout=300, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if completed.returncode: raise ValueError('Godot failed; inspect retained engine.log')
        actual = read(output/'engine-output.json')
        if len(actual['cases']) != len(cases): raise ValueError('Missing support engine case')
        checks = []
        for case, observed, reference in zip(cases, actual['cases'], references):
            check, errors, heights = check_case(case, observed, reference, rows); checks.append(check)
            save(output/f"{case['id']}-errors.json", errors)
            save(output/f"{case['id']}-support.json", heights)
        unchanged(files)
        if any(sha256(p) != h for p, h in methods.items()): raise ValueError('Support engine method changed')
        passed = all(c['engine_pose_pass'] for c in checks)
        save(output/'verification.json', dict(at=now(), engine=actual['engine'], checks=checks, engine_pose_pass=passed,
            scope='Actual headless Godot import, saved/reloaded original LINEAR bone-key Animation resources and authoring scrubbing at full 120Hz/native/fractional clocks. Sampled support projects the original GLB skin with observed engine bones. Ordinary playback, events, strict derivative-rate preservation, imported/GPU skin, collisions, forces, stationary soles, human quality and Studio selection are unverified.',
            quality_approved=False, selected_for_studio=False, gpu_skin_verified=False))
        save(output/'result.json', dict(at=now(), status='complete', engine_pose_pass=passed,
            outputs={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file() and p.name != 'pipeline.json'},
            quality_approved=False, selected_for_studio=False))
        save(output/'pipeline.json', dict(status='complete', engine_pose_pass=passed))
        print([dict(id=c['id'], samples=c['samples'], position_error_m=c['position_error_m'],
            basis_element_error=c['basis_element_error'], engine_pose_pass=c['engine_pose_pass'],
            engine_bones_original_skin_support_pass=c['engine_bones_original_skin_support_pass']) for c in checks], flush=True)
        return passed
    except Exception as error:
        save(output/'pipeline.json', dict(status='failed', reason=str(error))); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--engine', type=Path, help='Explicit local Godot executable; default is the cached development engine')
    args = parser.parse_args()
    if not run(args.study, args.output, engine=args.engine): raise SystemExit(2)
