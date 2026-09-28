import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from rig_clearance_fit import ClearanceFitter,foot_regions,native_heights,right_jacobian
from rig_asset import RigAsset
from target_rig_contact import baseline
from rig_contact_authoring import empty_spec
from scipy.spatial.transform import Rotation


def setup(frames=3):
    folder=ROOT/'reports/rig-jobs/20260926-231829-75e87cd5/transfer'
    report=read(folder/'report.json');report['frames']=frames
    rig=RigAsset.load(folder/'character.glb');world,local=baseline(rig,frames)
    spec=empty_spec(report);spec['patches']={k:dict(vertices=v.tolist()) for k,v in foot_regions(rig,report['mapping']).items()}
    targets={k:np.zeros(frames) for k in spec['patches']}
    return rig,world,local,spec,targets


def test_skin_and_objective_jacobian_matches_independent_finite_difference():
    rig,world,local,spec,targets=setup();f=ClearanceFitter(rig,spec,local,targets,np.ones(3),np.array([rig.vertices(w) for w in world]))
    x=np.random.default_rng(53).normal(size=len(f.bounds))*.014
    neighbors=[np.zeros_like(x),x*.5]
    height,j=f.height_jacobian(1,x)
    np.testing.assert_allclose(height,rig.vertices(f.pose(1,x)[0])[:,1],atol=1e-10)
    residual,jac=f.objective_pair(1,x,neighbors)
    _,surface_jac=f.surface_jacobian(1,x)
    for column in range(len(x)):
        d=np.eye(len(x))[column]*1e-7
        independent=(rig.vertices(f.pose(1,x+d)[0])[:,1]-rig.vertices(f.pose(1,x-d)[0])[:,1])/2e-7
        np.testing.assert_allclose(j[:,column],independent,atol=3e-8,rtol=2e-5)
        xyz=(rig.vertices(f.pose(1,x+d)[0])-rig.vertices(f.pose(1,x-d)[0]))/2e-7
        np.testing.assert_allclose(surface_jac[:,:,column],xyz,atol=3e-8,rtol=2e-5)
        numeric=(f.objective_residual(1,x+d,neighbors)-f.objective_residual(1,x-d,neighbors))/2e-7
        np.testing.assert_allclose(jac[:,column],numeric,atol=4e-7,rtol=3e-5)


def test_so3_jacobian_at_zero_and_finite_rotation():
    for x in [np.zeros(3),np.array([.3,-.4,.1])]:
        r=Rotation.from_rotvec(x).as_matrix()
        for i in range(3):
            d=np.eye(3)[i]*1e-7
            numeric=Rotation.from_matrix(r.T@Rotation.from_rotvec(x+d).as_matrix()).as_rotvec()/1e-7
            np.testing.assert_allclose(right_jacobian(x)[:,i],numeric,atol=2e-8)


@pytest.mark.parametrize('envelope',[[0,1],[0,float('nan'),1],[0,1.01,0],[0,-.1,0]])
def test_invalid_envelope(envelope):
    rig,_,local,spec,targets=setup()
    with pytest.raises(ValueError,match='envelope'):ClearanceFitter(rig,spec,local,targets,envelope)


def test_solver_preserves_frozen_edges_and_obeys_neighbor_limits(tmp_path):
    from threadpoolctl import threadpool_limits
    rig,world,local,spec,targets=setup(5)
    # Synthetic constant pose: targets demand a small rise only in the center.
    local[:]=local[0];spec['max_nfev']=10
    envelope=np.array([0,.5,1,.5,0.])
    base=rig.vertices(world[0]);targets={k:np.full(5,base[p['vertices'],1].min()+.01) for k,p in spec['patches'].items()}
    fitter=ClearanceFitter(rig,spec,local,targets,envelope)
    with threadpool_limits(limits=1):values,records,_=fitter.solve(tmp_path,max_sweeps=2)
    assert np.array_equal(values[[0,-1]],np.zeros_like(values[[0,-1]]))
    assert np.all(np.abs(values)<=fitter.bounds*envelope[:,None]+1e-9)
    assert np.linalg.norm(np.diff(values[:,:3],axis=0),axis=1).max()<=spec['limits']['root_step_m']+1e-9
    assert np.linalg.norm(np.diff(values[:,3:].reshape(5,-1,3),axis=0),axis=2).max()<=np.radians(spec['limits']['joint_step_degrees'])+1e-9
    assert all(r['cost_after']<=r['cost_before'] for r in records)
    assert np.linalg.norm(values[2])>1e-5
