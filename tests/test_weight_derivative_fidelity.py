"""The original skin remains the reference; corruption cannot become a baseline."""
from pathlib import Path
import sys
import copy
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from godot_weight_derivative import derivative, layout
from weight_derivative_fidelity import verify_derivative, measure_original
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from strep import sha256
from test_scene_import_measurements import fixture


def assets(tmp_path):
    fixture(tmp_path); source = tmp_path/'source.glb'; path = tmp_path/'derived.glb'
    derivative(source, path, source_sha256=sha256(source))
    return RigAsset.load(source), RigAsset.load(path)


def test_original_coefficients_remain_independent_of_derivative_reference(tmp_path):
    original, derived = assets(tmp_path)
    source_sampler = AnimationSampler(original.document, original.binary, 0)
    def distinct_bone_pose(time):
        pose = source_sampler.sample(time).copy()
        pose[original.joints[3], 0, 3] += .1
        return pose
    sampler = SimpleNamespace(sample=distinct_bone_pose)
    times = np.array([0., .25, .333333333333, 1., 2.])
    p = np.array([3., .4, -2.]); r = np.eye(3)
    scene = SimpleNamespace(times=times, actors=dict(A=dict(rig=derived, placement=(p,r))),
        actor_vertices=lambda name,t: derived.vertices(sampler.sample(t))@r.T+p)
    row, errors, witnesses = measure_original(original, sampler, scene, 'A')
    expected = [np.linalg.norm(derived.vertices(sampler.sample(t))-original.vertices(sampler.sample(t)),axis=1).max() for t in times]
    np.testing.assert_allclose(errors, expected, atol=1e-14)
    assert errors.max()>1e-8 and row['original_skin_reference_preserved']
    assert row['samples']==len(times) and row['vertices']==8 and len(witnesses)==len(times)


def test_existing_precision_screen_rejects_actual_imported_displacement(tmp_path):
    original, derived = assets(tmp_path);sampler=AnimationSampler(original.document, original.binary,0)
    times=np.array([0., .5, 1., 2.])
    scene=SimpleNamespace(times=times,actors=dict(A=dict(rig=derived,placement=(np.zeros(3),np.eye(3)))),
        actor_vertices=lambda name,t:original.vertices(sampler.sample(t))+[.00015,0,0])
    row, errors, _=measure_original(original,sampler,scene,'A')
    assert row['tolerance_m']==.0001 and not row['position_samples_passed']
    assert row['samples_over_tolerance']==len(times)
    np.testing.assert_allclose(errors,.00015,atol=1e-14)


@pytest.mark.parametrize('fault',['document','weight','joint','position','animation'])
def test_modified_non_influence_or_unchecked_derivative_rejected(tmp_path,fault):
    original,derived=assets(tmp_path)
    if fault=='document': derived.document['asset']['generator']='changed'
    else:
        binary=bytearray(derived.binary)
        attrs=derived.document['meshes'][0]['primitives'][0]['attributes']
        if fault=='weight': layout(derived.document,binary,attrs['WEIGHTS_0'])[0,0]+=.001
        elif fault=='joint': layout(derived.document,binary,attrs['JOINTS_0'])[0,0]=5
        else:
            number=attrs['POSITION'] if fault=='position' else derived.document['animations'][0]['samplers'][0]['output']
            accessor=derived.document['accessors'][number];view=derived.document['bufferViews'][accessor['bufferView']]
            start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
            # Modify a finite float32 payload without changing its metadata.
            np.ndarray((accessor['count'],),np.float32,buffer=binary,offset=start)[0]+=.001
        derived.binary=bytes(binary)
    with pytest.raises(ValueError):verify_derivative(original,derived)


def test_missing_vertex_cannot_reduce_fidelity_population(tmp_path):
    original,derived=assets(tmp_path);sampler=AnimationSampler(original.document,original.binary,0)
    scene=SimpleNamespace(times=np.array([0.,1.]),actors=dict(A=dict(rig=derived,placement=(np.zeros(3),np.eye(3)))),
        actor_vertices=lambda name,t:original.vertices(sampler.sample(t))[:-1])
    with pytest.raises(ValueError,match='vertex population'):measure_original(original,sampler,scene,'A')
