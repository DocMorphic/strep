from pathlib import Path
import sys
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from skin_pose_jacobian import SkinPoseJacobian
from linear_skin_operator import LinearSkinOperator


def data(width=8):
    rng=np.random.default_rng(19);ids=rng.integers(0,5,(9,width));weights=rng.normal(size=ids.shape);weights[0,0]=0;bind=rng.normal(size=ids.shape+(3,))
    r=np.tile(np.eye(3),(5,1,1));p=rng.normal(size=(5,3));dr=rng.normal(size=(5,3,3,6));dp=rng.normal(size=(5,3,6))
    return ids,weights,bind,r,p,dr,dp


@pytest.mark.parametrize('width',[1,4,8])
@pytest.mark.parametrize('chunk',[1,4,128])
def test_every_influence_and_column_matches_original_sparse_autograd(width,chunk):
    ids,w,b,r,p,dr,dp=data(width);skin=SkinPoseJacobian(ids,w,b,5);v,j=skin.frame(r,p,dr,dp,chunk_vertices=chunk)
    original=LinearSkinOperator(torch.tensor(ids),torch.tensor(w),torch.tensor(b),5)
    def fn(x):
        rot=torch.tensor(r)+torch.einsum('jabc,c->jab',torch.tensor(dr),x);pos=torch.tensor(p)+torch.einsum('jac,c->ja',torch.tensor(dp),x)
        return original(rot[None],pos[None])[0]
    x=torch.zeros(6,dtype=torch.float64);reference=fn(x).numpy();expected=torch.autograd.functional.jacobian(fn,x).numpy()
    assert v.shape==(9,3) and j.shape==(9,3,6) and np.allclose(v,reference,rtol=1e-12,atol=1e-12) and np.allclose(j,expected,rtol=1e-12,atol=1e-12)


def test_coefficients_are_owned_and_inputs_outputs_do_not_alias():
    ids,w,b,r,p,dr,dp=data();source=SkinPoseJacobian(ids,w,b,5);expected=source.frame(r,p,dr,dp);ids[:]=0;w[:]=0;b[:]=0
    actual=source.frame(r,p,dr,dp);assert all(np.array_equal(a,c) for a,c in zip(expected,actual))
    actual[0][:]=99;actual[1][:]=99;assert all(np.array_equal(a,c) for a,c in zip(expected,source.frame(r,p,dr,dp)))


@pytest.mark.parametrize('fault',['index_type','index_range','weights_shape','bind_shape','nan','complex','joint_count','constructor_budget','jacobian_shape','missing_column','pose_nan','chunk','working_budget'])
def test_invalid_or_unbounded_complete_models_reject(fault):
    ids,w,b,r,p,dr,dp=data();options={}
    if fault=='index_type':ids=ids.astype(float)
    elif fault=='index_range':ids[0,0]=5
    elif fault=='weights_shape':w=w[:2]
    elif fault=='bind_shape':b=b[:2]
    elif fault=='nan':w[0,0]=np.nan
    elif fault=='complex':b=b.astype(complex)
    elif fault=='joint_count':options['joint_count']=True
    elif fault=='constructor_budget':options['maximum_bytes']=1
    elif fault=='jacobian_shape':dr=dr[:2]
    elif fault=='missing_column':dp=dp[:,:,:-1]
    elif fault=='pose_nan':r[0,0,0]=np.nan
    with pytest.raises(ValueError):
        source=SkinPoseJacobian(ids,w,b,options.pop('joint_count',5),**options)
        if fault=='working_budget':source.maximum_bytes=1
        source.frame(r,p,dr,dp,chunk_vertices=0 if fault=='chunk' else 128)
