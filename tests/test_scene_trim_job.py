import copy
import shutil
import sys
import uuid
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save,sha256
from scene_trim_job import JOBS,metadata,prepare,run,source
from scene_release_job import source_metadata
from action_studio_server import allowed_file

URL='/files/scene-preview-v1/high-five-seed-11/palm.json'


@pytest.fixture
def folder():
    JOBS.mkdir(exist_ok=True);path=JOBS/('test-trim-'+uuid.uuid4().hex)
    yield path
    assert path.parent==JOBS and path.name.startswith('test-trim-')
    if path.exists():shutil.rmtree(path)


def payload():
    m=metadata(URL)
    return dict(source_url=URL,revision=m['revision'],first=20,last=100,label='Paired scene trim')


def test_actor_only_trim_does_not_enable_object_release_without_objects():
    assert metadata(URL)['objects']==0
    with pytest.raises(ValueError):source_metadata(URL,allow_native_runs=True)


@pytest.mark.parametrize('change',[{'revision':'old'},{'first':True},{'last':21},{'last':10000},{'label':''}])
def test_bad_request_does_not_create_output(folder,change):
    p=payload();p.update(change)
    with pytest.raises(ValueError):prepare(p,folder)
    assert not folder.exists()


@pytest.mark.parametrize('frames',[True,2,902,11.5])
def test_bad_retime_request_does_not_create_output(folder,frames):
    p=payload();p.pop('first');p.pop('last');p.update(operation='retime',frames=frames)
    with pytest.raises(ValueError):prepare(p,folder)
    assert not folder.exists()


def test_changed_snapshot_stops_before_trim(folder):
    prepare(payload(),folder)
    (folder/'input/events.json').write_text('{}')
    with pytest.raises(ValueError,match='Saved trim input changed'):run(folder)
    assert not (folder/'trimmed').exists()
    assert read(folder/'pipeline.json')['status']=='failed'


def test_real_pair_worker_keeps_both_actors_and_can_retrim_its_event_file(folder):
    original=source(URL);prepare(payload(),folder);run(folder)
    assert read(folder/'pipeline.json')['status']=='complete'
    result=read(folder/'trimmed.json');scene=result['scene']
    assert scene['frame_count']==81 and set(scene['actors'])=={'A','B'} and not scene['objects']
    assert [a['transform'] for a in scene['actors'].values()]==[a['transform'] for a in original['bundle']['scene']['actors'].values()]
    for row in read(folder/'manifest.json')['scenes']:
        for path in [*row['variants'].values(),*(d['path'] for d in row.get('downloads',[]))]:
            assert allowed_file('/files/scene-trim-jobs/'+folder.name+'/'+path)==folder/path
            assert (folder/path).is_file()
    url='/files/scene-trim-jobs/'+folder.name+'/trimmed.json'
    repeated=source(url)
    assert repeated['events_path']==folder/'trimmed/events.json'
    assert repeated['files'][repeated['events_path']]==sha256(folder/'trimmed/events.json')
    assert allowed_file('/files/scene-trim-jobs/'+folder.name+'/implementation/scene_trim_job.py') is None
    assert allowed_file('/files/scene-trim-jobs/../../README.md') is None
