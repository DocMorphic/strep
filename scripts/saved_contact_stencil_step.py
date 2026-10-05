"""Compose caller-selected saved coordinate responses; decoded checks required.

All original residual rows remain. This finite affine prediction cannot prove
motion feasibility, including Float32 storage effects or joint cross terms.
"""
import argparse
import math
from pathlib import Path
import shutil
import zipfile
import numpy as np
from strep import ROOT, read, save, sha256, now
from native_contact_norms import score, row_regression
from cumulative_coupled_contacts import conditions
from native_contact_mask_probe import stencils

METHODS = ('saved_contact_stencil_step.py', 'native_contact_norms.py',
           'cumulative_coupled_contacts.py', 'native_contact_mask_probe.py', 'strep.py')


def arrays(value):
    if not isinstance(value, dict) or set(value) != {'controls', 'native', 'surface'}:
        raise ValueError('Complete control/native/surface arrays required')
    result = {k: np.asarray(v, float) for k, v in value.items()}
    if any(v.ndim != 1 or not len(v) or not np.isfinite(v).all() for v in result.values()):
        raise ValueError('Complete finite one-dimensional populations required')
    if np.any(abs(result['controls']) > 1):
        raise ValueError('Original normalized control boxes required')
    return result


def compose(baseline, selected, *, step):
    base = arrays(baseline)
    if not isinstance(selected, list) or not 1 <= len(selected) <= 8:
        raise ValueError('Choose 1-8 complete explicit coordinate responses')
    if type(step) not in (int, float) or not np.isfinite(step) or not 1e-6 <= step <= .005:
        raise ValueError('Original bounded signed stencil step required')
    native, surface = base['native'].copy(), base['surface'].copy()
    delta = np.zeros_like(base['controls']); seen = set()
    for sample in selected:
        other = arrays(sample)
        if any(other[k].shape != base[k].shape for k in base):
            raise ValueError('Complete original row populations must match')
        changed = np.flatnonzero(other['controls'] != base['controls'])
        if len(changed) != 1 or int(changed[0]) in seen:
            raise ValueError('Distinct single-coordinate responses required')
        index = int(changed[0]); sign = int(np.sign(other['controls'][index] - base['controls'][index]))
        if other['controls'][index] != base['controls'][index] + sign*step:
            raise ValueError('Exact original signed stencil step required')
        seen.add(index); delta[index] = sign*step
        native += other['native'] - base['native']
        surface += other['surface'] - base['surface']
    controls = base['controls'] + delta
    if np.any(abs(controls) > 1) or not np.isfinite(np.r_[native, surface]).all():
        raise ValueError('Complete finite prediction within original boxes required')
    before, after = score(base['surface']), score(surface)
    native_pass = bool(np.all(native <= 0))
    guard_pass = bool(np.all(row_regression(base['surface'], surface) <= 0))
    improves = bool(np.all(after <= before) and np.any(after < before))
    report = dict(predicted_native_pass=native_pass, predicted_native_failed_rows=int((native > 0).sum()),
        predicted_contact_guard_pass=guard_pass,
        predicted_contact_guard_failed_rows=int((row_regression(base['surface'], surface) > 0).sum()),
        before_surface_score=before.tolist(), predicted_surface_score=after.tolist(),
        predicted_surface_score_improves=improves, seed_available=bool(native_pass and guard_pass and improves),
        changed_indices=sorted(seen), native_rows=len(native), surface_rows=len(surface),
        maximum_control_step=float(abs(delta).max()), decoded_verified=False,
        physical_feasibility_proved=False, quality_approved=False, training_admitted=False, release_approved=False)
    return dict(controls=controls, native=native, surface=surface, direction=delta), report


