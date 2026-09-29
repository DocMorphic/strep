import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from trim_scene import trim_clock, trim_export
from strep import ROOT
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from strep import read, save
from trim_scene import run
import uuid


def fixture():
    scene = dict(fps=30,frame_count=20,actors={'A': {'transform': {'translation_m':[2,0,1]}}},
                 contacts=[dict(id='held',start_frame=2,end_frame=12),dict(id='later',start_frame=15,end_frame=17)],
                 objects={'box':dict(shape='box',size_m=[1,1,1],keyframes=[dict(frame=f,translation_m=[f,0,0],rotation_xyzw=[0,0,0,1]) for f in [0,19]])})
    events=dict(fps=30,events=[dict(type=name,frame=f,time_s=f/30) for name,f in [('grasp',2),('a',7),('b',7),('release',12),('end',20)]])
    return scene,events


def test_trim_moves_all_clocks_but_not_placement_and_records_prior_state():
    scene,events=fixture();original=copy.deepcopy(scene)
    trimmed,mapped,context=trim_clock(scene,events,5,10)
    assert scene==original and trimmed['actors']==scene['actors']
    assert trimmed['frame_count']==6
    assert trimmed['contacts']==[dict(id='held',start_frame=0,end_frame=5)]
    assert [e['type'] for e in mapped['events']]==['a','b']
    assert [e['frame'] for e in mapped['events']]==[2,2]
    assert context['contacts_active_at_start']==['held']
    assert [e['type'] for e in context['events_before_range']]==['grasp']
    assert [e['type'] for e in context['events_after_range']]==['release','end']
    assert np.allclose([k['translation_m'][0] for k in trimmed['objects']['box']['keyframes']],np.arange(5,11))


def test_exclusive_source_terminal_event_only_survives_when_original_tail_is_kept():
    scene,events=fixture()
    _,kept,_=trim_clock(scene,events,5,19)
    assert kept['events'][-1]==dict(type='end',frame=15,time_s=.5)
    _,kept,_=trim_clock(scene,events,5,11)
    assert not any(e['type']=='release' for e in kept['events'])


@pytest.mark.parametrize('first,last',[(True,10),(5.5,10),(-1,10),(5,6),(10,5),(5,20)])
def test_invalid_range_rejected(first,last):
    with pytest.raises(ValueError):trim_clock(*fixture(),first,last)


def test_invalid_event_clock_rejected():
    scene,events=fixture();events['events'][0]['time_s']+=.1
    with pytest.raises(ValueError,match='event clock'):trim_clock(scene,events,5,10)


def test_fractional_events_and_retained_terminal_hold_keep_precise_time():
    scene,events=fixture()
    events['events']=[dict(type=str(f),frame=f,time_s=f/30) for f in [4.75,7.25,7.25,10.5,19.5,20]]
    _,mapped,context=trim_clock(scene,events,5,10)
    assert [e['frame'] for e in mapped['events']]==[2.25,2.25]
    assert all(e['time_s']==.075 for e in mapped['events'])
    assert [e['frame'] for e in context['events_before_range']]==[4.75]
    _,mapped,_=trim_clock(scene,events,5,19)
    assert [e['frame'] for e in mapped['events']][-2:]==[14.5,15]


def test_exact_contact_window_excluded_even_if_conservative_native_interval_touches_cut():
    from trim_scene import trim_exact_windows
    scene,_=fixture()
    contacts,mapped=trim_exact_windows(scene,dict(windows=[dict(id='held',exact_output_frames=[3.2,11.8]),dict(id='later',exact_output_frames=[15.1,16.2])]),12,19)
    assert [c['id'] for c in contacts]==['later']
    assert contacts[0]['start_frame']==3 and contacts[0]['end_frame']==5
    assert mapped['windows'][0]['exact_output_frames']==pytest.approx([3.1,4.2])
    assert mapped['excluded_exact_windows'][0]['id']=='held'


@pytest.mark.parametrize('name,path,frames',[
    ('actor','reports/scene-runtime-v2/paired/actors/0/actor.glb',150),
    ('objects','reports/scene-runtime-v2/release/objects.glb',180)])
