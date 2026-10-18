from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_motion_rate_vectors import motion_rate_vectors
from native_motion_rate_stencil import motion_rate_stencil,METRICS
from sampled_motion_caps import features,measures


def field(metric,columns=19,joints=3):
    frames=3 if metric.endswith('acceleration') else 2;rng=np.random.default_rng(938)
    base=rng.normal(size=(frames,joints,3))*.03;a=rng.normal(size=base.shape+(columns,))*.05
    b=rng.normal(size=a.shape)*.03;shift=rng.normal(size=base.shape)*.01
    def worlds(point):
        result=np.broadcast_to(np.eye(4),(frames,joints,4,4)).copy()
        result[:,:,:3,:3]=Rotation.from_rotvec((base+np.einsum('fjic,c->fji',a,point)).reshape(-1,3)).as_matrix().reshape(frames,joints,3,3)
        result[:,:,:3,3]=shift+np.sin(np.einsum('fjic,c->fji',b,point))
        return result
    return worlds


def world_jac(worlds,x):
    return np.stack([(worlds(x+np.eye(len(x))[c]*1e-6)-worlds(x-np.eye(len(x))[c]*1e-6))/2e-6 for c in range(len(x))],axis=-1)


@pytest.mark.parametrize('metric',METRICS)
@pytest.mark.parametrize('offset',[0.,.1])
def test_every_vector_column_and_canonical_scalar_matches_original_kernel(metric,offset):
    worlds=field(metric);x=np.linspace(-.07,.08,19)+offset;world=worlds(x);jac=world_jac(worlds,x);caps=np.array([.1,.7,2.]);dt=.03
    r=motion_rate_vectors(metric,world,caps,dt,jacobian=jac);old,old_jac,_=motion_rate_stencil(metric,world,caps,dt,jacobian=jac)
    assert r['canonical_violations'].tobytes()==old.tobytes() and r['jacobian'].shape==(3,3,19)
    canonical=measures(features(world,list(range(3))),dt)[METRICS.index(metric)][0]
    assert np.linalg.norm(r['vectors'],axis=1).tobytes()==canonical.tobytes()
    for c in range(19):
        d=np.eye(19)[c]*1e-5
        finite=(motion_rate_vectors(metric,worlds(x+d),caps,dt)['vectors']-motion_rate_vectors(metric,worlds(x-d),caps,dt)['vectors'])/2e-5
        np.testing.assert_allclose(r['jacobian'][:,:,c],finite,atol=3e-5,rtol=3e-5)
    unit=r['vectors']/np.linalg.norm(r['vectors'],axis=1)[:,None]
    projected=np.einsum('ji,jic->jc',unit,r['jacobian'])/r['normalizers'][:,None]
    np.testing.assert_allclose(projected,old_jac,atol=1e-8,rtol=1e-10)
    assert r['report']['derivative_columns']==19 and r['report']['all_joints_and_columns_retained']
    assert not r['report']['quality_approved'] and not r['report']['release_approved']


@pytest.mark.parametrize('metric',METRICS)
def test_known_axis_vector_values(metric):
    frames=3 if metric.endswith('acceleration') else 2;w=np.broadcast_to(np.eye(4),(frames,1,4,4)).copy();q=np.array([0.,.1,.3])[:frames]
    w[:,0,0,3]=q;w[:,0,:3,:3]=Rotation.from_rotvec(np.c_[q,np.zeros((frames,2))]).as_matrix()
    r=motion_rate_vectors(metric,w,[0.],.1)
    np.testing.assert_allclose(r['vectors'],[[10. if frames==3 else 1.,0,0]],atol=1e-13,rtol=1e-13)


@pytest.mark.parametrize('metric',METRICS)
def test_zero_norm_keeps_vector_derivatives_instead_of_scalar_zero_gradient(metric):
    frames=3 if metric.endswith('acceleration') else 2;w=np.broadcast_to(np.eye(4),(frames,1,4,4)).copy();j=np.zeros(w.shape+(3,))
    j[-1,0,:3,3,:]=np.eye(3)
    for c,axis in enumerate(np.eye(3)):
        x,y,z=axis;j[-1,0,:3,:3,c]=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    r=motion_rate_vectors(metric,w,[0.],.1,jacobian=j);old=motion_rate_stencil(metric,w,[0.],.1,jacobian=j)
    assert not np.any(old[1]) and not np.any(r['vectors']) and np.any(r['jacobian'])
    assert np.linalg.norm((r['jacobian']@np.array([.001,0,0]))[0])>r['radii'][0]


