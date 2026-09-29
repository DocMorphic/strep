import copy
import shutil
import sys
import tempfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from scene_region_job import JOBS,metadata,validate,prepare,run,audit_summary
from action_studio_server import allowed_file

URL='/files/scene-preview-v1/lift-box-seed-11/palm.json'


@pytest.fixture(scope='module')
def payload():
    source=metadata(URL)
    assert all(c['supported'] for c in source['contacts'])
    return dict(source_url=URL,revision=source['revision'],actor='A',label='Region job test',
                contacts=[c['edit'] for c in source['contacts']])


@pytest.fixture
def work():
    JOBS.mkdir(exist_ok=True);path=Path(tempfile.mkdtemp(prefix='test-',dir=JOBS)).resolve()
    yield path
    assert path.is_relative_to(JOBS.resolve()) and path.name.startswith('test-')
    shutil.rmtree(path)


def test_original_run_motion_can_be_snapshotted_without_exposing_runs_route(payload,work):
    source,scene,ids=validate(copy.deepcopy(payload))
    assert scene['actors']['A']['motion'].startswith('runs/')
    assert allowed_file('/files/scene-region-jobs/example/candidate.json')==JOBS/'example/candidate.json'
    assert allowed_file('/files/scene-region-jobs/../../README.md') is None
    assert allowed_file('/files/runs/private.npz') is None
    folder=work/'job';prepare(payload,folder)
    authored=read(folder/'source/authored-scene.json')
    assert all(c['region_contact']['schema']=='strep-scene-region-contact-v1' for c in authored['contacts'])
    assert (ROOT/authored['actors']['A']['motion']).is_file()
    assert read(source['path'])==source['bundle']


@pytest.mark.parametrize('failure',['revision','path','actor','duplicates','frames','surface','limits','mode'])
def test_invalid_request_does_not_create_job(payload,work,failure):
    p=copy.deepcopy(payload)
    if failure=='revision':p['revision']='stale'
    if failure=='path':p['source_url']='/files/../../README.md'
    if failure=='actor':p['actor']='missing'
    if failure=='duplicates':p['contacts'].append(copy.deepcopy(p['contacts'][0]))
    if failure=='frames':p['contacts'][0]['end_frame']=10000
    if failure=='surface':p['contacts'][0]['point_m']=[0,0,0]
    if failure=='limits':p['contacts'][0]['limits']['spacing_m']=float('nan')
    if failure=='mode':p['contacts'][0]['patch_mode']='saved'
    with pytest.raises((ValueError,KeyError)):prepare(p,work/'job')
    assert not (work/'job').exists()


def test_worker_rejects_changed_snapshot_before_fitting(payload,work):
    folder=work/'job';prepare(payload,folder)
    (folder/'source/authored-scene.json').write_text('{}')
    with pytest.raises(ValueError,match='Saved input changed'):run(folder)
    assert read(folder/'pipeline.json')['status']=='failed'
    assert not (folder/'fit').exists()


def test_completion_summary_never_promotes_failed_geometry_or_motion_regression():
    candidate=dict(contact_failures=0,contact_samples=34,geometry_failures=1,rows=[{}],peak_joint_speed_m_s=2.,peak_joint_acceleration_m_s2=3.)
    source=dict(peak_joint_speed_m_s=1.,peak_joint_acceleration_m_s2=3.)
    result=audit_summary(dict(hard_edit_bounds_passed=True,variants=dict(source=source,candidate=candidate)))
    assert not result['contact_geometry_passed'] and not result['quality_approved']
    assert result['motion_regressions']==['peak_joint_speed_m_s']
