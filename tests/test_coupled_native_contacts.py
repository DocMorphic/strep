"""Every gate remains necessary when surface objectives improve."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_native_contacts import CoupledContactModel,acceptable
from native_contact_norms import ContactNorms
from native_scene_norms import rows
from test_native_contact_norms import prepared


@pytest.mark.parametrize('fault',['native','previous-native','passing-contact','failing-contact','geometry','missing-geometry','unchanged','worst-contact'])
def test_each_retention_gate_rejects_regression_or_missing_measurements(fault):
    native=np.array([-1.,0.]);after_native=native.copy();before=np.array([2.,.1,-1.]);after=np.array([1.9,.05,-.1]);geometry=dict(sampled_conditions_pass=True)
    if fault=='native':after_native[0]=1e-12
    if fault=='previous-native':native[0]=1e-12
    if fault=='passing-contact':after[2]=1e-12
    if fault=='failing-contact':after[1]=.10000001
    if fault=='geometry':geometry['sampled_conditions_pass']=False
    if fault=='missing-geometry':geometry=None
    if fault=='unchanged':after=before.copy()
    if fault=='worst-contact':after[0]=2.01
    assert not acceptable(native,after_native,before,after,geometry)


def test_strictly_improving_contacts_with_complete_native_and_geometry_pass_can_be_retained():
    assert acceptable([-1.,0.],[-.5,0.],[2.,.1,-1.],[1.9,.05,-.1],dict(sampled_conditions_pass=True))


@pytest.mark.parametrize('fault',['shape','nan','empty','broadcast'])
def test_incomplete_condition_populations_reject(fault):
    before=np.array([1.,-1.]);after=before.copy()
    if fault=='shape':after=after[:1]
    if fault=='nan':after[0]=float('nan')
    if fault=='empty':before=after=np.array([])
    if fault=='broadcast':after=after[None]
    with pytest.raises(ValueError):acceptable([-1.],[-1.],before,after,dict(sampled_conditions_pass=True))


def test_full_model_retains_native_rows_authored_contact_suffix_and_individual_guards(tmp_path):
    problem,p,digest=prepared(tmp_path,hold=True);model=CoupledContactModel(problem,p,digest)
    value=problem.initial.copy();worlds=problem.worlds(value)
    native=rows(problem,value,worlds);contact=ContactNorms(problem,p,digest).residual(worlds)
    system,jac,identity=model.linearize(value,worlds,.02,step=1e-4)
    count=len(native.caps);assert identity['hard_rows']==count+len(contact)
    np.testing.assert_array_equal(system.caps[:count],native.caps);np.testing.assert_array_equal(system.scales[:count],native.scales)
    np.testing.assert_allclose(system.residual()[:count],problem.constraints(value,worlds),atol=1e-9,rtol=0)
    np.testing.assert_allclose(system.residual()[count:count+len(contact)],np.minimum(contact,0),atol=1e-9,rtol=0)
    np.testing.assert_allclose(system.residual()[-len(contact):],contact,atol=1e-9,rtol=0)
    assert jac.shape==(3*len(system.caps),problem.size)
    assert identity['all_native_contact_positions_and_frame_speeds_protected'] and identity['source_caps_unchanged']
    assert identity['independent_decode_and_full_geometry_required'] and not identity['release_approved']


@pytest.mark.parametrize('fault',['cap','tolerance','dt','uniform'])
def test_source_rate_reset_or_sampling_changes_reject(tmp_path,fault):
    problem,p,digest=prepared(tmp_path);model=CoupledContactModel(problem,p,digest)
    if fault=='cap':problem.caps['A'].caps[0][0,0]+=1e-8
    if fault=='tolerance':problem.caps['A'].tolerance+=1e-8
    if fault=='dt':problem.caps['A'].dt+=1e-8
    if fault=='uniform':problem.uniform[1]+=1e-8
    with pytest.raises(ValueError,match='source-rate'):model.check_caps()


def test_already_failed_native_start_cannot_enter_improvement_model(tmp_path):
    problem,p,digest=prepared(tmp_path);model=CoupledContactModel(problem,p,digest)
    value=problem.initial.copy();value[:]=.5
    with pytest.raises(ValueError,match='feasible'):model.linearize(value,problem.worlds(value),.02)
