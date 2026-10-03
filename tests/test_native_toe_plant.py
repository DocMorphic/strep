"""Extra permissions, unchanged original constraints and actual decoded proposals."""
from pathlib import Path
import sys
import copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_native_support_articulation import toe_fixture
from native_support_permissions import validate_permissions, preserve, audit
from native_toe_plant import ToePlantProblem
from native_toe_plant_job import run
from native_frame_plant import FramePlantProblem
from native_support_spec import validate
from native_support_clock import NativeSupportSampler
from native_support_feasibility import colored_jacobian
from native_foot_plant import preserve as leg_only_preserve
from native_foot_plant import policy_rows
from native_leg_floor import export_rotations
from native_support_roundtrip import preview_values
from paired_temporal_neighbor import rotation_channels
from rig_asset import RigAsset
from gltf_tools import write_glb, append_accessor
from strep import save, read, sha256


def setup(tmp_path, *, animated=True):
    source, rig, reader, spec, rows = toe_fixture(tmp_path, animated=animated)
    spec['supports'][0]['plane']['offset_m'] = .188
    draft = tmp_path / 'draft.json'; save(draft, spec)
    permissions = dict(schema='strep-native-support-rotation-permissions-v1', source_sha256=sha256(source),
        draft_sha256=sha256(draft), supports=[dict(id='left-stance', rotations=[dict(node=4, maximum_angle_degrees=2.)])])
    path = tmp_path / 'permissions.json'; save(path, permissions)
    policy = dict(schema='strep-native-foot-plant-v1', source_sha256=sha256(source), base_sha256=sha256(source),
        draft_sha256=sha256(draft), supports=[dict(id='left-stance', maximum_patch_anchor_error_m=.001, maximum_patch_speed_m_s=.005)])
    policy_path = tmp_path / 'policy.json'; save(policy_path, policy)
    limits = policy_rows(policy, source, source, draft, rows)
    return source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits


def problem(tmp_path):
    data = setup(tmp_path); source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = data
    additions = validate_permissions(permissions, rig, rows, sha256(source), sha256(draft))
    return ToePlantProblem(rig, reader, rows, limits, reader, additions), data


@pytest.mark.parametrize('fault', ['source', 'draft', 'schema', 'unknown', 'duplicate-support', 'missing-id', 'empty',
    'duplicate-node', 'leg-node', 'root', 'unrelated', 'boolean', 'angle-boolean', 'angle-nan', 'angle-large', 'clock', 'static'])
def test_permission_contract_rejects_wrong_bindings_nodes_clocks_and_bounds(tmp_path, fault):
    data = setup(tmp_path, animated=fault != 'static')
    source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = data
    item = permissions['supports'][0]; declaration = item['rotations'][0]
    if fault == 'source': permissions['source_sha256'] = '0' * 64
    if fault == 'draft': permissions['draft_sha256'] = '0' * 64
    if fault == 'schema': permissions['schema'] = 'old-leg-only'
    if fault == 'unknown': declaration['editable_root'] = True
    if fault == 'duplicate-support': permissions['supports'].append(copy.deepcopy(item))
    if fault == 'missing-id': item['id'] = 'missing'
    if fault == 'empty': item['rotations'] = []
    if fault == 'duplicate-node': item['rotations'].append(copy.deepcopy(declaration))
    if fault == 'leg-node': declaration['node'] = 3
    if fault == 'root': declaration['node'] = 0
    if fault == 'unrelated': declaration['node'] = 5
    if fault == 'boolean': declaration['node'] = True
    if fault == 'angle-boolean': declaration['maximum_angle_degrees'] = True
    if fault == 'angle-nan': declaration['maximum_angle_degrees'] = float('nan')
    if fault == 'angle-large': declaration['maximum_angle_degrees'] = 45.1
    if fault == 'clock':
        doc = copy.deepcopy(rig.document); data = bytearray(rig.binary)
        sampler = doc['animations'][0]['samplers'][-1]
        sampler['input'] = append_accessor(doc, data, np.linspace(0, 2, 11) + .001, 'SCALAR')
        write_glb(source, doc, data); rig = RigAsset.load(source); permissions['source_sha256'] = sha256(source)
    with pytest.raises(ValueError): validate_permissions(permissions, rig, rows, sha256(source), sha256(draft))


