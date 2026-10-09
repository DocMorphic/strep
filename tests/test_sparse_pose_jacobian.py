"""Exact derivative parity with full-skin maxima and eight LBS influences."""
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_pose_restoration import RestorationProblem
from support_contact_v8 import rodrigues
from object_geometry import Geometry
from sparse_pose_jacobian import SparsePoseJacobian


class FixtureProblem(RestorationProblem):
    def __init__(self,grouping,shape):
        self.t=lambda a:torch.as_tensor(a,dtype=torch.float64)
        self.dim=4;self.limits=np.array([.4]);self.cache=None;self.frame=1;self.grouping=grouping;self.headroom_m=1e-6
        points=np.array([[.02,-.2,.03],[.09,-.12,.03],[-.05,-.08,.06],[.08,-.05,-.04],[-.07,-.03,-.01],[.04,-.01,.05]])
        self.indices=np.tile([0,1,0,1,0,1,0,1],(len(points),1))
        weights=np.tile([.1,.2,.1,.15,.1,.15,.1,.1],(len(points),1))
        self.weights=self.t(weights);self.bind=self.t(np.repeat(points[:,None],8,axis=1))
        self.contacts=[dict(region='LeftHand',vertex=0,target=[.03,.3,.01])];self.point_limits=np.array([.00499])
        self.normals=[('palm',np.array([[0,1,2]]),self.t([.2,0.,np.sqrt(.96)]))]
        self.config={'normal_tolerance_degrees':10.,'clearance_m':.002}
        self.objects=[(Geometry(shape,(.35,.45,.3) if shape=='box' else (.16,.3) if shape=='cylinder' else (.18,)),
            'object',self.t([[.03,.28,.03]]),self.t(np.eye(3)[None]))]
        self.margins={'object':np.linspace(1e-5,.00201,len(points))}
        self.vertex_groups=[('first',np.array([0,1,2])),('second',np.array([3,4,5]))]
        self.references={n:self.t(np.broadcast_to([[0,.4,0],[.08,.4,.02]],(3,2,3)).copy()) for n in ['raw','limb','previous']}
        self.references['raw'][1,0,0]=.004
        self.neighbors={0:self.t([[0,.4,0],[.08,.4,.02]]),2:self.t([[.001,.4,0],[.08,.4,.02]])}
        self.labels=['point','normal','floor']+(['object:first','object:second'] if grouping=='native-joint' else ['object'])
        self.labels+=['body']*(6 if grouping=='native-joint' else 3)

    def fk(self,x,*,vertices=True):
        r=rodrigues(x[:3][None])[0];rot=torch.stack([r,r])
        root=torch.stack([x[-1]*0,x[-1]+.4,x[-1]*0])
        positions=torch.stack([root,root+r@self.t([.08,0,.02])])
        vertices=(((rot[self.indices]@self.bind[:,:,:,None]).squeeze(-1)+positions[self.indices])*self.weights[:,:,None]).sum(1) if vertices else None
        return rot,positions,rot,vertices


def test_sparse_derivatives_keep_full_skin_selection_but_skip_discarded_mesh(monkeypatch):
    p=FixtureProblem('native-joint','box');calls=[];original=p.fk
    def record(x,*,vertices=True):
        calls.append((vertices,torch.is_grad_enabled()))
        return original(x,vertices=vertices)
    monkeypatch.setattr(p,'fk',record)
    sparse=SparsePoseJacobian(p,row_chunk=4);x=np.array([.03,-.02,.01,.003])
    sparse(x)
    assert calls==[(True,False),(False,True)]
    calls.clear();sparse.vector_linearization(x)
    assert calls==[(False,True)]


