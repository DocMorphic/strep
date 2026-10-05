"""Bounded actual-curve stage traces do not replace full native/geometry audits."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_native_scene_fit import prepare
from native_scene_fit import SceneProblem
from native_scene_norms import rows, rate_vectors
from sampled_motion_caps import features
from native_condition_ledger import NativeConditionLedger, RATE_METRICS
from native_rate_stage_trace import trace, rate_vector


def fixture(tmp_path, rotation=False, kind='joint_angular_acceleration'):
    _, _, _, _, _, scene, edits = prepare(tmp_path, rotation=rotation)
    problem = SceneProblem(scene, edits)
    ledger = NativeConditionLedger(scene, edits)
    block = next(b for b in ledger.blocks if b['kind'] == kind)
    order = next(order for name, order, unit in RATE_METRICS if name == kind)
    # A sample strictly within editable support, retaining original skin order.
    sample = 113
    joint = 3 if rotation else 0
    row = block['start'] + sample * len(block['items']) + joint
    metric = next(i for i, (name, _, _) in enumerate(RATE_METRICS) if name == kind)
    cap = float(problem.caps['A'].caps[metric][sample, joint])
    value = edits.initial.copy()
    value.reshape(-1, 3)[:, 1] = [.03, .06, .04]
    path = tmp_path / 'candidate.glb'
    edits.export('A', value, path)
    return scene, edits, problem, ledger, row, cap, value, path


@pytest.mark.parametrize('rotation', [False, True])
@pytest.mark.parametrize('kind', [name for name, _, _ in RATE_METRICS])
def test_each_actual_native_rate_row_matches_complete_decoded_math_and_fixed_source_interval(tmp_path, rotation, kind):
    scene, edits, problem, ledger, row, cap, value, path = fixture(tmp_path, rotation, kind)
    result = trace(edits, value, row, path, source_cap=cap, source_tolerance=problem.caps['A'].tolerance)
    native, worlds = problem.decoded({'A': path}, value)
    vectors = rows(problem, value, worlds)
    assert result['row'] == ledger.locate(row)
    order = next(order for name, order, _ in RATE_METRICS if name == kind)
    assert result['sample_count'] == order + 1
    assert result['source_interval_s'] == problem.caps['A'].dt
    np.testing.assert_allclose(result['stages']['decoded']['vector'], vectors.vectors[row], atol=1e-12, rtol=1e-12)
    assert result['stages']['decoded']['residual'] == pytest.approx(native[row], abs=1e-10, rel=1e-12)
    assert result['stages']['decoded']['local_row_pass'] == bool(native[row] <= 0)
    assert result['all_controlled_native_keys_matched'] and result['static_and_unselected_payloads_preserved']
    assert result['candidate_sha256'] and result['source_actors_sha256']
    assert not result['full_motion_audited'] and not result['source_cap_provenance_checked']
    assert not result['source_caps_reconstructed'] and not result['geometry_checked'] and not result['release_approved']
    assert result['differences']['quantized_proxy_vs_decoded']['maximum_basis_component_difference'] < 1e-12


def test_supplied_controls_must_match_all_serialized_curve_keys_not_only_selected_rate_row(tmp_path):
    scene, edits, problem, ledger, row, cap, value, path = fixture(tmp_path)
    other = value.copy()
    other[-1] += .001
    with pytest.raises(ValueError, match='keys do not match'):
        trace(edits, other, row, path, source_cap=cap, source_tolerance=1e-5)


@pytest.mark.parametrize('fault', ['changed-input', 'changed-candidate', 'static-candidate', 'outside-box', 'non-rate-row'])
def test_rebound_inputs_payloads_controls_or_wrong_row_cannot_produce_a_trace(tmp_path, monkeypatch, fault):
    scene, edits, problem, ledger, row, cap, value, path = fixture(tmp_path)
    if fault == 'changed-input':
        source = Path(next(iter(scene.inputs)))
        source.write_bytes(source.read_bytes() + b'bad')
    if fault == 'changed-candidate':
        original = edits.worlds
        def change(*args, **kwargs):
            result = original(*args, **kwargs)
            path.write_bytes(path.read_bytes() + b'changed')
            return result
        monkeypatch.setattr(edits, 'worlds', change)
    if fault == 'static-candidate':
        from rig_asset import RigAsset
        from gltf_tools import write_glb
        rig = RigAsset.load(path)
        rig.document['nodes'][0]['name'] = 'different-static-node'
        write_glb(path, rig.document, bytearray(rig.binary))
    if fault == 'outside-box': value[0] = np.nextafter(1., np.inf)
    if fault == 'non-rate-row': row = 0
    with pytest.raises(ValueError): trace(edits, value, row, path, source_cap=cap, source_tolerance=1e-5)


@pytest.mark.parametrize('cap,tolerance', [(True, 1e-5), (1, False), (-1, 0), (0, -1), (np.nan, 0), (1, np.inf), (None, 0)])
def test_invalid_original_caps_and_tolerances_reject(tmp_path, cap, tolerance):
    _, edits, _, _, row, _, value, path = fixture(tmp_path)
    with pytest.raises(ValueError): trace(edits, value, row, path, source_cap=cap, source_tolerance=tolerance)


@pytest.mark.parametrize('kind', [name for name, _, _ in RATE_METRICS])
def test_independent_vectors_match_complete_rate_conventions_on_nonzero_rotating_translating_samples(kind):
    dt = 1 / 120
    times = np.arange(12) * dt
    poses = np.repeat(np.eye(4)[None], len(times), axis=0)
    poses[:, :3, 3] = np.c_[times**2, times * .3, times**3]
    poses[:, :3, :3] = Rotation.from_rotvec(np.c_[times * .8, times**2, times * .4]).as_matrix()
    complete = rate_vectors(features(poses[:, None], [0]), dt)
    metric = next(i for i, (name, _, _) in enumerate(RATE_METRICS) if name == kind)
    order = RATE_METRICS[metric][1]
    for sample in range(len(times) - order):
        vector = rate_vector(poses[sample:sample + order + 1], times[sample:sample + order + 1], kind, interval_s=dt)
        np.testing.assert_array_equal(vector, complete[metric][sample, 0])


def test_source_dt_is_used_instead_of_local_timestamp_subtraction():
    dt = 1 / 120
    times = np.array([2.225, 2.2333333333333334, 2.2416666666666667])
    assert times[1] - times[0] != dt
    poses = np.repeat(np.eye(4)[None], 3, axis=0)
    poses[:, 0, 3] = [0, .1, .21]
    vector = rate_vector(poses, times, 'joint_linear_acceleration', interval_s=dt)
    np.testing.assert_array_equal(vector, np.diff(poses[:, :3, 3], n=2, axis=0)[0] / dt**2)


@pytest.mark.parametrize('fault', ['width', 'count', 'nan', 'times-short', 'times-descending', 'times-negative',
    'times-nan', 'nonuniform', 'projective', 'rotation-scale', 'reflection', 'pi-angle',
    'dt-zero', 'dt-bool', 'dt-inf', 'dt-other-clock', 'unknown-metric', 'overflow'])
def test_invalid_rate_support_or_ambiguous_rotations_reject(fault):
    dt = 1 / 120
    times = np.array([0, dt, 2 * dt])
    poses = np.repeat(np.eye(4)[None], 3, axis=0)
    kind = 'joint_angular_acceleration'
    if fault == 'width': poses = poses[:, :3]
    if fault == 'count': poses = poses[:2]
    if fault == 'nan': poses[0, 0, 0] = np.nan
    if fault == 'times-short': times = times[:2]
    if fault == 'times-descending': times = times[::-1]
    if fault == 'times-negative': times -= 1
    if fault == 'times-nan': times[0] = np.nan
    if fault == 'nonuniform': times[-1] += .001
    if fault == 'projective': poses[0, 3, 0] = 1
    if fault == 'rotation-scale': poses[0, 0, 0] = 2
    if fault == 'reflection': poses[0, 0, 0] = -1
    if fault == 'pi-angle': poses[1, :3, :3] = Rotation.from_rotvec([np.pi, 0, 0]).as_matrix()
    if fault == 'dt-zero': dt = 0
    if fault == 'dt-bool': dt = True
    if fault == 'dt-inf': dt = np.inf
    if fault == 'dt-other-clock': dt = 1 / 60
    if fault == 'unknown-metric': kind = 'contact_position'
    if fault == 'overflow':
        kind = 'joint_linear_acceleration'
        poses[:, 0, 3] = [1e308, -1e308, 1e308]
    with pytest.raises(ValueError): rate_vector(poses, times, kind, interval_s=dt)