def load_arrays(path, *, maximum_bytes=64*1024**2):
    """Bound headers and complete payload before loading generated NPZ arrays."""
    if type(maximum_bytes) is not int or not 1024 <= maximum_bytes <= 256*1024**2:
        raise ValueError('Explicit finite array budget required')
    path = Path(path)
    if path.stat().st_size > maximum_bytes:
        raise ValueError('Complete archive exceeds byte budget')
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) != 3 or {e.filename for e in entries} != {'controls.npy', 'native.npy', 'surface.npy'}:
            raise ValueError('Complete unique control/native/surface archive entries required')
        total = 0
        for entry in entries:
            if entry.file_size > maximum_bytes:
                raise ValueError('Complete array payload exceeds budget')
            with archive.open(entry) as stream:
                version = np.lib.format.read_magic(stream)
                if version not in ((1, 0), (2, 0)):
                    raise ValueError('Explicit generated numeric NPY format required')
                reader = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
                shape, _, dtype = reader(stream)
                if len(shape) != 1 or not shape[0] or dtype.kind != 'f' or dtype.itemsize != 8:
                    raise ValueError('Complete generated Float64 vectors required')
                size = math.prod(shape)*dtype.itemsize; total += size
                if total > maximum_bytes or size + stream.tell() != entry.file_size:
                    raise ValueError('Complete array population exceeds budget or payload differs')
    with np.load(path, allow_pickle=False) as data:
        return arrays({k: data[k] for k in data.files})


def load_baseline(path, *, maximum_bytes=1024**2):
    """Check original baseline NPY header before any shape-driven allocation."""
    if type(maximum_bytes) is not int or not 1024 <= maximum_bytes <= 1024**2:
        raise ValueError('Explicit finite baseline byte budget required')
    path = Path(path); size = path.stat().st_size
    if size > maximum_bytes:
        raise ValueError('Complete baseline exceeds byte budget')
    with path.open('rb') as stream:
        version = np.lib.format.read_magic(stream)
        if version not in ((1, 0), (2, 0)):
            raise ValueError('Explicit original numeric baseline format required')
        reader = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
        shape, _, dtype = reader(stream)
        if len(shape) != 1 or not shape[0] or dtype.kind != 'f' or dtype.itemsize not in (4, 8):
            raise ValueError('Complete original floating baseline vector required')
        logical = math.prod(shape)*dtype.itemsize
        if logical > maximum_bytes or logical + stream.tell() != size:
            raise ValueError('Baseline header exceeds budget or payload differs')
    return np.load(path, allow_pickle=False)


