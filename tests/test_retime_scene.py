import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from retime_scene import frame_scale,map_frame,retime_clock,retime_export
from gltf_tools import append_accessor,write_glb,read_glb,accessor
from rig_clip_import import AnimationSampler


def fixture():
    scene=dict(fps=30,frame_count=10,actors={},objects={},contacts=[dict(id='touch',start_frame=4,end_frame=4)])
    events=dict(fps=30,events=[dict(type=name,frame=f,time_s=f/30) for name,f in [('a',4),('b',4),('final_pose',9),('end',10)]])
    return scene,events


def test_exact_event_timing_ties_and_terminal_hold_conservative_contact_enclosure():
    scene,events=fixture();before=copy.deepcopy((scene,events))
    result,mapped,windows=retime_clock(scene,events,6)
    assert (scene,events)==before
    assert result['contacts'][0]['start_frame']==2 and result['contacts'][0]['end_frame']==3
    assert [e['type'] for e in mapped['events']]==['a','b','final_pose','end']
    assert mapped['events'][0]['frame']==pytest.approx(20/9)
    assert mapped['events'][-2]['frame']==5 and mapped['events'][-1]['frame']==6
    assert windows[0]['exact_output_frames']==pytest.approx([20/9,20/9])
    assert 0 < windows[0]['maximum_enclosure_seconds'] < 1/30


def test_fractional_event_can_be_retimed_again_without_rounding():
    scene,events=fixture()
    new,mapped,_=retime_clock(scene,events,6)
    _,again,_=retime_clock(new,mapped,10)
    assert [e['frame'] for e in again['events']]==[4,4,9,10]
    assert map_frame(9.5,10,6)==5.5


def test_retime_trim_retime_does_not_expand_exact_contact_intent():
    from trim_scene import trim_clock,trim_exact_windows
    scene,events=fixture()
    new,mapped,windows=retime_clock(scene,events,6)
    cut,cut_events,_=trim_clock(new,mapped,1,4)
    cut['contacts'],precise=trim_exact_windows(new,dict(windows=windows),1,4)
    final,_,final_windows=retime_clock(cut,cut_events,10,precise)
    assert final_windows[0]['exact_output_frames']==pytest.approx([11/3,11/3])
    assert final['contacts'][0]['start_frame']==3 and final['contacts'][0]['end_frame']==4


@pytest.mark.parametrize('frames',[True,2,902,30.5,float('nan')])
def test_invalid_target_clock_rejected(frames):
    with pytest.raises(ValueError):frame_scale(10,frames)


@pytest.mark.parametrize('mode',['LINEAR','STEP','CUBICSPLINE'])
def test_thirty_second_endpoint_does_not_overflow_from_float32_source_clock(tmp_path,mode):
    from retime_scene import curve_audit
    doc=dict(asset=dict(version='2.0'),nodes=[dict(name='root')],scenes=[dict(nodes=[0])],scene=0,buffers=[{}],bufferViews=[],accessors=[])
    binary=bytearray();times=append_accessor(doc,binary,[0,1/30,2/30],'SCALAR')
    positions=np.array([[0,0,0],[1,1,0],[2,0,0]],dtype=float)
    values=positions if mode!='CUBICSPLINE' else np.stack([np.zeros((3,3)),positions,np.zeros((3,3))],axis=1).reshape(-1,3)
    output=append_accessor(doc,binary,values,'VEC3')
    doc['animations']=[dict(channels=[dict(sampler=0,target=dict(node=0,path='translation'))],samplers=[dict(input=times,output=output,interpolation=mode)])]
    path=tmp_path/'source.glb';write_glb(path,doc,binary)
    result,data=retime_export(path,3,901);sampler=AnimationSampler(result,data,0)
    assert sampler.duration==30
    audit=curve_audit(path,(result,data),3,901)
    assert audit['maximum_matrix_error']<1e-5
    assert audit['target_export_duration_s']==30
    np.testing.assert_allclose(sampler.sample(30)[0,:3,3],positions[-1])


@pytest.mark.parametrize('fault',['frame','time','fps','contact'])
def test_invalid_source_clock_rejected(fault):
    scene,events=fixture()
    if fault=='frame':events['events'][0]['frame']=True
    if fault=='time':events['events'][0]['time_s']+=.1
    if fault=='fps':scene['fps']=60
    if fault=='contact':scene['contacts'][0]['end_frame']=10
    with pytest.raises(ValueError):retime_clock(scene,events,6)


@pytest.mark.parametrize('mode',['LINEAR','STEP','CUBICSPLINE'])
def test_timing_preserves_source_channels_and_cubic_derivatives(tmp_path,mode):
    doc=dict(asset=dict(version='2.0'),nodes=[dict(name='object')],scenes=[dict(nodes=[0])],scene=0,
             buffers=[{}],bufferViews=[],accessors=[],materials=[dict(name='unchanged')])
    binary=bytearray();times=np.array([0,.1,.2])
    positions=np.array([[0,0,0],[.1,.3,0],[.4,.1,.2]])
    values=positions if mode!='CUBICSPLINE' else np.stack([np.ones((3,3))*.2,positions,np.ones((3,3))*.4],axis=1).reshape(-1,3)
    time=append_accessor(doc,binary,times,'SCALAR');out=append_accessor(doc,binary,values,'VEC3')
    doc['animations']=[dict(channels=[dict(sampler=0,target=dict(node=0,path='translation'))],samplers=[dict(input=time,output=out,interpolation=mode)])]
    path=tmp_path/'source.glb';write_glb(path,doc,binary)
    original,original_binary=read_glb(path);result,data=retime_export(path,7,10)
    assert result['nodes']==original['nodes'] and result['materials']==original['materials']
    assert data[:len(original_binary)]==original_binary
    a=AnimationSampler(original,original_binary,0);b=AnimationSampler(result,data,0)
    from scene_runtime import import_rate
    retimed_path=tmp_path/'retimed.glb';write_glb(retimed_path,result,data)
    assert import_rate(path)==pytest.approx(10,rel=1e-6)
    assert import_rate(retimed_path)==pytest.approx(10/1.5,rel=1e-6)
    for t in [0,.037,.085,.13,.181,.2]:
        np.testing.assert_allclose(a.sample(t),b.sample(t*1.5),atol=1e-7)
    if mode=='CUBICSPLINE':
        v=accessor(result,data,result['animations'][0]['samplers'][0]['output'])
        np.testing.assert_allclose(v[1::3],positions,atol=1e-7)
        np.testing.assert_allclose(v[0::3],.2/1.5,atol=1e-7)
        np.testing.assert_allclose(v[2::3],.4/1.5,atol=1e-7)
