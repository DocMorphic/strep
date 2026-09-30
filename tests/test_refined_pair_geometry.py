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


@pytest.mark.parametrize('fault', [None, 'angular_failure', 'angular_tolerance', 'angular_missing', 'reasons'])
def test_reserve_candidate_requires_both_motion_policies(tmp_path, fault):
    trial = fixture(tmp_path)
    trial['bound'] = trial.pop('retained_surface')
    trial['motion_reviews'] = [dict(actor=r['actor'], positional=dict(failures=0),
        angular={k:dict(exceeding_observations=0, tolerance=1e-5) for k in ['angular_speed_rad_s', 'angular_acceleration_rad_s2']}) for r in trial.pop('independent_rates')]
    trial['reasons'] = []
    angular = trial['motion_reviews'][0]['angular']
    if fault == 'angular_failure': angular['angular_acceleration_rad_s2']['exceeding_observations'] = 1
    if fault == 'angular_tolerance': angular['angular_speed_rad_s']['tolerance'] = .1
    if fault == 'angular_missing': angular.pop('angular_speed_rad_s')
    if fault == 'reasons': trial['reasons'] = ['failed']
    save(tmp_path/'trials.json', [trial]); save(tmp_path/'trial-0/review.json', trial)
    result = read(tmp_path/'result.json'); result['trials_sha256'] = sha256(tmp_path/'trials.json'); save(tmp_path/'result.json', result)
    if fault is None: assert selected_trial(tmp_path, 0)[1] == trial
    else:
        with pytest.raises(ValueError): selected_trial(tmp_path, 0)


@pytest.mark.parametrize('fault',[None,'missing','failed','clock_tolerance'])
def test_angular_refinement_requires_complete_passing_rotation_review(tmp_path,fault):
    trial=fixture(tmp_path)
    trial['angular_rates']=[dict(actor=a['actor'],rates={k:dict(exceeding_observations=0,tolerance=1e-5) for k in ['angular_speed_rad_s','angular_acceleration_rad_s2']}) for a in trial['actors']]
    if fault=='missing':trial['angular_rates'].pop()
    if fault=='failed':trial['angular_rates'][0]['rates']['angular_speed_rad_s']['exceeding_observations']=1
    if fault=='clock_tolerance':trial['angular_rates'][0]['rates']['angular_acceleration_rad_s2']['tolerance']=.1
    save(tmp_path/'request.json',dict(angular_motion=True));save(tmp_path/'trials.json',[trial]);save(tmp_path/'trial-0/review.json',trial)
    result=read(tmp_path/'result.json');result.update(request_sha256=sha256(tmp_path/'request.json'),trials_sha256=sha256(tmp_path/'trials.json'));save(tmp_path/'result.json',result)
    if fault is None:assert selected_trial(tmp_path,0)[1]==trial
    else:
        with pytest.raises(ValueError):selected_trial(tmp_path,0)
