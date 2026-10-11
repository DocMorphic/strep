"""Explicit clip-edge controls; protected interpolation support stays hard."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_contacts import setup
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from gltf_tools import append_accessor,write_glb
from strep import save,sha256


def prepare(tmp_path,chosen,*,path='translation'):
    source,rig,reader,spec=setup(tmp_path);spec['contacts']=[];scene=SceneContacts(spec,tmp_path)
    save(tmp_path/'contacts.json',spec);digest=sha256(tmp_path/'contacts.json')
    request=dict(schema='strep-native-scene-edit-v2',contacts_sha256=digest,actors=dict(A=dict(
        window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],
        tracks=[dict(node=0 if path=='translation' else 3,path=path,maximum_change=.02 if path=='translation' else 10.)],
        maximum_joint_displacement_m=.02,editable_clip_boundaries=chosen)))
    return source,scene,request,digest


@pytest.mark.parametrize('path',['translation','rotation'])
@pytest.mark.parametrize('chosen',[['start'],['end'],['start','end']])
def test_actual_endpoint_exports_follow_explicit_permissions(tmp_path,path,chosen):
    source,scene,request,digest=prepare(tmp_path,chosen,path=path);before=sha256(source)
    edits=SceneEdits(request,scene,digest);value=edits.initial.copy();value.reshape(-1,3)[:,0]=.1
    output=tmp_path/'candidate.glb';edits.export('A',value,output);audit=edits.audit('A',output,0)
    assert audit['passed'] and len(audit['clip_boundary_changes'])==len(chosen)
    assert audit['editable_clip_boundaries']==chosen and not audit['boundary_transition_compatibility_verified']
    decoded=RigAsset.load(output);sampler=NativeSupportSampler(decoded.document,decoded.binary,0)
    node=request['actors']['A']['tracks'][0]['node'];target=(node,path)
    old=next(c for c in scene.actors['A']['sampler'].channels if c[:2]==target)
    new=next(c for c in sampler.channels if c[:2]==target)
    for edge,index in [('start',0),('end',-1)]:
        assert np.array_equal(old[3][index],new[3][index]) is (edge not in chosen)
    for original,changed in zip(scene.actors['A']['sampler'].channels,sampler.channels):
        np.testing.assert_array_equal(original[2],changed[2])
        if original[:2]!=target:np.testing.assert_array_equal(original[3],changed[3])
    times=np.unique(np.r_[np.linspace(0.,2.,21),old[2]])
    np.testing.assert_allclose(edits.worlds('A',value,times),[sampler.sample(float(t)) for t in times],rtol=0,atol=2e-12)
    assert sha256(source)==before


def test_empty_v2_boundary_declaration_matches_legacy_controls(tmp_path):
    _,scene,request,digest=prepare(tmp_path,[]);legacy=copy.deepcopy(request)
    legacy['schema']='strep-native-scene-edit-v1';del legacy['actors']['A']['editable_clip_boundaries']
    a=SceneEdits(request,scene,digest);b=SceneEdits(legacy,scene,digest)
    assert a.size==b.size==3
    np.testing.assert_array_equal(a.actors['A']['tracks'][0]['ids'],b.actors['A']['tracks'][0]['ids'])
    np.testing.assert_array_equal(a.actors['A']['tracks'][0]['weights'],b.actors['A']['tracks'][0]['weights'])


@pytest.mark.parametrize('chosen',[None,True,'start',['start','start'],['middle'],[False]])
def test_invalid_opt_in_rejected(tmp_path,chosen):
    _,scene,request,digest=prepare(tmp_path,chosen)
    with pytest.raises(ValueError,match='Distinct explicit'):SceneEdits(request,scene,digest)


@pytest.mark.parametrize('edge,span',[('start',[0.,0.]),('start',[.05,.1]),('end',[2.,2.]),('end',[1.9,1.99])])
def test_endpoint_or_its_interpolation_support_cannot_touch_protected_time(tmp_path,edge,span):
    _,scene,request,digest=prepare(tmp_path,[edge]);request['actors']['A']['protected_s']=[span]
    with pytest.raises(ValueError,match='protected'):SceneEdits(request,scene,digest)


@pytest.mark.parametrize('edge',['start','end'])
def test_internal_edit_window_boundary_is_not_a_clip_boundary(tmp_path,edge):
    _,scene,request,digest=prepare(tmp_path,[edge]);actor=request['actors']['A']
    actor['window_s']=[.2,1.8];actor['knots_s']=[.2,1.,1.8]
    with pytest.raises(ValueError,match='actual'):SceneEdits(request,scene,digest)


def test_selected_track_requires_an_actual_end_key(tmp_path):
    source,scene,request,digest=prepare(tmp_path,['end']);rig=scene.actors['A']['rig']
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    animation=document['animations'][0];channel=next(c for c in animation['channels'] if c['target']==dict(node=0,path='translation'))
    selected=animation['samplers'][channel['sampler']]
    clock=next(c[2] for c in scene.actors['A']['sampler'].channels if c[:2]==(0,'translation')).copy()
    clock[-1]=1.9;selected['input']=append_accessor(document,binary,clock,'SCALAR');write_glb(source,document,binary)
    # Rebuild the explicit scene: other tracks still end at time 2.
    spec=dict(schema='strep-native-scene-contacts-v1',duration_s=2.,actors=dict(A=dict(glb=source.name,sha256=sha256(source),animation_index=0,
        placement=dict(translation_m=[0.,0.,0.],rotation_xyzw=[0.,0.,0.,1.]))),objects={},contacts=[])
    changed=SceneContacts(spec,tmp_path)
    with pytest.raises(ValueError,match='actual final'):SceneEdits(request,changed,digest)


def test_legacy_schema_cannot_silently_enable_boundary_changes(tmp_path):
    _,scene,request,digest=prepare(tmp_path,['start']);request['schema']='strep-native-scene-edit-v1'
    with pytest.raises(ValueError,match='actor edit'):SceneEdits(request,scene,digest)
