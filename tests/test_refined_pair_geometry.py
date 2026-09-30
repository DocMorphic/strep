import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_refined_pair_geometry import selected_trial
from strep import save, sha256, read


def fixture(root):
    folder = root/'trial-0'; folder.mkdir()
    actors = []
    for i in range(2):
        path = folder/f'actor-{i}.glb'; path.write_bytes(b'fixture'+bytes([i]))
        actors.append(dict(actor=str(i), path=path.name, sha256=sha256(path), preserved=True, rate_failures=0))
    trial = dict(actors=actors, preliminary_checks_pass=True, retained_surface=dict(cap=0., distance=0.),
        independent_rates=[dict(actor=str(i), failures=0) for i in range(2)])
    save(folder/'review.json', trial); save(root/'trials.json', [trial]); save(root/'request.json', {})
    save(root/'result.json', dict(status='complete', request_sha256=sha256(root/'request.json'), trials_sha256=sha256(root/'trials.json')))
    return trial


def test_exact_passing_review_can_enter_fresh_geometry_audit(tmp_path):
    trial = fixture(tmp_path)
    assert selected_trial(tmp_path, 0)[1] == trial
    with pytest.raises(ValueError): selected_trial(tmp_path, 1)
    with pytest.raises(ValueError): selected_trial(tmp_path, -1)


@pytest.mark.parametrize('fault', ['clip', 'incomplete', 'record', 'rate', 'independent', 'surface', 'nan', 'preservation', 'actor_order', 'escape'])
def test_failed_or_changed_trial_cannot_enter_geometry_audit(tmp_path, fault):
    trial = fixture(tmp_path)
    if fault == 'clip': (tmp_path/'trial-0/actor-0.glb').write_bytes(b'changed')
    elif fault == 'incomplete':
        result = read(tmp_path/'result.json'); result['status'] = 'processing'; save(tmp_path/'result.json', result)
    elif fault == 'record': save(tmp_path/'trial-0/review.json', {})
    else:
        if fault == 'rate': trial['actors'][0]['rate_failures'] = 1
        if fault == 'independent': trial['independent_rates'][1]['failures'] = 1
        if fault == 'surface': trial['retained_surface']['cap'] = 2e-6
        if fault == 'nan': trial['retained_surface']['cap'] = 'not a number'
        if fault == 'preservation': trial['actors'][0]['preserved'] = False
        if fault == 'actor_order': trial['independent_rates'].reverse()
        if fault == 'escape': trial['actors'][0]['path'] = '../actor-0.glb'
        save(tmp_path/'trials.json', [trial]); save(tmp_path/'trial-0/review.json', trial)
        result = read(tmp_path/'result.json'); result['trials_sha256'] = sha256(tmp_path/'trials.json'); save(tmp_path/'result.json', result)
    with pytest.raises((ValueError, TypeError)): selected_trial(tmp_path, 0)