def test_zero_extra_controls_keep_original_leg_values_caps_and_frame_clocks_exact(tmp_path):
    p, data = problem(tmp_path); source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = data
    original = FramePlantProblem(rig, reader, rows, limits, reader)
    np.testing.assert_array_equal(p.initial[:p.leg_size], original.initial)
    np.testing.assert_array_equal(p.lower[:p.leg_size], original.lower)
    np.testing.assert_array_equal(p.upper[:p.leg_size], original.upper)
    np.testing.assert_array_equal(p.uniform, original.uniform)
    np.testing.assert_array_equal(p.raw[p.rate_ids], original.raw[original.rate_ids])
    for a, b in zip(p.caps.caps, original.caps.caps): np.testing.assert_array_equal(a, b)
    assert p.caps.tolerance == original.caps.tolerance
    x = p.initial.copy(); x[p.data[0]['ids'][2]] = .0001
    extra, _ = p.rotations(x); legacy, _ = original.rotations(x[:p.leg_size])
    for node in original.nodes: np.testing.assert_array_equal(extra[node], legacy[node])
    np.testing.assert_array_equal(extra[4], p.channels[4][2])
    world = p.world(extra); np.testing.assert_allclose(world, original.world(legacy), atol=2e-12, rtol=0)
    base_core = original.core_constraints(legacy, world)
    np.testing.assert_allclose(p.core_constraints(extra, world)[:len(base_core)], base_core, atol=2e-8, rtol=0)
    np.testing.assert_array_equal(p.contact_constraints(world), original.contact_constraints(world))
    assert len(p.data[0]['frame_populations']) == 12
    for a, b in zip(p.data[0]['frame_populations'], original.data[0]['frame_populations']):
        np.testing.assert_array_equal(a['times_s'], b['times_s'])


def test_raw_and_shadow_proposals_match_independent_scalar_decoders(tmp_path):
    p, data = problem(tmp_path); source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = data
    x = p.initial.copy(); x[p.extras[0]['ids'][2]] = [.0002, -.0003, .0001]
    values, _ = p.rotations(x); raw = tmp_path / 'raw.glb'; export_rotations(rig.document, rig.binary, values, raw)
    actual = RigAsset.load(raw); channels = rotation_channels(actual.document, actual.binary)
    shadow = tmp_path / 'shadow.glb'
    export_rotations(rig.document, rig.binary, preview_values({n: channels[n][2] for n in p.nodes}, p.channels), shadow)
    parts = []
    for file in (raw, shadow):
        asset = RigAsset.load(file); sampler = NativeSupportSampler(asset.document, asset.binary, 0)
        q = rotation_channels(asset.document, asset.binary)
        world = np.array([sampler.sample(float(t)) for t in p.times])
        parts.append(p.constraints({n: q[n][2] for n in p.nodes}, world))
    np.testing.assert_allclose(p.model(x, quantized=True, native_roundtrip=True), np.r_[tuple(parts)], atol=2e-8, rtol=0)
    assert p.sparsity(native_roundtrip=True).shape == (sum(len(g) for g in parts), len(x))


def test_colored_graph_covers_all_extra_joint_contact_and_original_rate_dependencies(tmp_path):
    p, _ = problem(tmp_path); x = p.initial.copy(); pattern = p.sparsity(native_roundtrip=True)
    function = lambda z: p.model(z, quantized=True, native_roundtrip=True)
    grouped = colored_jacobian(function, x, p.lower, p.upper, pattern, step=1e-5).toarray()
    baseline = function(x)
    full = np.column_stack([(function(x + np.eye(1, len(x), k=j).ravel() * 1e-5) - baseline) / 1e-5 for j in range(len(x))])
    np.testing.assert_allclose(grouped, full, atol=1e-7, rtol=0)


