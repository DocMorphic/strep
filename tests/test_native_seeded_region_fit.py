"""Complete seeded edits, frozen poses, bounded rows and native codec replay."""
from pathlib import Path
import sys
import copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_seeded_region_fit import SeededRegionProblem,fit
from native_partitioned_affine_pose import PartitionedAffineKeyPose
from native_key_pose_map import KeyPoseMap
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from scipy.spatial.transform import Rotation
from test_native_key_pose_map import inputs


def setup(tmp_path,**updates):
    model,stamp,seed,_=inputs(tmp_path);clock=next(c[2] for c in model.actor['sampler'].channels if c[:2]==(model.nodes[0],'rotation'))
    region=dict(vertices=[0,1,2],normal_world=[0.,1.,0.],offset_m=-10.,sign=1,minimum_gap_m=0.)
    kwargs=dict(actor=model.actor,nodes=model.nodes.copy(),degrees=[20.]*len(model.nodes),clock=clock.copy(),seed_controls=seed.copy(),
        active_pairs=[(5,model.nodes[0]),(6,model.nodes[-1])],frozen_keys=[0,2,len(clock)-1],
        world_caps_m=np.ones(len(model.rig.joints)),observations=[dict(time_s=stamp,regions=[region]),dict(time_s=float(clock[1]),regions=[region])])
    kwargs.update(updates);return kwargs


def test_multi_time_complete_rows_match_independent_helpers_and_differences(tmp_path):
    problem=SeededRegionProblem(**setup(tmp_path));value=problem.initial+.015
    rows,jac=problem.evaluate(value);blocks=[m.region_rows(p,value) for m,p in problem.samples]
    np.testing.assert_array_equal(rows,np.concatenate([b[0] for b in blocks]));np.testing.assert_array_equal(jac,np.vstack([b[1] for b in blocks]))
    for column in range(problem.size):
        delta=np.eye(problem.size)[column]*2e-6;fd=(problem.evaluate(value+delta)[0]-problem.evaluate(value-delta)[0])/4e-6
        np.testing.assert_allclose(jac[:,column],fd,atol=4e-6,rtol=4e-6)
    # Time1 is outside the active interpolation brackets; all its pose rows remain.
    second=blocks[1];assert np.count_nonzero(second[1][:-len(problem.pairs)])==0
    assert len(rows)==problem.rows==problem.report['complete_rows']


def test_export_retains_fixed_nonzero_seed_frozen_keys_and_actual_float32_worlds(tmp_path):
    kwargs=setup(tmp_path);seed=kwargs['seed_controls'].copy();problem=SeededRegionProblem(**kwargs);value=problem.initial+.02
    controls=problem.controls(value);mask=np.ones(controls.shape[:2],bool)
    for key,node in problem.pairs:mask[key,problem.nodes.index(node)]=False
    np.testing.assert_array_equal(controls[mask],seed[mask]);np.testing.assert_array_equal(controls[list(problem.frozen)],seed[list(problem.frozen)])
    path=tmp_path/'proposal.glb';index=problem.export(value,path);rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,index)
    source=kwargs['actor']['rig'];assert rig.binary[:len(source.binary)]==source.binary and rig.document['animations'][:-1]==source.document['animations']
    for mapper,_ in problem.samples:
        full=mapper.controls(value,quantized=True);world,points,*_=mapper.model.evaluate_columns(full,[])
        np.testing.assert_allclose(world,reader.sample(mapper.time_s),atol=3e-13,rtol=0);np.testing.assert_allclose(points,rig.vertices(reader.sample(mapper.time_s)),atol=3e-13,rtol=0)
    quantized=problem.quantized_rows(value);assert quantized.shape==(problem.rows,) and np.isfinite(quantized).all()
    before=path.read_bytes()
    with pytest.raises(ValueError,match='Fresh'):problem.export(value,path)
    assert path.read_bytes()==before


