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
