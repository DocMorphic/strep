import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT
from carry_scene_actor import carry_export,carried_native,transform
from scene_object_export import export_objects
from rig_clip_import import AnimationSampler
from rig_asset import RigAsset
from gltf_tools import read_glb,write_glb


@pytest.fixture
def fixture(tmp_path):
    actor=ROOT/'reports/scene-runtime-v2/release/actors/0/actor.glb'
    scene=dict(frame_count=180,fps=30,objects={'platform':dict(shape='box',size_m=[2,.2,2],keyframes=[
        dict(frame=0,translation_m=[0,.3,0],rotation_xyzw=[0,0,0,1]),
        dict(frame=179,translation_m=[.6,.6,.4],rotation_xyzw=Rotation.from_euler('y',1.2).as_quat().tolist())])})
    objects=tmp_path/'objects.glb';export_objects(scene,objects)
    placement=dict(translation_m=[.2,.4,-.15],rotation_xyzw=Rotation.from_euler('y',.3).as_quat().tolist())
    return actor,objects,placement


def test_carrier_preserves_relative_surface_at_subframes_with_rotated_placement(fixture):
    actor,objects,placement=fixture
    doc,binary,node=carry_export(actor,objects,'platform',placement,37,180)
    rigs=[RigAsset.load(actor),RigAsset(doc,binary)]
    a=AnimationSampler(rigs[0].document,rigs[0].binary,0);b=AnimationSampler(doc,binary,0);o=AnimationSampler(*read_glb(objects),0)
    p=transform(placement);reference=o.sample(37/30)[node]
    for f in [0,.13,36.5,37,98.75,179]:
        old=p@a.sample(f/30);new=p@b.sample(f/30)
        expected=o.sample(f/30)[node]@np.linalg.inv(reference)@old
        np.testing.assert_allclose(new[:len(old)],expected,atol=1e-6)
        before=rigs[0].vertices(a.sample(f/30));after=rigs[1].vertices(b.sample(f/30))
        change=np.linalg.inv(p)@o.sample(f/30)[node]@np.linalg.inv(reference)@p
        np.testing.assert_allclose(after,before@change[:3,:3].T+change[:3,3],atol=1e-6)


def test_native_root_heading_and_predictions_follow_carrier(fixture):
    actor,objects,placement=fixture
    doc,binary,node=carry_export(actor,objects,'platform',placement,0,180)
    original=dict(np.load(actor.with_name('motion.npz')))
    original['smooth_root_pos']=original['root_positions'].copy()
    result=carried_native(original,doc,binary,AnimationSampler(*read_glb(objects),0),node,placement,0,180)
    np.testing.assert_array_equal(result['foot_contacts'],original['foot_contacts'])
    np.testing.assert_allclose(result['smooth_root_pos'],result['root_positions'],atol=1e-5)
    assert np.linalg.norm(result['global_root_heading'][-1]-original['global_root_heading'][-1])>.5
    np.testing.assert_allclose(np.linalg.norm(result['global_root_heading'],axis=1),1,atol=1e-8)


@pytest.mark.parametrize('frame',[-1,180,True,1.5])
def test_invalid_reference_rejected(fixture,frame):
    actor,objects,placement=fixture
    with pytest.raises(ValueError):carry_export(actor,objects,'platform',placement,frame,180)


def test_scaled_carrier_rejected(fixture):
    actor,objects,placement=fixture
    doc,binary=read_glb(objects);doc['nodes'][0]['scale']=[1,2,1];write_glb(objects,doc,binary)
    with pytest.raises(ValueError,match='unit-scale'):carry_export(actor,objects,'platform',placement,0,180)
