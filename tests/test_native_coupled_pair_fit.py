"""Physical stop semantics, editable repair, frozen support and codec checks."""
from pathlib import Path
import sys,copy
from types import SimpleNamespace
import numpy as np
import pytest
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_coupled_key_pair_rows.py').is_file())
sys.path[:0]=[str(Path(__file__).parent),str(root/'scripts'),str(root/'tests')]
import native_coupled_pair_fit as fitter
from native_coupled_key_pair_rows import CoupledKeyPairRows
from test_native_coupled_key_pair_rows import setup


def no_solver(*args,**kwargs):raise AssertionError('Optimization should not start')


def active_failure(tmp_path):
    left,right,observations,_=setup(tmp_path);observations=observations[-1:]
    observations[0]['gaps'][0]['normal_world']=[-1.,0.,0.]
    return CoupledKeyPairRows(left,right,observations)


def test_feasible_seed_preserved_without_optimization(tmp_path,monkeypatch):
    *_,p=setup(tmp_path);monkeypatch.setattr(fitter,'minimize',no_solver)
    value,result=fitter.fit(p,search_reserve=np.full(p.rows,.1))
    np.testing.assert_array_equal(value,p.initial)
    assert result['stop']=='initial_physical_conditions_pass' and result['physical_declared_conditions_pass']
    assert not result['solver_was_run'] and result['complete_evaluations']==0
    assert result['original_selected'] and not result['release_approved'] and not result['optimizer_completion_claimed']


@pytest.mark.parametrize('self_pair',[False,True])
def test_fixed_physical_condition_rejected_with_all_original_pair_indices(tmp_path,monkeypatch,self_pair):
    left,right,observations,_=setup(tmp_path)
    gap=observations[0]['gaps'][0]
    if self_pair:gap['actor_sides']=[0,0]
    else:gap['normal_world']=[-1.,0.,0.]
    p=CoupledKeyPairRows(left,right,observations);monkeypatch.setattr(fitter,'minimize',no_solver)
    before=p.postcheck(p.initial);value,result=fitter.fit(p)
    assert result['stop']=='fixed_physical_condition_failure' and not result['solver_was_run']
    fixed=result['preflight']['fixed_conditions_failed'];assert len(fixed)==1 and fixed[0]['kind']=='gap'
    assert fixed[0]['raw_original_pairs']==fixed[0]['encoded_original_pairs']==[0]
    assert fixed[0]['raw_global_rows'] and fixed[0]['encoded_global_rows']
    assert not result['physical_declared_conditions_pass'] and not result['optimizer_completion_claimed']
    np.testing.assert_array_equal(value,p.initial)
    for name in ['raw_rows','encoded_rows','raw_pair_rows','encoded_pair_rows']:np.testing.assert_array_equal(before[name],p.postcheck(value)[name])


def test_fixed_self_failure_not_hidden_by_other_actor_editability(tmp_path):
    left,right,observations,_=setup(tmp_path);right['active_pairs'].append((1,right['nodes'][0]))
    observations[0]['gaps'][0]['actor_sides']=[0,0]
    result=fitter.preflight(CoupledKeyPairRows(left,right,observations))
    assert result['rejected'] and result['fixed_conditions_failed'][0]['kind']=='gap'


def test_fixed_negative_smooth_proxy_is_not_a_physical_infeasibility_proof(tmp_path):
    left,right,observations,p=setup(tmp_path);observations=observations[:1]
    before=p.postcheck(p.initial)['raw_pair_rows'][0]*.01+2e-5
    position,rotation=right['actor']['placement'];right['actor']['placement']=(position+np.array([.00004-before,0,0]),rotation)
    p=CoupledKeyPairRows(left,right,observations)
    assert p.postcheck(p.initial)['declared_conditions_pass']
    assert any(np.any(p.values(p.initial)[first:last]<0) for kind,t,s,first,last,fixed in p.layout if kind=='gap' and fixed)
    checked=fitter.preflight(p);assert not checked['rejected'] and not checked['fixed_conditions_failed']


@pytest.mark.parametrize('change',['support','layout','offset'])
def test_changed_structural_support_or_layout_rejected(tmp_path,change):
    *_,p=setup(tmp_path)
    if change=='support':p._samples[0][1][0][0].dependent=(0,)
    elif change=='layout':p._layout[0]=(*p._layout[0][:-1],not p._layout[0][-1])
    else:p._offsets.reverse()
    with pytest.raises(ValueError,match='support|layout'):fitter.fit(p)


