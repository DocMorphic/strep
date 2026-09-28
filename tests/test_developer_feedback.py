"""Synthetic data only; these tests never populate release review evidence."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import developer_feedback as feedback
from strep import save, sha256


@pytest.fixture
def packet(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, 'ROOT', tmp_path)
    folder = tmp_path/'reports/rig-jobs/synthetic'; folder.mkdir(parents=True)
    clip = folder/'clip.glb'; clip.write_bytes(b'synthetic hash fixture, not animation')
    catalog = folder/'catalog.json'
    variant = dict(id='selected', glb='/files/rig-jobs/synthetic/clip.glb', sha256=sha256(clip))
    row = dict(id='synthetic-case', frames=120, fps=30, prompt='Synthetic fixture.', seed=1, variants=[variant])
    save(catalog, dict(cases=[row]))
    data = dict(schema='strep-developer-observation-v1', created_at='2026-09-28T00:00:00Z', reviewer_id='Synthetic fixture',
        notes='Synthetic test, not a human rating.', review_type='non_blind_developer', independent_human=False,
        cleanup_test_performed=False, quality_approved=False, frame_range=dict(start=0,end_inclusive=119),
        source=dict(study_url='/files/rig-jobs/synthetic/catalog.json',catalog_sha256=sha256(catalog),
            case_id=row['id'],variant=variant['id'],glb_url=variant['glb'],glb_sha256=variant['sha256'],
            frames=120,fps=30,prompt=row['prompt'],seed=1))
    return catalog, clip, data


def test_terminal_frame_observation_stays_unapproved(packet, tmp_path):
    catalog, _, data = packet
    response = tmp_path/'synthetic.json'; save(response,data)
    result = feedback.import_feedback(catalog,response,tmp_path/'imported')
    assert result['valid'] and not result['quality_approved'] and not result['independent_review']
    with pytest.raises(ValueError,match='Preserve'):feedback.import_feedback(catalog,response,tmp_path/'imported')


@pytest.mark.parametrize('failure', ['catalog','clip','variant','range','boolean_frame','independent','cleanup','approval','empty','timestamp'])
def test_stale_or_invalid_observation_is_rejected(packet,failure):
    catalog, clip, data = packet; data=copy.deepcopy(data)
    if failure=='catalog':data['source']['catalog_sha256']='0'*64
    if failure=='clip':clip.write_bytes(b'changed')
    if failure=='variant':data['source']['variant']='raw'
    if failure=='range':data['frame_range']['end_inclusive']=120
    if failure=='boolean_frame':data['frame_range']['start']=False
    if failure=='independent':data['independent_human']=True
    if failure=='cleanup':data['cleanup_test_performed']=True
    if failure=='approval':data['quality_approved']=True
    if failure=='empty':data['notes']=' '
    if failure=='timestamp':data['created_at']='2026-09-28T00:00:00'
    with pytest.raises(ValueError):feedback.validate(data,catalog)
