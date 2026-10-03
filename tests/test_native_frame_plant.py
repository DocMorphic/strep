"""Fixed-clock constraint identity, native decode and exterior-key proposals."""
from pathlib import Path
import sys
import copy
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_native_foot_plant import setup
from native_frame_plant import FramePlantProblem, exterior_ramp
from native_joint_plant import JointPlantProblem
from native_joint_plant_job import run
from native_support_feasibility import colored_jacobian
from native_leg_floor import export_rotations
from native_support_clock import NativeSupportSampler
from paired_temporal_neighbor import rotation_channels
from native_support_roundtrip import preview_values
from rig_asset import RigAsset
from engine_contact_sampling import frame_populations, contract_sha256
from strep import save, read, sha256
from gltf_tools import append_accessor, write_glb, global_matrices, accessor


def fixture(tmp_path):
    source, rig, reader, spec, draft, policy, rows, limits = setup(tmp_path)
    return FramePlantProblem(rig, reader, rows, limits, reader), (source, rig, reader, spec, draft, policy, rows, limits)


def test_original_rate_caps_uniform_raw_and_source_controls_are_exact(tmp_path):
    p, data = fixture(tmp_path)
    source, rig, reader, spec, draft, policy, rows, limits = data
    legacy = JointPlantProblem(rig, reader, rows, limits, reader)
    np.testing.assert_array_equal(p.raw[p.rate_ids], legacy.raw[legacy.rate_ids])
    np.testing.assert_array_equal(p.uniform, legacy.uniform)
    assert p.caps.tolerance == legacy.caps.tolerance
    for a, b in zip(p.caps.caps, legacy.caps.caps):
        np.testing.assert_array_equal(a, b)
    for field in ('initial', 'lower', 'upper'):
        np.testing.assert_array_equal(getattr(p, field), getattr(legacy, field))
    for d in p.data:
        expected = frame_populations(d['row']['stance_s'])
        assert len(d['frame_populations']) == 12
        for actual, declared in zip(d['frame_populations'], expected):
            assert actual['id'] == declared['id']
            np.testing.assert_array_equal(actual['times_s'], declared['times_s'])
            np.testing.assert_array_equal(p.times[actual['indices']], declared['times_s'])
        assert set(d['contact_clock']).issubset(p.times)
        assert set(d['clock']).issubset(p.times)


def test_contact_rows_use_each_clock_separately_and_never_union_derivatives(tmp_path):
    p, _ = fixture(tmp_path)
    x = p.initial.copy(); x[p.data[0]['ids'][2, 1]] = [.0001, -.0001, .0002]
    values, _ = p.rotations(x); world = p.world(values)
    expected = []
    for d in p.data:
        up = d['row']['up']; limit = p.limits[d['row']['id']]
        points = np.stack([pr.evaluate(world) for pr in d['patch_projections']], axis=2)
        error = points[d['stance']] - d['anchor']; error -= (error @ up)[..., None] * up
        expected.append(((np.linalg.norm(error, axis=2) - limit['anchor']) / max(limit['anchor'], .0001)).ravel())
        clocks = [(d['contact_ids'], 1 / np.diff(d['contact_clock']))]
        clocks += [(pop['indices'], pop['rate_hz']) for pop in d['frame_populations']]
        for ids, rate in clocks:
            velocity = np.diff(points[ids], axis=0)
            velocity *= rate if np.isscalar(rate) else rate[:, None, None]
            velocity -= (velocity @ up)[..., None] * up
            expected.append(((np.linalg.norm(velocity, axis=2) - limit['speed']) / max(limit['speed'], .001)).ravel())
    np.testing.assert_allclose(p.contact_constraints(world), np.concatenate(expected), atol=2e-12, rtol=0)


def test_raw_shadow_models_match_exported_scalar_pose_decoders(tmp_path):
    p, data = fixture(tmp_path); rig = data[1]
    x = p.initial.copy(); x[p.data[0]['ids'][2, 1]] = [.0001, -.0001, .0002]
    values, _ = p.rotations(x)
    raw_path = tmp_path / 'raw.glb'; export_rotations(rig.document, rig.binary, values, raw_path)
    asset = RigAsset.load(raw_path); channels = rotation_channels(asset.document, asset.binary)
    preview_path = tmp_path / 'preview.glb'
    export_rotations(rig.document, rig.binary,
        preview_values({n: channels[n][2] for n in p.nodes}, p.channels), preview_path)
    actual = []
    for path in (raw_path, preview_path):
        asset = RigAsset.load(path); reader = NativeSupportSampler(asset.document, asset.binary, 0)
        world = np.array([reader.sample(float(t)) for t in p.times])
        channels = rotation_channels(asset.document, asset.binary)
        actual.append(p.constraints({n: channels[n][2] for n in p.nodes}, world))
    np.testing.assert_allclose(p.model(x, quantized=True, native_roundtrip=True), np.concatenate(actual), atol=2e-8, rtol=0)


