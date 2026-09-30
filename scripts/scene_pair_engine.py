"""Reuse completed engine observations only for the exact exported clip identities."""
from pathlib import Path
import shutil
import math
from strep import ROOT, read, save, sha256, now


def copy_verified_engine(study, previous, output):
    study, previous, output = [Path(p).resolve() for p in [study, previous, output]]
    if output.exists(): raise ValueError('Fresh engine evidence destination required')
    if read(previous/'pipeline.json')['status'] != 'complete': raise ValueError('Completed engine observations required')
    report = read(previous/'verification.json'); request = read(previous/'request.json')
    if report['runner_sha256'] != sha256(ROOT/'scripts/run_godot_rig_import.py') or report['engine_script_sha256'] != sha256(ROOT/'scripts/godot_import_audit.gd'):
        raise ValueError('Engine observation method changed')
    cases = read(study/'manifest.json')['cases']; selected = []
    if not cases: raise ValueError('Nonempty current export population required')
    for case in cases:
        if case['fps'] != 30 or case.get('sample_by_time') is not True:
            raise ValueError('Native time-sampled clip manifest required')
        path = (study/case['path']).resolve()
        if not path.is_relative_to(study) or sha256(path) != case['sha256']:
            raise ValueError('Current export differs from its manifest')
        checks = [c for c in report['checks'] if c['id'] == case['id']]
        inputs = [c for c in request['cases'] if c['id'] == case['id']]
        if len(checks) != 1 or len(inputs) != 1: raise ValueError('Matching distinct engine case required')
        check, original = checks[0], inputs[0]
        if sha256(original['path']) != case['sha256'] or check['source_sha256'] != case['sha256'] or check['frames'] != case['frames'] or original['frames'] != case['frames']:
            raise ValueError('Engine observations belong to another clip or clock')
        errors = [check['max_position_error_m'], check['max_basis_element_error']]
        if any(not math.isfinite(e) or e < 0 or e > 1e-4 for e in errors) or check['bones'] != 77 or check['imported_skinned_surfaces'] < 1 or check['imported_loop_mode'] != 0 or not check['sampled_original_by_time'] or not original['sample_by_time']:
            raise ValueError('Matching native nonlooping skinned import checks required')
        selected.append(case['id'])
    if len(set(selected)) != len(selected): raise ValueError('Distinct current clip IDs required')
    files = {name: sha256(previous/name) for name in ['request.json', 'verification.json', 'engine-output.json', 'pipeline.json']}
    output.mkdir()
    for name, digest in files.items():
        shutil.copyfile(previous/name, output/name)
        if sha256(output/name) != digest or sha256(previous/name) != digest: raise ValueError('Engine evidence changed during copy')
    save(output/'reused-evidence.json', dict(at=now(), source=str(previous), files=files, matched_cases=selected,
        manifest_sha256=sha256(study/'manifest.json'), quality_approved=False,
        scope='Existing all-frame observations reused by exact clip bytes, actor ID, native clock and unchanged verifier. Extra observed attempts remain in the report. No new engine run or motion approval.'))
