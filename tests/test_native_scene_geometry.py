"""Full topology, moving scene/partner/plane and source-bound audit checks."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_contacts import setup
from native_scene_contacts import SceneContacts
import native_scene_geometry as geometry
from gltf_tools import append_accessor, write_glb
from rig_asset import RigAsset
from strep import read, save, sha256


def policy(spec_path, *, mode='explicit', planes=None):
    return dict(schema='strep-native-scene-geometry-v1', contacts_sha256=sha256(spec_path),
        clock=dict(mode=mode, times_s=[0., 1., 2.]),
        limits=dict(penetration_m=.005, depth_resolution_m=1e-6, surface_tolerance_m=1e-8),
        planes={} if planes is None else planes)


def closed_fixture(tmp_path):
    source, rig, reader, spec = setup(tmp_path)
    doc = copy.deepcopy(rig.document); data = bytearray(rig.binary)
    cube = trimesh.creation.box(extents=[.4, .4, .4]); vertices = cube.vertices + [0., .2, 0.]
    def unsigned(values, kind):
        values = np.asarray(values, dtype='<u2')
        while len(data) % 4: data.append(0)
        doc['bufferViews'].append(dict(buffer=0, byteOffset=len(data), byteLength=values.nbytes)); data.extend(values.tobytes())
        doc['accessors'].append(dict(bufferView=len(doc['bufferViews'])-1, componentType=5123, count=len(values), type=kind))
        return len(doc['accessors'])-1
    primitive = dict(attributes=dict(POSITION=append_accessor(doc, data, vertices, 'VEC3'),
        JOINTS_0=unsigned(np.tile([3, 0, 0, 0], (len(vertices), 1)), 'VEC4'),
        WEIGHTS_0=append_accessor(doc, data, np.tile([1., 0, 0, 0], (len(vertices), 1)), 'VEC4')),
        indices=unsigned(cube.faces.reshape(-1), 'SCALAR'))
    doc['meshes'][0]['primitives'] = [primitive]; write_glb(source, doc, data)
    spec['actors']['A']['sha256'] = sha256(source)
    path = tmp_path/'contacts.json'; save(path, spec)
    return source, path, spec


def evaluate(path, spec, value):
    return geometry.evaluate(SceneContacts(spec, path.parent), value, sha256(path))


def test_surface_interior_is_checked_even_when_vertices_miss_object(tmp_path):
    source, rig, reader, spec = setup(tmp_path)
    center = rig.vertices(reader.sample(1)).mean(axis=0)
    spec['objects']['ball'] = dict(geometry=dict(schema='strep-object-geometry-v1', shape='sphere', radius_m=.005),
        keyframes=[dict(time_s=0., translation_m=center.tolist(), rotation_xyzw=[0, 0, 0, 1])])
    path = tmp_path/'contacts.json'; save(path, spec)
    result, arrays = evaluate(path, spec, policy(path))
    row = result['samples'][1]['actor_objects'][0]
    assert row['maximum_depth_lower_m'] > .0049
    assert row['containment']['status'] == 'unavailable'
    assert not row['passed'] and not result['sampled_conditions_pass']
    assert len(arrays['frame_1_A_ball_depth_lower_m']) == 1


@pytest.mark.parametrize('shape', [dict(shape='box', size_m=[.2, .2, .2]),
    dict(shape='sphere', radius_m=.1), dict(shape='cylinder', radius_m=.1, height_m=.2)])
def test_closed_actor_and_object_containment_is_separate_from_surface_depth(tmp_path, shape):
    source, path, spec = closed_fixture(tmp_path)
    scene = SceneContacts(spec, tmp_path); center = scene.actors['A']['rig'].vertices(scene.actors['A']['sampler'].sample(1)).mean(0)
    spec['objects']['item'] = dict(geometry=dict(schema='strep-object-geometry-v1', **shape),
        keyframes=[dict(time_s=0., translation_m=center.tolist(), rotation_xyzw=[0, 0, 0, 1])])
    save(path, spec); result, _ = evaluate(path, spec, policy(path)); row = result['samples'][1]['actor_objects'][0]
    assert row['maximum_depth_lower_m'] == 0 and row['maximum_depth_upper_m'] < 1e-6
    assert row['containment']['status'] == 'inside'
    assert not row['passed'] and not result['sampled_conditions_pass']


def test_all_objects_actor_pairs_placements_and_declared_planes_are_included(tmp_path):
    source, path, spec = closed_fixture(tmp_path)
    spec['actors']['B'] = copy.deepcopy(spec['actors']['A']); spec['actors']['B']['placement']['translation_m'] = [5., 0, 0]
    spec['objects']['far'] = dict(geometry=dict(schema='strep-object-geometry-v1', shape='cylinder', radius_m=.1, height_m=.2),
        keyframes=[dict(time_s=0., translation_m=[10., 0, 0], rotation_xyzw=[0, 0, 0, 1]),
                   dict(time_s=2., translation_m=[12., 0, 0], rotation_xyzw=[0, 0, 0, 1])])
    spec['objects']['another'] = copy.deepcopy(spec['objects']['far'])
    save(path, spec); p = policy(path, planes=dict(floor=dict(normal_world=[0., 1, 0], offset_m=-1.)))
    result, arrays = evaluate(path, spec, p)
    assert result['sampled_conditions_pass']
    assert all(len(s['actor_objects']) == 4 and len(s['actor_pairs']) == 1 and len(s['world_planes']) == 2 for s in result['samples'])
    assert all(s['actor_pairs'][0]['vertex_containment'][0]['max_depth_m'] == 0 for s in result['samples'])
    assert not any(result[k] for k in ('collision_verified', 'self_collision_verified', 'engine_playback_verified', 'quality_approved', 'release_approved'))
    # A newly declared wall is measured for both actors, without guessing a floor.
    p['planes']['wall'] = dict(normal_world=[1., 0, 0], offset_m=.3)
    failed, _ = evaluate(path, spec, p)
    assert not failed['sampled_conditions_pass'] and failed['declared_planes'] == ['floor', 'wall']


def test_partner_surface_overlap_is_visible_when_vertex_depth_is_zero(tmp_path):
    source, path, spec = closed_fixture(tmp_path)
    spec['actors']['B'] = copy.deepcopy(spec['actors']['A'])
    spec['actors']['B']['placement']['translation_m'][0] = .2
    save(path, spec); result, _ = evaluate(path, spec, policy(path))
    assert not result['sampled_conditions_pass']
    for sample in result['samples']:
        pair = sample['actor_pairs'][0]
        assert pair['surface']['records'] and all(d['available'] for d in pair['vertex_containment'])
        # Cube vertices lie on the other cube's coplanar side boundaries:
        # vertex penetration alone would miss this solid overlap.
        assert max(d['max_depth_m'] for d in pair['vertex_containment']) == 0


def test_nested_closed_partners_fail_without_surface_crossings(tmp_path):
    source, path, spec = closed_fixture(tmp_path)
    rig = RigAsset.load(source); doc = copy.deepcopy(rig.document); data = bytearray(rig.binary)
    vertices = (rig.primitives[0]['positions'] - [0., .2, 0.]) * .5 + [0., .2, 0.]
    doc['meshes'][0]['primitives'][0]['attributes']['POSITION'] = append_accessor(doc, data, vertices, 'VEC3')
    inner = tmp_path/'inner.glb'; write_glb(inner, doc, data)
    spec['actors']['B'] = copy.deepcopy(spec['actors']['A'])
    spec['actors']['B'].update(glb=inner.name, sha256=sha256(inner)); save(path, spec)
    result, _ = evaluate(path, spec, policy(path))
    assert not result['sampled_conditions_pass']
    for sample in result['samples']:
        pair = sample['actor_pairs'][0]
        assert not pair['surface']['records']
        assert pair['vertex_containment'][1]['max_depth_m'] > .099


def test_unavailable_conditions_do_not_pass_and_frames_include_native_and_contact_keys(tmp_path):
    _, _, _, spec = setup(tmp_path)
    path = tmp_path/'contacts.json'; save(path, spec)
    empty, _ = evaluate(path, spec, policy(path))
    assert not empty['sampled_conditions_pass'] and all(not s['conditions_available'] for s in empty['samples'])
    p = policy(path, mode='native-and-frame-populations', planes=dict(ground=dict(normal_world=[0., 1, 0], offset_m=-2.)))
    result, arrays = evaluate(path, spec, p)
    assert result['sampled_conditions_pass'] and len(result['frame_populations']) == 12
    assert result['times_s'][0] == 0 and result['times_s'][-1] == 2
    for row in result['frame_populations']: assert np.isin(row['times_s'], arrays['times_s']).all()
    assert np.isin(spec['contacts'][0]['interval_s'], arrays['times_s']).all()


def test_original_multi_primitive_topology_and_nonindexed_triangles_preserved(tmp_path):
    source, rig, reader, spec = setup(tmp_path)
    doc = copy.deepcopy(rig.document); data = bytearray(rig.binary)
    primitive = copy.deepcopy(doc['meshes'][0]['primitives'][0]); del primitive['indices']
    doc['meshes'][0]['primitives'].append(primitive); write_glb(source, doc, data)
    rig = RigAsset.load(source); faces, population = geometry.faces_for(rig)
    np.testing.assert_array_equal(faces, [[0, 1, 2], [3, 4, 5]])
    assert population[1]['first_vertex'] == 3 and population[1]['first_face'] == 1
    assert len(rig.vertices(reader.sample(1.))) == 6


def test_run_preserves_source_snapshots_and_failure_state(tmp_path, monkeypatch):
    source, path, spec = closed_fixture(tmp_path)
    p = policy(path, planes=dict(floor=dict(normal_world=[0., 1, 0], offset_m=-2.)))
    pp = tmp_path/'policy.json'; save(pp, p)
    out = tmp_path/'audit'; report = geometry.run(path, pp, out)
    assert report['sampled_conditions_pass'] and report['original_selected']
    assert read(out/'pipeline.json')['status'] == 'complete'
    assert sha256(out/'observations.npz') == report['observations_sha256']
    for source_path, entry in report['source_snapshots'].items(): assert sha256(source_path) == sha256(out/entry['path'])
    with pytest.raises(ValueError): geometry.run(path, pp, out)
    original = geometry.evaluate
    def changed(*args, **kwargs):
        value = original(*args, **kwargs); path.write_bytes(path.read_bytes()+b'\n'); return value
    monkeypatch.setattr(geometry, 'evaluate', changed)
    with pytest.raises(ValueError, match='source or snapshot changed'): geometry.run(path, pp, tmp_path/'changed')
    assert read(tmp_path/'changed/pipeline.json')['status'] == 'failed'
    assert not (tmp_path/'changed/result.json').exists()


def test_fitting_attaches_geometry_without_changing_native_pass_or_selection(tmp_path, monkeypatch):
    from test_native_scene_fit import prepare
    import native_scene_fit as fitting
    from native_support_feasibility import merit
    source, spec, contacts, permissions, permissions_path, scene, edits = prepare(tmp_path)
    p = policy(contacts, planes=dict(wall=dict(normal_world=[1., 0, 0], offset_m=0.)))
    pp = tmp_path/'policy.json'; save(pp,p)
    def original(problem, evaluate, iterations, trust):
        residual = evaluate(problem.initial,'initial')
        return problem.initial,dict(final_merit=list(merit(residual)),history=[])
    monkeypatch.setattr(fitting,'optimize',original)
    result = fitting.run(contacts,permissions_path,tmp_path/'fit',iterations=1,geometry_policy=pp)
    assert result['original_selected'] and not result['sampled_geometry_conditions_pass']
    assert not result['collision_verified']
    audit = read(tmp_path/'fit/geometry-audit/result.json')
    derived = read(tmp_path/'fit/geometry-audit/policy.json')
    assert derived['contacts_sha256'] == sha256(tmp_path/'fit/proposal/contacts.json')
    assert {k:v for k,v in derived.items() if k!='contacts_sha256'} == {k:v for k,v in p.items() if k!='contacts_sha256'}
    assert audit['authored_policy_sha256'] == sha256(pp)
    assert result['geometry_result_sha256'] == sha256(tmp_path/'fit/geometry-audit/result.json')
    assert sha256(tmp_path/'fit/geometry-policy.json') == sha256(pp)
    assert sha256(source) == spec['actors']['A']['sha256']


@pytest.mark.parametrize('fault', ['hash', 'schema', 'extra', 'missing-endpoint', 'duplicate-clock', 'clock-bool',
    'mode', 'resolution', 'negative-limit', 'plane-scale', 'plane-bool'])
def test_invalid_geometry_policy_rejects(tmp_path, fault):
    _, path, spec = closed_fixture(tmp_path); p = policy(path)
    if fault == 'hash': p['contacts_sha256'] = '0'*64
    if fault == 'schema': p['schema'] = 'old'
    if fault == 'extra': p['approved'] = True
    if fault == 'missing-endpoint': p['clock']['times_s'] = [0., 1.]
    if fault == 'duplicate-clock': p['clock']['times_s'] = [0., 1., 1., 2.]
    if fault == 'clock-bool': p['clock']['times_s'][1] = True
    if fault == 'mode': p['clock']['mode'] = 'preview'
    if fault == 'resolution': p['limits']['depth_resolution_m'] = 0
    if fault == 'negative-limit': p['limits']['penetration_m'] = -.001
    if fault.startswith('plane'):
        p['planes']['floor'] = dict(normal_world=[0., 2. if fault == 'plane-scale' else True, 0.], offset_m=0.)
    with pytest.raises(ValueError): evaluate(path, spec, p)
