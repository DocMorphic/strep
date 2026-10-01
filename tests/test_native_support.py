"""Source-bound arbitrary-name fixtures; no human-motion quality evidence."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from gltf_tools import append_accessor, write_glb, global_matrices
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler as AnimationSampler
from native_support_spec import validate
from native_support_path import propose, bend_box
from native_leg_smoothing import smooth
from strep import sha256, save


def fixture(tmp_path, plane=.2):
    doc = dict(asset=dict(version='2.0'), buffers=[{}], bufferViews=[], accessors=[],
        nodes=[dict(name='pelvis-custom', translation=[0, 1.2, 0], children=[1, 5]),
               dict(name='femur-X', translation=[-.2, 0, 0], children=[2]),
               dict(name='tibia-Y', translation=[0, -.5, .03], children=[3]),
               dict(name='ankle-Z', translation=[0, -.5, -.03], children=[4]),
               dict(name='toe-extra', translation=[0, 0, .1]),
               dict(name='unchanged-hand', translation=[.5, .1, 0]), dict(mesh=0, skin=0)],
        skins=[dict(joints=list(range(6)), skeleton=0)], animations=[dict(channels=[], samplers=[])],
        meshes=[dict(primitives=[])], scenes=[dict(nodes=[0, 6])], scene=0)
    data = bytearray(); clock = np.linspace(0, 2, 11).astype(np.float32)
    def unsigned(value, kind):
        array = np.asarray(value, dtype='<u2')
        while len(data)%4: data.append(0)
        view = len(doc['bufferViews']); doc['bufferViews'].append(dict(buffer=0, byteOffset=len(data), byteLength=array.nbytes))
        data.extend(array.tobytes()); acc = len(doc['accessors'])
        doc['accessors'].append(dict(bufferView=view, componentType=5123, count=len(array), type=kind))
        return acc
    time = append_accessor(doc, data, clock, 'SCALAR')
    values = append_accessor(doc, data, np.tile([0., 0., 0., 1.], (11, 1)), 'VEC4')
    doc['animations'][0]['samplers'] = [dict(input=time, output=values, interpolation='LINEAR')]
    doc['animations'][0]['channels'] = [dict(sampler=0, target=dict(node=n, path='rotation')) for n in (1, 2, 3)]
    root_positions = np.tile([0., 1.2, 0.], (11, 1))
    root_positions[:, 1] += .06*np.maximum(0, np.abs(clock-1)-.3)
    pos = append_accessor(doc, data, root_positions, 'VEC3')
    doc['animations'][0]['samplers'].append(dict(input=time, output=pos, interpolation='LINEAR'))
    doc['animations'][0]['channels'].append(dict(sampler=1, target=dict(node=0, path='translation')))
    world = global_matrices(doc); inverse = np.linalg.inv(world[:6])
    doc['skins'][0]['inverseBindMatrices'] = append_accessor(doc, data, inverse.transpose(0, 2, 1).reshape(-1, 16), 'MAT4')
    positions = append_accessor(doc, data, [[-.22, .19, -.02], [-.18, .19, -.02], [-.2, .19, .1]], 'VEC3')
    joints = unsigned(np.tile([3, 0, 0, 0], (3, 1)), 'VEC4')
    weights = append_accessor(doc, data, np.tile([1., 0., 0., 0.], (3, 1)), 'VEC4')
    indices = unsigned([0, 1, 2], 'SCALAR')
    doc['meshes'][0]['primitives'] = [dict(attributes=dict(POSITION=positions, JOINTS_0=joints, WEIGHTS_0=weights), indices=indices)]
    source = tmp_path/'source.glb'; write_glb(source, doc, data)
    rig = RigAsset.load(source); reader = AnimationSampler(rig.document, rig.binary, 0)
    spec = dict(schema='strep-native-support-v1', glb_sha256=sha256(source), animation_index=0,
                duration_s=2., root_node=0, mapping=dict(LeftLeg='femur-X', LeftShin='tibia-Y', LeftFoot='ankle-Z'),
                supports=[dict(id='left-stance', foot='LeftFoot', stance_s=[.8, 1.2], edit_keys=[1, 9],
                    plane=dict(normal_xyz=[0., 1., 0.], offset_m=plane), clearance_m=.00025,
                    maximum_gap_m=.005, maximum_displacement_m=.03, maximum_angle_degrees=45.)])
    return source, rig, reader, spec


def test_arbitrary_names_preserve_native_clocks_free_phase_and_unedited_branch(tmp_path):
    source, rig, reader, spec = fixture(tmp_path)
    mapping, rows = validate(spec, rig, reader, sha256(source))
    assert mapping == dict(LeftLeg=1, LeftShin=2, LeftFoot=3)
    out = tmp_path/'proposal.glb'; reports = propose(rig, reader, rows, out)
    assert reports[0]['edits']
    changed = RigAsset.load(out); sampler = AnimationSampler(changed.document, changed.binary, 0)
    for a, b in zip(reader.channels, sampler.channels): np.testing.assert_array_equal(a[2], b[2])
    for t in (0., .15, .2, 1.8, 1.9, 2.): np.testing.assert_array_equal(reader.sample(t), sampler.sample(t))
    for t in (.35, .853725, 1., 1.45):
        a, b = reader.sample(t), sampler.sample(t)
        np.testing.assert_array_equal(a[[0, 5, 6]], b[[0, 5, 6]])
    assert not np.array_equal(reader.sample(1), sampler.sample(1))


def test_signed_lowering_and_fixed_endpoints_without_relaxing_reach(tmp_path):
    source, rig, reader, spec = fixture(tmp_path, plane=.185)
    _, rows = validate(spec, rig, reader, sha256(source)); r = rows[0]
    times = r['clock'][1:10]; worlds = np.array([reader.sample(float(t)) for t in times])
    heights = np.full(len(times), .0055)
    box = bend_box(worlds, rig.parents, r['chain'], heights, times, r)
    assert np.all(box['upper_lift'][(times >= .8)&(times <= 1.2)] < 0)
    assert box['lower_lift'][0] == box['upper_lift'][0] == 0
    assert box['lower_lift'][-1] == box['upper_lift'][-1] == 0


@pytest.mark.parametrize('fault', ['hash', 'duration', 'root', 'name', 'duplicate', 'helper', 'clock', 'window', 'overlap', 'normal', 'offset', 'gap', 'angle', 'displacement', 'unknown', 'boolean'])
def test_bad_or_misbound_native_drafts_are_rejected(tmp_path, fault):
    source, rig, reader, spec = fixture(tmp_path); r = spec['supports'][0]
    if fault == 'hash': spec['glb_sha256'] = '0'*64
    if fault == 'duration': spec['duration_s'] = 1
    if fault == 'root': spec['root_node'] = 1
    if fault == 'name': spec['mapping']['LeftFoot'] = 'missing'
    if fault == 'duplicate': spec['mapping']['LeftFoot'] = 'tibia-Y'
    if fault == 'helper': rig.parents[3] = 1
    if fault == 'clock': rig.document['animations'][0]['samplers'][0]['interpolation'] = 'STEP'
    if fault == 'window': r['edit_keys'] = [3, 5]
    if fault == 'overlap': spec['supports'].append({**copy.deepcopy(r), 'id': 'overlap'})
    if fault == 'normal': r['plane']['normal_xyz'] = [0, 2, 0]
    if fault == 'offset': r['plane']['offset_m'] = float('nan')
    if fault == 'gap': r['maximum_gap_m'] = .02
    if fault == 'angle': r['maximum_angle_degrees'] = 46
    if fault == 'displacement': r['maximum_displacement_m'] = .04
    if fault == 'unknown': r['silent_flag'] = True
    if fault == 'boolean': spec['animation_index'] = False
    with pytest.raises(ValueError): validate(spec, rig, reader, sha256(source))


def test_reference_smoothing_supports_fixed_source_boundaries():
    t = [0., .1, .3, .7, 1.]; lo = np.array([.3, .2, .2, .2, .3]); hi = np.array([.3, .5, .5, .5, .3])
    reference = np.array([.3, .4, .25, .4, .3]); x, _ = smooth(t, lo, hi, reference=reference)
    assert x[0] == x[-1] == .3
    with pytest.raises(ValueError): smooth(t, lo, hi, reference=reference+1)


def test_job_preserves_input_and_failed_proposals_when_rate_caps_fail(tmp_path, monkeypatch):
    import native_support_job as job
    source, rig, reader, spec = fixture(tmp_path)
    monkeypatch.setattr(job, 'ROOT', tmp_path); (tmp_path/'reports').mkdir()
    spec_path = tmp_path/'draft.json'; save(spec_path, spec)
    result = job.run(source, spec_path, tmp_path/'reports/rejected')
    assert result['retained_input'] and result['selected_trial'] is None
    assert result['candidate_sha256'] == sha256(source)
    assert any(r.get('source_rate_failed_rows') for r in result['trials'])
    assert any((tmp_path/f'reports/rejected/trial-{i}.glb').exists() for i in range(4))
    assert not result['quality_approved'] and not result['engine_import_verified']


def test_already_satisfied_job_is_not_claimed_as_motion_improvement(tmp_path, monkeypatch):
    import native_support_job as job
    source, rig, reader, spec = fixture(tmp_path, plane=.188)
    # Exact constant source geometry throughout the authored edit window.
    spec['supports'][0]['edit_keys'] = [3, 7]
    monkeypatch.setattr(job, 'ROOT', tmp_path); (tmp_path/'reports').mkdir()
    spec_path = tmp_path/'draft.json'; save(spec_path, spec)
    result = job.run(source, spec_path, tmp_path/'reports/satisfied')
    assert result['selected_trial'] is None and result['retained_input'] and result['input_already_satisfied']
    assert result['output_support_samples_pass'] and result['candidate_sha256'] == sha256(source)
    exported = RigAsset.load(tmp_path/'reports/satisfied/candidate.glb')
    current = AnimationSampler(exported.document, exported.binary, 0)
    for t in (0., .617, .853725, 1., 1.38, 2.):
        np.testing.assert_array_equal(current.sample(t), reader.sample(t))
    assert not result['quality_approved']


@pytest.mark.parametrize('mode', ['LINEAR', 'STEP', 'CUBICSPLINE'])
def test_exact_native_rotation_keys_do_not_depend_on_edited_next_key(mode):
    from scipy.spatial.transform import Rotation
    times = np.array([0., .48814305663108826, 1.], np.float32)
    keys = Rotation.from_rotvec([[.24, -.08, .31], [.05, .36, -.73], [-.41, .32, .61]]).as_quat()
    changed = keys.copy(); changed[2] = Rotation.from_rotvec([.06, .57, -.25]).as_quat()
    if mode == 'CUBICSPLINE':
        original_values = np.zeros((9, 4)); changed_values = original_values.copy()
        original_values[1::3] = keys; changed_values[1::3] = changed
    else: original_values, changed_values = keys, changed
    t = float(times[1]); original = AnimationSampler.value('rotation', times, original_values, mode, t)
    edited = AnimationSampler.value('rotation', times, changed_values, mode, t)
    np.testing.assert_array_equal(edited, original)
    np.testing.assert_array_equal(original, keys[1]/np.linalg.norm(keys[1]))
    if mode != 'STEP':
        # Nearby fractional contact times remain interpolated; no tolerance snap.
        near = t+1.0667498e-7
        assert not np.array_equal(AnimationSampler.value('rotation', times, changed_values, mode, near), edited)


def test_disjoint_same_foot_windows_preserve_the_gap_and_keep_all_trials(tmp_path, monkeypatch):
    import native_support_job as job
    source, rig, reader, spec = fixture(tmp_path, plane=.215)
    clock = reader.channels[0][2]
    first = spec['supports'][0]; first['edit_keys'] = [0, 4]
    first['stance_s'] = [float(clock[1]), float(clock[2])]
    second = copy.deepcopy(first); second.update(id='second-stance', edit_keys=[6, 10], stance_s=[float(clock[8]), float(clock[9])])
    spec['supports'].append(second)
    monkeypatch.setattr(job, 'ROOT', tmp_path); (tmp_path/'reports').mkdir()
    spec_path = tmp_path/'draft.json'; save(spec_path, spec)
    result = job.run(source, spec_path, tmp_path/'reports/disjoint')
    completed = [r for r in result['trials'] if r['status'] == 'complete']
    assert completed
    for trial in completed:
        for support in trial['supports']: assert support['outside_edit_world_exact']
        rig_after = RigAsset.load(tmp_path/f"reports/disjoint/trial-{trial['trial']}.glb")
        sampler = AnimationSampler(rig_after.document, rig_after.binary, 0)
        for t in (float(clock[4]), .917234, 1., float(clock[6])):
            np.testing.assert_array_equal(sampler.sample(t), reader.sample(t))


def test_fractional_stance_boundaries_use_both_interpolation_keys(tmp_path):
    from paired_approach_basis import BoundSkin
    from native_leg_floor import foot_region
    from contact_rate_path import ProjectedSkin
    source, rig, reader, spec = fixture(tmp_path)
    spec['supports'][0]['stance_s'] = [.61, 1.39]
    _, rows = validate(spec, rig, reader, sha256(source)); path = tmp_path/'fractional.glb'
    propose(rig, reader, rows, path)
    exported = RigAsset.load(path); current = AnimationSampler(exported.document, exported.binary, 0)
    times = np.r_[.61, np.arange(74, 167)/120, 1.39]
    skin = BoundSkin(exported); vertices = foot_region(skin, exported.parents, 3)
    height = ProjectedSkin(skin, vertices, rows[0]['up'], rows[0]['offset']).evaluate(np.array([current.sample(t) for t in times])).min(axis=1)
    assert height.min() >= 0 and height.max() <= .005


def test_metadata_describes_real_names_and_shared_clock_without_inference(tmp_path):
    from native_support_job import describe
    source, rig, reader, spec = fixture(tmp_path); path = tmp_path/'metadata.json'
    record = describe(source, path)
    assert record['glb_sha256'] == sha256(source) and len(record['clocks']) == 1
    assert {j['name'] for j in record['joints']} == {'pelvis-custom', 'femur-X', 'tibia-Y', 'ankle-Z', 'toe-extra', 'unchanged-hand'}
    assert 'mapping' not in record and record['clocks'][0]['times_s'][4] == float(reader.channels[0][2][4])
    with pytest.raises(ValueError): describe(source, path)


def test_native_input_mutation_is_detected_before_publication(tmp_path, monkeypatch):
    import native_support_job as job
    source, rig, reader, spec = fixture(tmp_path); spec_path = tmp_path/'draft.json'; save(spec_path, spec)
    monkeypatch.setattr(job, 'ROOT', tmp_path); (tmp_path/'reports').mkdir()
    original = source.read_bytes(); load = RigAsset.load
    def mutating_load(path):
        loaded = load(path); Path(path).write_bytes(original+b'changed'); return loaded
    monkeypatch.setattr(RigAsset, 'load', mutating_load)
    with pytest.raises(ValueError, match='changed'): job.describe(source, tmp_path/'metadata.json')
    assert not (tmp_path/'metadata.json').exists()
    source.write_bytes(original)
    with pytest.raises(ValueError, match='changed'): job.run(source, spec_path, tmp_path/'reports/new')
    assert not (tmp_path/'reports/new').exists()


@pytest.mark.parametrize('normal,offset', [([0., 1., 0.], .185), ([0., .8, .6], .135)])
def test_signed_pose_correction_keeps_plane_tangent_and_foot_orientation(tmp_path, normal, offset):
    source, rig, reader, spec = fixture(tmp_path, plane=offset)
    spec['supports'][0]['plane']['normal_xyz'] = normal
    spec['supports'][0]['stance_s'] = [float(reader.channels[0][2][4]), float(reader.channels[0][2][6])]
    _, rows = validate(spec, rig, reader, sha256(source)); path = tmp_path/'signed.glb'
    reports = propose(rig, reader, rows, path)
    assert any(e['displacement_m'] < -1e-5 for e in reports[0]['edits'])
    exported = RigAsset.load(path); current = AnimationSampler(exported.document, exported.binary, 0)
    a, b = reader.sample(1.), current.sample(1.)
    up = np.asarray(normal); delta = b[3, :3, 3]-a[3, :3, 3]
    np.testing.assert_allclose(delta-(delta@up)*up, 0, atol=1e-7, rtol=0)
    np.testing.assert_allclose(b[3, :3, :3], a[3, :3, :3], atol=1e-7, rtol=0)
