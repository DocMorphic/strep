"""All-frame Godot joint verification for explicit-profile target rig exports."""
import argparse
import shutil
import subprocess
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from gltf_tools import sample_animation


def run(study, output):
    study, output = Path(study).resolve(), Path(output).resolve()
    manifest = read(study / 'manifest.json')
    cases = []
    for item in manifest['cases']:
        path = study / item['path']
        if item['fps'] != 30 or sha256(path) != item['sha256']:
            raise ValueError('Engine fixture requires unchanged 30fps GLB')
        timed=item.get('sample_by_time',False)
        if type(timed) is not bool:raise ValueError('Invalid source sampling option')
        if timed and len(RigAsset.load(path).document.get('animations',[]))!=1:
            raise ValueError('Time-sampled source audit requires one unambiguous animation')
        case=dict(id=item['id'], path=str(path), frames=item['frames'],sample_by_time=timed)
        if timed:case['sample_times_s']=(np.arange(item['frames'],dtype=np.float32)/30).astype(float).tolist()
        cases.append(case)
    output.mkdir(parents=True, exist_ok=False)
    project = output / 'project'; project.mkdir()
    (project / 'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep target rig audit"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', encoding='utf8')
    script = ROOT / 'scripts/godot_import_audit.gd'
    shutil.copyfile(script, project / 'audit.gd')
    save(output / 'request.json', dict(cases=cases))
    save(output / 'pipeline.json', dict(status='processing'))
    engine = ROOT / '.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    with (output / 'engine.log').open('w', encoding='utf8') as log:
        completed = subprocess.run([str(engine), '--headless', '--path', str(project), '--script', 'audit.gd', '--', str(output / 'request.json'), str(output / 'engine-output.json')],
                                   stdout=log, stderr=subprocess.STDOUT, timeout=300, creationflags=subprocess.CREATE_NO_WINDOW)
    if completed.returncode:
        save(output / 'pipeline.json', dict(status='failed', exit_code=completed.returncode))
        raise ValueError('Godot import failed; inspect engine.log')
    actual = read(output / 'engine-output.json')
    if len(actual['cases']) != len(cases):
        raise ValueError('Missing engine cases')
    checks = []
    for case, observed in zip(cases, actual['cases']):
        if case['id'] != observed['id'] or len(observed['frames']) != case['frames']:
            raise ValueError('Engine case/frame mismatch')
        rig = RigAsset.load(case['path'])
        names = {rig.document['nodes'][node].get('name'): node for node in rig.joints}
        if len(names) != len(rig.joints) or set(observed['bone_names']) != set(names):
            raise ValueError('Engine renamed, omitted or added joints; needs explicit engine-node mapping')
        order = [names[name] for name in observed['bone_names']]
        source_sampler=None
        if case['sample_by_time']:
            from rig_clip_import import AnimationSampler
            source_sampler=AnimationSampler(rig.document,rig.binary,0)
        position_error, basis_error = 0., 0.
        for frame, pose in enumerate(observed['frames']):
            expected = (source_sampler.sample(case['sample_times_s'][frame]) if source_sampler else sample_animation(rig.document, rig.binary, 0, frame))[order]
            found = np.asarray(pose['bones'])
            position_error = max(position_error, float(np.abs(found[:, 3] - expected[:, :3, 3]).max()))
            basis_error = max(basis_error, float(np.abs(found[:, :3].transpose(0, 2, 1) - expected[:, :3, :3]).max()))
        expected_duration = source_sampler.duration if source_sampler else (case['frames'] - 1) / 30
        if max(position_error, basis_error, abs(observed['duration_s'] - expected_duration)) > 1e-4:
            save(output/'pipeline.json',dict(status='failed',case=case['id'],max_position_error_m=position_error,max_basis_error=basis_error,reason='Engine animation differs from expected rig samples'))
            raise ValueError('Engine animation differs from exported rig')
        # Surface counts survive import; Godot may reorder/deduplicate vertices,
        # so do not equate mesh ordering with CPU skin validation here.
        skinned = [m for m in observed['meshes'] if m['weights']]
        checks.append(dict(id=case['id'], frames=case['frames'], bones=len(order), source_sha256=sha256(case['path']),
                           max_position_error_m=position_error, max_basis_element_error=basis_error,
                           duration_s=observed['duration_s'], imported_loop_mode=observed.get('imported_loop_mode'),imported_skinned_surfaces=len(skinned),sampled_original_by_time=case['sample_by_time']))
        if not skinned:
            raise ValueError('Engine dropped skinned mesh')
    save(output / 'verification.json', dict(created_at=now(), engine=actual['engine'], checks=checks,
        runner_sha256=sha256(__file__), engine_script_sha256=sha256(script),
        scope='Actual Godot GLB import and all-frame world joint transforms on target rig. CPU mesh roundtrip is separate; GPU skin, contact correctness and animator review are not established.'))
    save(output / 'pipeline.json', dict(status='complete'))
    print(checks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); run(args.study, args.output)
