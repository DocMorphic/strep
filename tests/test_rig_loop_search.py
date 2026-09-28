import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from rig_loop_search import validate,measure,mesh_diagnostics,ROLES


def request():
    frozen=read(ROOT/'reports/rig-jobs/20260926-213335-362828ae/loop.json')
    return dict(schema='strep-cycle-search-v1',**{k:frozen[k] for k in ('job','variant','glb_sha256','root_mode','blend_frames','turn_degrees')},start_min=0,start_max=30,period_min=30,period_max=90,stride=5)


@pytest.mark.parametrize('fault',['hash','float','negative','oversize','empty','turn','root'])
def test_rejects_invalid_search(fault):
    p=request()
    if fault=='hash':p['glb_sha256']='0'*64
    if fault=='float':p['stride']=1.5
    if fault=='negative':p['start_min']=-1
    if fault=='oversize':p['stride']=1
    if fault=='empty':p.update(start_min=110,start_max=110)
    if fault=='turn':p['turn_degrees']=float('nan')
    if fault=='root':p['root_mode']='drifting'
    with pytest.raises(ValueError):validate(p)


def test_candidate_grid_is_bounded_and_never_reads_beyond_continuation():
    snap,pairs=validate(request());assert len(pairs)==88
    assert all(a+p+8<=snap[3]['frames'] for a,p in pairs)


def test_periodic_motion_ranks_above_phase_mismatch_and_unknown_is_not_zero():
    rig=SimpleNamespace(parents=[-1,0],joints=[1]);raw=np.tile(np.eye(4),(80,2,1,1))
    raw[:,1,:3,:3]=Rotation.from_euler('x',.4*np.sin(np.arange(80)*2*np.pi/30)).as_matrix()
    masks={r:np.arange(80)%30<15 for r in ROLES}
    base=dict(start_frame=0,blend_frames=8,turn_degrees=0,root_mode='in_place')
    good,_,_=measure(rig,0,raw[:38],dict(base,period_frames=30),masks,'source_model_predictions')
    bad,_,_=measure(rig,0,raw[:32],dict(base,period_frames=24),masks,'source_model_predictions')
    assert good['score']<bad['score'];assert good['metrics']['pose_gap_max_deg']<1e-10
    assert good['metrics']['predicted_support_disagreement_fraction']==0
    unknown,_,_=measure(rig,0,raw[:38],dict(base,period_frames=30),masks,'none_supplied')
    assert unknown['metrics']['predicted_support_disagreement_fraction'] is None


def test_partial_blend_contacts_are_included_in_patch_sliding():
    rig=SimpleNamespace(vertices=lambda world:world[:,:3,3]);single=np.tile(np.eye(4),(11,1,1,1));single[:,0,0,3]=np.arange(11)*.001
    recipe=dict(start_frame=0,period_frames=10,blend_frames=4)
    # Only the ending continuation is annotated; frames 1 and 2 carry partial weights.
    result=mesh_diagnostics(rig,single,np.array([0,.2,.8,1.]),recipe,[dict(vertices=[0],frames=[10,11,12])])
    assert result['measured_patch_velocity_steps']==2
    assert result['any_weight_authored_patch_speed_p95_m_s']==pytest.approx(.03)


def test_unknown_predictions_survive_authored_timeline_lineage():
    from rig_contact_tracks import prediction_origin
    assert prediction_origin(dict(origin='loop_source_predictions',source_origin='none_supplied'))=='none_supplied'
    assert prediction_origin(dict(origin='blended_source_predictions',source_origins=['none_supplied','source_model_predictions']))=='partially_unknown'
    assert prediction_origin(dict(origin='loop_source_predictions',source_origin='partially_unknown'))=='partially_unknown'
    assert prediction_origin(dict(origin='loop_source_predictions',source_origin='source_model_predictions'))=='loop_source_predictions'