def test_constructor_input_copies_and_source_mutation_rejection(tmp_path):
    kwargs=setup(tmp_path);problem=SeededRegionProblem(**kwargs);expected=problem.controls(problem.initial)
    kwargs['seed_controls'][:]=0;kwargs['nodes'].reverse();kwargs['degrees'][:]=[1.]*len(kwargs['degrees']);kwargs['observations'][0]['regions'][0]['vertices'].reverse();kwargs['frozen_keys'].clear()
    np.testing.assert_array_equal(problem.controls(problem.initial),expected)
    mapper=problem.samples[0][0];mapper.model.maximum_derivative_controls+=3
    with pytest.raises(ValueError):problem.evaluate(problem.initial)
    with pytest.raises(ValueError):problem.quantized_rows(problem.initial)
    with pytest.raises(ValueError):problem.export(problem.initial,tmp_path/'rejected.glb')
    assert not (tmp_path/'rejected.glb').exists()


def test_quantized_native_ball_rows_match_actual_exports_even_outside_bracket(tmp_path):
    problem=SeededRegionProblem(**setup(tmp_path));overshoots=0
    for i,direction in enumerate(([1.,0,0],[-1.,0,0],[0,1.,0],[0,-1.,0],[0,0,1.],[0,0,-1.],[.6,.8,0])):
        value=problem.initial.copy();value[:3]=direction
        path=tmp_path/('unit-ball-'+str(i)+'.glb');index=problem.export(value,path)
        rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,index);expected=[]
        for key,node in problem.pairs:
            old=next(c for c in problem.actor['sampler'].channels if c[:2]==(node,'rotation'))
            new=next(c for c in reader.channels if c[:2]==(node,'rotation'))
            fraction=(Rotation.from_quat(old[3][key]).inv()*Rotation.from_quat(new[3][key])).magnitude()/np.radians(20.)
            expected.append(1-fraction*fraction)
        overshoots+=int(expected[0]<0)
        rows=problem.quantized_rows(value);cursor=0
        for _,helper in problem.samples:
            cursor+=helper.report['rows'];np.testing.assert_allclose(rows[cursor:cursor+len(problem.pairs)],expected,atol=4e-15,rtol=0);cursor+=len(problem.pairs)
    assert overshoots>0  # An unrounded unit vector must not hide an encoded overshoot.


def test_feasible_seed_solver_preserves_seed_and_reports_actual_conditions(tmp_path):
    problem=SeededRegionProblem(**setup(tmp_path));value,report=fit(problem,iterations=3)
    np.testing.assert_array_equal(value,problem.initial);np.testing.assert_array_equal(problem.controls(value),problem.seed)
    assert report['declared_raw_conditions_pass'] and report['declared_quantized_conditions_pass']
    assert report['raw_failed_rows']==report['quantized_failed_rows']==0
    assert report['original_selected'] and not report['quality_approved'] and not report['release_approved']


def test_infeasible_fixed_pose_is_retained_and_not_reported_as_accepted(tmp_path):
    kwargs=setup(tmp_path);kwargs['observations'][1]['regions'][0]['offset_m']=100.
    problem=SeededRegionProblem(**kwargs);value,report=fit(problem,iterations=2)
    assert not report['declared_raw_conditions_pass'] and not report['declared_quantized_conditions_pass']
    assert report['raw_failed_rows']==int(np.count_nonzero(problem.evaluate(value)[0]<0))
    assert report['quantized_failed_rows']==int(np.count_nonzero(problem.quantized_rows(value)<0))
    assert len(report['evaluations'])>0


