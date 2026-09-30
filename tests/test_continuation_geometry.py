import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_scene_pair_continuation as audit
from strep import save,sha256


@pytest.mark.parametrize('peak,cap,floor,reasons',[
    (.021,0.,0.,[]),(.02255,0.,0.,['no_improvement_over_previous_correction']),
    (.022522,0.,0.,['no_improvement_over_previous_correction']),
    (.021,2e-6,0.,['fresh_surface_caps']),(.021,0.,2e-6,['floor_regression'])])
def test_local_acceptance_requires_improvement_over_previous_not_only_raw(peak,cap,floor,reasons):
    geometry=dict(source_peak_m=.022569,candidate_peak_m=peak,maximum_cap_excess_m=cap,maximum_floor_increase_m=floor)
    assert audit.improvement_reasons(geometry,.022522)==reasons


@pytest.mark.parametrize('fault',[None,'failed_trial','failed_replay','angular','positional','identity','unbound'])
def test_geometry_requires_matching_independent_passing_replay(tmp_path,monkeypatch,fault):
    study=tmp_path/'study';study.mkdir();replay=tmp_path/'replay';replay.mkdir()
    artifact=study/'bound.json';save(artifact,dict(example=True));files={str(artifact):sha256(artifact)}
    trial=dict(factor=.5,preliminary_pass=True,reasons=[],actors=[dict(actor=n) for n in ['A','B']])
    review=dict(trial=0,factor=.5,preliminary_pass=True,reasons=[],actors=[dict(actor=n,
        exact_export_reconstruction=True,positional=dict(failures=0),
        angular={k:dict(exceeding_observations=0,tolerance=1e-5) for k in ['angular_speed_rad_s','angular_acceleration_rad_s2']}) for n in ['A','B']])
    if fault=='failed_trial':trial['reasons']=['failed']
    if fault=='failed_replay':review['reasons']=['failed']
    if fault=='angular':review['actors'][1]['angular']['angular_speed_rad_s']['exceeding_observations']=1
    if fault=='positional':review['actors'][0]['positional']['failures']=1
    if fault=='identity':review['actors'].reverse()
    save(replay/'request.json',dict(study=str(study),inputs={} if fault=='unbound' else files,implementation={}))
    save(replay/'reviews.json',[review])
    save(replay/'verification.json',dict(status='complete',request_sha256=sha256(replay/'request.json'),reviews_sha256=sha256(replay/'reviews.json')))
    monkeypatch.setattr(audit,'load_continuation',lambda _: ({}, {}, [trial],dict(files)))
    monkeypatch.setattr(audit,'parent_trial',lambda _: dict(previous=True))
    if fault is None:assert audit.reviewed_trial(study,replay,0)[1]==trial
    else:
        with pytest.raises(ValueError):audit.reviewed_trial(study,replay,0)