def test_real_export_trim_preserves_mesh_rig_and_fractional_poses(name,path,frames):
    path=ROOT/path;doc,binary=read_glb(path)
    result,data=trim_export(path,frames,20,100)
    for key in ['nodes','meshes','materials','skins','textures','images']:
        assert result.get(key)==doc.get(key)
    assert data[:len(binary)]==binary
    a=AnimationSampler(doc,binary,0);b=AnimationSampler(result,data,0)
    for f in [0,.25,1,17.5,53.75,80]:
        assert np.max(np.abs(a.sample((20+f)/30)-b.sample(f/30)))<1e-5


@pytest.mark.parametrize('path,frames,first,last',[
    ('reports/scene-retime-import-v1/paired/actors/0/actor.glb',223,35,185),
    ('reports/scene-retime-import-v1/release/objects.glb',121,20,100),
])
def test_retimed_curve_trim_keeps_interior_keys_and_between_key_poses(path,frames,first,last,tmp_path):
    from gltf_tools import write_glb,accessor
    from scene_runtime import import_rate
    from scene_animation_curves import write as curves
    doc,binary=read_glb(ROOT/path);result,data=trim_export(ROOT/path,frames,first,last)
    for key in ['nodes','meshes','materials','skins','textures','images']:
        assert result.get(key)==doc.get(key)
    a=AnimationSampler(doc,binary,0);b=AnimationSampler(result,data,0)
    for f in [0,.01,.25,.5,1,17.33,last-first-.01,last-first]:
        assert np.max(abs(a.sample((first+f)/30)-b.sample(f/30)))<1e-5
    out=tmp_path/'trim.glb';write_glb(out,result,data)
    assert import_rate(out) is None
    target=tmp_path/'curves.json';curves(out,target)
    from strep import sha256
    bound=read(target)
    assert bound['source_sha256']==sha256(out)
    assert len(bound['channels'])==len(result['animations'][0]['channels'])
    assert any(len(c['times_s'])!=last-first+1 for c in bound['channels'])
    np.testing.assert_allclose(bound['channels'][0]['times_s'],accessor(result,data,result['animations'][0]['samplers'][0]['input']))


def test_step_jump_just_after_cut_must_not_be_smoothed_or_dropped(tmp_path):
    from gltf_tools import append_accessor,write_glb
    doc=dict(asset=dict(version='2.0'),scene=0,scenes=[dict(nodes=[0])],nodes=[dict(name='Jump')],buffers=[],bufferViews=[],accessors=[])
    binary=bytearray();time=append_accessor(doc,binary,[0,1/30,.1],'SCALAR')
    values=append_accessor(doc,binary,[[0,0,0],[1,0,0],[1,0,0]],'VEC3')
    doc['animations']=[dict(samplers=[dict(input=time,output=values,interpolation='STEP')],channels=[dict(sampler=0,target=dict(node=0,path='translation'))])]
    path=tmp_path/'step.glb';write_glb(path,doc,binary)
    trimmed,data=trim_export(path,4,1,3)
    sample=AnimationSampler(trimmed,data,0)
    assert sample.sample(0)[0,0,3]==0
    assert sample.sample(.00001)[0,0,3]==1
    assert len(sample.channels[0][2])==3


@pytest.mark.parametrize('fault',['placement','ownership','fps'])
def test_inconsistent_runtime_rejected_before_any_output(tmp_path,fault):
    source=ROOT/'reports/scene-runtime-v2/release'
    for name in ['portable-scene.json','events.json','scene-runtime.json']:
        (tmp_path/name).write_bytes((source/name).read_bytes())
    runtime=read(tmp_path/'scene-runtime.json')
    if fault=='placement':runtime['actors']['A']['placement']['translation_m'][0]+=1
    elif fault=='ownership':next(iter(runtime['objects'].values()))['ownership']='live_physics'
    else:runtime['fps']=60
    save(tmp_path/'scene-runtime.json',runtime)
    output=ROOT/'reports'/('test-trim-rejection-'+uuid.uuid4().hex)
    with pytest.raises(ValueError):run(tmp_path,output,20,100)
    assert not output.exists()
