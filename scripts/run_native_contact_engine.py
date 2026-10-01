"""Audit completed native contact exports in Godot without changing their clocks."""
import argparse
from pathlib import Path
import shutil
import subprocess
import numpy as np
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from native_engine_clock import audit_clock, compare_poses, clock_echo_matches
from native_godot_payload import payload


def run(study, output, native_tracks=False, authoring_seek=False):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists() or output.parent != ROOT/'reports':
        raise ValueError('Fresh immediate reports folder required')
    if authoring_seek and not native_tracks: raise ValueError('Authoring seek requires native tracks')
    q, result = read(study/'request.json'), read(study/'result.json')
    if result['status'] != 'complete' or not result['native_animation_exported']:
        raise ValueError('Completed native exports required')
    files = dict(q['inputs'])
    for name in ('request.json', 'result.json'):
        files[str(study/name)] = sha256(study/name)
    for root, entries in [(study, result['outputs']), (study/'implementation', q['implementation'])]:
        for name, digest in entries.items():
            path = (root/name).resolve()
            if path.parent != root: raise ValueError('Escaping evidence path')
            if str(path) in files and files[str(path)] != digest: raise ValueError('Conflicting evidence')
            files[str(path)] = digest
    def unchanged():
        for path, digest in files.items():
            if sha256(path) != digest: raise ValueError('Changed engine audit evidence')
    unchanged()
    declared = list(q['guard_times_s'])+list(q['window_s'])
    declared += [t for span in q.get('protected_spans', []) for t in span]
    declared += list(q.get('plane_times_s', []))
    # Include the motion-cap clock when the source study declares it.
    if 'uniform_times_s' in q: declared += list(q['uniform_times_s'])
    cases, sources = [], []
    for i in range(2):
        path = study/f'candidate-{i}.glb'
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound candidate')
        rig = RigAsset.load(path)
        if len(rig.document.get('animations', [])) != 1: raise ValueError('One native animation required')
        sampler = AnimationSampler(rig.document, rig.binary, 0)
        names = [rig.document['nodes'][j].get('name') for j in rig.joints]
        if any(not n for n in names) or len(set(names)) != len(names): raise ValueError('Unique named joints required')
        times = audit_clock(sampler.duration, [c[2] for c in sampler.channels], declared, q['event_time_s'])
        cases.append(dict(id=f'actor-{i}', path=str(path), frames=len(times), sample_times_s=times.tolist(), authoring_seek=authoring_seek))
        if native_tracks:
            cases[-1].update(native_payload=payload(rig, sampler, sha256(path)),
                            native_animation_output=str(output/f'actor-{i}-animation.res'))
        sources.append((rig, sampler, names))
    engine = ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    files[str(engine)] = sha256(engine)
    methods = {}
    for path in [Path(__file__), ROOT/'scripts/native_engine_clock.py', ROOT/'scripts/native_godot_import_audit.gd',
                 ROOT/'scripts/native_godot_payload.py', ROOT/'scripts/native_godot_tracks.gd',
                 ROOT/'scripts/native_godot_preview.gd',
                 ROOT/'scripts/rig_asset.py', ROOT/'scripts/rig_clip_import.py', ROOT/'scripts/gltf_tools.py', ROOT/'scripts/strep.py']:
        methods[path] = sha256(path)
    output.mkdir(); project = output/'project'; project.mkdir()
    archive = output/'implementation'; archive.mkdir()
    for path, digest in methods.items():
        target = archive/path.name; shutil.copyfile(path, target)
        if sha256(target) != digest: raise ValueError('Method copy differs')
        files[str(target)] = digest
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep native clock audit"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', encoding='utf8')
    shutil.copyfile(ROOT/'scripts/native_godot_import_audit.gd', project/'audit.gd')
    shutil.copyfile(ROOT/'scripts/native_godot_tracks.gd', project/'native_godot_tracks.gd')
    shutil.copyfile(ROOT/'scripts/native_godot_preview.gd', project/'native_godot_preview.gd')
    save(output/'request.json', dict(at=now(), study=str(study), inputs=files, cases=cases, tolerance=1e-4,
        event_time_s=q['event_time_s'], bake_fps=30, native_tracks=native_tracks, authoring_seek=authoring_seek,
        seek_scope='Explicit full-clip 120Hz, native keys/midpoints and authored event/window/guard/plane/protected clock; exact deduplication only.'))
    save(output/'pipeline.json', dict(status='processing'))
    try:
        with (output/'engine.log').open('w', encoding='utf8') as log:
            completed = subprocess.run([str(engine), '--headless', '--path', str(project), '--script', 'audit.gd', '--',
                str(output/'request.json'), str(output/'engine-output.json')], stdout=log, stderr=subprocess.STDOUT,
                timeout=300, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if completed.returncode: raise ValueError('Godot failed; inspect retained engine.log')
        actual = read(output/'engine-output.json')
        if len(actual['cases']) != len(cases): raise ValueError('Missing engine case')
        checks = []
        for case, observed, (rig, sampler, names) in zip(cases, actual['cases'], sources):
            if observed['id'] != case['id'] or len(observed['frames']) != case['frames']: raise ValueError('Engine case/frame mismatch')
            if len(observed['bone_names']) != len(names) or set(observed['bone_names']) != set(names): raise ValueError('Engine joint names differ')
            if len([n for n in observed['animations'] if n != 'RESET']) != 1: raise ValueError('Ambiguous engine animation')
            order = [rig.joints[names.index(n)] for n in observed['bone_names']]
            rows = []
            for time, frame in zip(case['sample_times_s'], observed['frames']):
                if not clock_echo_matches(time, frame['requested_time_s']): raise ValueError('Engine used a different requested clock')
                row = compare_poses(sampler.sample(time)[order], frame['bones'])
                rows.append(dict(time_s=time, actual_time_s=frame['actual_time_s'], **row))
            save(output/f"{case['id']}-errors.json", rows)
            maximum = {k: max(r[k] for r in rows) for k in ('position_error_m', 'basis_element_error')}
            time_error = max(abs(r['time_s']-r['actual_time_s']) for r in rows)
            duration_error = abs(observed['duration_s']-sampler.duration)
            surfaces = sum(bool(m['weights']) for m in observed['meshes'])
            seek_clock_pass = all(clock_echo_matches(r['time_s'], r['actual_time_s']) for r in rows)
            passed = max(*maximum.values(), duration_error) <= 1e-4 and seek_clock_pass and observed['imported_loop_mode'] == 0 and surfaces > 0
            event = next(r for r in rows if r['time_s'] == q['event_time_s'])
            checks.append(dict(id=case['id'], samples=len(rows), bones=len(order), source_sha256=sha256(case['path']),
                **maximum, maximum_seek_time_error_s=time_error, duration_error_s=duration_error, event=event,
                seek_clock_pass=seek_clock_pass,
                imported_skinned_surfaces=surfaces, imported_loop_mode=observed['imported_loop_mode'], engine_pose_pass=bool(passed)))
        unchanged()
        if any(sha256(p) != digest for p, digest in methods.items()): raise ValueError('Method changed during audit')
        passed = all(c['engine_pose_pass'] for c in checks)
        save(output/'verification.json', dict(at=now(), engine=actual['engine'], checks=checks, engine_pose_pass=passed,
            native_tracks=native_tracks,
            authoring_seek=authoring_seek,
            scope='Actual headless Godot import and world-joint seek at explicit native/fractional/full-clip samples.'+(' Default baked animation replaced by original LINEAR bone keys and saved/reloaded binary Animation resources.' if native_tracks else ' Default fixed-rate Godot import retained.')+(' Direct native-track authoring scrubbing; ordinary AnimationPlayer playback and event dispatch are separate.' if authoring_seek else ' Ordinary AnimationPlayer seek.')+' Imported GPU skin, contact/collision correctness, human quality and Studio selection are not established.',
            quality_approved=False, selected_for_studio=False, gpu_skin_verified=False))
        save(output/'result.json', dict(at=now(), status='complete', engine_pose_pass=passed,
            outputs={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file() and p.name != 'pipeline.json'},
            quality_approved=False, selected_for_studio=False))
        save(output/'pipeline.json', dict(status='complete', engine_pose_pass=passed))
        print(checks, flush=True)
        return passed
    except Exception as error:
        save(output/'pipeline.json', dict(status='failed', reason=str(error)))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--native-tracks', action='store_true')
    parser.add_argument('--authoring-seek', action='store_true')
    args = parser.parse_args()
    if not run(args.study, args.output, args.native_tracks, args.authoring_seek): raise SystemExit(2)
