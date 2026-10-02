"""Exact limits, bounded lift recovery, probe replay and default isolation."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from threadpoolctl import threadpool_limits
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_mesh_contact_feasibility import setup
from rig_mesh_trajectory import MeshContactTrajectoryFitter,CoupledMeshContactFitter,run
from rig_coupled_pose import window_basis
from mesh_contact_feasibility import MeshContactFeasibility
from mesh_contact_guarded_trials import GuardedMeshTrials
from strep import read,save,sha256


@pytest.mark.parametrize('fixed',[False,True])
def test_value_only_limits_match_full_jacobian_path(tmp_path,fixed):
    _,_,f,c,_=setup(tmp_path,fixed=fixed);rng=np.random.default_rng(165)
    for scale in (0.,.0001,.003,.1,1.):
        x=rng.normal(size=np.prod(c.shape))*scale
        np.testing.assert_allclose(c.inequality_values(x),c.inequality_pair(x)[0],atol=2e-10,rtol=1e-10)
    # Also compare a nonzero warm start, including fixed context boundaries.
    seed=rng.normal(size=np.prod(c.shape))*.0001;c.synchronize(seed)
    warm=CoupledMeshContactFitter(f,c.basis)
    np.testing.assert_allclose(warm.inequality_values(seed),warm.inequality_pair(seed)[0],atol=2e-10,rtol=1e-10)


def test_lift_rescues_sampled_floor_with_unchanged_limits(tmp_path):
    _,spec,f,_,_=setup(tmp_path)
    local=f.local.copy();local[:]=local[0];local[:,0,1,3]-=.23
    spec=copy.deepcopy(spec);spec['contacts'][0]['target_position_m']=[-.2,-.004,.02]
    f=MeshContactTrajectoryFitter(f.rig,spec,local,np.ones(7));c=CoupledMeshContactFitter(f,window_basis(f.envelope,2))
    guard=GuardedMeshTrials(c,.01);endpoint=np.zeros(c.shape);endpoint[:,1]=-.04
    candidates=list(guard.candidates(np.zeros(endpoint.size),endpoint.ravel()))
    rescue=next((x,info,seen) for x,info,seen in candidates if info['kind']=='floor_lift_segment' and seen is not None)
    x,info,(floor,contact)=rescue
    assert info['lift_m']>0 and floor.min()>=.01-1e-8
    assert c.inequality_pair(x)[0].min()>=-1e-8
    for frame,value in enumerate(c.parameters(x)):
        points=f.rig.vertices(f.pose(frame,value)[0]);assert points[:,1].min()>=-.00495-1e-9
    before=c.parameters(endpoint.ravel());after=c.parameters(x)
    np.testing.assert_array_equal(after[:,0],before[:,0]);np.testing.assert_array_equal(after[:,2:],before[:,2:])
    np.testing.assert_allclose(after[:,1]-before[:,1],info['lift_m'],atol=1e-12)


def test_rescue_cannot_move_fixed_floor_geometry(tmp_path):
    _,_,f,c,_=setup(tmp_path,-.26,fixed=True)
    guard=GuardedMeshTrials(c,.01)
    floor,contact,lift=guard.observe(np.zeros(np.prod(c.shape)))
    assert floor.min()<.01 and lift is None
    assert not any(info['kind']=='floor_lift_segment' for _,info,_ in guard.candidates(np.zeros(np.prod(c.shape)),np.zeros(np.prod(c.shape))))


def test_over_budget_rescue_is_retained_as_rejected_probe(tmp_path):
    _,_,f,c,_=setup(tmp_path,-.5)
    candidates=list(GuardedMeshTrials(c,.01).candidates(np.zeros(np.prod(c.shape)),np.zeros(np.prod(c.shape))))
    lifted=[(x,info,seen) for x,info,seen in candidates if info['kind']=='floor_lift_segment']
    assert lifted and all(info['motion_min']<0 and seen is None for _,info,seen in lifted)


def test_guarded_solve_archives_replayable_probes_and_protects_floor(tmp_path):
    _,spec,f,c,_=setup(tmp_path)
    spec['contacts'][0]['target_position_m'][1]=-2.
    stage=MeshContactFeasibility(c,True)
    with threadpool_limits(limits=1):values,trace,result=stage.solve(tmp_path,3,5)
    assert result['guarded_trials'] and not result['contacts_reached'] and result['floor_reached']
    records=read(tmp_path/'contacts-trials.json')['records']
    data=np.load(tmp_path/'contacts-trials.npz',allow_pickle=False)
    assert len(records)==len(data['controls']) and records
    retained=[r for r in records if r['status']=='retained'];assert retained
    assert result['phases']['contacts']['guarded_trials']['retained_updates']==len(retained)
    for record in retained:
        params=data['warm_parameters']+data['basis']@data['controls'][record['index']].reshape(c.shape)
        for frame,value in enumerate(params):
            assert f.rig.vertices(f.pose(frame,value)[0])[:,1].min()>=-.00495-1e-9
        assert record['motion_min']>=-1e-8
    np.testing.assert_allclose(values,data['warm_parameters']+data['basis']@data['selected_controls'].reshape(c.shape),atol=1e-12)
    assert all(f.constraints(i,x)[0].min()>=-1e-7 for i,x in enumerate(values))


def test_default_has_no_guarded_probes_and_real_opt_in_is_bound(tmp_path):
    source,spec,_,_,_=setup(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    default=tmp_path/'default';guarded=tmp_path/'guarded'
    run(source,draft,default,2,2,True,3)
    result=run(source,draft,guarded,2,2,True,3,True)
    assert read(default/'request.json')['guarded_trials'] is False
    assert not (default/'contacts-trials.npz').exists()
    assert read(guarded/'request.json')['guarded_trials'] is True
    assert sha256(guarded/'contact-spec.json')==sha256(draft)
    assert 'contacts-trials.npz' in result['outputs'] and not result['quality_approved']


@pytest.mark.parametrize('choice',[1,None,'true'])
def test_flag_requires_boolean(tmp_path,choice):
    _,_,_,c,_=setup(tmp_path)
    with pytest.raises(ValueError,match='choice'):MeshContactFeasibility(c,choice)


def test_guarded_cli_requires_feasibility_mode_before_creating_output(tmp_path):
    source,spec,_,_,_=setup(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    with pytest.raises(ValueError,match='feasibility mode'):run(source,draft,tmp_path/'out',guarded_trials=True)
    assert not (tmp_path/'out').exists()