def test_actual_small_partner_repair_keeps_all_domains_and_saved_pair_gap(tmp_path):
    from native_key_contact_initializer import encode
    from native_support_clock import NativeSupportSampler
    from native_scene_geometry import faces_for
    from rig_asset import RigAsset
    left,right,observations,p=setup(tmp_path);observations=observations[-1:]
    before=p.postcheck(p.initial)['raw_pair_rows'][-1]*.01+2e-5
    position,rotation=right['actor']['placement'];right['actor']['placement']=(position+np.array([.0001-before,0,0]),rotation)
    observations[0]['gaps'][0].update(minimum_gap_m=.0002,temperature_m=1e-7)
    p=CoupledKeyPairRows(left,right,observations);assert not p.postcheck(p.initial)['declared_conditions_pass']
    seen=[];value,result=fitter.fit(p,iterations=16,search_reserve=np.full(p.rows,.0001),on_evaluation=lambda row:seen.append(row))
    assert result['physical_declared_conditions_pass'] and result['solver_was_run'] and not result['preflight']['rejected']
    assert result['complete_evaluations']==len(seen)>1 and all(r['rows'].shape==(p.rows,) for r in seen)
    assert result['stop']=='independently_postchecked_feasible_checkpoint' and not result['optimizer_completion_claimed']
    points=[]
    for side,spec in enumerate([left,right]):
        actor=spec['actor'];controls=p.controls(side,value);mask=np.ones(controls.shape[:2],bool)
        for key,node in spec['active_pairs']:mask[key,spec['nodes'].index(node)]=False
        np.testing.assert_array_equal(controls[mask],spec['seed_controls'][mask])
        channels=[next(c for c in actor['sampler'].channels if c[:2]==(node,'rotation')) for node in spec['nodes']]
        path=tmp_path/f'fit-{side}.glb';index=encode(actor['rig'],actor['animation_index'],spec['nodes'],channels,controls,spec['degrees'],path)
        rig=RigAsset.load(path);sampler=NativeSupportSampler(rig.document,rig.binary,index);position,rotation=actor['placement']
        world=rig.vertices(sampler.sample(observations[0]['time_s']))@rotation.T+position;points.append(world[faces_for(rig)[0][0]])
    assert points[1][:,0].min()-points[0][:,0].max()>=.0002


def test_optimizer_success_does_not_override_failed_physical_postchecks(tmp_path,monkeypatch):
    p=active_failure(tmp_path)
    monkeypatch.setattr(fitter,'minimize',lambda *a,**kw:SimpleNamespace(x=p.initial.copy(),success=True,status=0,message='fixture',nit=1))
    value,result=fitter.fit(p)
    assert result['solver_success'] and result['optimizer_completion_claimed'] and not result['physical_declared_conditions_pass']
    assert result['stop']=='optimizer_returned' and result['original_selected'] and not result['quality_approved']


def test_evaluation_budget_returns_last_complete_point_without_convergence_claim(tmp_path,monkeypatch):
    p=active_failure(tmp_path)
    def exhaust(*args,**kwargs):
        function=kwargs['constraints'][0]['fun'];function(p.initial);function(p.initial+.001)
        raise AssertionError('Budget must stop the second complete evaluation')
    monkeypatch.setattr(fitter,'minimize',exhaust)
    value,result=fitter.fit(p,maximum_evaluations=1)
    np.testing.assert_array_equal(value,p.initial)
    assert result['stop']=='complete_evaluation_budget_exhausted' and result['complete_evaluations']==1
    assert not result['optimizer_completion_claimed'] and not result['physical_declared_conditions_pass']


def test_callback_receives_copies_and_source_mutation_is_rejected(tmp_path,monkeypatch):
    p=active_failure(tmp_path)
    def observe(row):
        row['rows'][:]=999;row['controls'][:]=0
        p._specs[0]['actor']['placement']=(np.array([9.,0,0]),np.eye(3))
    def call(*args,**kwargs):kwargs['constraints'][0]['fun'](p.initial)
    monkeypatch.setattr(fitter,'minimize',call)
    with pytest.raises(ValueError):fitter.fit(p,on_evaluation=observe)


