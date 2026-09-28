import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from skin_edit_displacement_bound import skin_displacement_bound


def test_chain_bound_covers_coupled_rotations_and_mixed_skin_weights():
    parents=np.array([-1,0,1]);offsets=np.array([[0,0,0],[.04,0,0],[.03,0,0]])
    indices=np.array([[1,2],[0,2]]);weights=np.array([[.3,.7],[.2,.8]])
    points=np.array([[[.01,.02,0],[.02,.01,0]],[[.1,.02,0],[.03,0,.01]]]);limits=np.array([0.,.2,.4])
    bound=skin_displacement_bound(indices,weights,points,parents,np.linalg.norm(offsets,axis=1),limits)
    def pose(angles):
        r=[];p=[]
        for j,parent in enumerate(parents):
            local=Rotation.from_rotvec(angles[j]).as_matrix()
            r.append(local if parent<0 else r[parent]@local)
            p.append(np.zeros(3) if parent<0 else p[parent]+r[parent]@offsets[j])
        r=np.array(r);p=np.array(p)
        return ((np.einsum('vkij,vkj->vki',r[indices],points)+p[indices])*weights[:,:,None]).sum(1)
    baseline=pose(np.zeros((3,3)));rng=np.random.default_rng(716)
    for _ in range(300):
        directions=rng.normal(size=(3,3));directions/=np.linalg.norm(directions,axis=1)[:,None]
        angles=directions*(limits*rng.uniform(size=3))[:,None]
        assert np.all(np.linalg.norm(pose(angles)-baseline,axis=1)<=bound+1e-12)
    np.testing.assert_array_equal(skin_displacement_bound(indices,weights,points,parents,np.linalg.norm(offsets,axis=1),np.zeros(3)),0)


def test_single_hinge_bound_is_tight_for_opposite_budget_endpoints():
    limit=.3;radius=.08
    indices=np.array([[0]]);weights=np.array([[1.]])
    local=np.array([[[radius,0,0]]]);parents=np.array([-1]);lengths=np.array([0.])
    bound=skin_displacement_bound(indices,weights,local,parents,lengths,np.array([2*limit]))[0]
    a=Rotation.from_rotvec([0,0,-limit]).apply(local[0,0]);b=Rotation.from_rotvec([0,0,limit]).apply(local[0,0])
    np.testing.assert_allclose(bound,np.linalg.norm(a-b),atol=1e-14)
