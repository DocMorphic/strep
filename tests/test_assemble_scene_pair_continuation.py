import copy
import sys
import shutil
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import assemble_scene_pair_continuation as assembly
from strep import read,save,sha256


def test_normalization_never_approves_unaudited_trials_or_rebases_controls():
    trials=[dict(factor=f,controls=[.01+f*.001,0.,0.],actors=[],bounds={},angular_rates=[],preliminary_pass=True,reasons=[]) for f in [1.,.5,.25]]
    trials[0].update(preliminary_pass=False,reasons=['exported_motion'])
    original=copy.deepcopy(trials);rows=assembly.normalized_trials(trials,1,dict(candidate_peak_m=.02))
    assert rows[0]['reasons']==['exported_motion']
    assert rows[1]['accepted_local_step'] and rows[1]['folder']=='candidate'
    assert rows[2]['reasons']==['full_geometry_not_evaluated'] and not rows[2]['accepted_local_step']
    assert rows[1]['controls']==trials[1]['controls'] and trials==original
    assert all(not r['quality_approved'] for r in rows)
    with pytest.raises(ValueError):assembly.normalized_trials(trials,0,{})


def fixture(root,monkeypatch):
    from test_assemble_scene_pair_reserve import fixture as old_fixture
    parent,study,geometry=old_fixture(root)
    protocol=read(parent/'request.json');protocol['curve_actors']=[dict(fixture=True)];save(parent/'request.json',protocol)
    shutil.copyfile(study/'margins.npz',parent/'margins.npz')
    result=read(parent/'result.json');result.update(request_sha256=sha256(parent/'request.json'),margins_sha256=sha256(parent/'margins.npz'));save(parent/'result.json',result)
    # Different tangent matrix: it must not overwrite source replay's zero model.
    np.savez(study/'linearization.npz',gaps=np.array([-.0195]),radii=np.array([.9]))
    trials=read(study/'trials.json')
    for t in trials:
        t['bounds']=t.pop('bound');t['preliminary_pass']=t.pop('preliminary_checks_pass')
        t['angular_rates']=[dict(actor=a['actor'],rates=a['angular']) for a in t.pop('motion_reviews')]
        t['controls']=[.01,.02,.03]
    save(study/'trials.json',trials)
    save(study/'solver.json',dict(increment=[.001,.002,.003]))
    request=dict(study=str(parent),cumulative_controls=[.009,.018,.027],incremental_trust_degrees=.5,scale=.025,regularizer=5e-8)
    baseline=dict(geometry=dict(candidate_peak_m=.0195))
    monkeypatch.setattr(assembly,'reviewed_trial',lambda *args: (request,trials[0],baseline,{}))
    grequest=read(geometry/'request.json');grequest.update(study=str(study),replay=str(root/'replay'),previous_peak_m=.0195)
    save(geometry/'request.json',grequest)
    gresult=read(geometry/'result.json');gresult.update(request_sha256=sha256(geometry/'request.json'),previous_peak_m=.0195,improvement_over_previous_m=.0005)
    save(geometry/'result.json',gresult)
    return parent,study,geometry


def test_packaging_keeps_source_and_nonzero_proposal_matrices_separate(tmp_path,monkeypatch):
    parent,study,geometry=fixture(tmp_path,monkeypatch);output=tmp_path/'out';assembly.run(geometry,output)
    result=read(output/'result.json');request=read(output/'request.json')
    assert result['selected']=='candidate' and not result['quality_approved']
    assert sha256(output/'linearization.npz')==sha256(parent/'linearization.npz')
    assert sha256(output/'proposal-linearization.npz')==sha256(study/'linearization.npz')
    assert request['assembly']['solver_kind']=='increment_from_cumulative_base'
    assert read(output/'trials.json')[0]['controls']==[.01,.02,.03]
    assert sha256(output/'candidate/actor-0.glb')==sha256(study/'trial-0/actor-0.glb')
    assert request['trust_degrees']==.5
    with pytest.raises(ValueError):assembly.run(geometry,output)


@pytest.mark.parametrize('fault',['incomplete','rejected','previous_peak','gain','geometry','manifest_clip'])
def test_inconsistent_geometry_never_creates_completed_package(tmp_path,monkeypatch,fault):
    _,_,geometry=fixture(tmp_path,monkeypatch);result=read(geometry/'result.json')
    if fault=='incomplete':result['status']='processing'
    if fault=='rejected':result['accepted_local_step']=False
    if fault=='previous_peak':result['previous_peak_m']=.021
    if fault=='gain':result['improvement_over_previous_m']=.002
    if fault=='geometry':save(geometry/'geometry.json',[])
    if fault=='manifest_clip':(geometry/'candidate-actor-0.glb').write_bytes(b'changed')
    save(geometry/'result.json',result)
    output=tmp_path/'out'
    with pytest.raises(ValueError):assembly.run(geometry,output)
    assert not (output/'result.json').exists()
