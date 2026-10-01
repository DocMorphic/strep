"""Independent exact-IK and sparse derivative checks; not human realism tests."""
import sys
from pathlib import Path
import numpy as np
import pytest
import copy
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_native_support import fixture
from native_support_spec import validate
from native_support_rates import aligned,reach_rotations,SupportRateProblem
from two_bone_waypoint import align_vectors,reach
from elbow_swivel import local_transforms
from strep import sha256


def test_batch_direction_transport_matches_independent_exact_alignment():
    rng=np.random.default_rng(12);a=rng.normal(size=(50,3));b=rng.normal(size=(50,3))
    a[:3]=np.eye(3);b[:3]=-np.eye(3);b[3]=a[3]
    actual=aligned(a,b);expected=np.array([align_vectors(x,y) for x,y in zip(a,b)])
    np.testing.assert_allclose(actual,expected,atol=2e-15,rtol=0)
    np.testing.assert_allclose(np.einsum('nij,nj->ni',actual,a/np.linalg.norm(a,axis=1)[:,None]),b/np.linalg.norm(b,axis=1)[:,None],atol=2e-15,rtol=0)


@pytest.mark.parametrize('up',[[0,1,0],[0,.8,.6]])
def test_batch_reach_matches_independent_solver_including_signed_lifts(tmp_path,up):
    _,rig,reader,_=fixture(tmp_path)
    # Bend the nearly straight source so signed lowering is reachable too.
    worlds=[]
    for t in [.4,.8,1.,1.2,1.6]:
        source=reader.sample(t)
        bent,_=reach(source,rig.parents,1,2,3,source[3,:3,3]+np.array([0,.015,0]))
        worlds.append(bent)
    worlds=np.array(worlds);chain=[1,2,3];local=np.array([local_transforms(w,rig.parents) for w in worlds])
    original=Rotation.from_matrix(local[:,chain,:3,:3].reshape(-1,3,3)).as_quat().reshape(-1,3,4)
    amounts=np.array([-.003,0,.005,.002,-.001]);normal=np.array(up)
    actual=reach_rotations(worlds,rig.parents,chain,amounts,normal,original)
    expected=[]
    for w,lift in zip(worlds,amounts):
        _,changed=reach(w,rig.parents,*chain,w[3,:3,3]+normal*lift)
        expected.append(changed[chain,:3,:3])
    np.testing.assert_allclose(Rotation.from_quat(actual.reshape(-1,4)).as_matrix().reshape(-1,3,3,3),expected,atol=1e-12,rtol=0)
    np.testing.assert_array_equal(actual[1],original[1])


def problem(tmp_path):
    source,rig,reader,spec=fixture(tmp_path);_,rows=validate(spec,rig,reader,sha256(source))
    return SupportRateProblem(rig,reader,rows)


def test_proxy_world_matches_decoder_and_frozen_phases(tmp_path):
    p=problem(tmp_path)
    values={n:c[2].astype(float).copy() for n,c in p.channels.items() if n in p.nodes}
    np.testing.assert_allclose(p.world(values),p.raw,atol=2e-15,rtol=0)
    values,angles=p.rotations(p.initial);world=p.world(values)
    np.testing.assert_array_equal(world[:,[0,5,6]],p.raw[:,[0,5,6]])
    free=(p.times<=p.rows[0]['edit_s'][0])|(p.times>=p.rows[0]['edit_s'][1])
    np.testing.assert_array_equal(world[free],p.raw[free])
    assert np.isfinite(p.residual(p.initial)).all() and max(a.max() for a in angles)<45


def test_sparse_pattern_covers_every_actual_changed_residual_row(tmp_path):
    p=problem(tmp_path);pattern=p.sparsity().toarray();base=p.initial.copy()
    # Interior finite differences, including keys that bracket stance boundaries.
    for col in range(len(base)):
        x=base.copy();step=min(1e-5,(p.upper[col]-p.lower[col])/4)
        x[col]=min(p.upper[col]-step/2,max(p.lower[col]+step/2,x[col]))
        a=x.copy();b=x.copy();a[col]+=step/2;b[col]-=step/2
        delta=np.abs(p.residual(a)-p.residual(b))
        assert np.max(delta[pattern[:,col]==0],initial=0)<1e-9


def test_box_violations_and_invalid_directions_are_rejected(tmp_path):
    p=problem(tmp_path);bad=p.initial.copy();bad[0]=p.upper[0]+.001
    with pytest.raises(ValueError,match='boxes'):p.rotations(bad)
    with pytest.raises(ValueError):aligned([[0,0,0]],[[1,0,0]])


def test_quantized_proxy_matches_independent_export_decoder_at_all_audit_times(tmp_path):
    from native_leg_floor import export_rotations
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    p=problem(tmp_path);values,_=p.rotations(p.initial)
    path=tmp_path/'candidate.glb';export_rotations(p.rig.document,p.rig.binary,values,path)
    exported=RigAsset.load(path);reader=NativeSupportSampler(exported.document,exported.binary,0)
    actual=np.array([reader.sample(float(t)) for t in p.times])
    proxy=p.world({n:q.astype(np.float32).astype(float) for n,q in values.items()})
    np.testing.assert_allclose(proxy,actual,atol=2e-14,rtol=0)


def test_disjoint_same_foot_windows_keep_gap_and_sparse_dependencies(tmp_path):
    source,rig,reader,spec=fixture(tmp_path,plane=.23);clock=reader.channels[0][2]
    a=spec['supports'][0];a['edit_keys']=[0,4];a['stance_s']=[float(clock[1]),float(clock[2])]
    b=copy.deepcopy(a);b.update(id='second',edit_keys=[6,10],stance_s=[float(clock[8]),float(clock[9])]);spec['supports'].append(b)
    _,rows=validate(spec,rig,reader,sha256(source));p=SupportRateProblem(rig,reader,rows)
    values,_=p.rotations(p.initial);world=p.world(values)
    middle=np.flatnonzero(p.times==1.)
    np.testing.assert_array_equal(world[middle],p.raw[middle])
    pattern=p.sparsity().toarray()
    for col in range(len(p.initial)):
        x=p.initial.copy();h=min(1e-5,(p.upper[col]-p.lower[col])/4)
        x[col]=min(p.upper[col]-h/2,max(p.lower[col]+h/2,x[col]));a=x.copy();b=x.copy();a[col]+=h/2;b[col]-=h/2
        delta=np.abs(p.residual(a)-p.residual(b));assert np.max(delta[pattern[:,col]==0],initial=0)<1e-9


@pytest.mark.parametrize('budget',[0,2001,True,1.5])
def test_joint_search_rejects_invalid_budget_before_reading_inputs(budget):
    from native_support_rates import propose
    with pytest.raises(ValueError,match='evaluations'):propose(None,None,None,None,maximum_evaluations=budget)