def test_transverse_angular_change_is_visible_to_norm_but_not_scalar_tangent():
    def worlds(x):
        w=np.broadcast_to(np.eye(4),(2,1,4,4)).copy();w[1,0,:3,:3]=Rotation.from_rotvec([.1,x[0],0]).as_matrix();return w
    x=np.zeros(1);w=worlds(x);j=world_jac(worlds,x);caps=measures(features(w,[0]),.1)[2][0]
    r=motion_rate_vectors('angular_speed',w,caps,.1,jacobian=j);value,gradient,_=motion_rate_stencil('angular_speed',w,caps,.1,jacobian=j)
    step=np.array([.01]);assert float(value[0]+gradient[0]@step)<0
    assert np.linalg.norm(r['vectors'][0]+r['jacobian'][0]@step)>r['radii'][0]
    assert motion_rate_stencil('angular_speed',worlds(step),caps,.1)[0][0]>0


@pytest.mark.parametrize('metric',['angular_speed','angular_acceleration'])
def test_complete_column_batches_match_independent_single_column_calls(metric):
    worlds=field(metric,columns=37);x=np.zeros(37);w=worlds(x);j=world_jac(worlds,x)
    r=motion_rate_vectors(metric,w,[1.,2.,3.],.01,jacobian=j)
    for c in range(37):
        single=motion_rate_vectors(metric,w,[1.,2.,3.],.01,jacobian=j[...,c:c+1])
        np.testing.assert_allclose(single['jacobian'][:,:,0],r['jacobian'][:,:,c],atol=1e-8,rtol=1e-10)


@pytest.mark.parametrize('metric',METRICS)
def test_768th_column_is_preserved(metric):
    frames=3 if metric.endswith('acceleration') else 2;w=np.broadcast_to(np.eye(4),(frames,1,4,4)).copy();j=np.zeros(w.shape+(768,))
    j[-1,0,0,3,767]=1.;j[-1,0,:3,:3,767]=[[0,0,0],[0,0,-1],[0,1,0]]
    r=motion_rate_vectors(metric,w,[1.],.1,jacobian=j)
    np.testing.assert_allclose(r['jacobian'][0,:,767],[100. if frames==3 else 10.,0.,0.],atol=1e-7,rtol=1e-9)
    assert r['jacobian'].shape==(1,3,768) and not np.any(r['jacobian'][:,:,:767])


@pytest.mark.parametrize('metric',['angular_speed','angular_acceleration'])
def test_near_orthogonal_worlds_keep_existing_decoder(metric):
    base=field(metric,columns=5);scale=np.diag([1+1e-8,1-2e-8,1.])
    def worlds(x):
        w=base(x);w[:,:,:3,:3]=w[:,:,:3,:3]@scale;return w
    x=np.linspace(-.1,.1,5);r=motion_rate_vectors(metric,worlds(x),[1.,2.,3.],.03,jacobian=world_jac(worlds,x))
    for c in range(5):
        d=np.eye(5)[c]*1e-5;finite=(motion_rate_vectors(metric,worlds(x+d),[1.,2.,3.],.03)['vectors']-motion_rate_vectors(metric,worlds(x-d),[1.,2.,3.],.03)['vectors'])/2e-5
        np.testing.assert_allclose(r['jacobian'][:,:,c],finite,atol=3e-5,rtol=3e-5)


@pytest.mark.parametrize('metric',METRICS)
def test_fixed_rigid_reexpression_rotates_vectors_and_all_columns(metric):
    worlds=field(metric,columns=4);x=np.zeros(4);w=worlds(x);j=world_jac(worlds,x);q=Rotation.from_rotvec([.2,-.3,.1]).as_matrix()
    moved=w.copy();moved[:,:,:3,:]=np.einsum('ab,fjbc->fjac',q,w[:,:,:3,:]);dj=j.copy();dj[:,:,:3,:,:]=np.einsum('ab,fjbkc->fjakc',q,j[:,:,:3,:,:])
    a=motion_rate_vectors(metric,w,[1.,2.,3.],.03,jacobian=j);b=motion_rate_vectors(metric,moved,[1.,2.,3.],.03,jacobian=dj)
    np.testing.assert_allclose(b['vectors'],a['vectors']@q.T,atol=1e-11,rtol=1e-11)
    np.testing.assert_allclose(b['jacobian'],np.einsum('ab,jbc->jac',q,a['jacobian']),atol=3e-5,rtol=3e-5)


