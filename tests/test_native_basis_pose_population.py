"""Complete populations, exact source signs, cross-block routing and full gradients."""
from pathlib import Path
import sys,hashlib
import numpy as np
import pytest
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_basis_pose_rows.py').is_file())
sys.path[:0]=[str(Path(__file__).parent),str(root/'scripts'),str(root/'tests')]
import native_basis_pose_population as module
from native_basis_pose_population import BasisPosePopulation
from native_basis_pose_rows import BasisPoseRows
from native_partitioned_affine_pose import PartitionedAffineKeyPose
from native_key_pose_map import KeyPoseMap
from native_key_basis import NativeKeyBasis
from test_native_basis_pose_rows import setup


def prepare(tmp_path):
    model,mapper,basis,caps,base,point=setup(tmp_path)
    def helper(stamp,bands=None,degrees=None,seed=None):
        nodes=list(model.nodes);seed=mapper.seed if seed is None else seed
        m=PartitionedAffineKeyPose(model.actor,float(stamp),nodes,np.degrees(model.caps).tolist() if degrees is None else degrees)
        clock=mapper.clock;key=int(np.searchsorted(clock,stamp,side='left'));keys=[0] if key==0 else [len(clock)-1] if key==len(clock) else [key] if clock[key]==stamp else [key-1,key]
        mapping=KeyPoseMap(m,float(stamp),seed,[(int(k),n) for k in keys for n in nodes])
        own_basis=NativeKeyBasis(clock,nodes,seed,[0,5,6,len(clock)-1],[0,len(clock)-1])
        return BasisPoseRows(mapping,own_basis,caps if bands is None else bands)
    poses=[helper(mapper.time_s),helper(0.),helper(float(mapper.clock[5]))]
    return base,poses,point,helper


@pytest.mark.parametrize('jacobian',[True,False])
def test_all_declared_rows_hashes_signs_and_order_match_independent_helpers(tmp_path,jacobian):
    base,poses,point,_=prepare(tmp_path);population=BasisPosePopulation(base,poses);result=population.evaluate(point,jacobian=jacobian)
    coefficients=base.export_coefficients(point);native=(1-np.sum(coefficients*coefficients,axis=2)).ravel()
    expected=np.concatenate([native]+[h.evaluate(point,jacobian=False)['margins'] for h in poses])
    assert result['original_margins'].tobytes()==expected.tobytes() and result['report']['raw_rows']==len(expected)
    assert result['report']['complete_declared_population'] and result['report']['columns']==len(point) and not result['report']['quality_approved']
    assert result['report']['observation_times_s']==[h.report['time_s'] for h in poses]
    for i,(g,r) in enumerate(zip(population.layout,result['report']['groups_report'])):
        values=-expected[g['first']:g['last']]
        assert r['rows']==r['rows_seen']==len(values) and r['values_sha256']==hashlib.sha256(values.astype('<f8').tobytes()).hexdigest()
        assert result['exact_margins'][i]==-values.max() and r['failed_rows']==np.count_nonzero(values>0)
    assert (result['exact_margins']>=0).all()==(expected>=0).all()
    if jacobian:assert result['smooth_jacobian'].shape==(len(population.layout),len(point))
    else:assert result['smooth_jacobian'] is None


def test_all_group_gradients_match_complete_nonlinear_directional_replays(tmp_path):
    base,poses,point,_=prepare(tmp_path);population=BasisPosePopulation(base,poses);result=population.evaluate(point)
    for seed in [17,43,'last']:
        direction=np.eye(len(point))[-1] if seed=='last' else np.random.default_rng(seed).normal(size=len(point));direction/=np.linalg.norm(direction);step=1e-6
        a=population.evaluate(point+step*direction,jacobian=False)['smooth_margins'];b=population.evaluate(point-step*direction,jacobian=False)['smooth_margins']
        np.testing.assert_allclose(result['smooth_jacobian']@direction,(a-b)/(2*step),atol=2e-5,rtol=1e-4)


def test_more_than_one_backend_block_retains_every_duplicate_observation_and_column(tmp_path):
    base,poses,point,_=prepare(tmp_path);repeated=[poses[0]]*260;population=BasisPosePopulation(base,repeated)
    assert population.report['groups']>512 and population.report['backend_partitions']>=2
    result=population.evaluate(point);layout=population.layout
    assert len(result['report']['groups_report'])==len(layout) and result['report']['pose_observations']==260
    assert result['report']['pose_rows']==260*poses[0].report['rows'] and result['smooth_jacobian'].shape==(len(layout),len(point))
    first=base.report['native_keys']
    np.testing.assert_array_equal(result['smooth_jacobian'][first:first+2],result['smooth_jacobian'][-2:])
    np.testing.assert_array_equal(result['exact_margins'][first:first+2],result['exact_margins'][-2:])


