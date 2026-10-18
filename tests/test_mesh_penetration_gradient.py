from pathlib import Path
import sys
import numpy as np
import pytest
import torch
import trimesh
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from mesh_penetration_gradient import MeshPenetration
from convex_partner_surface import penetration


def fixture():
    mesh=trimesh.creation.box(extents=[2,2,2])
    source=torch.tensor([[.21,.13,.8],[.16,-.22,.7],[4.,0.,0.]],dtype=torch.float64,requires_grad=True)
    target=torch.tensor(np.asarray(mesh.vertices),dtype=torch.float64,requires_grad=True)
    return mesh,source,target


def test_complete_depths_match_existing_triangle_query_and_outside_zero():
    mesh,source,target=fixture();operator=MeshPenetration(mesh.faces);depth=operator(source,target)
    expected=np.maximum(0,trimesh.proximity.signed_distance(mesh,source.detach().numpy()))
    np.testing.assert_array_equal(depth.detach().numpy(),expected)
    before=penetration(source.detach().numpy(),target.detach().numpy(),mesh.faces)
    assert depth.max().item()==before['max_depth_m'] and depth.tolist()==pytest.approx([.2,.3,0.])
    record=operator.records[0];assert record['source_vertices']==3 and record['all_source_vertices_considered'] and record['original_triangle_mesh_queried']


def test_finite_difference_gradcheck_moves_both_bodies():
    mesh,source,target=fixture();operator=MeshPenetration(mesh.faces,maximum_records=512)
    assert torch.autograd.gradcheck(operator,(source,target),eps=1e-6,atol=1e-5,rtol=1e-4)


def test_translation_balance_and_independent_target_gradient():
    mesh,source,target=fixture();depth=MeshPenetration(mesh.faces)(source,target)
    left,right=torch.autograd.grad(depth.square().sum(),(source,target))
    assert left.abs().sum()>0 and right.abs().sum()>0 and torch.equal(left[-1],torch.zeros(3,dtype=left.dtype))
    torch.testing.assert_close(left.sum(0)+right.sum(0),torch.zeros(3,dtype=left.dtype),atol=1e-14,rtol=0)


def test_coupled_descent_rechecks_actual_depth_after_edit():
    mesh,source,target=fixture();operator=MeshPenetration(mesh.faces)
    depth=operator(source,target);loss=depth.square().sum();a,b=torch.autograd.grad(loss,(source,target))
    after=operator(source-.02*a,target-.02*b).square().sum()
    assert after<loss and operator.records[-1]['maximum_depth_m']<operator.records[0]['maximum_depth_m']


def test_nonconvex_hole_uses_actual_mesh_not_hull():
    mesh=trimesh.creation.annulus(r_min=.5,r_max=1.,height=.5,sections=16)
    points=torch.tensor([[0.,0.,0.],[.73,.02,.06]],dtype=torch.float64,requires_grad=True)
    target=torch.tensor(np.asarray(mesh.vertices),dtype=torch.float64)
    operator=MeshPenetration(mesh.faces);depth=operator(points,target)
    assert depth[0]==0 and depth[1]>0
    assert operator.records[0]['broadphase']['hull_candidates']==2


def test_chunking_preserves_all_depths_and_gradients():
    mesh,source,target=fixture();outputs=[]
    for chunk in [1,2,32]:
        operator=MeshPenetration(mesh.faces,query_batch_size=chunk);depth=operator(source,target)
        gradients=torch.autograd.grad(depth.square().sum(),(source,target));outputs.append((depth,*gradients))
    for values in outputs[1:]:
        for a,b in zip(outputs[0],values):torch.testing.assert_close(a,b,atol=1e-14,rtol=0)


def test_shared_rigid_rotation_and_translation_preserve_depth():
    mesh,source,target=fixture();rotation=torch.tensor([[0.,0.,1.],[0.,1.,0.],[-1.,0.,0.]],dtype=source.dtype)
    shift=torch.tensor([2.,3.,4.],dtype=source.dtype)
    a=MeshPenetration(mesh.faces)(source,target);b=MeshPenetration(mesh.faces)(source@rotation.T+shift,target@rotation.T+shift)
    torch.testing.assert_close(a,b,atol=1e-14,rtol=0)


@pytest.mark.parametrize('fault',['open','reverse','collapsed','nan','missing_index'])
def test_invalid_target_rejects_without_repair(fault):
    mesh,source,target=fixture();faces=mesh.faces.copy();values=target.detach().clone()
    if fault=='open':faces=faces[:-1]
    elif fault=='reverse':faces=faces[:,::-1].copy()
    elif fault=='collapsed':values[:]=0
    elif fault=='nan':values[0,0]=float('nan')
    else:faces[0,0]=len(values)
    with pytest.raises(ValueError):MeshPenetration(faces)(source,values)


def test_source_ownership_receipts_and_budget_are_explicit():
    mesh,source,target=fixture();faces=mesh.faces.copy();operator=MeshPenetration(faces,maximum_records=1);faces[:]=0
    operator(source,target);records=operator.records;records[0]['source_vertices']=999
    assert operator.records[0]['source_vertices']==3 and operator.records[0]['added_physical_tolerance_m']==0
    with pytest.raises(ValueError,match='budget'):operator(source,target)


def test_mutated_target_before_backward_rejects_stale_derivative():
    mesh,source,target=fixture();depth=MeshPenetration(mesh.faces)(source,target)
    with torch.no_grad():target[0,0]+=.001
    with pytest.raises(RuntimeError,match='modified by an inplace operation'):depth.sum().backward()


@pytest.mark.parametrize('fault',['integer','dtype','nonfinite','shape','count'])
def test_invalid_source_and_tensor_contracts_reject(fault):
    mesh,source,target=fixture()
    if fault=='integer':source=torch.zeros((3,3),dtype=torch.int64)
    elif fault=='dtype':source=source.float()
    elif fault=='nonfinite':source=torch.full((3,3),float('inf'),dtype=source.dtype)
    elif fault=='shape':source=torch.zeros((3,2),dtype=source.dtype)
    else:source=torch.zeros((32769,3),dtype=source.dtype)
    with pytest.raises(ValueError):MeshPenetration(mesh.faces)(source,target)


def test_second_derivative_is_not_silently_invented():
    mesh,source,target=fixture();depth=MeshPenetration(mesh.faces)(source,target)
    first=torch.autograd.grad(depth.sum(),source,create_graph=True)[0]
    assert not first.requires_grad