def test_nonzero_seed_correction_improves_explicit_surface_target(tmp_path):
    kwargs=setup(tmp_path);kwargs['observations']=kwargs['observations'][:1]
    probe=SeededRegionProblem(**kwargs);mapper,_=probe.samples[0];full=mapper.controls(probe.initial)
    _,vertices,derivative,_=mapper.model.evaluate_columns(full,[0]);normal=derivative[0,:,0];normal/=np.linalg.norm(normal)
    position,rotation=kwargs['actor']['placement'];point=vertices[0]@rotation.T+position;axis=rotation@normal
    kwargs['observations'][0]['regions']=[dict(vertices=[0],normal_world=axis.tolist(),offset_m=float(point@axis+.002),sign=1,minimum_gap_m=0.)]
    problem=SeededRegionProblem(**kwargs);before=problem.evaluate(problem.initial)[0]
    reserve=np.zeros(problem.rows);helper=problem.samples[0][1];reserve[helper.hard_rows:helper.report['rows']]=.001
    value,report=fit(problem,iterations=16,search_reserve=reserve);after=problem.evaluate(value)[0]
    assert before.min()<-.1 and after.min()>before.min()+.1
    assert report['raw_failed_rows']==int(np.count_nonzero(after<0))
    assert report['declared_raw_conditions_pass'] and report['declared_quantized_conditions_pass']
    assert report['search_reserve']==reserve.tolist()
    np.testing.assert_array_equal(problem.controls(value)[list(problem.frozen)],problem.seed[list(problem.frozen)])


@pytest.mark.parametrize('change',['missing_endpoint','bool_key','frozen_pair','wrong_clock','extra_observation_field','row_budget','jacobian_budget'])
def test_invalid_permissions_clock_and_budgets_reject(tmp_path,change):
    kwargs=setup(tmp_path)
    if change=='missing_endpoint':kwargs['frozen_keys']=[0]
    elif change=='bool_key':kwargs['frozen_keys']=[0,True,len(kwargs['clock'])-1]
    elif change=='frozen_pair':kwargs['frozen_keys'].append(5)
    elif change=='wrong_clock':kwargs['clock'][4]+=.00001
    elif change=='extra_observation_field':kwargs['observations'][0]['dropped_rows']=[]
    elif change=='row_budget':kwargs['maximum_rows']=1
    else:kwargs['maximum_jacobian_bytes']=1
    with pytest.raises(ValueError):SeededRegionProblem(**kwargs)


@pytest.mark.parametrize('iterations',[0,True,65])
def test_invalid_solver_budget_rejects(tmp_path,iterations):
    problem=SeededRegionProblem(**setup(tmp_path))
    with pytest.raises(ValueError):fit(problem,iterations=iterations)


@pytest.mark.parametrize('operation',['evaluate','quantized_rows','controls'])
def test_nonconsecutive_same_times_reuse_frames_and_keep_every_ordered_row(tmp_path,monkeypatch,operation):
    kwargs=setup(tmp_path);observations=copy.deepcopy(kwargs['observations']*2)
    observations[2]['regions'][0]['vertices'].reverse();observations[3]['regions'][0]['offset_m']=-9.
    kwargs['observations']=observations;problem=SeededRegionProblem(**kwargs);value=problem.initial+.015
    individual=[SeededRegionProblem(**dict(kwargs,observations=[observation])) for observation in observations]
    if operation=='evaluate':expected=tuple(np.concatenate([p.evaluate(value)[i] for p in individual],axis=0) for i in [0,1])
    elif operation=='quantized_rows':expected=np.concatenate([p.quantized_rows(value) for p in individual])
    else:expected=individual[0].controls(value)
    calls=[0]
    for mapper,_ in problem.groups:
        original=mapper.model.evaluate_columns
        def wrapped(*args,_original=original,**kw):calls[0]+=1;return _original(*args,**kw)
        monkeypatch.setattr(mapper.model,'evaluate_columns',wrapped)
    actual=getattr(problem,operation)(value)
    if operation=='evaluate':
        for a,b in zip(actual,expected):np.testing.assert_array_equal(a,b)
    else:np.testing.assert_array_equal(actual,expected)
    assert problem.report['unique_pose_times']==2 and len(problem.samples)==4
    assert calls[0]==(0 if operation=='controls' else 2)


