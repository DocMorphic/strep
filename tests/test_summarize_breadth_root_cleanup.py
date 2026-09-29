import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read,save,sha256
from summarize_breadth_root_cleanup import run


def refresh(study):
    request=read(study/'request.json');rows=read(study/'results.json')['rows']
    save(study/'freeze.json',dict(request_sha256=sha256(study/'request.json')))
    save(study/'completion.json',dict(request_sha256=sha256(study/'request.json'),results_sha256=sha256(study/'results.json'),engine_sha256=sha256(study/'engine/verification.json'),engine_actor_frames=24*3,selected_candidates=0,failed=0))


@pytest.fixture
def study(tmp_path):
    study=tmp_path/'study';study.mkdir();cases=[];rows=[];engine=[];manifest=[]
    for i in range(24):
        name='case-'+str(i);folder=study/'takes'/name/'candidate';folder.mkdir(parents=True);path=folder/'character.glb';path.write_bytes(b'fixture-'+str(i).encode());digest=sha256(path)
        cases.append(dict(id=name,action='fixture',family='fixture',rig='fixture',seed=1301,frames=3,files={'candidate/character.glb':digest},original_root_peak_m_s2=1.,prior_root_peak_m_s2=2.))
        rows.append(dict(id=name,status='no_solver_proposal',selected=str(path),selected_sha256=digest))
        engine.append(dict(id=name,source_sha256=digest,frames=3));manifest.append(dict(id=name,path=str(path),sha256=digest,frames=3))
    save(study/'request.json',dict(cases=cases,implementation={},policy=dict(acceleration_tolerance_m_s2=.0036)))
    save(study/'results.json',dict(rows=rows));save(study/'manifest.json',dict(cases=manifest));save(study/'engine/verification.json',dict(checks=engine));save(study/'pipeline.json',dict(status='complete'));refresh(study)
    return study


def test_no_proposal_is_retained_without_quality_promotion(study,tmp_path):
    result=run(study,tmp_path/'summary')
    assert result['population']==24 and result['status_counts']=={'no_solver_proposal':24}
    assert result['engine_actor_frames']==72 and result['original_root_peak_recovered']==0
    assert not result['quality_approved']


@pytest.mark.parametrize('kind',['missing','export','engine','promotion'])
def test_inconsistent_evidence_is_rejected(study,tmp_path,kind):
    if kind=='missing':
        data=read(study/'results.json');data['rows'].pop();save(study/'results.json',data);refresh(study)
    elif kind=='export':(study/'takes/case-0/candidate/character.glb').write_bytes(b'changed')
    elif kind=='engine':
        data=read(study/'engine/verification.json');data['checks'][0]['source_sha256']='wrong';save(study/'engine/verification.json',data);refresh(study)
    else:
        data=read(study/'results.json');data['rows'][0].update(status='candidate_preserved',attempts=0,last_audit={});save(study/'results.json',data);refresh(study);save(study/'takes/case-0/attempts.json',[])
    with pytest.raises((ValueError,IndexError)):run(study,tmp_path/'summary')