def test_explicit_joint_bands_may_vary_while_source_rotation_units_stay_bound(tmp_path):
    base,poses,point,helper=prepare(tmp_path);strict=helper(poses[0].report['time_s'],bands=base._caps*.5)
    result=BasisPosePopulation(base,[poses[0],strict]).evaluate(point,jacobian=False)
    assert result['report']['observation_world_caps_sha256'][0]!=result['report']['observation_world_caps_sha256'][1]
    rows=np.r_[poses[0].evaluate(point,jacobian=False)['margins'],strict.evaluate(point,jacobian=False)['margins']]
    assert result['original_margins'][-len(rows):].tobytes()==rows.tobytes()


@pytest.mark.parametrize('fault',['empty','tuple','wrong_helper','foreign_actor','seed','rotation_caps','jac_zero','jac_bool','jac_small','work_small','temperature_bool','temperature_zero'])
def test_incomplete_domains_and_budgets_reject_before_any_population_backend(tmp_path,monkeypatch,fault):
    base,poses,point,helper=prepare(tmp_path);kwargs={}
    if fault=='empty':poses=[]
    elif fault=='tuple':poses=tuple(poses)
    elif fault=='wrong_helper':poses=[None]
    elif fault=='foreign_actor':
        other=tmp_path/'other';other.mkdir();poses=[prepare(other)[0]]
    elif fault=='seed':poses=[helper(poses[0].report['time_s'],seed=base._mapper.seed*.9)]
    elif fault=='rotation_caps':poses=[helper(poses[0].report['time_s'],degrees=[15.]*len(base._mapper.nodes))]
    elif fault=='jac_zero':kwargs['maximum_jacobian_bytes']=0
    elif fault=='jac_bool':kwargs['maximum_jacobian_bytes']=True
    elif fault=='jac_small':kwargs['maximum_jacobian_bytes']=1
    elif fault=='work_small':kwargs['maximum_working_bytes']=1
    elif fault=='temperature_bool':kwargs['temperature']=True
    else:kwargs['temperature']=0.
    monkeypatch.setattr(module,'CompleteMaxRows',lambda *a,**k:pytest.fail('invalid population allocated backend'))
    with pytest.raises(ValueError):BasisPosePopulation(base,poses,**kwargs)


def test_unobserved_full_source_channel_change_is_caught_before_pose(tmp_path,monkeypatch):
    base,poses,point,_=prepare(tmp_path);population=BasisPosePopulation(base,poses)
    selected={(n,'rotation') for n in base.report['rotation_nodes']}
    last_observed=max(h.report['time_s'] for h in [base,*poses])
    channel=next(c for c in base._model.actor['sampler'].channels if c[:2] not in selected and len(c[2])>=3 and float(c[2][-2])>last_observed);channel[3][-1,0]+=.0001
    for h in [base,*poses]:h._check()
    for h in poses:monkeypatch.setattr(h,'evaluate',lambda *a,**k:pytest.fail('changed source evaluated pose'))
    with pytest.raises(ValueError):population.evaluate(point)


def test_reports_input_list_and_outputs_cannot_mutate_bound_population(tmp_path):
    base,poses,point,_=prepare(tmp_path);population=BasisPosePopulation(base,poses);before=population.evaluate(point);poses.clear()
    expected=before['smooth_jacobian'].copy();before['smooth_jacobian'][:]=99;before['original_margins'][:]=99;population.layout.clear();population.report['observation_times_s'].clear()
    after=population.evaluate(point);np.testing.assert_array_equal(after['smooth_jacobian'],expected);assert after['report']['pose_observations']==3


@pytest.mark.parametrize('fault',['short','nan','infinite','bool','outside','int_min','jacobian_mode'])
def test_invalid_points_reject_before_backend_allocation(tmp_path,monkeypatch,fault):
    base,poses,point,_=prepare(tmp_path);population=BasisPosePopulation(base,poses);kwargs={}
    if fault=='short':point=point[:-1]
    elif fault=='nan':point[0]=np.nan
    elif fault=='infinite':point[0]=np.inf
    elif fault=='bool':point=point>0
    elif fault=='outside':point[0]=1.01
    elif fault=='int_min':point=np.full(len(point),np.iinfo(np.int64).min,dtype=np.int64)
    else:kwargs['jacobian']=1
    monkeypatch.setattr(module,'CompleteMaxRows',lambda *a,**k:pytest.fail('invalid point allocated backend'))
    with pytest.raises(ValueError):population.evaluate(point,**kwargs)