def test_colored_graph_covers_every_observed_frame_and_legacy_dependency(tmp_path):
    p, _ = fixture(tmp_path); x = p.initial.copy(); pattern = p.sparsity(native_roundtrip=True)
    function = lambda z: p.model(z, quantized=True, native_roundtrip=True)
    grouped = colored_jacobian(function, x, p.lower, p.upper, pattern, step=1e-5).toarray()
    full = np.column_stack([(function(x + np.eye(1, len(x), k=j).ravel() * 1e-5)
                             - function(x)) / 1e-5 for j in range(len(x))])
    np.testing.assert_allclose(grouped, full, atol=1e-7, rtol=0)


def cross_weighted_fixture(tmp_path, problem_type):
    source, rig, reader, spec, draft, policy, rows, limits = setup(tmp_path)
    doc = copy.deepcopy(rig.document); binary = bytearray(rig.binary)
    doc['nodes'].extend([dict(name='right-thigh', translation=[.2, 0, 0], children=[8]),
        dict(name='right-shin', translation=[0, -.5, .03], children=[9]),
        dict(name='right-foot', translation=[0, -.5, -.03])])
    doc['nodes'][0]['children'].append(7)
    doc['skins'][0]['joints'].extend([7, 8, 9])
    inverse = np.linalg.inv(global_matrices(doc)[doc['skins'][0]['joints']])
    doc['skins'][0]['inverseBindMatrices'] = append_accessor(doc, binary, inverse.transpose(0, 2, 1).reshape(-1, 16), 'MAT4')
    animation = doc['animations'][0]
    animation['channels'].extend(dict(sampler=0, target=dict(node=node, path='rotation')) for node in (7, 8, 9))
    left = doc['meshes'][0]['primitives'][0]
    right = copy.deepcopy(left)
    positions = accessor(doc, binary, left['attributes']['POSITION'])
    right['attributes']['POSITION'] = append_accessor(doc, binary, positions + [.4, 0, 0], 'VEC3')
    def joints(values):
        array = np.asarray(values, dtype='<u2')
        while len(binary) % 4: binary.append(0)
        view = len(doc['bufferViews']); doc['bufferViews'].append(dict(buffer=0, byteOffset=len(binary), byteLength=array.nbytes))
        binary.extend(array.tobytes()); index = len(doc['accessors'])
        doc['accessors'].append(dict(bufferView=view, componentType=5123, count=len(array), type='VEC4'))
        return index
    # A left-dominant patch can legitimately retain a right-foot influence.
    # It lies outside this fitter's fully foot-bound region contract.
    left['attributes']['JOINTS_0'] = joints(np.tile([3, 8, 0, 0], (len(positions), 1)))
    left['attributes']['WEIGHTS_0'] = append_accessor(doc, binary, np.tile([.9, .1, 0, 0], (len(positions), 1)), 'VEC4')
    right['attributes']['JOINTS_0'] = joints(np.tile([8, 0, 0, 0], (len(positions), 1)))
    right['attributes']['WEIGHTS_0'] = append_accessor(doc, binary, np.tile([1, 0, 0, 0], (len(positions), 1)), 'VEC4')
    doc['meshes'][0]['primitives'].append(right)
    write_glb(source, doc, binary)
    spec['glb_sha256'] = sha256(source)
    spec['mapping'].update(RightLeg=7, RightShin=8, RightFoot=9)
    other = copy.deepcopy(spec['supports'][0]); other.update(id='right-stance', foot='RightFoot')
    spec['supports'].append(other); save(draft, spec)
    rig = RigAsset.load(source); reader = NativeSupportSampler(rig.document, rig.binary, 0)
    from native_support_spec import validate
    _, rows = validate(spec, rig, reader, sha256(source))
    limits['right-stance'] = dict(limits['left-stance'])
    return problem_type(rig, reader, rows, limits, reader)


@pytest.mark.parametrize('problem_type', (JointPlantProblem, FramePlantProblem))
def test_cross_branch_soles_without_fully_owned_regions_remain_rejected(tmp_path, problem_type):
    with pytest.raises(ValueError, match='No fully foot-bound mesh region'):
        cross_weighted_fixture(tmp_path, problem_type)


def test_short_frame_population_is_unavailable_not_replaced_by_boundaries(tmp_path):
    p, data = fixture(tmp_path); source, rig, reader, spec, draft, policy, rows, limits = data
    rows = copy.deepcopy(rows); rows[0]['stance_s'] = [1., 1.01]
    with pytest.raises(ValueError, match='two stance frames'):
        FramePlantProblem(rig, reader, rows, limits, reader)


