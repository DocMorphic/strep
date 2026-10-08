from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_fit_body_policy import arguments, validate_mode
from scene_fit_body_policy import reach_report
from skin_point_reach_bound import error_lower_bound
from scipy.spatial.transform import Rotation


def motion(frames=4):
    return {'posed_joints': np.zeros((frames, 77, 3), dtype=np.float32)}


def test_references_keep_complete_clocks_and_are_independent_snapshots():
    raw, limb, previous = motion(), motion(), motion()
    raw['posed_joints'][:, 0, 0] = [0, 1, 2, 3]
    options = arguments(raw, limb, previous)
    raw['posed_joints'].fill(99)
    options['native_body_references']['limb']['posed_joints'].fill(10)
    assert np.array_equal(options['native_body_references']['raw']['posed_joints'][:, 0, 0], [0, 1, 2, 3])
    assert not limb['posed_joints'].any()
    assert not options['native_body_references']['previous']['posed_joints'].any()
    assert all(ref['posed_joints'].dtype == np.float64 and ref['posed_joints'].shape == (4, 77, 3)
               for ref in options['native_body_references'].values())


@pytest.mark.parametrize('bad', [None, {}, {'posed_joints': np.zeros((1, 77, 3))},
    {'posed_joints': np.zeros((4, 76, 3))}, {'posed_joints': np.zeros((4, 77, 2))},
    {'posed_joints': np.zeros((4, 77, 3), dtype=bool)},
    {'posed_joints': np.full((4, 77, 3), np.nan)}, {'posed_joints': np.full((4, 77, 3), np.inf)}])
def test_invalid_reference_rejected(bad):
    with pytest.raises(ValueError):
        arguments(motion(), bad, motion())


def test_clock_mismatch_rejected_before_any_fit():
    with pytest.raises(ValueError):
        arguments(motion(), motion(5), motion())


@pytest.mark.parametrize('flag', [None, 0, 1, 'true'])
def test_mode_requires_explicit_boolean(flag):
    with pytest.raises(ValueError):
        validate_mode(17, flag)


@pytest.mark.parametrize('version', [2, 8, 16, 18, '17', 17.0, True])
def test_enabled_mode_rejects_other_solver_versions(version):
    with pytest.raises(ValueError):
        validate_mode(version, True)


def test_disabled_mode_preserves_existing_baseline_versions():
    for version in [2, 8, 16, 17]:
        validate_mode(version, False)
    validate_mode(17, True)


def test_reach_bound_is_conservative_for_random_rotations_and_joint_edits():
    rng = np.random.default_rng(42)
    positions = rng.normal(size=(128, 8, 3))
    raw_rotations = Rotation.random(128*8, random_state=rng).as_matrix().reshape(128, 8, 3, 3)
    # Include finite source matrix rounding; the bound uses its actual norm.
    raw_rotations *= 1.000001
    local = rng.normal(size=(8, 3))*.04
    weights = rng.random(8); weights /= weights.sum()
    targets = rng.normal(size=(128, 3))
    result = error_lower_bound(positions, raw_rotations, local, weights, targets, .22)
    edits = rng.normal(size=positions.shape)
    edits *= (.22*rng.random((128, 8, 1)))/np.linalg.norm(edits, axis=2, keepdims=True)
    new_rotations = Rotation.random(128*8, random_state=rng).as_matrix().reshape(128, 8, 3, 3)
    new_points = np.sum((np.einsum('fnij,nj->fni', new_rotations, local)+positions+edits)*weights[None, :, None], axis=1)
    assert np.all(np.linalg.norm(new_points-targets, axis=1) >= result['error_lower_bound_m'])


def test_reach_bound_can_prove_impossible_target_and_is_tight_in_simple_case():
    positions = np.zeros((1, 1, 3))
    rotations = np.eye(3)[None, None]
    local = np.array([[1., 0, 0]])
    target = np.array([[-1.25, 0, 0]])
    result = error_lower_bound(positions, rotations, local, np.ones(1), target, .22)
    assert result['error_lower_bound_m'][0] == pytest.approx(.03-1e-6)
    closest_point = np.array([-1.22, 0, 0]) # 180-degree turn + full .22 m joint edit
    assert np.linalg.norm(closest_point-target[0]) == pytest.approx(.03)


