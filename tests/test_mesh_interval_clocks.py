"""Independent exported mixed clocks, derivatives, protection and strict binding."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_mesh_contact_clock import moving_fixture,continuous_contacts
from test_mesh_contact_feasibility import setup
from mesh_contact_clock import layout,validate_overrides
from rig_asset import RigAsset
from target_rig_contact import baseline
from rig_mesh_trajectory import MeshContactTrajectoryFitter,CoupledMeshContactFitter,run
from rig_coupled_pose import window_basis
from mesh_contact_playback import MeshPlaybackFloor
from mesh_contact_feasibility import MeshContactFeasibility
from rig_subframe_contacts import inspect
from rig_loop import encode
from strep import sha256,read,save


@pytest.mark.parametrize('value',[[],True,{'00':'frame-hold'},{'-1':'frame-hold'},{'2':'frame-hold'},
    {0:'frame-hold'},{'١':'frame-hold'},{'0':None},{'0':'unknown'}])
def test_clock_overrides_reject_ambiguous_or_missing_intervals(value):
    with pytest.raises(ValueError):validate_overrides(value,2)


def test_overrides_copy_and_mixed_half_open_boundaries():
    keys=(np.arange(5,dtype=np.float32)/30).astype(float);times=np.sort(np.r_[keys,(keys[:-1]+keys[1:])/2])
    spec=dict(frames=4,fps=30,contacts=[dict(start_frame=1,end_frame_exclusive=3),dict(start_frame=1,end_frame_exclusive=3)])
    overrides={'1':'frame-hold'};selected,indices=layout(spec,times,'authored-keys',overrides)
    np.testing.assert_array_equal(selected[indices==0],keys[1:3])
    np.testing.assert_array_equal(selected[indices==1],times[(times>=keys[1])&(times<keys[3])])
    validated=validate_overrides(overrides,2);overrides['1']='authored-keys';assert validated['1']=='frame-hold'


def mixed(tmp_path):
    path,spec=moving_fixture(tmp_path)
    spec['patches']['second']=copy.deepcopy(next(iter(spec['patches'].values())))
    spec['contacts'].append({**spec['contacts'][0],'patch':'second'})
    rig=RigAsset.load(path);_,local=baseline(rig,7)
    fitter=MeshContactTrajectoryFitter(rig,spec,local,np.ones(7))
    coupled=CoupledMeshContactFitter(fitter,window_basis(fitter.envelope,2))
    return path,spec,fitter,coupled


def test_independent_export_checks_keys_and_hold_on_the_same_motion(tmp_path):
    path,spec,_,_=mixed(tmp_path);before=(sha256(path),copy.deepcopy(spec))
    result=inspect(path,spec,contact_clock_overrides={'1':'frame-hold'})
    a,b=result['contacts'];assert a['failed_samples']==0 and b['failed_samples']>0
    assert a['contact_clock']=='authored-keys' and b['contact_clock']=='frame-hold'
    assert b['samples']>a['samples'] and b['worst_time_s']>a['worst_time_s']
    assert result['failed_intervals']==1 and not result['quality_approved']
    assert (sha256(path),spec)==before


def test_model_and_independently_decoded_mixed_centroids_match(tmp_path):
    _,spec,f,c=mixed(tmp_path);p=MeshPlaybackFloor(c,contact_clock_overrides={'1':'frame-hold'})
    x=np.random.default_rng(824).normal(size=np.prod(c.shape))*.002
    world=np.array([f.pose(i,v)[0] for i,v in enumerate(c.parameters(x))])
    path=tmp_path/'baked.glb';encode(f.rig,world,set(p.animated),spec['root_node'],path,'mixed fixture')
    exported=copy.deepcopy(spec);exported['glb_sha256']=sha256(path)
    decoded=inspect(path,exported,contact_clock_overrides={'1':'frame-hold'})
    values=p.contact_values(x)
    np.testing.assert_allclose([1-r['error_max_m']/.02 for r in decoded['contacts']],
        [values[p.contact_groups==i].min() for i in range(2)],atol=2e-6,rtol=0)
    assert decoded['samples']==len(p.contact_times)
    _,jac=p.contact_pair(x);rng=np.random.default_rng(632)
    for _ in range(3):
        direction=rng.normal(size=len(x));direction/=np.linalg.norm(direction);eps=1e-6
        numeric=(continuous_contacts(f,c,p,x+eps*direction)-continuous_contacts(f,c,p,x-eps*direction))/(2*eps)
        np.testing.assert_allclose(jac@direction,numeric,atol=3e-5,rtol=2e-5)


def test_mixed_protection_freezes_only_the_interval_that_really_passes(tmp_path):
    _,_,_,c=mixed(tmp_path);stage=MeshContactFeasibility(c,True,True,contact_clock_overrides={'1':'frame-hold'})
    # The raw active-key rows precede interval-grouped playback rows.
    raw_groups=np.array([c.fitter.spec['contacts'].index(t) for active in c.fitter.active for t in active])
    groups=np.r_[raw_groups,stage.playback.contact_groups]
    assert len(stage.protected)>0 and np.all(groups[stage.protected]==0)
    assert not np.any(groups[stage.protected]==1)


def test_actual_stages_and_export_keep_the_overrides(tmp_path):
    source,spec,_,_,_=setup(tmp_path);spec['patches']['second']=copy.deepcopy(next(iter(spec['patches'].values())))
    spec['contacts'].append({**spec['contacts'][0],'patch':'second'})
    draft=tmp_path/'draft.json';save(draft,spec);output=tmp_path/'fit'
    result=run(source,draft,output,2,3,True,2,True,True,'authored-keys',{'1':'frame-hold'})
    assert result['solver']['contact_clock_overrides']=={'1':'frame-hold'}
    assert read(output/'request.json')['contact_clock_overrides']=={'1':'frame-hold'}
    assert read(output/'floor-trials.json')['contact_clock_overrides']=={'1':'frame-hold'}
    assert read(output/'contacts-trials.json')['contact_clock_overrides']=={'1':'frame-hold'}
    decoded=read(output/'playback-contact-inspection.json')
    assert [c['contact_clock'] for c in decoded['contacts']]==['authored-keys','frame-hold']
    assert sha256(output/'original.glb')==sha256(source) and not result['quality_approved']


def test_mixed_export_failure_retains_input_despite_mocked_solver_success(tmp_path,monkeypatch):
    path,spec,_,_=mixed(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    def unchanged(stage,*args,**kwargs):return stage.coupled.fitter.values.copy(),[],dict(solver_success=True,constraint_min=1.)
    monkeypatch.setattr(MeshContactFeasibility,'solve',unchanged)
    result=run(path,draft,tmp_path/'fit',2,2,True,2,True,True,contact_clock_overrides={'1':'frame-hold'})
    assert read(tmp_path/'fit/independent-inspection.json')['failed_intervals']==0
    assert read(tmp_path/'fit/subframe-floor-inspection.json')['sampled_floor_passed']
    assert result['retained_input'] and result['solver']['solver_success']
    assert read(tmp_path/'fit/audit.json')['flags']==['decoded_contact_clock_screen_failed']
    contacts=read(tmp_path/'fit/playback-contact-inspection.json')['contacts']
    assert contacts[0]['failed_samples']==0 and contacts[1]['failed_samples']>0


def test_invalid_override_or_unguarded_timing_never_creates_output(tmp_path):
    source,spec,_,_,_=setup(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    for overrides,guards in [({'1':'frame-hold'},True),({'0':'frame-hold'},False)]:
        with pytest.raises(ValueError):run(source,draft,tmp_path/'fit',2,2,True,2,guards,guards,contact_clock_overrides=overrides)
        assert not (tmp_path/'fit').exists()
