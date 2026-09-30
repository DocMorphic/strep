import sys
from pathlib import Path
import numpy as np
import pytest
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from regional_pose_witness import reduced_region_residual,RegionalPoseProblem
from strep import read


@pytest.mark.parametrize('count',[3,17,256])
def test_patch_maximum_cannot_hide_a_single_penetrating_vertex(count):
    g=torch.full((count+13,),-2.,dtype=torch.float64,requires_grad=True)
    with torch.no_grad():g[count//2]=.001
    reduced=reduced_region_residual(g,count)
    assert len(reduced)==14 and reduced[0]==.001 and g.mean()<0
    assert (reduced<=0).all()==(g<=0).all()
    reduced[0].backward();expected=torch.zeros_like(g);expected[count//2]=1
    torch.testing.assert_close(g.grad,expected)
    with torch.no_grad():g[count//2]=-.001;g[-1]=.2
    assert reduced_region_residual(g,count)[-1]==.2


@pytest.mark.parametrize('count,shape',[(True,16),(2,15),(3,17),(17,29)])
def test_invalid_residual_layout_is_rejected(count,shape):
    with pytest.raises(ValueError):reduced_region_residual(torch.zeros(shape),count)


@pytest.fixture(scope='module')
def problem():
    return RegionalPoseProblem(ROOT/'reports/scene-region-jobs/cylinder-contact-v1/fit',96)


def test_native_seed_replays_saved_export_audit_without_approving_failed_pose(problem):
    expected=read(ROOT/'reports/scene-region-jobs/cylinder-contact-v1/audit/verification.json')['variants']['candidate']['rows'][96*4]
    actual,motion=problem.independent(problem.seed)
    assert actual['bounds_passed'] and not actual['pose_witness_passed']
    assert len(actual['contacts'])==2
    assert abs(actual['minimum_floor_m']-expected['minimum_floor_m'])<2e-6
    assert abs(actual['objects'][0]['minimum_clearance_m']-expected['object_clearances_m']['can'])<2e-6
    for a,e in zip(actual['contacts'],expected['contacts']):
        assert a['id']==e['contact_id']
        assert abs(a['anchor_error_m']-e['anchor_error_m'])<2e-6
        assert abs(a['minimum_region_clearance_m']-e['minimum_region_clearance_m'])<2e-6
        assert a['all_conditions_passed']==e['all_conditions_passed']
    np.testing.assert_array_equal(motion['root_positions'][:,[0,2]],problem.base['root_positions'][96:97,[0,2]])
    np.testing.assert_array_equal(motion['foot_contacts'],problem.base['foot_contacts'][96:97])


def test_independent_acceptance_rejects_out_of_budget_root_and_rotation(problem):
    x=problem.seed.copy();x[-1]=problem.config['max_root_lift_m']+.001
    audit,_=problem.independent(x)
    assert not audit['bounds_passed'] and not audit['pose_witness_passed']
    x=problem.seed.copy();x[:3]=problem.limits[0]*np.array([.9,.9,0])
    audit,_=problem.independent(x)
    assert not audit['bounds_passed'] and not audit['pose_witness_passed']


@pytest.mark.parametrize('frame',[True,-1,180,96.25])
def test_pose_probe_rejects_non_native_or_outside_frame(frame):
    with pytest.raises(ValueError,match='Native integer frame'):
        RegionalPoseProblem(ROOT/'reports/scene-region-jobs/cylinder-contact-v1/fit',frame)