def test_zero_reach_lower_bound_is_not_feasibility_certificate():
    result = error_lower_bound(np.zeros((1, 1, 3)), np.eye(3)[None, None],
        np.array([[1., 0, 0]]), np.ones(1), np.zeros((1, 3)), 0.)
    assert result['error_lower_bound_m'][0] == 0
    # With zero joint movement, every proper rotation keeps this point at radius
    # one; the requested center cannot be reached despite the zero lower bound.
    assert np.linalg.norm(np.array([1., 0, 0])) == 1


@pytest.mark.parametrize('budget', [True, -1, float('nan'), float('inf')])
def test_invalid_reach_budget_rejected(budget):
    with pytest.raises(ValueError):
        error_lower_bound(np.zeros((1, 1, 3)), np.eye(3)[None, None], np.zeros((1, 3)), np.ones(1), np.zeros((1, 3)), budget)


@pytest.mark.parametrize('weights', [np.array([-1.]), np.zeros(1), np.array([np.nan]), np.array([True])])
def test_invalid_reach_weights_rejected(weights):
    with pytest.raises(ValueError):
        error_lower_bound(np.zeros((1, 1, 3)), np.eye(3)[None, None], np.zeros((1, 3)), weights, np.zeros((1, 3)), .22)


def small_skin():
    return dict(bind_rig_transform=np.repeat(np.eye(4)[None], 77, axis=0),
                bind_vertices=np.array([[.01, 0, 0]]), lbs_indices=np.zeros((1, 8), dtype=int),
                lbs_weights=np.array([[1., 0, 0, 0, 0, 0, 0, 0]]))


def reach_fixture():
    raw = motion(); raw['global_rot_mats'] = np.broadcast_to(np.eye(3), (4, 77, 3, 3)).copy()
    spec = dict(frame_count=4, regions=dict(LeftHand=dict(mode='explicit', segments=[
        dict(start_frame=1, end_frame=2, space='track', vertex_id=0,
             positions_m=[[1., 0, 0], [0., 0, 0]], tolerance_m=.03)])))
    return raw, small_skin(), spec


def test_compiled_contact_preflight_reports_only_proven_native_conflicts():
    raw, skin, spec = reach_fixture()
    original = raw['posed_joints'].copy()
    result = reach_report(raw, skin, spec)
    assert result['status'] == 'provably_incompatible_native_keys'
    assert result['rows'][0]['incompatible_frames'] == [1]
    assert result['rows'][0]['authored_incompatible_frames'] == [1]
    assert result['rows'][0]['working_tolerance_m'] == pytest.approx(.00499)
    assert np.array_equal(raw['posed_joints'], original)
    assert not result['quality_approved'] and not result['release_approved']


def test_unsupported_target_selection_is_explicitly_skipped():
    raw, skin, spec = reach_fixture()
    del spec['regions']['LeftHand']['segments'][0]['vertex_id']
    result = reach_report(raw, skin, spec)
    assert result['status'] == 'not_proven_incompatible' and result['skipped'] and not result['rows']


def test_static_target_and_tighter_authored_limit_do_not_widen_acceptance():
    raw, skin, spec = reach_fixture()
    spec['regions']['LeftHand']['segments'][0] = dict(start_frame=1, end_frame=2,
        space='world', vertex_id=0, position_m=[1., 0, 0], tolerance_m=.001)
    result = reach_report(raw, skin, spec)
    assert result['rows'][0]['working_tolerance_m'] == pytest.approx(.00099)
    assert result['rows'][0]['incompatible_frames'] == [1, 2]


def test_bad_reference_clock_rejected_in_preflight():
    raw, skin, spec = reach_fixture(); spec['frame_count'] = 5
    with pytest.raises(ValueError): reach_report(raw, skin, spec)
