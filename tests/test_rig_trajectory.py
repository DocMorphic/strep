import copy
import numpy as np
import pytest
from test_rig_clearance import setup
from rig_trajectory_fit import TrajectoryFitter
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits


def fixture(frames=5):
    rig,world,local,spec,targets=setup(frames)
    ids=spec['patches']['Right']['vertices'][:4]
    support=dict(vertices=ids,start_frame=0,end_frame_exclusive=frames,target_position_m=rig.vertices(world[0])[ids].mean(axis=0).tolist(),provenance='Synthetic test constraint, not motion annotation',side='Right')
    return rig,world,local,spec,targets,support


def test_trajectory_and_actual_rotation_constraint_jacobians():
    rig,world,local,spec,targets,s=fixture()
    f=TrajectoryFitter(rig,spec,local,targets,np.ones(5),[s])
    rng=np.random.default_rng(73)
    for frame in (0,1,2,4):
        x=rng.normal(size=len(f.bounds))*.005
        for n in range(5):
            if n!=frame:f.accept(n,rng.normal(size=len(f.bounds))*.002)
        r,j=f.trajectory_pair(frame,x);c,cj=f.constraints(frame,x)
        for k in range(len(x)):
            d=np.eye(len(x))[k]*1e-7
            np.testing.assert_allclose(j[:,k],(f.trajectory_pair(frame,x+d)[0]-f.trajectory_pair(frame,x-d)[0])/2e-7,atol=5e-7,rtol=4e-5)
            np.testing.assert_allclose(cj[:,k],(f.constraints(frame,x+d)[0]-f.constraints(frame,x-d)[0])/2e-7,atol=8e-5,rtol=8e-5)


def test_explicit_support_fit_reduces_drift_and_preserves_bounds(tmp_path):
    rig,world,local,spec,targets,s=fixture(7)
    local[:]=local[0]
    root=spec['root_node']
    local[:,root,0,3]+=np.array([0,0,.004,.008,.004,0,0])
    base=rig.vertices(world[0]);targets={k:np.full(7,base[p['vertices'],1].min()) for k,p in spec['patches'].items()}
    # Target remains at the initial footprint; the synthetic input moves it.
    f=TrajectoryFitter(rig,spec,local,targets,np.array([0,.5,1,1,1,.5,0]),[s])
    initial=f.positions.copy();spec['max_nfev']=20
    with threadpool_limits(limits=1):values,records,_=f.solve(tmp_path,max_sweeps=3)
    ids=s['vertices'];target=s['target_position_m']
    assert np.linalg.norm(f.positions[3,ids].mean(axis=0)-target)<np.linalg.norm(initial[3,ids].mean(axis=0)-target)
    assert np.array_equal(values[[0,-1]],np.zeros_like(values[[0,-1]]))
    assert np.all(np.abs(values)<=f.bounds*f.envelope[:,None]+1e-9)
    for i,x in enumerate(values):assert f.constraints(i,x)[0].min()>-1e-7
    assert all(r['cost_after']<=r['cost_before'] for r in records)
    rotations=f.locals[:,f.nodes,:3,:3]
    steps=Rotation.from_matrix((rotations[:-1].transpose(0,1,3,2)@rotations[1:]).reshape(-1,3,3)).magnitude().reshape(6,-1)
    assert np.all(steps<=f.rotation_limits+1e-7)


@pytest.mark.parametrize('change',[{'end_frame_exclusive':10},{'target_position_m':[0,float('nan'),0]},{'vertices':[-1]},{'provenance':''},{'side':'unknown'}])
def test_invalid_support_rejected(change):
    rig,_,local,spec,targets,s=fixture();s.update(change)
    with pytest.raises(ValueError):TrajectoryFitter(rig,spec,local,targets,np.ones(5),[s])


def test_overlapping_supports_rejected():
    rig,_,local,spec,targets,s=fixture()
    with pytest.raises(ValueError,match='Overlapping'):TrajectoryFitter(rig,spec,local,targets,np.ones(5),[s,copy.deepcopy(s)])


def test_coordinate_gradient_matches_independent_whole_trajectory_energy():
    from verify_trajectory_fit import energy
    rig,world,local,spec,targets,s=fixture()
    f=TrajectoryFitter(rig,spec,local,targets,np.ones(5),[s])
    original_world=f.world.copy();original_points=f.positions.copy();original_local=f.locals.copy()
    for frame in range(5):f.accept(frame,np.random.default_rng(frame+81).normal(size=len(f.bounds))*.003)
    frame=2;x=f.values[frame].copy();res,jac=f.trajectory_pair(frame,x);gradient=2*jac.T@res
    request={'targets_m':{k:v.tolist() for k,v in targets.items()}}
    def whole(candidate):
        w=f.world.copy();p=f.positions.copy();l=f.locals.copy()
        w[frame],l[frame]=f.pose(frame,candidate);p[frame]=rig.vertices(w[frame])
        return energy(w,p,l,original_world,original_points,original_local,spec,request,[s],f.settings)['total']
    for k in range(len(x)):
        d=np.eye(len(x))[k]*1e-7
        assert gradient[k]==pytest.approx((whole(x+d)-whole(x-d))/2e-7,abs=1e-5,rel=5e-5)