def test_exterior_ramps_keep_stance_key_vectors_and_exact_source_boundaries(tmp_path):
    p, _ = fixture(tmp_path); x = p.initial.copy(); d = p.data[0]
    inside = np.flatnonzero((d['clock'] >= d['row']['stance_s'][0]) & (d['clock'] <= d['row']['stance_s'][1]))
    for key in inside:
        x[d['ids'][np.flatnonzero(d['free'] == key)[0], 1]] = [.001, .002, -.001]
    z = exterior_ramp(p, x)
    vectors = np.zeros((len(d['clock']), 3, 3)); vectors[d['free']] = z[d['ids']]
    original = np.zeros_like(vectors); original[d['free']] = x[d['ids']]
    np.testing.assert_array_equal(vectors[inside], original[inside])
    np.testing.assert_array_equal(vectors[[0, -1]], 0)
    assert np.any(z != x) and np.linalg.norm(vectors[inside[-1] + 1]) > 0
    old, _ = p.rotations(x); new, _ = p.rotations(z)
    first, last = d['row']['edit_keys']
    for node in p.nodes:
        np.testing.assert_array_equal(old[node][first + inside], new[node][first + inside])
        np.testing.assert_array_equal(new[node][:first + 1], p.channels[node][2][:first + 1])
        np.testing.assert_array_equal(new[node][last:], p.channels[node][2][last:])


def test_ramp_with_no_free_exterior_keys_is_an_exact_noop(tmp_path):
    p, _ = fixture(tmp_path); d = p.data[0]
    d['row']['stance_s'] = [float(d['clock'][0]), float(d['clock'][-1])]
    x = p.initial.copy(); x[d['ids'][2, 1]] = [.001, .002, -.001]
    np.testing.assert_array_equal(exterior_ramp(p, x), x)


def test_exterior_overshoot_is_rejected_instead_of_clipped(tmp_path):
    p, _ = fixture(tmp_path); d = p.data[0]; x = p.initial.copy()
    inside = np.flatnonzero((d['clock'] >= d['row']['stance_s'][0]) & (d['clock'] <= d['row']['stance_s'][1]))
    for key, amount in zip(inside[:2], (.7, -.7)):
        x[d['ids'][np.flatnonzero(d['free'] == key)[0], 1, 0]] = amount
    p.rotations(x)
    with pytest.raises(ValueError, match='component boxes'):
        exterior_ramp(p, x)


@pytest.mark.parametrize('options', [dict(frame_sampling=1), dict(exterior_seed_ramp=1)])
def test_modes_require_explicit_booleans_before_inputs(options):
    with pytest.raises(ValueError, match='frame/ramp'):
        run(None, None, None, None, None, **options)


@pytest.mark.parametrize('options', [dict(frame_sampling=True), dict(exterior_seed_ramp=True),
                                    dict(frame_sampling=True, exterior_seed_ramp=True)])
def test_real_job_flags_archive_models_and_retain_failed_proposal(tmp_path, options):
    source, rig, reader, spec, draft, policy, rows, limits = setup(tmp_path)
    policy_path = tmp_path / 'policy.json'; save(policy_path, policy)
    result = run(source, source, draft, policy_path, tmp_path / 'fit', iterations=1, **options)
    assert result['retained_input'] and result['candidate_sha256'] == sha256(source)
    assert not result['quality_approved'] and not result['release_approved']
    assert (tmp_path / 'fit/implementation/native_frame_plant.py').is_file()
    assert (tmp_path / 'fit/implementation/engine_contact_sampling.py').is_file()
    request = read(tmp_path / 'fit/request.json')
    if options.get('frame_sampling'):
        assert request['frame_sampling_contract_sha256'] == contract_sha256()
        assert request['proposal_skin'] == 'Native, not imported engine skin'
        assert (tmp_path / 'fit/implementation/engine_contact_sampling.py').is_file()
    if options.get('exterior_seed_ramp'):
        assert request['exterior_seed_ramp'].startswith('Cubic Hermite')


def test_passing_source_keeps_input_and_no_quality_approval_with_both_modes(tmp_path):
    source, rig, reader, spec, draft, policy, rows, limits = setup(tmp_path, moving=False)
    policy_path = tmp_path / 'policy.json'; save(policy_path, policy)
    result = run(source, source, draft, policy_path, tmp_path / 'fit', iterations=1,
                 frame_sampling=True, exterior_seed_ramp=True)
    assert result['retained_input'] and result['selected']['passed']
    assert result['optimization']['iterations'] == 0
    assert result['candidate_sha256'] == sha256(source) and not result['quality_approved']
