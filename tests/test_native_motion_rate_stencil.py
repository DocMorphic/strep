"""Unchanged exact values, complete columns, nonlinear directional references."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/sampled_motion_caps.py').is_file())
sys.path[:0]=[str(Path(__file__).parent),str(root/'scripts')]
from native_motion_rate_stencil import motion_rate_stencil,METRICS
from sampled_motion_caps import features,measures


def field(metric,columns=19,joints=3):
    frames=3 if metric.endswith('acceleration') else 2;rng=np.random.default_rng(834)
    base=rng.normal(size=(frames,joints,3))*.03;a=rng.normal(size=(frames,joints,3,columns))*.05
    b=rng.normal(size=a.shape)*.03;shift=rng.normal(size=base.shape)*.01
    def worlds(point):
        result=np.broadcast_to(np.eye(4),(frames,joints,4,4)).copy()
        result[:,:,:3,:3]=Rotation.from_rotvec((base+np.einsum('fjic,c->fji',a,point)).reshape(-1,3)).as_matrix().reshape(frames,joints,3,3)
        result[:,:,:3,3]=shift+np.sin(np.einsum('fjic,c->fji',b,point))
        return result
    return worlds


@pytest.mark.parametrize('metric',METRICS)
@pytest.mark.parametrize('offset',[0.,.1])
def test_every_value_and_derivative_column_matches_independent_nonlinear_worlds(metric,offset):
    worlds=field(metric);x=np.linspace(-.07,.08,19)+offset;world=worlds(x);step=1e-6
    jac=np.stack([(worlds(x+step*np.eye(19)[c])-worlds(x-step*np.eye(19)[c]))/(2*step) for c in range(19)],axis=-1)
    dt=.03;caps=np.array([.1,.7,2.]);index=METRICS.index(metric)
    actual,gradient,report=motion_rate_stencil(metric,world,caps,dt,jacobian=jac)
    expected=(measures(features(world,list(range(3))),dt)[index][0]-caps-1e-5)/np.maximum(caps,.001)
    assert actual.tobytes()==expected.tobytes() and gradient.shape==(3,19)
    for column in range(19):
        direction=np.eye(19)[column]*1e-5
        plus=motion_rate_stencil(metric,worlds(x+direction),caps,dt)[0];minus=motion_rate_stencil(metric,worlds(x-direction),caps,dt)[0]
        np.testing.assert_allclose(gradient[:,column],(plus-minus)/2e-5,atol=3e-5,rtol=3e-5)
    assert report['rows']==3 and report['derivative_columns']==19
    assert not report['quality_approved'] and not report['release_approved']


@pytest.mark.parametrize('metric',METRICS)
def test_zero_norm_uses_zero_symmetric_subgradient_without_feasibility_claim(metric):
    frames=3 if metric.endswith('acceleration') else 2;world=np.broadcast_to(np.eye(4),(frames,2,4,4)).copy()
    jac=np.zeros(world.shape+(3,));jac[-1,:,:3,3,:]=np.eye(3)
    values,gradient,report=motion_rate_stencil(metric,world,np.zeros(2),.1,jacobian=jac)
    np.testing.assert_array_equal(values,[-.01,-.01]);assert not np.any(gradient)
    assert 'not a fixed-condition proof' in report['zero_norm_derivative']


def test_full_angular_column_batches_equal_independent_one_column_calls():
    worlds=field('angular_acceleration',columns=37);x=np.zeros(37);world=worlds(x);jac=np.stack([(worlds(x+np.eye(37)[i]*1e-6)-worlds(x-np.eye(37)[i]*1e-6))/2e-6 for i in range(37)],axis=-1)
    values,gradient,_=motion_rate_stencil('angular_acceleration',world,[1.,2.,3.],.01,jacobian=jac)
    for column in range(37):
        single=motion_rate_stencil('angular_acceleration',world,[1.,2.,3.],.01,jacobian=jac[...,column:column+1])
        np.testing.assert_array_equal(single[0],values);np.testing.assert_allclose(single[1][:,0],gradient[:,column],atol=1e-10,rtol=1e-12)


@pytest.mark.parametrize('metric',['angular_speed','angular_acceleration'])
def test_near_orthogonal_rig_matrices_retain_existing_decoder_derivatives(metric):
    original=field(metric,columns=5);scale=np.diag([1+1e-8,1-2e-8,1.])
    def worlds(value):
        world=original(value);world[:,:,:3,:3]=world[:,:,:3,:3]@scale;return world
    value=np.linspace(-.1,.1,5);world=worlds(value)
    jac=np.stack([(worlds(value+np.eye(5)[i]*1e-6)-worlds(value-np.eye(5)[i]*1e-6))/2e-6 for i in range(5)],axis=-1)
    actual=motion_rate_stencil(metric,world,[1.,2.,3.],.03,jacobian=jac)
    for column in range(5):
        delta=np.eye(5)[column]*1e-5;plus=motion_rate_stencil(metric,worlds(value+delta),[1.,2.,3.],.03)[0];minus=motion_rate_stencil(metric,worlds(value-delta),[1.,2.,3.],.03)[0]
        np.testing.assert_allclose(actual[1][:,column],(plus-minus)/2e-5,atol=3e-5,rtol=3e-5)


@pytest.mark.parametrize('metric',METRICS)
def test_inputs_not_modified_and_value_only_does_not_invent_zero_columns(metric):
    worlds=field(metric);world=worlds(np.zeros(19));before=world.copy();caps=np.ones(3)
    values,gradient,report=motion_rate_stencil(metric,world,caps,.1)
    assert gradient is None and report['derivative_columns']==report['output_jacobian_bytes']==0
    np.testing.assert_array_equal(world,before);np.testing.assert_array_equal(caps,np.ones(3))
    assert np.isfinite(values).all()


def test_complete_input_budget_rejects_before_derivative_copy(monkeypatch):
    world=np.broadcast_to(np.eye(4),(2,1,4,4)).copy();jac=np.zeros(world.shape+(3,))
    with pytest.raises(ValueError,match='budget'):motion_rate_stencil('linear_speed',world,[1.],.1,jacobian=jac,maximum_jacobian_bytes=jac.nbytes-1)
    assert motion_rate_stencil('linear_speed',world,[1.],.1,jacobian=jac,maximum_jacobian_bytes=jac.nbytes)[1].nbytes==24


@pytest.mark.parametrize('fault',['shape','frames','caps_shape','caps_negative','caps_nan','world_nan','world_bool','world_complex','homogeneous','rotation_scale','rotation_reflection','angular_pi','jac_shape','jac_empty','jac_columns','jac_nan','jac_bool','jac_bottom'])
def test_incomplete_or_invalid_world_caps_or_jacobian_rejected(fault):
    world=np.broadcast_to(np.eye(4),(2,2,4,4)).copy();caps=np.ones(2);jac=None
    if fault=='shape':world=world[:,:,:3,:3]
    elif fault=='frames':world=world[:1]
    elif fault=='caps_shape':caps=np.ones(1)
    elif fault=='caps_negative':caps[0]=-1
    elif fault=='caps_nan':caps[0]=np.nan
    elif fault=='world_nan':world[0,0,0,0]=np.nan
    elif fault=='world_bool':world=world.astype(bool)
    elif fault=='world_complex':world=world.astype(complex)
    elif fault=='homogeneous':world[0,0,3,0]=.1
    elif fault=='rotation_scale':world[0,0,0,0]=2
    elif fault=='rotation_reflection':world[0,0,0,0]=-1
    elif fault=='angular_pi':world[1,0,:3,:3]=Rotation.from_rotvec([np.pi-1e-7,0,0]).as_matrix()
    else:
        jac=np.zeros(world.shape+(2,))
        if fault=='jac_shape':jac=jac[:1]
        elif fault=='jac_empty':jac=jac[...,:0]
        elif fault=='jac_columns':jac=np.zeros(world.shape+(769,))
        elif fault=='jac_nan':jac[0,0,0,0,0]=np.nan
        elif fault=='jac_bool':jac=jac.astype(bool)
        elif fault=='jac_bottom':jac[0,0,3,0,0]=.1
    with pytest.raises(ValueError):motion_rate_stencil('angular_speed',world,caps,.1,jacobian=jac)


@pytest.mark.parametrize('settings',[dict(metric='other'),dict(dt=0),dict(dt=True),dict(dt=float('nan')),dict(tolerance=-1),dict(tolerance=True),dict(angular_step=0),dict(maximum_jacobian_bytes=True),dict(maximum_jacobian_bytes=64*1024**2+1)])
def test_bad_settings_rejected(settings):
    args=dict(metric='linear_speed',world=np.broadcast_to(np.eye(4),(2,1,4,4)),caps=[0.],dt=.1);args.update(settings)
    with pytest.raises(ValueError):motion_rate_stencil(**args)


def test_angular_branch_crossing_rejected_without_silently_zeroing_gradient():
    world=np.broadcast_to(np.eye(4),(2,1,4,4)).copy();world[1,0,:3,:3]=Rotation.from_rotvec([0.,0.,np.pi-1e-5]).as_matrix()
    jac=np.zeros(world.shape+(1,));jac[1,0,:3,:3,0]=world[1,0,:3,:3]@np.array([[0.,-100.,0.],[100.,0.,0.],[0.,0.,0.]])
    with pytest.raises(ValueError,match='branch'):motion_rate_stencil('angular_speed',world,[1.],.1,jacobian=jac)