@pytest.mark.parametrize('metric',METRICS)
def test_value_only_and_input_bytes_unchanged(metric):
    worlds=field(metric);w=worlds(np.zeros(19));old=w.copy();caps=np.ones(3);r=motion_rate_vectors(metric,w,caps,.1)
    assert r['jacobian'] is None and r['report']['derivative_columns']==r['report']['output_jacobian_bytes']==0
    assert r['report']['physical_margin_tolerance_added']==0 and r['report']['canonical_scalar_arithmetic_authoritative']
    np.testing.assert_array_equal(w,old);np.testing.assert_array_equal(caps,np.ones(3))


def test_complete_combined_input_output_budget_has_exact_boundary():
    w=np.broadcast_to(np.eye(4),(2,1,4,4)).copy();j=np.zeros(w.shape+(2,));budget=j.size*8+1*3*2*8
    with pytest.raises(ValueError,match='budget'):motion_rate_vectors('linear_speed',w,[1.],.1,jacobian=j,maximum_jacobian_bytes=budget-1)
    r=motion_rate_vectors('linear_speed',w,[1.],.1,jacobian=j,maximum_jacobian_bytes=budget)
    assert r['report']['input_jacobian_bytes']+r['report']['output_jacobian_bytes']==budget


def test_zero_physical_cap_and_zero_tolerance_are_not_inflated():
    w=np.broadcast_to(np.eye(4),(2,1,4,4)).copy();r=motion_rate_vectors('linear_speed',w,[0.],.1,tolerance=0.)
    assert r['radii'].tolist()==[0.] and r['canonical_violations'].tolist()==[0.]


@pytest.mark.parametrize('fault',['shape','frames','caps_shape','caps_negative','caps_nan','world_nan','world_bool','world_complex','homogeneous','rotation_scale','rotation_reflection','angular_pi','jac_shape','jac_empty','jac_columns','jac_nan','jac_bool','jac_bottom'])
def test_invalid_complete_inputs_rejected(fault):
    w=np.broadcast_to(np.eye(4),(2,2,4,4)).copy();caps=np.ones(2);j=None
    if fault=='shape':w=w[:,:,:3,:3]
    elif fault=='frames':w=w[:1]
    elif fault=='caps_shape':caps=np.ones(1)
    elif fault=='caps_negative':caps[0]=-1
    elif fault=='caps_nan':caps[0]=np.nan
    elif fault=='world_nan':w[0,0,0,0]=np.nan
    elif fault=='world_bool':w=w.astype(bool)
    elif fault=='world_complex':w=w.astype(complex)
    elif fault=='homogeneous':w[0,0,3,0]=.1
    elif fault=='rotation_scale':w[0,0,0,0]=2.
    elif fault=='rotation_reflection':w[0,0,0,0]=-1.
    elif fault=='angular_pi':w[1,0,:3,:3]=Rotation.from_rotvec([np.pi-1e-7,0,0]).as_matrix()
    else:
        j=np.zeros(w.shape+(2,))
        if fault=='jac_shape':j=j[:1]
        elif fault=='jac_empty':j=j[...,:0]
        elif fault=='jac_columns':j=np.zeros(w.shape+(769,))
        elif fault=='jac_nan':j[0,0,0,0,0]=np.nan
        elif fault=='jac_bool':j=j.astype(bool)
        elif fault=='jac_bottom':j[0,0,3,0,0]=.1
    with pytest.raises(ValueError):motion_rate_vectors('angular_speed',w,caps,.1,jacobian=j)


@pytest.mark.parametrize('settings',[dict(metric='other'),dict(dt=0),dict(dt=True),dict(dt=float('nan')),dict(tolerance=-1),dict(tolerance=True),dict(angular_step=0),dict(maximum_jacobian_bytes=True),dict(maximum_jacobian_bytes=64*1024**2+1)])
def test_invalid_settings_rejected(settings):
    args=dict(metric='linear_speed',world=np.broadcast_to(np.eye(4),(2,1,4,4)),caps=[0.],dt=.1);args.update(settings)
    with pytest.raises(ValueError):motion_rate_vectors(**args)


def test_decoder_branch_crossing_rejected_without_zeroing_columns():
    w=np.broadcast_to(np.eye(4),(2,1,4,4)).copy();w[1,0,:3,:3]=Rotation.from_rotvec([0,0,np.pi-1e-5]).as_matrix();j=np.zeros(w.shape+(1,))
    j[1,0,:3,:3,0]=w[1,0,:3,:3]@np.array([[0,-100.,0],[100.,0,0],[0,0,0]])
    with pytest.raises(ValueError,match='branch'):motion_rate_vectors('angular_speed',w,[1.],.1,jacobian=j)
