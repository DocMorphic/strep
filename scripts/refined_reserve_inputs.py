"""Bind a completed refined export audit without changing original motion policy."""
from pathlib import Path
import numpy as np
from strep import ROOT, read, sha256
from bound_evidence import bind_inputs


def completed(folder, names):
    folder = Path(folder).resolve()
    result = read(folder/'result.json')
    if result.get('status') != 'complete': raise ValueError('Completed evidence required')
    files = {str(folder/'result.json'): sha256(folder/'result.json')}
    for name in names:
        digest = result[name.split('.')[0]+'_sha256']
        if sha256(folder/name) != digest: raise ValueError('Refined evidence changed: '+name)
        files[str(folder/name)] = digest
    request = read(folder/'request.json')
    files.update(bind_inputs({}, request['inputs']))
    for name, digest in request['implementation'].items():
        path = folder/'implementation'/name
        if sha256(path) != digest or sha256(ROOT/'scripts'/name) != digest:
            raise ValueError('Refined method changed: '+name)
        files[str(path)] = digest
    return request, files


def load_refined_audit(audit, study, original, required):
    audit = Path(audit).resolve()
    audit_request, files = completed(audit, ['request.json', 'trials.json'])
    if audit_request.get('angular_motion') is not True: raise ValueError('Angular refined audit required')
    refinement = Path(audit_request['refinement']).resolve()
    request, refined_files = completed(refinement, ['request.json', 'solver.json', 'linearization.npz'])
    if Path(request['study']).resolve() != Path(study).resolve(): raise ValueError('Refined study differs')
    bind_inputs(required, request['inputs'])
    bind_inputs(refined_files, audit_request['inputs'])
    files.update(refined_files)
    with np.load(refinement/'linearization.npz', allow_pickle=False) as archive: linear = dict(archive)
    for key in ['surface_vectors', 'gaps', 'depth_caps', 'vectors', 'radii']:
        np.testing.assert_allclose(linear[key], original[key], atol=1e-12, rtol=0)
    np.testing.assert_array_equal(linear['kinds'], original['kinds'])
    scaling = request.get('solver_scaling', dict(scale=.005, regularizer=1e-4))
    scale, regularizer = scaling['scale'], scaling['regularizer']
    if not np.isfinite([scale, regularizer]).all() or min(scale, regularizer) <= 0 or not np.isclose(scale*regularizer, 5e-7, rtol=1e-12, atol=0):
        raise ValueError('Equivalent positive physical objective scaling required')
    return request, linear, files, dict(scale=scale, regularizer=regularizer)


def install_refined_models(actors, descriptions):
    from timed_rotation_edit import TimedRotationEdit
    from diagnose_scene_pair_refinement import refine_knots
    if [a['name'] for a in actors] != [d['actor'] for d in descriptions]: raise ValueError('Refined actor order differs')
    for actor, description in zip(actors, descriptions):
        old = actor['model']
        np.testing.assert_array_equal(old.knots, description['original_knots_s'])
        expected, _ = refine_knots(old.knots, len(old.nodes))
        np.testing.assert_array_equal(expected, description['refined_knots_s'])
        if old.size != description['original_controls']: raise ValueError('Original control count differs')
        fine = TimedRotationEdit(old.document, old.binary, [old.document['nodes'][n]['name'] for n in old.nodes],
            old.times, old.window, old.protected, knots=expected, limit_degrees=old.limit_degrees)
        if fine.size != description['refined_controls']: raise ValueError('Refined control count differs')
        for before, after in zip(old.entries, fine.entries):
            for key in ['ids', 'original', 'clock', 'source']: np.testing.assert_array_equal(before[key], after[key])
        np.testing.assert_array_equal(old.source_world, fine.source_world)
        actor['original_knots'] = old.knots.copy()
        actor['model'] = fine
        # Keep actor['rates'] and caller's angular policies from the original model.
