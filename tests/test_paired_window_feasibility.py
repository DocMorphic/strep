import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from paired_window_feasibility import movable_times, fixed_collision_floor


def model():
    return SimpleNamespace(times=np.arange(9)/4, entries=[dict(ids=np.array([2]), clock=np.arange(5)/2, weights=np.ones((1, 1)))])


def samples(m):
    return [dict(sample=i, time_s=float(t), directions=[dict(maximum_depth_m=.02 if i == 1 else 0), dict(maximum_depth_m=0)]) for i,t in enumerate(m.times)]


def test_native_support_has_open_endpoints_and_includes_editable_key():
    m = model(); assert movable_times(m).tolist() == [False, False, False, True, True, True, False, False, False]


def test_fixed_penetration_rules_out_complete_clearance():
    m = model(); report = fixed_collision_floor([m, m], samples(m))
    assert report['unavoidable_sampled_peak_m'] == .02 and report['fixed_failing_samples'] == 1
    assert report['clearance_ruled_out_by_fixed_samples']


def test_one_movable_actor_is_enough_to_avoid_a_fixed_pair_claim():
    a = model(); b = model(); b.entries[0]['ids'] = np.array([1])
    result = fixed_collision_floor([a, b], samples(a))
    assert not result['clearance_ruled_out_by_fixed_samples']


def test_incomplete_source_geometry_cannot_prove_a_floor():
    m = model()
    with pytest.raises(ValueError): fixed_collision_floor([m, m], samples(m)[:-1])


def test_all_zero_basis_weights_cannot_move_a_selected_key():
    m = model(); m.entries[0]['weights'][:] = 0; assert not movable_times(m).any()


def test_native_decoder_preserves_every_predicted_fixed_sample():
    from test_timed_rotation_edit import fixture
    from timed_rotation_edit import TimedRotationEdit
    doc, binary = fixture(); m = TimedRotationEdit(doc, binary, ['Arm'], np.arange(181)/120, [.1, 1.3], [[.713, .713]])
    fixed = ~movable_times(m); assert fixed.any()
    for seed in range(3):
        controls = np.random.default_rng(seed).normal(size=m.size)*.01
        np.testing.assert_allclose(m.world(controls)[fixed], m.source_world[fixed], atol=1e-12, rtol=0)