def test_reused_frame_still_checks_each_observation_fixed_seed(tmp_path):
    kwargs=setup(tmp_path);kwargs['observations']=[kwargs['observations'][0]]*2;problem=SeededRegionProblem(**kwargs)
    later=problem.samples[1][1];later.base=later.base.copy();later.base[3]+=.01
    with pytest.raises(ValueError,match='Fixed'):problem.evaluate(problem.initial)
    with pytest.raises(ValueError,match='Fixed'):problem.quantized_rows(problem.initial)


def test_callback_and_search_reserve_copies_cannot_change_solver_observations(tmp_path):
    problem=SeededRegionProblem(**setup(tmp_path));reserve=np.zeros(problem.rows);reserve[3]=.001;expected=reserve.copy();events=[]
    def observe(event):
        events.append((event['evaluation'],event['failed_rows']));event['controls'][:]=99;event['rows'][:]=np.nan;reserve[:]=.1
    value,report=fit(problem,iterations=3,search_reserve=reserve,on_evaluation=observe)
    np.testing.assert_array_equal(value,problem.initial);assert events
    assert report['search_reserve']==expected.tolist() and report['declared_quantized_conditions_pass']
    assert report['evaluations'][0]['controls']==problem.initial.tolist()


@pytest.mark.parametrize('kind',['shape','negative','nan','bool','oversized','scalar'])
def test_invalid_search_reserves_reject_before_solving(tmp_path,kind):
    problem=SeededRegionProblem(**setup(tmp_path));value=np.zeros(problem.rows)
    if kind=='shape':value=np.zeros(problem.rows+1)
    elif kind=='negative':value[0]=-.001
    elif kind=='nan':value[0]=np.nan
    elif kind=='bool':value=value.astype(bool)
    elif kind=='oversized':value[0]=.10001
    else:value=np.array(0.)
    with pytest.raises(ValueError,match='reserves'):fit(problem,search_reserve=value)


@pytest.mark.parametrize('callback',[True,object()])
def test_noncallable_observer_rejects(tmp_path,callback):
    problem=SeededRegionProblem(**setup(tmp_path))
    with pytest.raises(ValueError):fit(problem,on_evaluation=callback)


@pytest.mark.parametrize('count',[129,512])
def test_explicit_observation_budget_retains_every_row_and_reuses_one_time(tmp_path,monkeypatch,count):
    kwargs=setup(tmp_path);observation=kwargs['observations'][0];kwargs['observations']=[observation]
    reference=SeededRegionProblem(**kwargs);value=reference.initial+.01;expected=reference.evaluate(value)
    kwargs['observations']=[observation]*count
    with pytest.raises(ValueError):SeededRegionProblem(**kwargs)
    problem=SeededRegionProblem(**kwargs,maximum_observations=count);calls=[0]
    model=problem.groups[0][0].model;original=model.evaluate_columns
    def observed(*args,**kw):calls[0]+=1;return original(*args,**kw)
    monkeypatch.setattr(model,'evaluate_columns',observed)
    rows,jac=problem.evaluate(value)
    np.testing.assert_array_equal(rows,np.tile(expected[0],count));np.testing.assert_array_equal(jac,np.tile(expected[1],(count,1)))
    assert calls[0]==1 and len(problem.samples)==count and len(problem.groups)==1
    assert problem.report['maximum_observations']==count and problem.rows==count*reference.rows
    assert problem.report['maximum_rows']==100000 and problem.report['maximum_jacobian_bytes']==64*1024**2


@pytest.mark.parametrize('budget',[0,True,513,128.])
def test_invalid_observation_budget_rejects_before_pose_construction(tmp_path,monkeypatch,budget):
    kwargs=setup(tmp_path)
    import native_seeded_region_fit as module
    monkeypatch.setattr(module,'PartitionedAffineKeyPose',lambda *a,**k:pytest.fail('Invalid admission constructed a pose'))
    with pytest.raises(ValueError):module.SeededRegionProblem(**kwargs,maximum_observations=budget)


