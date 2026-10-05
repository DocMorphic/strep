import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import saved_contact_stencil_step as saved
from strep import read, save, sha256
from cumulative_coupled_contacts import conditions


def base_and_samples():
    base = dict(controls=np.zeros(3), native=np.array([-1., -.2]), surface=np.array([2., -1., 1.]))
    left = dict(controls=np.array([-.005, 0., 0.]), native=np.array([-.9, -.2]), surface=np.array([1.5, -1., 1.]))
    right = dict(controls=np.array([0., -.005, 0.]), native=np.array([-1., -.1]), surface=np.array([2., -1., .5]))
    return base, [left, right]


def test_complete_secants_compose_with_frozen_other_controls_and_no_approval():
    base, selected = base_and_samples(); values, report = saved.compose(base, selected, step=.005)
    np.testing.assert_allclose(values['native'], [-.9, -.1], atol=1e-15)
    np.testing.assert_allclose(values['surface'], [1.5, -1, .5], atol=1e-15)
    np.testing.assert_array_equal(values['direction'], [-.005, -.005, 0])
    assert report['seed_available'] and report['changed_indices'] == [0, 1]
    assert report['native_rows'] == 2 and report['surface_rows'] == 3
    for key in ('decoded_verified', 'physical_feasibility_proved', 'quality_approved', 'training_admitted', 'release_approved'):
        assert report[key] is False


def test_passing_affine_secants_cannot_certify_cross_terms():
    # Both single-coordinate samples pass; a possible nonlinear response is
    # -1 + .4*(u+v) + .8*u*v, where u,v are normalized stencil fractions.
    base, selected = base_and_samples(); base['native'] = np.array([-1.])
    for s in selected: s['native'] = np.array([-.6])
    _, report = saved.compose(base, selected, step=.005)
    assert report['predicted_native_pass'] and -1 + .4*(1+1) + .8*1*1 > 0
    assert not report['physical_feasibility_proved'] and not report['decoded_verified']


@pytest.mark.parametrize('case', ['native', 'passing-surface', 'failed-surface', 'no-improvement'])
def test_every_original_native_and_surface_guard_is_kept(case):
    base, selected = base_and_samples()
    if case == 'native': selected[1]['native'][-1] = .01
    if case == 'passing-surface': selected[1]['surface'][1] = .01
    if case == 'failed-surface': selected[1]['surface'][0] = 2.6
    if case == 'no-improvement':
        for s in selected: s['surface'] = base['surface'].copy()
    _, report = saved.compose(base, selected, step=.005)
    assert not report['seed_available']


@pytest.mark.parametrize('case', ['duplicate', 'multiple-controls', 'shape', 'nonfinite', 'wrong-step', 'extra-field'])
def test_invalid_coordinate_population_reject(case):
    base, selected = base_and_samples()
    if case == 'duplicate': selected[1]['controls'] = selected[0]['controls'].copy()
    if case == 'multiple-controls': selected[1]['controls'][2] = .005
    if case == 'shape': selected[1]['native'] = np.ones(1)
    if case == 'nonfinite': selected[1]['surface'][0] = np.nan
    if case == 'wrong-step': selected[1]['controls'][1] = -.004
    if case == 'extra-field': selected[1]['caps'] = [99]
    with pytest.raises(ValueError): saved.compose(base, selected, step=.005)


def fixture(tmp_path):
    study = tmp_path/'study'; study.mkdir(); base, selected = base_and_samples()
    baseline = tmp_path/'baseline.npy'; np.save(baseline, base['controls'])
    request = dict(schema='strep-native-contact-mask-probe-v1', indices=[0, 1], step=.005,
        predicted_probes=4, inputs_sha256={str(baseline.resolve()): sha256(baseline)},
        implementation_sha256={'native_contact_mask_probe.py': sha256(saved.ROOT/'scripts/native_contact_mask_probe.py')})
    save(study/'request.json', request)
    def write(name, value, decoded, **details):
        folder = study/name; folder.mkdir(); np.savez_compressed(folder/'conditions.npz', **value)
        return dict(**conditions(value['native'], value['surface']), native_rows=len(value['native']),
            surface_rows=len(value['surface']), independently_decoded=decoded,
            conditions_sha256=sha256(folder/'conditions.npz'), **details)
    rows = []
    for k in range(4):
        index, sign = k//2, -1 if k%2 == 0 else 1
        if sign == -1: value = selected[index]
        else:
            value = {n: a.copy() for n, a in base.items()}; value['controls'][index] = .005
        rows.append(write('predicted-'+str(k), value, False, probe=k, index=index, sign=sign))
    result = dict(schema='strep-native-contact-mask-probe-result-v1', status='complete',
        request_sha256=sha256(study/'request.json'), baseline=write('baseline', base, True), predicted=rows,
        native_caps_rebuilt_from_candidate=False, original_selected=True, collision_verified=False,
        engine_executed=False, quality_approved=False, training_admitted=False, release_approved=False)
    save(study/'result.json', result)
    return study, baseline


