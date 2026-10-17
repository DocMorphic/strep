"""Complete seeded edits, frozen poses, bounded rows and native codec replay."""
from pathlib import Path
import sys
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
    problem=SeededRegionProblem(**kwargs);before=problem.evaluate(problem.initial)[0];value,report=fit(problem,iterations=16);after=problem.evaluate(value)[0]
    assert before.min()<-.1 and after.min()>before.min()+.1
    assert report['raw_failed_rows']==int(np.count_nonzero(after<0))
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