def test_added_rotation_is_a_new_contract_and_frozen_keys_remain_exact(tmp_path):
    p, data = problem(tmp_path); source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = data
    x = p.initial.copy(); x[p.extras[0]['ids'][2]] = [.0002, -.0003, .0001]
    values, _ = p.rotations(x); candidate = tmp_path / 'extra.glb'
    export_rotations(rig.document, rig.binary, values, candidate)
    asset = RigAsset.load(candidate); changed = NativeSupportSampler(asset.document, asset.binary, 0)
    additions = validate_permissions(permissions, rig, rows, sha256(source), sha256(draft))
    preserve(reader, changed, rows, additions)
    with pytest.raises(ValueError, match='Unedited'): leg_only_preserve(reader, changed, rows)
    result = audit(source, candidate, draft, path, limits)
    assert result['additional_rotation_bounds_pass'] and result['uses_extended_rotation_permissions']
    assert not result['original_leg_only_preservation_verified']
    for old, new in zip(reader.channels, changed.channels):
        if old[0] != 4 or old[1] != 'rotation': np.testing.assert_array_equal(old[3], new[3])
        else: np.testing.assert_array_equal(old[3][[0, 1, 9, 10]], new[3][[0, 1, 9, 10]])
    values[4][1] = Rotation.from_rotvec([.001, 0, 0]).as_quat()
    export_rotations(rig.document, rig.binary, values, candidate)
    changed = NativeSupportSampler(RigAsset.load(candidate).document, RigAsset.load(candidate).binary, 0)
    with pytest.raises(ValueError, match='Frozen'): preserve(reader, changed, rows, additions)


def test_component_box_corners_cannot_bypass_cumulative_radial_angle_bound(tmp_path):
    p, data = problem(tmp_path); source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = data
    x = p.initial.copy(); x[p.extras[0]['ids'][2]] = p.upper[p.extras[0]['ids'][2]]
    values, _ = p.rotations(x); core = p.core_constraints(values, p.world(values))
    assert core[-len(p.extras[0]['clock']):].max() > .7
    candidate = tmp_path / 'angle.glb'; export_rotations(rig.document, rig.binary, values, candidate)
    result = audit(source, candidate, draft, path, limits)
    assert not result['additional_rotation_bounds_pass'] and not result['passed']
    assert result['additional_rotation_screens'][0]['maximum_local_angle_degrees'] > 3.4


@pytest.mark.parametrize('options', [dict(iterations=0), dict(iterations=True), dict(trust=0), dict(trust=float('nan')), dict(engine_check=1)])
def test_bad_search_modes_reject_before_paths(options):
    with pytest.raises(ValueError): run(None, None, None, None, None, None, **options)


def test_actual_diagnostic_job_archives_new_contract_and_keeps_failed_input(tmp_path):
    source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = setup(tmp_path)
    output = tmp_path / 'job'; result = run(source, source, draft, policy_path, path, output, iterations=1, engine_check=False)
    assert result['retained_input'] and result['candidate_sha256'] == sha256(source)
    assert result['uses_extended_rotation_permissions'] and not result['actual_engine_contacts_pass']
    assert not result['native_npz_conversion_verified'] and not result['quality_approved']
    assert read(output / 'request.json')['permissions'] == permissions
    for name in ('native_support_permissions.py', 'native_toe_plant.py', 'native_toe_plant_job.py', 'engine_contact_sampling.py'):
        assert (output / 'implementation' / name).is_file()
    assert read(output / 'pipeline.json')['status'] == 'complete'
    assert len(read(output / 'controls.json')['additional_rotations']) == 1
    for probe in result['probes']:
        assert sha256(output / probe['file']) == probe['sha256']
        assert sha256(output / probe['preview_file']) == probe['preview_sha256']


