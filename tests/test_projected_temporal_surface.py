import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from projected_temporal_surface import ProjectedTemporalSurface,projection
from paired_hand_trajectory import TemporalSurface


class Actor:
    def __init__(self,rng,dim):
        self.local=np.zeros((3,7,4,4));self.dim=dim
        self.skin_nodes=rng.integers(0,7,(11,4));self.skin_points=rng.normal(size=(11,4,4));self.skin_points[:,:,-1]=1
        self.weights=rng.random((11,4));self.weights/=self.weights.sum(axis=1)[:,None]
        self.rotation=Rotation.from_rotvec(rng.normal(size=3)).as_matrix();self.translation=rng.normal(size=3)
        self.world=rng.normal(size=(7,4,4));self.derivative=rng.normal(size=(7,4,4,dim))

    def world_pair(self,frame,x):
        return self.world+np.einsum('nijd,d->nij',self.derivative,x),self.derivative

    def skin_pair(self,frame,x,vertices):
        world,jac=self.world_pair(frame,x);points=[];derivatives=[]
        for v in vertices:
            p=np.zeros(3);j=np.zeros((3,self.dim))
            for node,local,weight in zip(self.skin_nodes[v],self.skin_points[v],self.weights[v]):
                p+=weight*(world[node]@local)[:3]
                j+=weight*np.einsum('ijd,j->id',jac[node,:3],local)
            points.append(self.rotation@p+self.translation);derivatives.append(self.rotation@j)
        return np.asarray(points),np.asarray(derivatives)


def fixture():
    rng=np.random.default_rng(781);actors=[Actor(rng,3),Actor(rng,5)];fitter=SimpleNamespace(actors=actors,sizes=[3,5])
    records=[dict(source=0,target=1,points=[[2,[1,1,8],[.1,.3,.6],[.2,-.3,.9]],[2,[0,4,7],[0.,.5,.5],[1.,0.,0.]]]),dict(source=1,target=0,points=[[5,[8,2,0],[.4,.2,.4],[.6,.6,-.6]]])]
    return fitter,records,rng


@pytest.mark.parametrize('frame',[0.,.25,1.,1.5,2.])
def test_projection_matches_independent_loop_skin_and_control_derivative(frame):
    fitter,records,rng=fixture();surface=ProjectedTemporalSurface(fitter,frame,records);reference=TemporalSurface(fitter,frame,records);x=rng.normal(size=8)
    found=surface.clearance(x,.013);expected=reference.clearance(x,.013)
    for a,b in zip(found,expected):np.testing.assert_allclose(a,b,rtol=1e-12,atol=1e-12)
    direction=rng.normal(size=8);step=1e-5
    difference=(surface.clearance(x+direction*step)[0]-surface.clearance(x-direction*step)[0])/(2*step)
    np.testing.assert_allclose(difference,found[1]@direction,atol=1e-9)


def test_records_frozen_and_empty_constraints_preserve_shape():
    fitter,records,rng=fixture();x=rng.normal(size=8);surface=ProjectedTemporalSurface(fitter,.5,records);before=surface.clearance(x)
    records[0]['points'][0][2][0]=5
    for a,b in zip(before,surface.clearance(x)):np.testing.assert_array_equal(a,b)
    gaps,jac=ProjectedTemporalSurface(fitter,.5,[]).clearance(x)
    assert gaps.shape==(0,) and jac.shape==(0,8)


@pytest.mark.parametrize('fault',['negative_vertex','fractional_vertex','nonfinite_normal','bad_shape','same_actor','bad_frame','bad_control'])
def test_invalid_projection_rejected(fault):
    fitter,records,rng=fixture();frame=.5;x=np.zeros(8)
    if fault=='negative_vertex':records[0]['points'][0][0]=-1
    if fault=='fractional_vertex':records[0]['points'][0][0]=.1
    if fault=='nonfinite_normal':records[0]['points'][0][3][0]=np.nan
    if fault=='bad_shape':records[0]['points'][0][2]=[1,0]
    if fault=='same_actor':records[0]['target']=0
    if fault=='bad_frame':frame=3.
    if fault=='bad_control':x[0]=np.inf
    with pytest.raises(ValueError):ProjectedTemporalSurface(fitter,frame,records).clearance(x)