def run(study, output, *, result_sha256, picks, baseline_source):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Fresh saved composition output required')
    if (not isinstance(picks, list) or not 1 <= len(picks) <= 8
            or any(type(k) is not int or k < 0 for k in picks) or len(set(picks)) != len(picks)):
        raise ValueError('Choose 1-8 distinct explicit probe numbers')
    if sha256(study/'result.json') != result_sha256:
        raise ValueError('Caller-pinned complete producer result required')
    if any((study/n).stat().st_size > 8*1024**2 for n in ('result.json', 'request.json')):
        raise ValueError('Complete producer JSON exceeds budget')
    result, request = read(study/'result.json'), read(study/'request.json')
    if (result.get('schema') != 'strep-native-contact-mask-probe-result-v1' or result.get('status') != 'complete'
            or request.get('schema') != 'strep-native-contact-mask-probe-v1'
            or result.get('request_sha256') != sha256(study/'request.json')
            or any(result.get(k) is not False for k in ('collision_verified', 'engine_executed', 'quality_approved', 'training_admitted', 'release_approved'))
            or result.get('original_selected') is not True or result.get('native_caps_rebuilt_from_candidate') is not False):
        raise ValueError('Unapproved complete source-bound mask experiment required')
    bindings = {str(study/n): sha256(study/n) for n in ('result.json', 'request.json')}
    bindings.update(request['inputs_sha256'])
    baseline_source = Path(baseline_source).resolve()
    if (str(baseline_source) not in request['inputs_sha256'] or baseline_source.stat().st_size > 1024**2
            or sha256(baseline_source) != request['inputs_sha256'][str(baseline_source)]):
        raise ValueError('Explicit producer-bound baseline controls required')
    for name, digest in request['implementation_sha256'].items():
        if Path(name).name != name or sha256(ROOT/'scripts'/name) != digest:
            raise ValueError('Original producer method required')
        bindings[str(ROOT/'scripts'/name)] = digest
    samples = result['predicted']
    if len(samples) != request['predicted_probes'] or len(samples) != 2*len(request['indices']):
        raise ValueError('Complete ordered predicted probe population required')
    if any(k >= len(samples) for k in picks):
        raise ValueError('Existing explicit probe number required')

    def load(folder, report):
        path = study/folder/'conditions.npz'
        if sha256(path) != report['conditions_sha256']:
            raise ValueError('Complete saved condition arrays changed')
        bindings[str(path)] = report['conditions_sha256']; value = load_arrays(path)
        expected = conditions(value['native'], value['surface'])
        if any(report.get(k) != v for k, v in expected.items()) or any(type(report.get(k)) is not bool for k in ('native_pass', 'surface_contacts_pass')):
            raise ValueError('Saved complete condition reductions differ')
        if len(value['native']) != report['native_rows'] or len(value['surface']) != report['surface_rows']:
            raise ValueError('Complete saved condition row population differs')
        return value

    baseline = load('baseline', result['baseline']); selected = []
    if not np.array_equal(baseline['controls'], load_baseline(baseline_source)):
        raise ValueError('Saved baseline controls differ from original bound baseline')
    original_stencils = stencils(baseline['controls'], request['indices'], request['step'])
    if result['baseline'].get('independently_decoded') is not True:
        raise ValueError('Independently decoded baseline required')
    for k in picks:
        report = samples[k]; index = request['indices'][k//2]; sign = -1 if k%2 == 0 else 1
        if (any(type(report.get(n)) is not int for n in ('probe', 'index', 'sign'))
                or report.get('probe') != k or report.get('index') != index or report.get('sign') != sign
                or report.get('independently_decoded') is not False):
            raise ValueError('Exact original coordinate and sign required')
        value = load('predicted-'+str(k), report)
        expected = original_stencils[k][2]
        if not np.array_equal(value['controls'], expected):
            raise ValueError('Original stencil control population differs')
        selected.append(value)
    combined, report = compose(baseline, selected, step=request['step'])
    implementation = {n: sha256(ROOT/'scripts'/n) for n in METHODS}
    for path, digest in bindings.items():
        if sha256(path) != digest:
            raise ValueError('Bound composition input changed')
    output.mkdir(); (output/'implementation').mkdir()
    for name in METHODS:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), producer_result_sha256=result_sha256, picks=picks,
        inputs_sha256=bindings, implementation_sha256=implementation, original_selected=True))
    np.savez_compressed(output/'prediction.npz', **combined)
    if report['seed_available']:
        np.save(output/'seed-direction.npy', combined['direction'])
    if any(sha256(p) != h for p, h in bindings.items()) or any(sha256(ROOT/'scripts'/n) != h or sha256(output/'implementation'/n) != h for n, h in implementation.items()):
        raise ValueError('Bound composition inputs or methods changed')
    report.update(schema='strep-saved-contact-stencil-step-v1', at=now(), status='complete',
        request_sha256=sha256(output/'request.json'), prediction_sha256=sha256(output/'prediction.npz'),
        seed_sha256=sha256(output/'seed-direction.npy') if report['seed_available'] else None,
        original_selected=True, retained_new_improvement=False, engine_executed=False, geometry_queries_rerun=False,
        scope='Complete finite affine secant prediction around one decoded baseline. No cross-term or storage-error certificate; full decoded/native/contact/geometry/import checks remain required.')
    save(output/'result.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study'); parser.add_argument('output')
    parser.add_argument('--result-sha256', required=True)
    parser.add_argument('--baseline-source', required=True)
    parser.add_argument('--picks', required=True, type=int, nargs='+')
    args = parser.parse_args()
    print(run(args.study, args.output, result_sha256=args.result_sha256, picks=args.picks,
              baseline_source=args.baseline_source))
