from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from auxiliary_root_diagnostic import diagnose
from rig_asset import RigAsset


def fixture():
    rig = SimpleNamespace(parents=[-1, 0], joints=[0, 1],
        reference=np.repeat(np.eye(4)[None], 2, axis=0),
        inverse=np.repeat(np.eye(4)[None], 2, axis=0))
    rig.primitives = [dict(node=2, positions=np.array([[0., -.2, 0.], [0., -.4, 0.], [0., -.8, 0.]]),
        joints=np.array([[0, 1], [0, 1], [0, 1]]), weights=np.array([[.25, .75], [0., 1.], [1e-14, 1.]]))]
    rig.vertices = lambda world: RigAsset.vertices(rig, world)
    def sample(time):
        world = rig.reference.copy()
        world[1, 1, 3] = time
        return world
    return rig, SimpleNamespace(sample=sample, duration=1.)


def test_raw_influence_and_conditional_lower_bound_preserve_inputs():
    rig, reader = fixture()
    before = rig.primitives[0]['weights'].copy()
    result = diagnose(rig, reader, 0, 1, [0., .5, 1.])
    assert result['affected_vertices'] == 2  # Tiny positive weight is not discarded.
    assert result['unaffected_vertices'] == 1
    assert result['unaffected_floor_lower_bound_max_m'] == pytest.approx(.4)
    assert result['rows'][-1]['maximum_vertex_change_m'] == pytest.approx(.25)
    assert result['maximum_delta_error_m'] < 1e-12
    assert not result['quality_approved'] and not result['release_approved']
    np.testing.assert_array_equal(before, rig.primitives[0]['weights'])


def test_rotation_and_nonunit_homogeneous_response():
    rig, reader = fixture()
    rig.inverse[0, 3, 3] = 1.000001
    def sample(time):
        world = rig.reference.copy()
        world[1, :3, :3] = [[np.cos(time), -np.sin(time), 0], [np.sin(time), np.cos(time), 0], [0, 0, 1]]
        world[1, 0, 3] = time
        return world
    reader.sample = sample
    result = diagnose(rig, reader, 0, 1, [0., 1.])
    assert result['maximum_delta_error_m'] < 1e-12
    assert result['maximum_hierarchy_reconstruction_error'] < 1e-12


@pytest.mark.parametrize('clock', [[0., 0., 1.], [0., .5], [0., float('nan'), 1.], [-1., 1.]])
def test_incomplete_clock_rejected(clock):
    rig, reader = fixture()
    with pytest.raises(ValueError, match='clock'):
        diagnose(rig, reader, 0, 1, clock)


@pytest.mark.parametrize('root,anchor', [(1, 0), (0, 0), (True, 1), (-1, 1)])
def test_invalid_root_selection_rejected(root, anchor):
    rig, reader = fixture()
    with pytest.raises(ValueError):
        diagnose(rig, reader, root, anchor, [0., 1.])
