import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from mesh_regression_cuts import MeshRegressionCuts
from sampled_surface_guard import topology


class Points:
    def evaluate(self, world, frames, vertices):
        return world[frames, vertices]


def fixture():
    triangle = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
    worlds = [np.array([triangle, triangle]), np.array([triangle+[0, 0, .1], triangle+[0, 0, .2]])]
    def snapshot(proper):
        return dict(topology=topology([np.array([[0, 1, 2]])]*2, [3, 3]), samples=[
            dict(time_s=float(i), tolerance_m=1e-8, proper=proper, uncertain=[], degenerate=[[], []], depths_m=[0., 0.])
            for i in range(2)])
    return worlds, snapshot([]), snapshot([[0, 0]])


def build(worlds, original, rejected, times=(0., 1.)):
    return MeshRegressionCuts([Points()]*2, [dict(rotation=np.eye(3), translation=np.zeros(3))]*2,
        times, [np.array([[0, 1, 2]])]*2, original, rejected, worlds)


def test_all_new_pair_times_retained_and_frozen_to_original():
    worlds, original, rejected = fixture()
    cuts = build(worlds, original, rejected)
    assert cuts.record['pairs'] == 2 and cuts.record['scalar_rows'] == 18
    assert np.all(cuts.margins(worlds) > 0)
    changed = [worlds[0].copy(), worlds[1].copy()]
    changed[1][1, :, 2] = -.01
    values = cuts.margins(changed).reshape(2, 9)
    assert np.all(values[0] > 0) and np.all(values[1] < 0)
    np.testing.assert_array_equal(cuts.floor, [-1e-8, -1e-8])
    assert cuts.record['fresh_mesh_validation_required'] and not cuts.record['quality_approved']


def test_existing_crossings_are_not_relabelled_as_new():
    worlds, original, rejected = fixture()
    original['samples'][0]['proper'] = [[0, 0]]
    cuts = build(worlds, original, rejected)
    assert cuts.record['pairs'] == 1 and cuts.record['rows'][0]['time_s'] == 1.


def test_missing_pose_time_rejected():
    worlds, original, rejected = fixture()
    with pytest.raises(ValueError, match='exact pose'):
        build(worlds, original, rejected, (0., 2.))


def test_topology_mismatch_rejected():
    worlds, original, rejected = fixture()
    rejected['topology'] = [dict(faces=2, vertices=4)]*2
    with pytest.raises(ValueError, match='Fixed topology'):
        build(worlds, original, rejected)


def test_empty_new_population_cannot_claim_repair():
    worlds, original, _ = fixture()
    with pytest.raises(ValueError, match='Observed new'):
        build(worlds, original, original)
