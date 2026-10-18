from pathlib import Path
import sys
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_mesh_jacobian import CoupledMeshJacobian
from mesh_penetration_gradient import MeshPenetration


def data():
    target=np.array([[0.,0,0],[1.,0,0],[0,1.,0],[0,0,1.]])
    faces=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
    source=np.array([[.1,.2,.25],[.35,.1,.2],[.2,.35,.1],[2.,2,2]])
    rng=np.random.default_rng(15);sj=rng.normal(size=(4,3,3))*.02;tj=rng.normal(size=(4,3,3))*.02
    return faces,source,target,sj,tj


@pytest.mark.parametrize('mode',['auditor','minimum'])
@pytest.mark.parametrize('chunk',[1,3,128])
def test_all_points_and_actor_columns_match_original_backward(mode,chunk):
    faces,s,t,sj,tj=data();op=CoupledMeshJacobian(faces,distance_mode=mode);depth,audit,j,receipt=op.linearize(s,t,sj,tj,[0,1,2],[3,4,5],6,chunk_points=chunk)
    def fn(x):
        a=torch.tensor(s)+torch.einsum('vic,c->vi',torch.tensor(sj),x[:3]);b=torch.tensor(t)+torch.einsum('vic,c->vi',torch.tensor(tj),x[3:])
        return MeshPenetration(faces,distance_mode=mode,maximum_records=1)(a,b)
    x=torch.zeros(6,dtype=torch.float64);np.random.seed(20261018);expected=torch.autograd.functional.jacobian(fn,x).numpy()
    assert j.shape==(4,6) and np.allclose(j,expected,rtol=1e-11,atol=1e-12) and depth[-1]==audit[-1]==0 and np.array_equal(j[-1],np.zeros(6))
    assert receipt['all_source_rows_returned'] and receipt['complete_control_columns']==6 and receipt['source_and_target_gradients']


def test_shared_rigid_translation_columns_cancel_without_losing_other_columns():
    faces,s,t,_,_=data();sj=np.tile(np.eye(3),(4,1,1));tj=sj.copy();op=CoupledMeshJacobian(faces,distance_mode='minimum')
    _,_,j,_=op.linearize(s,t,sj,tj,[0,1,2],[0,1,2],4)
    assert np.max(abs(j))<1e-14 and j.shape==(4,4)


def test_arbitrary_column_maps_and_returned_receipts_are_owned():
    faces,s,t,sj,tj=data();op=CoupledMeshJacobian(faces,distance_mode='minimum',maximum_records=1)
    _,audit,j,receipt=op.linearize(s,t,sj,tj,[2,0,4],[1,3,5],6);saved=j.copy();receipt['source_control_columns'][0]=99;audit[:]=99
    assert op.records[0]['source_control_columns']==[2,0,4] and np.all(op.last_auditor_depths<99) and np.array_equal(j,saved)
    with pytest.raises(ValueError):op.linearize(s,t,sj,tj,[2,0,4],[1,3,5],6)


@pytest.mark.parametrize('fault',['shape','jac_shape','nan','complex','bool','map_length','duplicate_map','outside_map','map_type','column_count','chunk','budget'])
def test_incomplete_or_unbounded_linearizations_reject(fault):
    faces,s,t,sj,tj=data();sm=[0,1,2];tm=[3,4,5];count=6;options={}
    if fault=='shape':s=s[:,:2]
    elif fault=='jac_shape':sj=sj[:2]
    elif fault=='nan':sj[0,0,0]=np.nan
    elif fault=='complex':tj=tj.astype(complex)
    elif fault=='bool':sj=np.zeros_like(sj,dtype=bool)
    elif fault=='map_length':sm=sm[:2]
    elif fault=='duplicate_map':sm=[0,0,2]
    elif fault=='outside_map':tm=[3,4,6]
    elif fault=='map_type':sm=[False,1,2]
    elif fault=='column_count':count=True
    elif fault=='chunk':options['chunk_points']=0
    else:options['maximum_bytes']=1
    with pytest.raises(ValueError):CoupledMeshJacobian(faces).linearize(s,t,sj,tj,sm,tm,count,**options)
