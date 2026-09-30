import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from diagnose_scene_pair_limits import constraint_population, trust_only_bound, original_checks, load_bound_study, variants_for
from strep import ROOT, save, sha256


def example():
    return dict(gaps=np.array([-.02, .01]), gap_jacobian=np.array([[1., 0, 0], [0, 0, 0]]),
        depth_caps=np.array([.02, .005]), vectors=np.array([[1., 0, 0], [0, 0, 0]]),
        jacobians=np.array([np.eye(3), np.eye(3)]), radii=np.array([1., .1]), kinds=np.array(['speed', 'edit']),
        surface_vectors=np.array([[-.02, 0, 0], [.01, 0, 0]]), surface_jacobians=np.array([np.eye(3), np.eye(3)]))


def test_inside_witnesses_only_join_norm_population_with_physical_kinds():
    population = constraint_population(example())
    assert population['kinds'].tolist() == ['speed', 'edit', 'surface_distance']
    np.testing.assert_array_equal(population['radii'], [1., .1, .02])
    np.testing.assert_array_equal(population['tolerances'], [1e-6, 1e-8, 1e-8])


def test_independent_control_balls_bound_uses_sum_of_block_norms():
    gaps = np.array([-.02, -.05]); jacobian = np.array([[3., 4, 0, 0, 0, 2], [0, 0, 0, 0, 0, 1]])
    bound = trust_only_bound(gaps, jacobian, .01)
    assert bound['limiting_row'] == 1 and bound['peak_floor_m'] == pytest.approx(.04)
    assert bound['row_maximum_gain_m'] == pytest.approx(.01)


def test_zero_derivative_collision_cannot_be_removed_by_any_affine_step():
    assert trust_only_bound(np.array([-.02]), np.zeros((1, 6)), 5.)['peak_floor_m'] == .02


def test_profiles_keep_matched_baseline_and_declare_every_relaxation():
    for profile in ['norms', 'surface-caps', 'angular-limits']:
        rows = variants_for(profile)
        assert rows[0]['name'] == 'original' and rows[0]['per_time_caps']
        assert rows[0]['omitted_norm_kinds'] == [] and rows[0]['regularizer'] == 1e-4
        assert len({r['name'] for r in rows}) == len(rows)
    capped = variants_for('surface-caps')[-1]
    assert not capped['per_time_caps'] and set(capped['omitted_norm_kinds']) == {'surface_distance', 'speed', 'acceleration'}
    with pytest.raises(ValueError): variants_for('unknown')


def test_angular_profile_separates_motion_families_and_preserves_edit_budgets():
    variants={v['name']:v for v in variants_for('angular-limits')}
    assert variants['without_angular']['omitted_norm_kinds']==['angular_speed','angular_acceleration']
    assert variants['without_positional']['omitted_norm_kinds']==['speed','acceleration']
    assert set(variants['without_all_motion']['omitted_norm_kinds'])=={'speed','acceleration','angular_speed','angular_acceleration'}
    assert all('edit' not in v['omitted_norm_kinds'] for v in variants.values())
    assert variants['without_surface_distance']['per_time_caps']
    assert not variants['without_local_surface_caps']['per_time_caps']
    assert variants['tenfold_trust']['trust_multiplier']==10


def test_original_checks_report_angular_violations_even_when_omitted_from_solve():
    linear=example();linear['kinds']=np.array(['angular_acceleration','edit'])
    result=original_checks(linear,constraint_population(linear),np.array([.01,0,0]),.02)
    assert result['groups']['angular_acceleration']['failures']==1
    assert result['groups']['angular_acceleration']['maximum_excess']==pytest.approx(.01)
    assert result['groups']['angular_speed']['rows']==0


def test_diagnostic_relaxation_still_reports_violation_of_original_limits():
    linear = example(); population = constraint_population(linear)
    result = original_checks(linear, population, np.array([.01, 0, 0]), .005)
    assert result['predicted_peak_m'] == pytest.approx(.01)
    assert result['groups']['speed']['failures'] == 1
    assert result['groups']['speed']['maximum_excess'] == pytest.approx(.01)
    assert result['groups']['surface_distance']['failures'] == 0
    assert result['groups']['acceleration']['rows'] == 0
    assert result['original_trust_excess_radians'] == pytest.approx(.005)


@pytest.mark.parametrize('fault', [None, 'array', 'witness', 'snapshot', 'input', 'unfinished'])
def test_diagnostic_requires_completed_bound_inputs(tmp_path, fault):
    (tmp_path/'source').mkdir(); (tmp_path/'implementation').mkdir()
    save(tmp_path/'source/sample.json', {'sample': 0})
    save(tmp_path/'source-index.json', {'sample.json': sha256(tmp_path/'source/sample.json')})
    methods = {}
    for name in ['coupled_pair_proposal.py', 'conic_root_descent.py']:
        path = tmp_path/'implementation'/name
        path.write_bytes((ROOT/'scripts'/name).read_bytes()); methods[name] = sha256(path)
    original = tmp_path/'actor.glb'; original.write_bytes(b'input fixture')
    save(tmp_path/'request.json', dict(implementation=methods, inputs={str(original): sha256(original)}))
    np.savez(tmp_path/'linearization.npz', **example()); save(tmp_path/'solver.json', {})
    record = dict(status='complete')
    for name in ['request.json', 'source-index.json', 'linearization.npz', 'solver.json']:
        record[name.split('.')[0].replace('-', '_')+'_sha256'] = sha256(tmp_path/name)
    if fault == 'unfinished': record['status'] = 'processing'
    save(tmp_path/'result.json', record)
    paths = dict(array='linearization.npz', witness='source/sample.json', snapshot='implementation/coupled_pair_proposal.py', input='actor.glb')
    if fault in paths: (tmp_path/paths[fault]).write_bytes(b'changed evidence')
    if fault:
        with pytest.raises(ValueError): load_bound_study(tmp_path)
    else:
        _, arrays, files = load_bound_study(tmp_path)
        np.testing.assert_array_equal(arrays['gaps'], example()['gaps'])
        assert str(original) in files
