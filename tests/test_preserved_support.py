import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_contact_v8 import select_inferred_supports
from support_contact_v8 import normalized_support_residual
from audit_scene_preserved_support import sample_target, summarize


def contact():
    return dict(active=np.array([True,True,False]),vertex_ids=np.array([4,4,5]),
                targets=np.array([[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]]))


def test_selection_preserves_authored_intent_and_rejects_empty_support():
    rows={'foot':contact(),'hand':{**contact(),'provenance':'explicit'},'disabled':{**contact(),'provenance':'disabled'},
          'air':{**contact(),'active':np.zeros(3,bool)}}
    assert select_inferred_supports(rows,['foot'])==[True,False,False,False]
    for names in [['hand'],['disabled'],['air'],['unknown'],['foot','foot'],'foot',[1]]:
        with pytest.raises(ValueError):select_inferred_supports(rows,names)
    assert select_inferred_supports(rows,[])==[False]*4


def test_normalization_preserves_feasible_set_and_is_unit_invariant():
    g=torch.tensor([-.001,0.,.002],dtype=torch.float64,requires_grad=True)
    normalized=normalized_support_residual(g,.005)
    assert torch.equal(normalized<=0,g<=0)
    torch.testing.assert_close(normalized,normalized_support_residual(g*1000,5.))
    normalized.sum().backward();torch.testing.assert_close(g.grad,torch.full_like(g,200.))
    for scale in [0.,-1.,float('nan')]:
        with pytest.raises(ValueError):normalized_support_residual(g,scale)


def test_audit_interpolates_fixed_material_point_only():
    row=contact();point,reason=sample_target(row,.5)
    assert point[0]==4 and reason is None
    np.testing.assert_array_equal(point[1],[.5,0,0])
    assert sample_target(row,1.5)[1]=='outside_active_interval'
    row['vertex_ids'][1]=5
    assert sample_target(row,.5)[1]=='vertex_identity_changes'
    assert sample_target(row,1)[0][0]==5


def test_drift_and_missing_material_coverage_cannot_pass():
    assert summarize([dict(error_m=.004)],[])['sampled_point_preservation_passed']
    assert not summarize([dict(error_m=.006)],[])['sampled_point_preservation_passed']
    assert not summarize([],[])['sampled_point_preservation_passed']
    assert not summarize([dict(error_m=.001)],[dict(reason='vertex_identity_changes')])['sampled_point_preservation_passed']


def test_publisher_requires_matching_support_evidence_and_keeps_failure():
    from package_scene_fit_review import support_assessment
    rows=[dict(error_m=.08)];candidate=dict(**summarize(rows,[]),rows=rows,skipped=[])
    report=dict(result_sha256='fit',regions=['foot'],requested_by_fit=['foot'],tolerance_m=.005,variants=dict(candidate=candidate))
    assert not support_assessment(report,['foot'],'fit')['sampled_point_preservation_passed']
    for bad in [None,{**report,'result_sha256':'other'},{**report,'regions':['hand']},{**report,'tolerance_m':.1}]:
        with pytest.raises(ValueError):support_assessment(bad,['foot'],'fit')
    candidate['sampled_point_preservation_passed']=True
    with pytest.raises(ValueError,match='summary'):support_assessment(report,['foot'],'fit')
    for value in [float('nan'),float('inf'),-.1]:
        candidate['rows'][0]['error_m']=value
        with pytest.raises(ValueError,match='finite'):support_assessment(report,['foot'],'fit')
