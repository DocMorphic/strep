import copy
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from region_contact_objective import RegionObjective, RegionInequalities
from object_geometry import Geometry


def fixture(mode='stage_refresh', augmented=False):
    points = torch.tensor([[-.01,.55,-.01],[.01,.55,-.01],[0.,.55,.02],
                           [-.01,.5025,-.01],[.01,.5025,-.01],[0.,.5025,.02]], dtype=torch.float64)
    limits = dict(clearance_m=.002, contact_gap_m=.003, spacing_m=.006,
                  area_m2=.000025, centroid_error_m=.005, local_radius_m=.03, normal_degrees=10.)
    # Construct a single compiled contact record to isolate stage behavior.
    obj = object.__new__(RegionObjective)
    obj.records = [dict(frame=0, hand='LeftHand', ids=np.arange(10,16), faces=np.array([[3,5,4]]),
                       triple=np.array([0,1,2]), anchor=3, target=np.array([0.,.5,0.]),
                       desired_normal=np.array([0.,1.,0.]), geometry=Geometry('box',(1.,1.,1.)),
                       position=np.zeros(3), rotation=np.eye(3), limits=limits, anchor_tolerance=.03)]
    obj.selections = [dict(contact_id='left',frame=0,vertices=[10,11,12])]
    obj.reduction='balanced';obj.witness_mode=mode;obj.witness_history=[];obj.witness_stage=0;obj.last_points=None
    obj.inequalities=RegionInequalities([6]) if augmented else None
    obj.mapping={i:i-10 for i in range(10,16)}
    return obj, points


def test_refresh_uses_valid_patch_ids_improves_score_without_changing_authored_limits():
    obj, points = fixture()
    limits = copy.deepcopy(obj.records[0]['limits'])
    obj.initialize_witnesses(points[None])
    change=obj.witness_history[0]['changes'][0]
    assert set(change['new_vertices']) == {13,14,15}
    assert change['new_score'] < change['old_score'] and change['new_score'] == 0
    assert obj.records[0]['limits'] == limits
    obj.refresh_witnesses([points])
    assert obj.witness_history[-1]['changes'] == []


def test_loss_calls_do_not_reselect_during_line_search():
    obj, points = fixture()
    original=obj.records[0]['triple'].copy()
    obj.loss(points[None])
    np.testing.assert_array_equal(obj.records[0]['triple'], original)
    assert obj.witness_history == []
    obj.advance_stage(4)
    assert obj.witness_stage == 1 and len(obj.witness_history[-1]['changes']) == 1


def test_new_witness_resets_only_changed_semantic_multiplier_rows():
    obj, points = fixture(augmented=True)
    obj.inequalities.multipliers=[torch.arange(1,20,dtype=points.dtype)]
    before=obj.inequalities.multipliers[0].clone()
    obj.initialize_witnesses(points[None])
    after=obj.inequalities.multipliers[0]
    torch.testing.assert_close(after[:6],before[:6])
    assert after[6:17].count_nonzero() == 0
    torch.testing.assert_close(after[17:],before[17:])


def test_frozen_mode_keeps_original_selection():
    obj, points = fixture(mode='frozen')
    obj.initialize_witnesses(points[None]);obj.loss(points[None]);obj.advance_stage(4)
    assert obj.witness_history == []
    np.testing.assert_array_equal(obj.records[0]['triple'], [0,1,2])


def test_malformed_refresh_and_missing_accepted_pose_rejected():
    obj,_=fixture()
    with pytest.raises(ValueError):obj.refresh_witnesses([])
    with pytest.raises(ValueError):obj.advance_stage(4)


def test_reselection_uses_latest_accepted_pose_after_trial_evaluations():
    obj, accepted = fixture(augmented=True)
    trial = accepted.clone();trial[:3],trial[3:] = accepted[3:].clone(),accepted[:3].clone()
    obj.loss(trial[None])
    obj.loss(accepted[None])
    obj.advance_stage(4)
    assert set(obj.records[0]['ids'][obj.records[0]['triple']]) == {13,14,15}
    assert obj.inequalities.penalty == 800
    assert obj.inequalities.multipliers[0][6:17].count_nonzero() == 0


def test_solver_margin_tightens_target_without_mutating_acceptance():
    from support_contact_v8 import CONFIG,object_clearance_target
    acceptance=CONFIG['object_clearance_m']
    assert object_clearance_target(0) == acceptance
    assert object_clearance_target(.00005) == acceptance+.00005
    assert CONFIG['object_clearance_m'] == acceptance
    for invalid in [-.001,True,float('nan'),float('inf')]:
        with pytest.raises(ValueError):object_clearance_target(invalid)


def test_contact_gap_margin_preserves_authored_limits_and_rejects_empty_window():
    from region_contact_objective import solver_region_limits
    limits=dict(clearance_m=.002,contact_gap_m=.003)
    assert solver_region_limits(limits,0) == limits
    assert solver_region_limits(limits,.00001)['contact_gap_m'] == .003-.00001
    assert limits['contact_gap_m'] == .003
    for invalid in [-.001,True,float('nan'),.001,.002]:
        with pytest.raises(ValueError):solver_region_limits(limits,invalid)


def test_zero_margin_preserves_existing_zero_width_contact_window():
    from region_contact_objective import solver_region_limits
    limits=dict(clearance_m=.002,contact_gap_m=.002)
    assert solver_region_limits(limits,0) == limits
    with pytest.raises(ValueError):solver_region_limits(limits,.00001)
