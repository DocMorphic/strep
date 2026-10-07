from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_key_control_support import effective_basis
from native_support_clock import NativeSupportSampler


def test_event_knot_has_neighbor_support_when_it_is_not_a_native_key():
    clock = np.array([0., .49, .51, 1.], np.float32)
    knots = np.array([0., .4, .5, .6, 1.])
    basis = np.stack([np.interp(clock, knots, np.eye(5)[i]) for i in range(5)], axis=1)
    nominal = np.array([np.interp(.5, knots, np.eye(5)[i]) for i in range(5)])
    actual = effective_basis(clock, np.arange(4), basis, .5)
    np.testing.assert_array_equal(nominal, [0., 0., 1., 0., 0.])
    assert actual[1] > .049 and actual[3] > .049 and actual[2] < .901
    # A change whose authored event-knot value is zero still changes rotation
    # at the event after native key interpolation.
    angles = basis @ np.array([0., .2, 0., 0., 0.])
    quats = Rotation.from_rotvec(np.c_[angles, np.zeros((4,2))]).as_quat()
    sampled = NativeSupportSampler.value('rotation', clock, quats, 'LINEAR', .5)
    assert Rotation.from_quat(sampled).magnitude() > .009


def test_exact_native_keys_have_only_their_own_authored_basis_and_frozen_keys_zero():
    clock = np.array([0., .1, .2, 1.], np.float32)
    weights = np.array([[2., -3.], [5., 7.]])
    for time in (float(clock[0]), float(clock[3])):
        np.testing.assert_array_equal(effective_basis(clock, [1,2], weights, time), [0.,0.])
    np.testing.assert_array_equal(effective_basis(clock, [1,2], weights, float(clock[1])), weights[0])
    np.testing.assert_array_equal(effective_basis(clock, [1,2], weights, float(clock[2])), weights[1])


def test_actual_linear_translation_response_matches_complete_effective_basis():
    rng = np.random.default_rng(713)
    clock = np.array([0., .1, .2, .9, 1.], np.float32)
    ids = np.array([1,2,3]); basis = rng.normal(size=(3,4)); controls = rng.normal(size=(4,3))
    source = rng.normal(size=(5,3)); changed = source.copy(); changed[ids] += basis@controls
    times = [0., .03, .15, .8, 1., 2.]
    for key in clock:
        times.extend([float(key), np.nextafter(float(key), -np.inf), np.nextafter(float(key), np.inf)])
    for time in times:
        if time < 0:
            continue
        old = NativeSupportSampler.value('translation',clock,source,'LINEAR',time)
        new = NativeSupportSampler.value('translation',clock,changed,'LINEAR',time)
        np.testing.assert_allclose(new-old,effective_basis(clock,ids,basis,time)@controls,atol=1e-14,rtol=0)


def test_original_inputs_unchanged_and_endpoint_scalar_type_preserved():
    clock = np.array([0., .1, .2, 1.],np.float32); ids=np.array([1]); basis=np.array([[1.]])
    before = [a.copy() for a in (clock,ids,basis)]
    time = np.nextafter(np.float64(1.), -np.inf)
    expected = NativeSupportSampler.value('translation',clock,np.array([[0.],[1.],[0.],[0.]]),'LINEAR',time)
    np.testing.assert_array_equal(effective_basis(clock,ids,basis,time),expected)
    for a,b in zip((clock,ids,basis),before):
        np.testing.assert_array_equal(a,b)


@pytest.mark.parametrize('clock,ids,weights,time', [
    ([0.,0.],[0],[[1.]],0.),
    ([-1.,1.],[0],[[1.]],0.),
    ([0.,np.inf],[0],[[1.]],0.),
    ([0.,1.],[True],[[1.]],0.),
    ([0.,1.],[0,0],[[1.],[1.]],0.),
    ([0.,1.],[2],[[1.]],0.),
    ([0.,1.],[0.],[[1.]],0.),
    ([0.,1.],[0],[[np.nan]],0.),
    ([0.,1.],[0],np.zeros((1,97)),0.),
    ([0.,1.],[0],[[1.]],True),
    ([0.,1.],[0],[[1.]],-.01),
    ([0.,1.],[0],[[1.]],1j),
])
def test_bad_or_incomplete_native_basis_is_rejected(clock,ids,weights,time):
    with pytest.raises(ValueError):
        effective_basis(clock,ids,weights,time)
