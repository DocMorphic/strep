"""Every selected vertex/eight influences, affine worlds and full columns."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_support_skin.py').is_file())
sys.path[:0]=[str(Path(__file__).parent),str(root/'scripts')]
from native_skin_frame_map import skin_frame_map
from native_support_skin import NativeSupportSkin


def fixture(vertices=17):
    rng=np.random.default_rng(639);skin=NativeSupportSkin.__new__(NativeSupportSkin)
    skin.nodes=rng.integers(0,5,(vertices,8));skin.weights=rng.uniform(.01,1,(vertices,8));skin.weights/=skin.weights.sum(axis=1,keepdims=True)
    skin.points=rng.normal(size=(vertices,8,4));skin.points[:,:,3]=rng.uniform(.8,1.2,(vertices,8))
    base=rng.normal(size=(5,3))*.1;a=rng.normal(size=(5,3,5))*.2;b=rng.normal(size=(5,3,5))*.05
    def worlds(value):
        world=np.broadcast_to(np.eye(4),(5,4,4)).copy();world[:,:3,:3]=Rotation.from_rotvec(base+np.einsum('nic,c->ni',a,value)).as_matrix()@np.diag([.9,1.1,1.05])
        world[:,:3,3]=np.sin(np.einsum('nic,c->ni',b,value));return world
    placement=(np.array([.7,-.2,1.3]),Rotation.from_euler('xyz',[17.,-8.,33.],degrees=True).as_matrix())
    return skin,worlds,placement


def reference(skin,world,placement,ids):
    position,rotation=placement;result=[]
    for vertex in ids:
        point=np.zeros(3)
        for slot in range(skin.nodes.shape[1]):point+=(world[skin.nodes[vertex,slot]]@skin.points[vertex,slot])[:3]*skin.weights[vertex,slot]
        result.append(rotation@point+position)
    return np.array(result)


@pytest.mark.parametrize('reduction',['vertices','centroid'])
@pytest.mark.parametrize('batch',[1,3,17])
def test_complete_affine_skin_and_every_column_match_independent_full_influence_reference(reduction,batch):
    skin,worlds,placement=fixture();value=np.linspace(-.1,.1,5);world=worlds(value);ids=np.array([16,4,9,0,2,8,7])
    jac=np.stack([(worlds(value+np.eye(5)[i]*1e-6)-worlds(value-np.eye(5)[i]*1e-6))/2e-6 for i in range(5)],axis=-1)
    budget=batch*8*3*4*8*6;points,derivative,report=skin_frame_map(skin,world,placement,ids,reduction,jacobian=jac,maximum_working_bytes=budget)
    expected=reference(skin,world,placement,ids);expected=expected.mean(axis=0,keepdims=True) if reduction=='centroid' else expected
    np.testing.assert_allclose(points,expected,atol=2e-15,rtol=2e-15)
    for column in range(5):
        delta=np.eye(5)[column]*1e-5;positive=reference(skin,worlds(value+delta),placement,ids);negative=reference(skin,worlds(value-delta),placement,ids)
        finite=(positive-negative)/2e-5;finite=finite.mean(axis=0,keepdims=True) if reduction=='centroid' else finite
        np.testing.assert_allclose(derivative[:,:,column],finite,atol=3e-10,rtol=3e-7)
    assert report['vertices']==len(ids) and report['influence_slots']==8 and report['derivative_columns']==5
    assert report['working_batch_vertices']==min(batch,len(ids)) and report['all_declared_vertices_and_influences_retained']
    assert not report['quality_approved'] and not report['release_approved']


def test_centroid_aggregates_every_point_without_allocating_full_point_jacobian():
    skin,worlds,placement=fixture(vertices=101);world=worlds(np.zeros(5));jac=np.zeros(world.shape+(5,));jac[0,:3,3,:3]=np.eye(3)
    ids=np.arange(101);budget=jac.nbytes
    with pytest.raises(ValueError,match='budget'):skin_frame_map(skin,world,placement,ids,'vertices',jacobian=jac,maximum_jacobian_bytes=budget)
    actual=skin_frame_map(skin,world,placement,ids,'centroid',jacobian=jac,maximum_jacobian_bytes=budget,maximum_working_bytes=8*3*4*8*6)
    complete=skin_frame_map(skin,world,placement,ids,'vertices',jacobian=jac)
    np.testing.assert_allclose(actual[0],complete[0].mean(0,keepdims=True),atol=0,rtol=0)
    np.testing.assert_allclose(actual[1],complete[1].mean(0,keepdims=True),atol=2e-16,rtol=2e-15)


def test_value_only_eighth_slot_and_homogeneous_coordinate_never_disappear():
    skin,worlds,placement=fixture();world=worlds(np.linspace(-.1,.1,5));ids=np.array([0,3,8]);before=copy.deepcopy(skin.__dict__)
    points,jac,report=skin_frame_map(skin,world,placement,ids,'vertices');assert jac is None and report['derivative_columns']==0
    np.testing.assert_allclose(points,reference(skin,world,placement,ids),atol=2e-15,rtol=2e-15)
    for name,expected in before.items():np.testing.assert_array_equal(getattr(skin,name),expected)
    skin.weights[:,7]=0;different=skin_frame_map(skin,world,placement,ids,'vertices')[0];assert np.max(np.abs(different-points))>.001
    skin.__dict__.update(before)
    skin.points[:,:,3]=1;different=skin_frame_map(skin,world,placement,ids,'vertices')[0];assert np.max(np.abs(different-points))>1e-6


@pytest.mark.parametrize('fault',['empty','duplicate','negative','escaping','bool_ids','float_ids','wrong_world','nan_world','bool_world','bottom_world','placement_shape','placement_scale','placement_reflection','bad_reduction','world_jac_shape','zero_columns','too_many_columns','nan_jac','bottom_jac','budget','work_budget','working_one_vertex','negative_weights','escaping_node','nan_points'])
def test_invalid_inputs_and_complete_budgets_fail_without_partial_result(fault):
    skin,worlds,placement=fixture();world=worlds(np.zeros(5));ids=np.array([0,3,8]);reduction='vertices';kwargs={}
    if fault=='empty':ids=np.array([],int)
    elif fault=='duplicate':ids=np.array([0,0])
    elif fault=='negative':ids[0]=-1
    elif fault=='escaping':ids[0]=len(skin.nodes)
    elif fault=='bool_ids':ids=ids.astype(bool)
    elif fault=='float_ids':ids=ids.astype(float)
    elif fault=='wrong_world':world=world[:,:3,:3]
    elif fault=='nan_world':world[0,0,0]=np.nan
    elif fault=='bool_world':world=world.astype(bool)
    elif fault=='bottom_world':world[0,3,0]=.1
    elif fault=='placement_shape':placement=(np.ones(2),np.eye(3))
    elif fault=='placement_scale':placement=(np.ones(3),np.eye(3)*2)
    elif fault=='placement_reflection':placement=(np.ones(3),np.diag([-1.,1.,1.]))
    elif fault=='bad_reduction':reduction='subset'
    elif fault=='budget':kwargs['maximum_jacobian_bytes']=True
    elif fault=='work_budget':kwargs['maximum_working_bytes']=64*1024**2+1
    elif fault=='working_one_vertex':kwargs['maximum_working_bytes']=8*3*4*8-1
    elif fault=='negative_weights':skin.weights[0,0]=-.1
    elif fault=='escaping_node':skin.nodes[0,0]=len(world)
    elif fault=='nan_points':skin.points[0,0,0]=np.nan
    else:
        jac=np.zeros(world.shape+(5,))
        if fault=='world_jac_shape':jac=jac[:1]
        elif fault=='zero_columns':jac=jac[...,:0]
        elif fault=='too_many_columns':jac=np.zeros(world.shape+(769,))
        elif fault=='nan_jac':jac[0,0,0,0]=np.nan
        elif fault=='bottom_jac':jac[0,3,0,0]=.1
        kwargs['jacobian']=jac
    with pytest.raises(ValueError):skin_frame_map(skin,world,placement,ids,reduction,**kwargs)
