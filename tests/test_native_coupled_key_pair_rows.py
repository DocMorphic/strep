"""Coupled native/source limits, independent finite differences and full codec."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_coupled_key_pair_rows import CoupledKeyPairRows
from test_native_seeded_region_fit import setup as single_spec


def setup(tmp_path,**settings):
    a=tmp_path/'left';b=tmp_path/'right';a.mkdir();b.mkdir()
    left=single_spec(a);right=single_spec(b)
    times=sorted(row['time_s'] for row in left.pop('observations'));right.pop('observations')
    position,rotation=right['actor']['placement'];right['actor']['placement']=(position+np.array([100.,0.,0.]),rotation.copy())
    observations=[dict(time_s=stamp,gaps=[dict(pairs=[[0,0]],normal_world=[1.,0.,0.],minimum_gap_m=2e-5,temperature_m=.01)]) for stamp in times]
    return left,right,observations,CoupledKeyPairRows(left,right,observations,**settings)


def test_complete_coupled_rows_both_native_domains_and_all_columns(tmp_path):
    left,right,observations,problem=setup(tmp_path);value=problem.initial+.012
    rows,jac=problem.evaluate(value);np.testing.assert_array_equal(rows,problem.values(value))
    expected=len(observations)*(len(left['nodes'])+len(left['actor']['rig'].joints)+len(right['nodes'])+len(right['actor']['rig'].joints)+1)+len(left['active_pairs'])+len(right['active_pairs'])
    assert len(rows)==problem.rows==expected and jac.shape==(expected,problem.size)
    assert problem.size==3*(len(left['active_pairs'])+len(right['active_pairs']))
    step=2e-6
    for column in range(problem.size):
        delta=np.eye(problem.size)[column]*step
        finite=(problem.values(value+delta)-problem.values(value-delta))/(2*step)
        np.testing.assert_allclose(jac[:,column],finite,atol=6e-6,rtol=6e-6)
    assert problem.report['original_pair_references']==2 and problem.report['jacobian_bytes']==jac.nbytes
    assert not problem.report['quality_approved'] and not problem.report['release_approved']


def test_fixed_time_still_contains_all_hard_pose_and_gap_rows(tmp_path):
    left,right,observations,p=setup(tmp_path);value=p.initial+.015;rows,jac=p.evaluate(value)
    fixed=[item for item in p.layout if item[-1]];assert {item[0] for item in fixed}=={'pose','gap'}
    for kind,stamp,side,first,last,is_fixed in fixed:assert np.count_nonzero(jac[first:last])==0
    assert any(not item[-1] for item in p.layout if item[0]=='pose')
    result=p.postcheck(p.initial)
    assert result['raw_rows'].shape==result['encoded_rows'].shape==(p.rows,)
    assert result['raw_pair_rows'].shape==result['encoded_pair_rows'].shape==(2,)
    assert result['declared_conditions_pass'] and result['original_selected'] and not result['release_approved']


def test_native_reconstruction_keeps_every_uneditable_and_frozen_key(tmp_path):
    left,right,observations,p=setup(tmp_path);value=p.initial+.02
    for side,spec in enumerate((left,right)):
        controls=p.controls(side,value);mask=np.ones(controls.shape[:2],bool)
        for key,node in spec['active_pairs']:mask[key,spec['nodes'].index(node)]=False
        np.testing.assert_array_equal(controls[mask],spec['seed_controls'][mask])
        np.testing.assert_array_equal(controls[spec['frozen_keys']],spec['seed_controls'][spec['frozen_keys']])
    value[:3]=[1.,1.,0.]
    with pytest.raises(ValueError,match='unit ball'):p.controls(0,value)


def test_specs_and_gap_contexts_are_snapshotted_but_source_changes_rejected(tmp_path):
    left,right,observations,p=setup(tmp_path);value=p.initial.copy();before=p.values(value)
    left['nodes'].reverse();left['degrees'][:]=[1.]*len(left['degrees']);left['seed_controls'][:]=0;left['active_pairs'].clear();left['frozen_keys'].clear()
    observations[0]['gaps'][0]['pairs'][0][:]=[9999,9999];observations[0]['gaps'][0]['normal_world'][:]=[0,0,0]
    np.testing.assert_array_equal(p.values(value),before)
    right['actor']['placement']=(np.array([20.,0,0]),np.eye(3))
    for operation in [lambda:p.evaluate(value),lambda:p.values(value),lambda:p.postcheck(value),lambda:p.controls(0,value)]:
        with pytest.raises(ValueError):operation()


def test_row_and_dense_jacobian_limits_reject_complete_request(tmp_path):
    left,right,observations,p=setup(tmp_path)
    for settings in [dict(maximum_rows=p.rows-1),dict(maximum_jacobian_bytes=p.rows*p.size*8-1)]:
        with pytest.raises(ValueError,match='Complete coupled'):CoupledKeyPairRows(left,right,observations,**settings)
    exact=CoupledKeyPairRows(left,right,observations,maximum_rows=p.rows,maximum_jacobian_bytes=p.rows*p.size*8)
    assert exact.evaluate(exact.initial)[1].nbytes==p.report['jacobian_bytes']


@pytest.mark.parametrize('side',[0,1])
def test_encoded_native_rows_match_actual_saved_channels(tmp_path,side):
    from native_key_contact_initializer import encode
    from native_support_clock import NativeSupportSampler
    from rig_asset import RigAsset
    from scipy.spatial.transform import Rotation
    left,right,observations,p=setup(tmp_path);spec=(left,right)[side]
    source=spec['actor'];channels=[next(c for c in source['sampler'].channels if c[:2]==(node,'rotation')) for node in spec['nodes']]
    first,last=next((a,b) for kind,t,s,a,b,fixed in p.layout if kind=='native' and s==side)
    offset=0 if side==0 else 3*len(left['active_pairs']);overshoots=0
    for i,direction in enumerate(([1.,0,0],[-1.,0,0],[0,1.,0],[0,-1.,0],[0,0,1.],[0,0,-1.],[.6,.8,0])):
        value=p.initial.copy();value[offset:offset+3]=direction;path=tmp_path/f'encoded-{side}-{i}.glb'
        index=encode(source['rig'],source['animation_index'],spec['nodes'],channels,p.controls(side,value),spec['degrees'],path)
        rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,index);expected=[]
        for key,node in spec['active_pairs']:
            track=spec['nodes'].index(node);old=channels[track];new=next(c for c in reader.channels if c[:2]==(node,'rotation'))
            fraction=(Rotation.from_quat(old[3][key]).inv()*Rotation.from_quat(new[3][key])).magnitude()/np.radians(spec['degrees'][track]);expected.append(1-fraction*fraction)
        checked=p.postcheck(value);np.testing.assert_allclose(checked['encoded_rows'][first:last],expected,atol=4e-15,rtol=0)
        overshoots+=int(expected[0]<0)
        if min(expected)<0:assert not checked['declared_conditions_pass']
    assert overshoots>0


@pytest.mark.parametrize('change',[
    'missing_endpoint','frozen_edit','duplicate_edit','wrong_clock','bad_seed',
    'bad_bands','bad_world_caps','duplicate_time','reverse_time','unknown_gap_field',
    'escaping_triangle','empty_gap_reference','unknown_observation_field',
])
def test_complete_explicit_domains_reject_invalid_requests(tmp_path,change):
    left,right,observations,p=setup(tmp_path)
    if change=='missing_endpoint':left['frozen_keys'].remove(0)
    elif change=='frozen_edit':left['active_pairs'][0]=(0,left['nodes'][0])
    elif change=='duplicate_edit':left['active_pairs'].append(left['active_pairs'][0])
    elif change=='wrong_clock':left['clock']=left['clock']+.001
    elif change=='bad_seed':left['seed_controls']=np.zeros((1,1,3))
    elif change=='bad_bands':left['degrees']=[True]*len(left['nodes'])
    elif change=='bad_world_caps':left['world_caps_m'][:]=-1.
    elif change=='duplicate_time':observations.append(copy.deepcopy(observations[-1]))
    elif change=='reverse_time':observations.reverse()
    elif change=='unknown_gap_field':observations[0]['gaps'][0]['silent_subset']=True
    elif change=='escaping_triangle':observations[0]['gaps'][0]['pairs']=[[2**31-1,0]]
    elif change=='empty_gap_reference':observations[0]['gaps'][0]['pairs']=[]
    elif change=='unknown_observation_field':observations[0]['drop_some_rows']=True
    with pytest.raises(ValueError):CoupledKeyPairRows(left,right,observations)


def test_explicit_pose_only_observations_keep_all_native_domains(tmp_path):
    left,right,observations,p=setup(tmp_path)
    for observation in observations:observation['gaps']=[]
    bounds=CoupledKeyPairRows(left,right,observations);result=bounds.postcheck(bounds.initial)
    assert bounds.report['original_pair_references']==0 and len(result['raw_pair_rows'])==len(result['encoded_pair_rows'])==0
    assert bounds.rows==p.rows-2 and result['declared_conditions_pass']


@pytest.mark.parametrize('value',[np.zeros(1),np.full(12,np.nan),np.zeros(12,dtype=bool)])
def test_bad_complete_proposals_rejected(tmp_path,value):
    left,right,observations,p=setup(tmp_path)
    for operation in [lambda:p.evaluate(value),lambda:p.values(value),lambda:p.postcheck(value)]:
        with pytest.raises(ValueError):operation()