@pytest.mark.parametrize('limit',['maximum_rows','maximum_jacobian_bytes'])
def test_larger_observation_admission_keeps_complete_global_budgets(tmp_path,limit):
    kwargs=setup(tmp_path);kwargs['observations']=[kwargs['observations'][0]]*129
    with pytest.raises(ValueError,match='Complete multi-time'):
        SeededRegionProblem(**kwargs,maximum_observations=512,**{limit:1})


@pytest.mark.parametrize('location',['outside','frozen','endpoint','between_fixed'])
def test_violated_fixed_pose_skips_optimizer_without_dropping_any_rows(tmp_path,monkeypatch,location):
    import native_seeded_region_fit as module
    kwargs=setup(tmp_path);clock=kwargs['clock'];stamp={'outside':float(clock[1]),'frozen':float(clock[2]),'endpoint':float(clock[-1]),'between_fixed':float((clock[2]+clock[3])/2)}[location]
    observation=copy.deepcopy(kwargs['observations'][1]);observation['time_s']=stamp;observation['regions'][0]['offset_m']=100.
    kwargs['observations'].append(observation);p=module.SeededRegionProblem(**kwargs);before=p.seed.copy();events=[]
    monkeypatch.setattr(module,'minimize',lambda *a,**k:pytest.fail('Unchangeable physical condition reached optimizer'))
    value,report=module.fit(p,on_evaluation=lambda event:events.append(event))
    np.testing.assert_array_equal(value,p.initial);np.testing.assert_array_equal(p.controls(value),before)
    assert not report['solver_was_run'] and report['preflight_rejected'] and report['solver_status']==-1 and report['iterations']==0
    failure=report['unchangeable_pose_violations'][0];assert failure['observation']==2 and failure['time_s']==stamp
    helper=p.samples[2][1];expected=np.flatnonzero(p.evaluate(value)[0][p.offsets[2]:p.offsets[2]+helper.report['rows']]<0)
    assert failure['failed_pose_rows']==expected.tolist() and failure['failed_global_rows']==(expected+p.offsets[2]).tolist()
    assert report['raw_failed_rows']==int(np.count_nonzero(p.evaluate(value)[0]<0)) and report['quantized_failed_rows']==int(np.count_nonzero(p.quantized_rows(value)<0))
    assert len(events)==len(report['evaluations'])==1 and events[0]['rows'].shape==(p.rows,)
    assert report['original_selected'] and not report['quality_approved'] and not report['release_approved']


def test_repeated_fixed_observations_keep_distinct_complete_failure_offsets(tmp_path,monkeypatch):
    import native_seeded_region_fit as module
    kwargs=setup(tmp_path);bad=copy.deepcopy(kwargs['observations'][1]);bad['regions'][0]['offset_m']=100.
    kwargs['observations']=[bad,kwargs['observations'][0],bad];p=module.SeededRegionProblem(**kwargs)
    monkeypatch.setattr(module,'minimize',lambda *a,**k:pytest.fail('Fixed constraints reached optimizer'))
    _,report=module.fit(p);failures=report['unchangeable_pose_violations'];assert [r['observation'] for r in failures]==[0,2]
    assert set(failures[0]['failed_global_rows']).isdisjoint(failures[1]['failed_global_rows'])


def record_solver_calls(monkeypatch,module):
    from types import SimpleNamespace
    calls=[]
    def minimize(function,value,**settings):
        calls.append(value.copy());return SimpleNamespace(x=value.copy(),success=False,status=9,message='one-point fixture',nit=1)
    monkeypatch.setattr(module,'minimize',minimize);return calls


