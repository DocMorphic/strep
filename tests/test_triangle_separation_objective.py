import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from triangle_separation_objective import gaps, choose_axes, TriangleSeparationObjective
from triangle_crossing import classify


A = np.array([[-1., -1, 0], [1, -1, 0], [0, 1, 0]])
B = np.array([[0., -.5, -1], [0, -.5, 1], [0, .5, .2]])


def test_nine_rows_match_support_gap_and_detect_crossing():
    assert classify(A, B)['kind'] == 'proper_crossing'
    axis = choose_axes(A[None], B[None]); values = gaps(A[None], B[None], axis)
    assert values.shape == (1, 9) and values.min() < 0
    expected = (B@axis[0]).min()-(A@axis[0]).max()
    assert values.min() == pytest.approx(expected)
    moved = B+axis[0]*(-expected+.001)
    assert gaps(A[None], moved[None], axis).min() == pytest.approx(.001)
    assert classify(A, moved)['kind'] == 'disjoint'


def test_fixed_rows_vary_linearly_under_vertex_translation():
    axis = choose_axes(A[None], B[None]); rng = np.random.default_rng(212)
    da, db = rng.normal(size=(2, 3, 3))
    initial = gaps(A[None], B[None], axis)
    derivative = gaps(da[None], db[None], axis)
    for step in [-.1, -.001, .001, .1]:
        np.testing.assert_allclose(gaps((A+step*da)[None], (B+step*db)[None], axis), initial+step*derivative, atol=1e-15)


def test_rigid_transform_and_actor_swap_preserve_gaps():
    rotation = Rotation.from_rotvec([.3, .1, -.8]).as_matrix(); translation = [2, -3, 4]
    axis = choose_axes(A[None], B[None])
    first = gaps(A[None], B[None], axis)
    moved = gaps((A@rotation.T+translation)[None], (B@rotation.T+translation)[None], axis@rotation.T)
    np.testing.assert_allclose(first, moved, atol=2e-15)
    np.testing.assert_allclose(first.reshape(3, 3), gaps(B[None], A[None], -axis).reshape(3, 3).T)


class Points:
    def evaluate(self, world, frames, vertices): return world[frames, vertices]


def test_objective_preserves_vertices_times_placements_and_immutable_axes():
    worlds = [np.stack([A, A+[1, 0, 0]]), np.stack([B, B+[2, 0, 0]])]
    frames = np.array([1, 0]); vertices = np.tile([0, 1, 2], (2, 2, 1))
    placements = [dict(rotation=np.eye(3), translation=np.array([0., 0, i])) for i in range(2)]
    left, right = worlds[0][frames], worlds[1][frames]+[0, 0, 1]
    axes = choose_axes(left, right)
    expected = (1e-8-gaps(left, right, axes)).ravel()
    objective = TriangleSeparationObjective([Points(), Points()], placements, frames, vertices, axes)
    frames[:] = 0; vertices[:] = 1; axes[:] = 0; placements[1]['translation'][:] = 0
    np.testing.assert_allclose(objective.depths(worlds), expected)


@pytest.mark.parametrize('kind', ['frame', 'vertices', 'axes', 'clearance', 'placement'])
def test_invalid_witness_data_fail_closed(kind):
    frames = np.array([0]); vertices = np.tile([0, 1, 2], (2, 1, 1)); axes = np.array([[1., 0, 0]])
    placements = [dict(rotation=np.eye(3), translation=np.zeros(3)) for _ in range(2)]; clearance = 1e-8
    if kind == 'frame': frames = np.array([-.1])
    elif kind == 'vertices': vertices = vertices.astype(float)
    elif kind == 'axes': axes *= 2
    elif kind == 'clearance': clearance = -1
    else: placements[0]['rotation'][0, 0] = 2
    with pytest.raises(ValueError): TriangleSeparationObjective([Points(), Points()], placements, frames, vertices, axes, clearance)


def test_pose_batch_population_is_checked():
    objective = TriangleSeparationObjective([Points(), Points()], [dict(rotation=np.eye(3), translation=np.zeros(3))]*2,
        np.array([1]), np.tile([0, 1, 2], (2, 1, 1)), np.array([[1., 0, 0]]))
    with pytest.raises(ValueError, match='frame'): objective.depths([A[None], B[None]])


def test_historical_proof_binds_archived_code_and_exact_assets(tmp_path):
    from study_triangle_hand_proposal import proof_inputs
    from strep import sha256
    source = tmp_path/'scripts'; source.mkdir()
    proof = tmp_path/'proof'; (proof/'implementation').mkdir(parents=True)
    current = source/'method.py'; current.write_text('new implementation')
    archived = proof/'implementation'/'method.py'; archived.write_text('old implementation')
    asset = tmp_path/'asset.glb'; asset.write_bytes(b'bound original bytes')
    declared = {str(current): sha256(archived), str(asset): sha256(asset)}
    bound = proof_inputs(proof, declared, source)
    assert bound == {str(archived): sha256(archived), str(asset): sha256(asset)}
    asset.write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed'): proof_inputs(proof, declared, source)


def test_tampered_archived_proof_code_is_rejected(tmp_path):
    from study_triangle_hand_proposal import proof_inputs
    from strep import sha256
    source = tmp_path/'scripts'; source.mkdir()
    proof = tmp_path/'proof'; (proof/'implementation').mkdir(parents=True)
    archived = proof/'implementation'/'method.py'; archived.write_text('old')
    declared = {str(source/'method.py'): sha256(archived)}
    archived.write_text('changed')
    with pytest.raises(ValueError, match='changed'): proof_inputs(proof, declared, source)
