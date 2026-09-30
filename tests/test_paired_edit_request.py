import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import paired_edit_request as requests
from strep import ROOT, read, sha256

URL = '/files/scene-trim-jobs/paired-studio-workflow-v2-trim/trimmed.json'
pytestmark = pytest.mark.skipif(not (ROOT/'reports/scene-trim-jobs/paired-studio-workflow-v2-trim/trimmed.json').exists(), reason='Local saved paired scene required')


def payload():
    data = requests.describe(URL); point = data['contacts'][0]['seconds'][0]
    return dict(schema='strep-paired-rotation-request-v1', source_url=URL, revision=data['revision'],
        actors={name: dict(joints=['LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand']) for name in data['actors']},
        window_s=[point-.5, point+.5], protected_contact_ids=[data['contacts'][0]['id']], limit_degrees=5.,
        knots_s=np.linspace(point-.5, point+.5, 5).tolist())


def test_precise_contact_and_both_actors_compile_from_saved_scene():
    data, models, protected = requests.compile_request(payload())
    assert set(models) == {'A', 'B'} and all(m.size == 36 for m in models.values())
    assert protected[0][0] == pytest.approx(62.75167785234899/30, abs=1e-12)
    assert protected[0][1] == protected[0][0]
    assert data['revision'] == requests.describe(URL)['revision']


@pytest.mark.parametrize('fault', ['revision', 'contact', 'actor', 'boolean_budget', 'reversed_knots'])
def test_stale_or_ambiguous_requests_are_rejected(fault):
    data = payload()
    if fault == 'revision': data['revision'] = '0'*64
    if fault == 'contact': data['protected_contact_ids'] = ['missing']
    if fault == 'actor': data['actors'].pop('B')
    if fault == 'boolean_budget': data['limit_degrees'] = True
    if fault == 'reversed_knots': data['knots_s'].reverse()
    with pytest.raises(ValueError):
        requests.compile_request(data)


def test_snapshots_preserve_reference_and_do_not_claim_a_finished_fit(tmp_path, monkeypatch):
    monkeypatch.setattr(requests, 'JOBS', tmp_path)
    data = payload(); output = tmp_path/'prepared'
    requests.prepare(data, output); record = read(output/'request.json')
    assert record['authored'] == data
    assert sha256(output/record['scene_snapshot']['path']) == record['scene_snapshot']['sha256']
    for actor in record['actors'].values():
        assert sha256(output/actor['path']) == actor['sha256']
    state = read(output/'state.json')
    assert state['status'] == 'prepared' and state['solver_executed'] is False and state['quality_approved'] is False
    with pytest.raises(ValueError, match='Fresh'):
        requests.prepare(data, output)
