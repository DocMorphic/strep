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
