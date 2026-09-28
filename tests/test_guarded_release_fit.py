import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from guarded_release_fit import acceleration_envelope_pair, support_envelope_pair, relax


def test_acceleration_envelope_includes_all_affected_centers_and_derivatives():
    rng = np.random.default_rng(61)
    track = rng.normal(size=(7, 2, 3))*.01
    jac = rng.normal(size=(2, 3, 4))*.03
    caps = np.full((5, 2), 30.)
    direction = rng.normal(size=4)
    for frame, expected in [(0, 2), (1, 4), (3, 6), (5, 4), (6, 2)]:
        values, derivative = acceleration_envelope_pair(track, frame, track[frame], jac, caps, 30.)
        assert len(values) == expected
        difference = np.einsum('sip,p->si', jac, direction)*1e-6
        minus = acceleration_envelope_pair(track, frame, track[frame]-difference, jac, caps, 30.)[0]
        plus = acceleration_envelope_pair(track, frame, track[frame]+difference, jac, caps, 30.)[0]
        np.testing.assert_allclose((plus-minus)/2e-6, derivative@direction, atol=1e-8, rtol=1e-7)
        changed = track.copy(); changed[frame] += difference
        centers = range(max(1, frame-1), min(len(track)-2, frame+1)+1)
        acceleration = np.diff(changed, n=2, axis=0)*30**2
        expected_values = [(caps[c-1]**2-(acceleration[c-1]**2).sum(axis=1))/caps[c-1]**2 for c in centers]
        np.testing.assert_allclose(plus, np.ravel(expected_values))


def test_support_envelope_respects_contact_steps_and_both_neighbor_signs():
    rng = np.random.default_rng(88)
    track = rng.normal(size=(5, 2, 3))*.001
    jac = rng.normal(size=(2, 3, 3))*.02
    active = np.array([[True, False], [True, True], [False, True], [False, False]])
    caps = np.full((4, 2), .3)
    direction = rng.normal(size=3)
    for frame in range(5):
        values, derivative = support_envelope_pair(track, frame, track[frame], jac, active, caps, 30.)
        ends = [end for end in (frame, frame+1) if 1 <= end < len(track)]
        assert len(values) == sum(active[end-1].sum() for end in ends)
        dx = np.einsum('sip,p->si', jac, direction)*1e-6
        minus = support_envelope_pair(track, frame, track[frame]-dx, jac, active, caps, 30.)[0]
        plus = support_envelope_pair(track, frame, track[frame]+dx, jac, active, caps, 30.)[0]
        np.testing.assert_allclose((plus-minus)/2e-6, derivative@direction, atol=1e-8, rtol=1e-7)


class ToyFitter:
    """A linear skin with a known avoidable acceleration spike."""
    nodes = [0, 1]
    bounds = np.ones(9)
    spec = dict(fps=1., patches=dict(Left=dict(vertices=[0]), Right=dict(vertices=[1])),
                limits=dict(root_step_m=1., joint_step_degrees=90.))

    class Rig:
        parents = [-1, -1]
        document = dict(nodes=[{}, {}])
        @staticmethod
        def vertices(world):
            return world[:, :3, 3]

    rig = Rig()

    def pose(self, frame, values):
        world = np.tile(np.eye(4), (2, 1, 1))
        world[:, 1, 3] = .001
        world[0, 0, 3] = values[6]
        world[1, 0, 3] = values[7]
        return world, world

    def surface_jacobian(self, frame, values):
        derivative = np.zeros((2, 3, 9))
        derivative[0, 0, 6] = 1.
        derivative[1, 0, 7] = 1.
        return self.rig.vertices(self.pose(frame, values)[0]), derivative


def test_solver_reduces_spike_without_changing_eliminated_tracks_or_caps():
    initial = np.zeros((5, 9)); initial[2, 6] = .1
    initial[:, :3] = [.001, .002, .003]
    initial[:, 3:6] = [.01, .02, .03]
    result, records, proof = relax(ToyFitter(), initial, np.zeros((3, 2)), np.zeros((5, 2), bool), [0], sweeps=2)
    np.testing.assert_array_equal(result[:, :6], initial[:, :6])
    # Two sweeps promise descent, not convergence to the linear skin's optimum.
    assert proof['energy_after'] < proof['energy_before']
    track = np.array([ToyFitter.rig.vertices(ToyFitter().pose(f, x)[0]) for f, x in enumerate(result)])
    acceleration = np.linalg.norm(np.diff(track, n=2, axis=0), axis=2)
    np.testing.assert_allclose(proof['energy_after'], np.sum(acceleration**2), atol=1e-12)
    assert np.all(acceleration <= np.array(proof['safety_caps_m_s2'])+1e-5)
    assert any(r['accepted'] for r in records)


def test_serialized_solver_checks_quantized_tracks_and_half_frames():
    from serialized_pose import SerializedPose
    fitter = ToyFitter()
    initial = np.zeros((5, 9)); initial[2, 6] = .100003
    class CountingEvaluator(SerializedPose):
        calls = 0
        def half_pose(self, *args):
            self.calls += 1
            return super().half_pose(*args)
    evaluator = CountingEvaluator(fitter.rig, {0, 1}, 0, 5)
    result, _, proof = relax(fitter, initial, np.zeros((3, 2)), np.zeros((5, 2), bool), [0], sweeps=2, pose_evaluator=evaluator)
    world = [fitter.pose(f, x)[0] for f, x in enumerate(result)]
    decoded = np.array([fitter.rig.vertices(evaluator.pose(w)) for w in world])
    acceleration = np.linalg.norm(np.diff(decoded, n=2, axis=0), axis=2)
    np.testing.assert_allclose(proof['energy_after'], np.sum(acceleration**2), atol=1e-12)
    assert proof['energy_after'] < proof['energy_before']
    assert np.all(acceleration <= np.asarray(proof['safety_caps_m_s2'])+1e-5)
    assert evaluator.calls > 4  # More than initial feasibility checks.
    for f in range(4):
        assert fitter.rig.vertices(evaluator.half_pose(world[f], world[f+1], f))[:, 1].min() >= -.005