@pytest.mark.parametrize('grouping',['global','native-joint'])
@pytest.mark.parametrize('shape',['box','sphere','cylinder'])
@pytest.mark.parametrize('row_chunk',[None,4,16])
def test_sparse_values_and_every_derivative_match_dense_for_all_primitives(grouping,shape,row_chunk):
    p=FixtureProblem(grouping,shape);sparse=SparsePoseJacobian(p,row_chunk=row_chunk)
    for x in [np.array([.03,-.02,.01,.003]),np.array([-.04,.03,.015,.007])]:
        dense_values,dense_jac=p.pair(x);values,jac=sparse(x)
        np.testing.assert_allclose(values,dense_values,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(jac,dense_jac,rtol=1e-10,atol=1e-10)
        assert sparse.dependencies['original_vertices']==6 and sparse.dependencies['all_maximum_ties_retained']
        assert len(values)==len(p.labels)+1


def test_floor_and_object_maximum_ties_keep_all_dependent_vertices():
    p=FixtureProblem('native-joint','box')
    p.bind[1]=p.bind[0];p.bind[4]=p.bind[5];p.margins['object'][:]=1e-5
    p.contacts=[];p.normals=[];p.labels=['floor','object1','object2']+['body']*6
    x=np.zeros(4);sparse=SparsePoseJacobian(p,row_chunk=16);values,jac=sparse(x);dense_values,dense_jac=p.pair(x)
    np.testing.assert_allclose(values,dense_values,rtol=1e-12,atol=1e-12)
    np.testing.assert_allclose(jac,dense_jac,rtol=1e-10,atol=1e-10)
    assert sparse.dependencies['active_vertices']>=4


def test_changing_original_row_population_is_rejected():
    p=FixtureProblem('global','sphere');p.labels.pop()
    with pytest.raises(ValueError,match='Complete original'):SparsePoseJacobian(p)(np.zeros(4))


@pytest.mark.parametrize('x',[np.zeros(3),np.array([0,0,0,float('nan')])])
def test_invalid_controls_rejected_before_pose_query(x):
    p=FixtureProblem('global','box')
    p.fk=lambda x:pytest.fail('Invalid controls reached the pose query')
    with pytest.raises(ValueError):SparsePoseJacobian(p)(x)


def test_all_vector_reference_populations_match_original_rows_and_derivatives():
    p=FixtureProblem('native-joint','box');sparse=SparsePoseJacobian(p,row_chunk=16);x=np.array([.03,-.02,.01,.003])
    v=sparse.vector_linearization(x);values,jac=sparse(x)
    offsets=v['offsets'];derivatives=v['jacobian'];radii=v['limits'];scales=v['scales'];distance=v['distance'];rows=v['rows']
    length=np.linalg.norm(offsets,axis=1)
    slacks=np.where(distance,(radii-length)/scales,1-length**2/radii**2)
    gradients=np.where(distance[:,None],-np.einsum('rk,rkd->rd',offsets,derivatives)/np.maximum(length,1e-12)[:,None]/scales[:,None],
        -2*np.einsum('rk,rkd->rd',offsets,derivatives)/radii[:,None]**2)
    for row in set(rows):
        active=(rows==row)&(slacks==slacks[rows==row].min())
        np.testing.assert_allclose(slacks[active],values[row],rtol=1e-11,atol=1e-11)
        np.testing.assert_allclose(gradients[active].mean(0),jac[row],rtol=1e-9,atol=1e-9)
    for row in range(5,11):assert np.sum(rows==row)==3
    assert np.sum(distance)==2 and len(v['offsets'])==21
    direction=np.array([.2,-.3,.1,.4]);step=1e-6
    plus=sparse.vector_linearization(x+step*direction);minus=sparse.vector_linearization(x-step*direction)
    np.testing.assert_allclose((plus['offsets']-minus['offsets'])/(2*step),np.einsum('rkd,d->rk',derivatives,direction),rtol=1e-6,atol=1e-8)


def test_geometry_vectors_reject_unsupported_grouping_before_fk():
    p=FixtureProblem('global','box');p.fk=lambda x:pytest.fail('Unsupported vector grouping reached FK')
    with pytest.raises(ValueError):SparsePoseJacobian(p).vector_linearization(np.zeros(4))
