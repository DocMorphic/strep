import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rig_clip_import import AnimationSampler,catalog,export
from rig_asset import RigAsset
from gltf_tools import append_accessor
from strep import ROOT,read,sha256


def test_interpolation_clamps_steps_and_handles_different_key_spacing():
    t=np.array([1.,3.]);v=np.array([[0.,0,0],[4.,0,0]])
    for time,expected in [(0,0),(1,0),(2,2),(3,4),(4,4)]:
        assert AnimationSampler.value('translation',t,v,'LINEAR',time)[0]==pytest.approx(expected)
    assert AnimationSampler.value('translation',t,v,'STEP',2.999)[0]==0
    assert AnimationSampler.value('translation',t,v,'STEP',3)[0]==4


def test_quaternion_linear_uses_shortest_arc_and_cubic_normalizes():
    t=np.array([0.,2.]);a=Rotation.from_euler('z',0,degrees=True).as_quat();b=-Rotation.from_euler('z',90,degrees=True).as_quat()
    q=AnimationSampler.value('rotation',t,np.array([a,b]),'LINEAR',1.)
    assert Rotation.from_quat(q).as_euler('xyz',degrees=True)[2]==pytest.approx(45)
    v=np.array([[0,0,0,0],a,[0,0,0,0],[0,0,0,0],-b,[0,0,0,0]])
    q=AnimationSampler.value('rotation',t,v,'CUBICSPLINE',1.)
    assert np.linalg.norm(q)==pytest.approx(1.)
    assert Rotation.from_quat(q).as_euler('xyz',degrees=True)[2]==pytest.approx(45)


def test_cubic_tangents_are_scaled_by_interval_duration():
    t=np.array([1.,3.]);v=np.array([[0,0,0],[0,0,0],[2,0,0],[0,0,0],[4,0,0],[0,0,0]],float)
    assert AnimationSampler.value('translation',t,v,'CUBICSPLINE',2.)[0]==pytest.approx(2.5)


def test_step_boundary_uses_the_exact_stored_sample_timestamp():
    times=np.array([0,.8,1],dtype=np.float32);values=np.array([[0,0,0],[1,0,0],[2,0,0]])
    assert AnimationSampler.value('translation',times,values,'STEP',.8)[0]==0
    assert AnimationSampler.value('translation',times,values,'STEP',float(np.float32(.8)))[0]==1


def test_invalid_animation_is_reported_without_dropping_channels():
    r=RigAsset.load(ROOT/'assets/characters/cesium-man/CesiumMan.glb')
    d=copy.deepcopy(r.document);d['animations'][0]['channels'].append(copy.deepcopy(d['animations'][0]['channels'][0]))
    with pytest.raises(ValueError,match='distinct'):AnimationSampler(d,r.binary,0)
    d=copy.deepcopy(r.document);b=bytearray(r.binary)
    channel=next(c for c in d['animations'][0]['channels'] if c['target']['path']=='scale')
    sampler=d['animations'][0]['samplers'][channel['sampler']]
    from rig_asset import array
    values=array(d,b,sampler['output']);values[:,0]=2
    sampler['output']=append_accessor(d,b,values,'VEC3')
    with pytest.raises(ValueError,match='scale'):AnimationSampler(d,b,0)


def test_existing_clip_export_has_no_fabricated_contacts_and_preserves_source(tmp_path):
    source=ROOT/'assets/characters/cesium-man/CesiumMan.glb';digest=sha256(source)
    assert catalog(source)[0]['supported']
    report=export(source,source.parent/'rig-profile-v2.json',0,tmp_path/'clip')
    assert report['frames']==61 and report['source_kind']=='gltf_animation'
    assert report['roundtrip_max_vertex_error_m']<1e-5 and report['roundtrip_max_matrix_error']<1e-5
    assert read(tmp_path/'clip/contacts.json')['intervals']==[]
    assert sha256(source)==digest
    from audit_rig_ground import audit
    ground=audit(tmp_path/'clip')
    assert ground['contact_provenance']=='none_supplied'
    assert all(p['hover_max_m'] is None and p['predicted_frames']==[] for p in ground['foot_envelope_support'])
