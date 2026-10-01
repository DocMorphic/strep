"""Bend-plane freedom keeps exact reach, native targets and dependency bounds."""
from pathlib import Path
import sys
import copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_native_support import fixture
from native_support_spec import validate
from native_support_rates import SupportRateProblem,reach_rotations
from native_support_swivel import SupportSwivelProblem
from native_leg_floor import export_rotations
from native_leg_smoothing import lifts
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from two_bone_waypoint import reach
from elbow_swivel import local_transforms
from strep import sha256


@pytest.mark.parametrize('normal',[[0,1,0],[0,.8,.6]])
def test_batched_lift_and_swivel_match_independent_reach(normal,tmp_path):
    _,rig,reader,_=fixture(tmp_path);worlds=[]
    for t in [.4,.8,1.,1.2,1.6]:
        w=reader.sample(t);bent,_=reach(w,rig.parents,1,2,3,w[3,:3,3]+[0,.015,0]);worlds.append(bent)
    worlds=np.array(worlds);local=np.array([local_transforms(w,rig.parents) for w in worlds]);nodes=[1,2,3]
    original=Rotation.from_matrix(local[:,nodes,:3,:3].reshape(-1,3,3)).as_quat().reshape(-1,3,4)
    amounts=np.array([-.003,0,.005,.002,0]);swivels=np.deg2rad([-5,3,0,5,0]);normal=np.array(normal)
    q=reach_rotations(worlds,rig.parents,nodes,amounts,normal,original,swivels)
    expected=[]
    for w,lift,theta in zip(worlds,amounts,swivels):
        _,l=reach(w,rig.parents,*nodes,w[3,:3,3]+normal*lift,radians=theta);expected.append(l[nodes,:3,:3])
    np.testing.assert_allclose(Rotation.from_quat(q.reshape(-1,4)).as_matrix().reshape(-1,3,3,3),expected,atol=1e-12,rtol=0)
    np.testing.assert_array_equal(q[-1],original[-1])
    assert not np.array_equal(q[1],original[1]) # Zero lift still permits a swivel.


def problem(tmp_path,disjoint=False):
    source,rig,reader,spec=fixture(tmp_path,plane=.23 if disjoint else .2)
    if disjoint:
        clock=reader.channels[0][2];a=spec['supports'][0];a.update(edit_keys=[0,4],stance_s=[float(clock[1]),float(clock[2])])
        b=copy.deepcopy(a);b.update(id='second',edit_keys=[6,10],stance_s=[float(clock[8]),float(clock[9])]);spec['supports'].append(b)
    _,rows=validate(spec,rig,reader,sha256(source))
    return SupportSwivelProblem(rig,reader,rows)


def test_zero_swivel_initialization_retains_bend_only_proposal(tmp_path):
    p=problem(tmp_path);base=SupportRateProblem(p.rig,p.reader,p.rows)
    a,aa=p.rotations(p.initial);b,bb=base.rotations(base.initial)
    for n in a:np.testing.assert_array_equal(a[n],b[n])
    np.testing.assert_array_equal(aa,bb)


def test_nonzero_swivels_keep_native_foot_targets_orientation_and_frozen_motion(tmp_path):
    p=problem(tmp_path);x=p.initial.copy()
    for d in p.data:x[d['swivel_ids']]=.025*np.sin(np.arange(len(d['swivel_ids']))+1)
    values,_=p.rotations(x);path=tmp_path/'swivel.glb';export_rotations(p.rig.document,p.rig.binary,values,path)
    rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,0)
    for d in p.data:
        bends=d['bend'].copy();bends[d['free']]=x[d['ids']];amounts=lifts(d['box'],bends);r=d['row'];foot=r['chain'][-1]
        for t,w,amount in zip(d['clock'],d['worlds'],amounts):
            actual=reader.sample(float(t));expected=w[foot].copy();expected[:3,3]+=r['up']*amount
            np.testing.assert_allclose(actual[foot],expected,atol=1e-7,rtol=0)
        for n in r['chain']:
            q=values[n];np.testing.assert_array_equal(q[[r['edit_keys'][0],r['edit_keys'][1]]],p.channels[n][2][r['edit_keys']])
    world=p.world(values);free=(p.times<=p.rows[0]['edit_s'][0])|(p.times>=p.rows[0]['edit_s'][1])
    np.testing.assert_array_equal(world[free],p.raw[free]);np.testing.assert_array_equal(world[:,[0,5,6]],p.raw[:,[0,5,6]])
    np.testing.assert_allclose(p.world({n:q.astype(np.float32).astype(float) for n,q in values.items()}),np.array([reader.sample(float(t)) for t in p.times]),atol=2e-14,rtol=0)


@pytest.mark.parametrize('disjoint',[False,True])
def test_swivel_sparse_graph_covers_all_finite_differences(tmp_path,disjoint):
    p=problem(tmp_path,disjoint);x=p.initial.copy()
    for d in p.data:x[d['swivel_ids']]=.01
    pattern=p.sparsity().toarray()
    for col in range(len(x)):
        h=min(1e-5,(p.upper[col]-p.lower[col])/4);z=x.copy();z[col]=min(p.upper[col]-h/2,max(p.lower[col]+h/2,z[col]));a=z.copy();b=z.copy();a[col]+=h/2;b[col]-=h/2
        changed=np.abs(p.residual(a)-p.residual(b));assert changed[pattern[:,col]==0].max(initial=0)<1e-9


@pytest.mark.parametrize('limit',[0,5.01,True,float('nan')])
def test_invalid_swivel_freedom_is_rejected_before_loading_rig(limit):
    with pytest.raises(ValueError):SupportSwivelProblem(None,None,None,swivel_limit_degrees=limit)