def execute(study, baseline, output):
    return saved.run(study, output, result_sha256=sha256(study/'result.json'), picks=[0, 2], baseline_source=baseline)


def test_saved_transport_full_arrays_and_explicit_baseline(tmp_path):
    study, baseline = fixture(tmp_path); output = tmp_path/'combined'
    report = execute(study, baseline, output)
    assert report['seed_available'] and report['original_selected'] and not report['retained_new_improvement']
    np.testing.assert_array_equal(np.load(output/'seed-direction.npy', allow_pickle=False), [-.005, -.005, 0])
    assert report['prediction_sha256'] == sha256(output/'prediction.npz')
    with pytest.raises(ValueError, match='Fresh'): execute(study, baseline, output)


@pytest.mark.parametrize('case', ['result-pin', 'arrays', 'false-index', 'reduction', 'baseline', 'population', 'wrong-probe'])
def test_tampered_or_mixed_saved_evidence_rejects(tmp_path, case):
    study, baseline = fixture(tmp_path); result = read(study/'result.json')
    if case == 'result-pin':
        with pytest.raises(ValueError, match='Caller-pinned'):
            saved.run(study, tmp_path/'out', result_sha256='0'*64, picks=[0, 2], baseline_source=baseline)
        return
    if case == 'arrays':
        (study/'predicted-0/conditions.npz').write_bytes(b'changed')
    if case == 'false-index': result['predicted'][0]['index'] = False
    if case == 'reduction': result['predicted'][0]['contact_score'][0] += .1
    if case == 'baseline': np.save(baseline, np.ones(3)*.01)
    if case == 'population': result['predicted'].pop()
    if case == 'wrong-probe': result['predicted'][0]['sign'] = 1
    save(study/'result.json', result)
    with pytest.raises(ValueError): execute(study, baseline, tmp_path/'out')
    assert not (tmp_path/'out/result.json').exists()


def test_archive_header_budget_and_non_numeric_payload_reject(tmp_path):
    path = tmp_path/'arrays.npz'; base, _ = base_and_samples(); np.savez_compressed(path, **base)
    assert saved.load_arrays(path)['native'].shape == (2,)
    huge = dict(base); huge['surface'] = np.zeros(1024); np.savez_compressed(path, **huge)
    with pytest.raises(ValueError, match='budget'): saved.load_arrays(path, maximum_bytes=1024)
    objects = dict(base); objects['controls'] = np.array(['wrong'], object); np.savez_compressed(path, **objects)
    with pytest.raises(ValueError, match='Float64'): saved.load_arrays(path)


@pytest.mark.parametrize('dtype', [np.float32, np.float64])
def test_baseline_header_keeps_original_numeric_values(tmp_path, dtype):
    path = tmp_path/'baseline.npy'; values = np.array([.1, -.4, .3], dtype=dtype); np.save(path, values)
    loaded = saved.load_baseline(path)
    assert loaded.dtype == values.dtype
    np.testing.assert_array_equal(loaded, values)


@pytest.mark.parametrize('case', ['huge-header', 'missing-payload', 'object', 'extra-payload'])
def test_baseline_rejects_bad_header_before_array_allocation(tmp_path, case):
    path = tmp_path/'baseline.npy'
    if case in ('huge-header', 'missing-payload'):
        with path.open('wb') as stream:
            np.lib.format.write_array_header_1_0(stream, dict(descr='<f8', fortran_order=False,
                shape=(2**35 if case == 'huge-header' else 5,)))
            stream.write(np.array([0.], dtype='<f8').tobytes())
    elif case == 'object': np.save(path, np.array(['bad'], object))
    else:
        np.save(path, np.zeros(3))
        with path.open('ab') as stream: stream.write(b'extra')
    with pytest.raises(ValueError): saved.load_baseline(path)
