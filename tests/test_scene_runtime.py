import copy
import shutil
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save,sha256
from scene_runtime import write


def fixture(tmp_path):
    source=ROOT/'reports/scene-runtime-v2/release'
    for name in ('actors','objects.glb','portable-scene.json','events.json'):
        if (source/name).is_dir():shutil.copytree(source/name,tmp_path/name)
        else:shutil.copyfile(source/name,tmp_path/name)
    return read(tmp_path/'portable-scene.json')


@pytest.mark.parametrize('fault',['traversal','source_hash','actor_clock','unknown_actor','unknown_object','event_clock'])
def test_invalid_scene_package_rejected_before_manifest(tmp_path,fault):
    scene=fixture(tmp_path);events=read(tmp_path/'events.json')
    if fault=='traversal':scene['actors']['A']['preview_glb']='../elsewhere.glb'
    if fault=='source_hash':scene['actors']['A']['source_sha256']='0'*64
    if fault=='actor_clock':scene['frame_count']-=1
    if fault=='unknown_actor':events['events'][0]['actor']='missing'
    if fault=='unknown_object':events['events'][0]['object']='missing'
    if fault=='event_clock':events['events'][0]['time_s']+=1
    save(tmp_path/'portable-scene.json',scene);save(tmp_path/'events.json',events)
    with pytest.raises(ValueError):write(tmp_path)
    assert not (tmp_path/'scene-runtime.json').exists()


def test_exclusive_contact_end_and_same_time_order_retained(tmp_path):
    scene=fixture(tmp_path);frames=scene['frame_count']
    events=dict(fps=30,events=[dict(type='contact_end',actor='A',frame=frames,time_s=frames/30),dict(type='first',actor='A',frame=0,time_s=0),dict(type='second',actor='A',frame=0,time_s=0)])
    save(tmp_path/'events.json',events);data=write(tmp_path)
    assert [(m['frame'],m['payload']['type']) for m in data['markers']]==[(0,'first'),(0,'second'),(frames,'contact_end')]
    assert len({m['id'] for m in data['markers']})==3
    assert data['source_events_sha256']==sha256(tmp_path/'events.json')


def test_runtime_rejects_sphere_metadata_paired_with_an_old_box_glb(tmp_path):
    scene=fixture(tmp_path);obj=next(iter(scene['objects'].values()))
    obj.pop('shape');obj.pop('size_m')
    obj['geometry']=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.2)
    save(tmp_path/'portable-scene.json',scene)
    with pytest.raises(ValueError,match='geometry'):write(tmp_path)


def test_fractional_markers_use_v2_without_quantizing_or_reordering_ties(tmp_path):
    fixture(tmp_path)
    events=dict(fps=30,events=[dict(type=n,actor='A',frame=f,time_s=f/30) for n,f in [('later',4.9),('a',4.25),('b',4.25)]])
    save(tmp_path/'events.json',events);data=write(tmp_path)
    assert data['schema']=='strep-runtime-scene-v2'
    assert [(m['frame'],m['payload']['type']) for m in data['markers']]==[(4.25,'a'),(4.25,'b'),(4.9,'later')]


@pytest.mark.parametrize('frame',[True,float('nan'),float('inf'),-0.5])
def test_invalid_fractional_marker_rejected(tmp_path,frame):
    fixture(tmp_path)
    import json
    (tmp_path/'events.json').write_text(json.dumps(dict(fps=30,events=[dict(type='test',frame=frame,time_s=0)])))
    with pytest.raises(ValueError):write(tmp_path)


def test_integer_events_with_retimed_keys_also_require_v2(tmp_path):
    from gltf_tools import read_glb,write_glb,accessor,append_accessor
    import numpy as np
    scene=fixture(tmp_path)
    # Add exact midpoint samples on a 60fps key grid without changing duration
    # or native-array count. Integer markers must not label this as old v1.
    path=tmp_path/scene['actors']['A']['preview_glb'];doc,binary=read_glb(path);buffer=bytearray(binary)
    from rig_clip_import import AnimationSampler
    sampler=AnimationSampler(doc,binary,0);animation=doc['animations'][0]
    for item,(_,prop,times,values,mode) in zip(animation['samplers'],sampler.channels):
        dense=np.linspace(0,times[-1],2*len(times)-1)
        item['input']=append_accessor(doc,buffer,dense,'SCALAR')
        item['output']=append_accessor(doc,buffer,np.array([sampler.value(prop,times,values,mode,t) for t in dense]),'VEC4' if prop=='rotation' else 'VEC3')
    write_glb(path,doc,buffer)
    data=write(tmp_path)
    assert data['schema']=='strep-runtime-scene-v2'
    assert data['actors']['A']['bake_fps']==pytest.approx(60,rel=1e-6)
    assert all(float(m['frame']).is_integer() for m in data['markers'])