def test_native_diagnostic_keeps_already_passing_input_and_never_infers_engine_approval(tmp_path):
    data = setup(tmp_path)
    source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = data
    doc = copy.deepcopy(rig.document); binary = bytearray(rig.binary)
    sampler = doc['animations'][0]['samplers'][-1]
    sampler['output'] = append_accessor(doc, binary, np.tile([0., 0., 0., 1.], (11, 1)), 'VEC4')
    write_glb(source, doc, binary); spec['glb_sha256'] = sha256(source); save(draft, spec)
    permissions.update(source_sha256=sha256(source), draft_sha256=sha256(draft)); save(path, permissions)
    policy.update(source_sha256=sha256(source), base_sha256=sha256(source), draft_sha256=sha256(draft)); save(policy_path, policy)
    result = run(source, source, draft, policy_path, path, tmp_path / 'static', iterations=1, engine_check=False)
    assert result['native_model_and_audits_pass'] and result['baseline']['passed']
    assert result['optimization']['iterations'] == 0
    assert result['retained_input'] and not result['actual_engine_contacts_pass']
    assert result['retention_reason'] == 'native_diagnostic_only'


def test_proposal_target_cannot_weaken_public_contact_limits(tmp_path):
    source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = setup(tmp_path)
    loose = copy.deepcopy(policy); loose['supports'][0]['maximum_patch_speed_m_s'] = .006
    search = tmp_path / 'loose.json'; save(search, loose)
    output = tmp_path / 'loose-job'
    with pytest.raises(ValueError, match='looser'): run(source, source, draft, policy_path, path, output, search_policy=search, engine_check=False)
    assert not output.exists()


@pytest.mark.parametrize('node', [0, 5])
def test_root_translation_and_unrelated_rotation_remain_protected(tmp_path, node):
    p, data = problem(tmp_path); source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = data
    changed = copy.deepcopy(reader)
    for index, channel in enumerate(changed.channels):
        if channel[0] == node:
            values = channel[3].copy(); values[5, 0] += .001
            changed.channels[index] = (*channel[:3], values, channel[4]); break
    else:
        # The unrelated hand has no source rotation channel; adding one also fails.
        changed.channels.append((node, 'rotation', rows[0]['clock'], np.tile([0., 0., 0., 1.], (11, 1)), 'LINEAR'))
    additions = validate_permissions(permissions, rig, rows, sha256(source), sha256(draft))
    with pytest.raises(ValueError): preserve(reader, changed, rows, additions)


def test_failed_engine_import_keeps_exact_input_and_terminal_failure(tmp_path, monkeypatch):
    source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = setup(tmp_path)
    import native_engine_contacts
    def failure(*args, **kwargs): raise RuntimeError('injected engine import failure')
    monkeypatch.setattr(native_engine_contacts, 'run', failure)
    output = tmp_path / 'engine-failure'
    with pytest.raises(RuntimeError, match='engine import failure'):
        run(source, source, draft, policy_path, path, output, iterations=1)
    assert read(output / 'pipeline.json')['status'] == 'failed'
    assert sha256(output / 'candidate.glb') == sha256(source)
    assert not (output / 'result.json').exists()


def test_mutated_permission_bounds_cannot_be_used_for_final_selection(tmp_path, monkeypatch):
    source, rig, reader, spec, rows, draft, permissions, path, policy, policy_path, limits = setup(tmp_path)
    import native_toe_plant_job as module
    original = module.restore
    def changed(*args, **kwargs):
        fitted = original(*args, **kwargs)
        permissions['supports'][0]['rotations'][0]['maximum_angle_degrees'] = 3.
        save(path, permissions)
        return fitted
    monkeypatch.setattr(module, 'restore', changed)
    output = tmp_path / 'changed-permissions'
    with pytest.raises(ValueError, match='inputs or methods changed'):
        run(source, source, draft, policy_path, path, output, iterations=1, engine_check=False)
    assert read(output / 'pipeline.json')['status'] == 'failed'
    assert sha256(output / 'candidate.glb') == sha256(output / 'input.glb') == sha256(source)
    assert not (output / 'result.json').exists()