def test_nonempty_clock_support_is_not_proved_infeasible_by_zero_surface_gradient(tmp_path,monkeypatch):
    import native_seeded_region_fit as module
    kwargs=setup(tmp_path);kwargs['active_pairs']=[(5,kwargs['nodes'][-1])];kwargs['observations']=kwargs['observations'][:1]
    kwargs['observations'][0]['regions']=[dict(vertices=[1],normal_world=[0.,1.,0.],offset_m=100.,sign=1,minimum_gap_m=0.)]
    p=module.SeededRegionProblem(**kwargs);mapper,helper=p.samples[0];rows,jac=p.evaluate(p.initial)
    assert mapper.dependent and rows[helper.hard_rows]<0 and not np.any(jac[helper.hard_rows])
    calls=record_solver_calls(monkeypatch,module);_,report=module.fit(p)
    assert calls and report['solver_was_run'] and not report['preflight_rejected']


def test_fixed_search_reserve_failure_is_not_a_physical_preflight_rejection(tmp_path,monkeypatch):
    import native_seeded_region_fit as module
    kwargs=setup(tmp_path);kwargs['observations']=kwargs['observations'][1:];probe=module.SeededRegionProblem(**kwargs)
    mapper,helper=probe.samples[0];point=helper.evaluate(mapper.controls(probe.initial)[helper.coordinates])[3][0]
    kwargs['observations'][0]['regions']=[dict(vertices=[0],normal_world=[0.,1.,0.],offset_m=float(point[1]),sign=1,minimum_gap_m=0.)]
    p=module.SeededRegionProblem(**kwargs);row=p.samples[0][1].hard_rows;assert p.evaluate(p.initial)[0][row]==0
    reserve=np.zeros(p.rows);reserve[row]=.001;calls=record_solver_calls(monkeypatch,module);_,report=module.fit(p,search_reserve=reserve)
    assert calls and not report['preflight_rejected'] and report['declared_raw_conditions_pass'] and report['declared_quantized_conditions_pass'] and report['search_failed_rows']>0


def test_encoded_native_ball_outside_pose_bracket_remains_variable(tmp_path,monkeypatch):
    import native_seeded_region_fit as module
    kwargs=setup(tmp_path);kwargs['observations']=kwargs['observations'][1:];found=None
    for direction in ([1.,0,0],[-1.,0,0],[0,1.,0],[0,-1.,0],[0,0,1.],[0,0,-1.],[.6,.8,0]):
        changed=dict(kwargs,seed_controls=kwargs['seed_controls'].copy());changed['seed_controls'][5,0]=direction;p=module.SeededRegionProblem(**changed)
        helper=p.samples[0][1]
        if np.any(p.quantized_rows(p.initial)[helper.report['rows']:]<0):found=p;break
    assert found is not None and not found.samples[0][0].dependent
    calls=record_solver_calls(monkeypatch,module);_,report=module.fit(found)
    assert calls and not report['preflight_rejected'] and report['quantized_failed_rows']>0


@pytest.mark.parametrize('field',['bracket','dependent','pairs'])
def test_changed_temporal_support_cannot_fabricate_a_fixed_pose_rejection(tmp_path,monkeypatch,field):
    import native_seeded_region_fit as module
    p=module.SeededRegionProblem(**setup(tmp_path));mapper=p.groups[0][0]
    if field=='bracket':mapper.bracket=np.array([0])
    elif field=='dependent':mapper.dependent=()
    else:mapper.pairs=tuple(reversed(mapper.pairs))
    monkeypatch.setattr(module,'minimize',lambda *a,**k:pytest.fail('Mutated temporal support reached optimizer'))
    with pytest.raises(ValueError):module.fit(p)


def test_preflight_observation_callback_failure_propagates_before_solving(tmp_path,monkeypatch):
    import native_seeded_region_fit as module
    p=module.SeededRegionProblem(**setup(tmp_path));monkeypatch.setattr(module,'minimize',lambda *a,**k:pytest.fail('Callback failure reached optimizer'))
    def reject(event):raise RuntimeError('Retain numerical failure')
    with pytest.raises(RuntimeError,match='Retain numerical failure'):module.fit(p,on_evaluation=reject)
