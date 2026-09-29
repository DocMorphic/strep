import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from study_breadth_peak_restore import select_cases,PeakProblem,root_metrics
from verify_authored_root_correction import samples


def population():
    return dict(cases=[dict(id=str(i)) for i in range(24)]),dict(rows=[dict(id=str(i),status='candidate_preserved',original_root_peak_recovered=i%3==0) for i in range(24)])


def test_selection_keeps_every_failure_and_order():
    request,summary=population();selected=select_cases(request,summary)
    assert [c['id'] for c in selected]==[str(i) for i in range(24) if i%3]
    selected[0]['id']='edited';assert request['cases'][1]['id']=='1'


@pytest.mark.parametrize('kind',['missing','duplicate','failed','unknown'])
def test_selection_rejects_ambiguous_evidence(kind):
    request,summary=population()
    if kind=='missing':summary['rows'].pop()
    if kind=='duplicate':request['cases'][1]['id']='0';summary['rows'][1]['id']='0'
    if kind=='failed':summary['rows'][0]['status']='failed'
    if kind=='unknown':summary['rows'][0]['original_root_peak_recovered']=None
    with pytest.raises(ValueError):select_cases(request,summary)


def test_peak_cap_comes_from_original_raw_export():
    parent=ROOT/'reports/breadth-root-cleanup-v1'
    if not parent.exists():pytest.skip('Provisioned completed breadth fixtures required')
    request=read(parent/'request.json');case=request['cases'][1];folder=parent/'takes'/case['id']
    problem=PeakProblem(folder,case,request['policy']);norms=[]
    counts=problem.additional_constraints(lambda *_:None,lambda v,m,c:norms.append((v,m,c)),lambda *_:None)
    _,raw=samples(folder/'input/character.glb',problem.frames)
    expected=np.linalg.norm((raw[4::2,problem.root,:3,3]-2*raw[2:-2:2,problem.root,:3,3]+raw[:-4:2,problem.root,:3,3])*900,axis=1).max()
    caps=norms[-(problem.frames-2):]
    assert len(caps)==counts['peak_constraints']==problem.frames-2
    assert all(abs(cap-expected)<1e-12 for _,_,cap in caps)
    assert max(np.linalg.norm(v)-cap for v,_,cap in caps)>1
    measured=root_metrics(folder/'input/character.glb',problem.frames,problem.root)
    assert abs(measured['peak_m_s2']-expected)<1e-12
    assert 1<=measured['peak_center_frame']<problem.frames-1