@pytest.mark.parametrize('settings',[
    dict(iterations=0),dict(iterations=65),dict(iterations=True),
    dict(maximum_evaluations=0),dict(maximum_evaluations=513),dict(maximum_evaluations=True),
    dict(on_evaluation=1),dict(search_reserve=np.array([0.])),dict(search_reserve=True),
    dict(search_reserve=-1.),dict(search_reserve=np.nan),
])
def test_invalid_complete_search_settings_rejected(tmp_path,settings):
    *_,p=setup(tmp_path)
    with pytest.raises(ValueError):fitter.fit(p,**settings)


@pytest.mark.parametrize('mode',['fit','preflight'])
def test_foreign_problem_rejected(mode):
    with pytest.raises(ValueError):getattr(fitter,mode)(object())


@pytest.mark.parametrize('value',[np.array([0.]),np.full(12,np.nan),np.zeros(12,dtype=bool)])
def test_invalid_preflight_values_rejected(tmp_path,value):
    *_,p=setup(tmp_path)
    with pytest.raises(ValueError):fitter.preflight(p,value)


def test_resume_start_preserves_original_seed_objective_and_domain(tmp_path,monkeypatch):
    p=active_failure(tmp_path);original=p.initial.copy();start=original+.003
    def measured(fun,x0,**settings):
        np.testing.assert_array_equal(x0,start)
        assert fun(original)==0 and fun(start)>0
        np.testing.assert_array_equal(settings['jac'](original),np.zeros(p.size))
        np.testing.assert_allclose(settings['jac'](start),start-original,atol=0,rtol=0)
        return SimpleNamespace(x=start.copy(),success=False,status=9,message='fixture',nit=1)
    monkeypatch.setattr(fitter,'minimize',measured)
    value,result=fitter.fit(p,starting_value=start)
    np.testing.assert_array_equal(value,start);np.testing.assert_array_equal(p.initial,original)
    assert result['starting_value_provided'] and not result['physical_declared_conditions_pass']


def test_feasible_resume_revalidated_without_rebasing_original_seed(tmp_path,monkeypatch):
    left,right,observations,p=setup(tmp_path);original=p.initial.copy();start=original+.001
    assert p.postcheck(start)['declared_conditions_pass']
    monkeypatch.setattr(fitter,'minimize',no_solver)
    value,result=fitter.fit(p,starting_value=start)
    np.testing.assert_array_equal(value,start);np.testing.assert_array_equal(p.initial,original)
    assert result['starting_value_provided'] and result['physical_declared_conditions_pass'] and not result['solver_was_run']


def test_cached_derivatives_reject_callback_mutation_even_when_pose_rows_failed(tmp_path,monkeypatch):
    p=active_failure(tmp_path)
    def mutate(row):p._specs[0]['actor']['placement']=(np.array([8.,0,0]),np.eye(3))
    def evaluate_then_reuse(*args,**kwargs):
        value=p.initial.copy();value[:3]=[1.,1.,0.]
        constraints=kwargs['constraints'][0]
        constraints['fun'](value)
        constraints['jac'](value)
    monkeypatch.setattr(fitter,'minimize',evaluate_then_reuse)
    with pytest.raises(ValueError):fitter.fit(p,on_evaluation=mutate)


@pytest.mark.parametrize('value',[np.array([0.]),np.full(12,np.nan),np.zeros(12,dtype=bool),np.full(12,1.01)])
def test_invalid_resume_proposals_not_silently_clipped(tmp_path,value):
    *_,p=setup(tmp_path)
    with pytest.raises(ValueError):fitter.fit(p,starting_value=value)


def test_fresh_kernels_and_cached_derivatives_both_check_every_source(tmp_path,monkeypatch):
    p=active_failure(tmp_path);mappers=[mapper for stamp,contexts,gaps in p._samples for mapper,helper in contexts]
    counts=[0]*len(mappers)
    for index,mapper in enumerate(mappers):
        original=mapper._check
        def checked(index=index,original=original):counts[index]+=1;return original()
        monkeypatch.setattr(mapper,'_check',checked)
    def probe(*args,**kwargs):
        value=p.initial.copy();value[:3]=[1.,1.,0.];constraints=kwargs['constraints'][0]
        counts[:]=[0]*len(counts);constraints['fun'](value);assert all(n>0 for n in counts)
        counts[:]=[0]*len(counts);constraints['jac'](value);assert all(n>0 for n in counts)
        return SimpleNamespace(x=p.initial.copy(),success=False,status=9,message='fixture',nit=1)
    monkeypatch.setattr(fitter,'minimize',probe)
    value,report=fitter.fit(p);assert not report['physical_declared_conditions_pass']
