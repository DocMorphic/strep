"""Independent clock/geometry/rate fixtures; no model or renderer required."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from engine_contact_sampling import (contract,contract_sha256,frame_populations,frame_speed,point_limits,evaluate)


def fixture(stance=(.1,.9)):
    populations=frame_populations(stance)
    times=np.unique(np.concatenate([np.asarray(stance),*(p['times_s'] for p in populations)]))
    points=np.zeros((len(times),1,3));points[:,:,1]=.001
    anchor=np.array([[0,.001,0.]])
    limits=dict(anchor_m=1.,clearance_m=.00025,maximum_gap_m=.005,speed_m_s=.005)
    return populations,times,points,anchor,limits


def audited(populations,times,points,anchor,limits,ids=None):
    if ids is None:ids=np.arange(len(times))
    return evaluate(points,anchor,[0,1,0],0,[0],ids,populations,times,limits)


def test_all_twelve_clocks_declared_before_results_and_stable():
    populations=frame_populations([0,1])
    assert len(populations)==12
    assert [(p['rate_hz'],p['phase_offset_frames']) for p in populations]==[(r,q) for r in (30,60,120) for q in (0.,.25,.5,.75)]
    for p in populations:
        assert np.diff(p['tick_indices']).tolist()==[1]*(len(p['times_s'])-1)
        assert np.allclose(np.diff(p['times_s']),1/p['rate_hz'],rtol=0,atol=2e-16)
    digest=contract_sha256();c=contract();c['rates_hz'][:]=[1]
    assert contract()['rates_hz']==[30,60,120] and contract_sha256()==digest


def test_tiny_endpoint_not_inserted_into_a_frame_velocity_clock():
    a,b=1.600000023841858,2.4000000953674316
    for p in frame_populations([a,b]):
        assert p['times_s'][0]>=a and p['times_s'][-1]<=b
        assert np.diff(p['times_s']).min()>1/121
        assert b not in p['times_s']


@pytest.mark.parametrize('stance',[[1,0],[-1,0],[0,31],[0,float('nan')],[0],[0,0]])
def test_invalid_stance_rejected(stance):
    with pytest.raises(ValueError):frame_populations(stance)


def test_linear_slip_has_same_speed_across_rates_and_phases():
    p,t,x,a,limits=fixture();x[:,0,0]=.004*(t-t[0])
    found=audited(p,t,x,a,limits)
    assert found['passed'] and not found['continuous_contact_certified'] and not found['quality_approved']
    assert all(row['maximum_speed_m_s']==pytest.approx(.004,abs=2e-16) for row in found['populations'])


def test_strict_speed_overlimit_retained_across_populations():
    p,t,x,a,limits=fixture();x[:,0,0]=.005000000001*(t-t[0])
    found=audited(p,t,x,a,limits)
    assert not found['passed'] and all(not row['passed'] for row in found['populations'])


def test_endpoint_position_is_checked_even_without_a_frame_velocity_pair():
    p,t,x,a,limits=fixture();x[-1,0,1]=-.001
    found=audited(p,t,x,a,limits)
    assert all(row['passed'] for row in found['populations'])
    assert found['points']['minimum_region_height_m']==-.001 and not found['passed']


def test_source_anchor_not_replaced_by_candidate_start():
    p,t,x,a,limits=fixture();limits['anchor_m']=.001;x[:,:,0]=.002
    found=audited(p,t,x,a,limits)
    assert all(row['passed'] for row in found['populations'])
    assert found['points']['maximum_patch_anchor_error_m']==.002 and not found['passed']


def test_short_contact_reports_unavailable_never_fallback_or_pass():
    p,t,x,a,limits=fixture((.50001,.50002))
    found=audited(p,t,x,a,limits)
    assert found['points']['passed'] and not found['passed']
    assert all(not row['available'] and row['maximum_speed_m_s'] is None for row in found['populations'])


def test_phase_failure_cannot_be_hidden_by_other_passes():
    p,t,x,a,limits=fixture()
    clock=p[-1]['times_s'];time=clock[len(clock)//2]
    x[np.searchsorted(t,time),0,0]=.0001
    found=audited(p,t,x,a,limits)
    assert any(row['passed'] for row in found['populations'])
    assert not found['populations'][-1]['passed'] and not found['passed']


@pytest.mark.parametrize('fault',['missing_population','missing_frame','omitted_geometry','changed_ticks','changed_phase','nonfinite'])
def test_invalid_or_incomplete_populations_rejected(fault):
    p,t,x,a,limits=fixture();ids=None
    if fault=='missing_population':p=p[:-1]
    if fault=='missing_frame':
        k=np.searchsorted(t,p[-1]['times_s'][1]);t=np.delete(t,k);x=np.delete(x,k,axis=0)
    if fault=='omitted_geometry':ids=np.arange(2,len(t))
    if fault=='changed_ticks':p[-1]['tick_indices'][1]+=1
    if fault=='changed_phase':p[-1]['phase_offset_frames']=.125
    if fault=='nonfinite':x[0,0,0]=float('nan')
    with pytest.raises(ValueError):audited(p,t,x,a,limits,ids=ids)


def test_nanoscale_endpoint_jitter_is_geometry_not_a_game_frame_derivative():
    p,t,x,a,limits=fixture((1.600000023841858,2.4000000953674316))
    x[-1,0,0]=2e-8
    found=audited(p,t,x,a,limits)
    assert found['passed'] and found['points']['maximum_patch_anchor_error_m']==2e-8
    assert all(row['maximum_speed_m_s']==0 for row in found['populations'])


def test_reordered_bone_palette_preserves_imported_skin_function():
    from native_engine_contacts import imported_bindings,imported_world
    from test_native_engine_contacts import gd_matrix
    data=dict(bone_names=['other','root'],meshes=[dict(node='mesh',surface=0,
        positions=[[1,2,3]],weights=[1,0,0,0],bones=[0,0,0,0],binds=[dict(bone=1,pose=gd_matrix())])],
        frames=[dict(requested_time_s=0.,actual_time_s=0.,bones=[gd_matrix(),gd_matrix()],
        skeleton_world=gd_matrix(),mesh_world=[dict(node='mesh',matrix=gd_matrix())])])
    data['frames'][0]['bones'][1][3]=[2,0,0]
    bound,_,order=imported_bindings(data,['root','other']);world=imported_world(data,[0],order)
    assert order.tolist()==[1,0]
    found=np.einsum('tbij,vbj->tvi',world[:,:,:3,:],bound)
    assert np.array_equal(found,[[[3,2,3]]])
