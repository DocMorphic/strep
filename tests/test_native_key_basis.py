"""Explicit new domains, complete derivative columns, original frozen bytes."""
from pathlib import Path
import sys
import numpy as np
import pytest
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_key_basis.py').is_file())
sys.path[:0]=[str(Path(__file__).parent),str(root/'scripts')]
from native_key_basis import NativeKeyBasis


def declaration(**changes):
    values=dict(clock=np.array([0.,.05,.3,.8,1.,1.8,2.]),nodes=[17,3],
        seed_controls=np.zeros((7,2,3)),knots=[0,2,3,4,6],frozen_keys=[0,3,6])
    values.update(changes)
    return values


def test_nonuniform_clock_and_full_parameter_order_match_independent_interpolation():
    args=declaration();basis=NativeKeyBasis(**args);value=np.arange(basis.size)*.013-.08
    seed=args['seed_controls'];delta=value.reshape(2,2,3);expected=seed.copy()
    for node in range(2):
        for axis in range(3):
            expected[:,node,axis]+=np.interp(args['clock'],args['clock'][args['knots']],
                [0,delta[0,node,axis],0,delta[1,node,axis],0])
    np.testing.assert_allclose(basis.coefficients(value),expected,atol=2e-17,rtol=0)
    assert basis.parameters==tuple((key,node,axis) for key in [2,4] for node in [17,3] for axis in range(3))
    assert basis.size==12 and basis.report['variables']==12
    assert basis.report['original_selected'] and not basis.report['quality_approved']
    assert not basis.report['release_approved']


def test_every_column_of_endpoint_and_native_derivatives_matches_finite_difference():
    rng=np.random.default_rng(117);args=declaration(seed_controls=rng.uniform(-.1,.1,(7,2,3)))
    basis=NativeKeyBasis(**args);value=rng.uniform(-.2,.2,basis.size);keys=[5,0,2,6,1,3,4]
    endpoints,jac=basis.endpoint_map(value,keys);rows,derivative=basis.native_chunk(value,0,7)
    np.testing.assert_array_equal(endpoints,basis.coefficients(value)[keys])
    np.testing.assert_allclose(rows,1-np.sum(basis.coefficients(value)**2,axis=2).ravel(),rtol=0,atol=0)
    for column in range(basis.size):
        delta=np.eye(basis.size)[column]*1e-6
        finite=(basis.endpoint_map(value+delta,keys,jacobian=False)[0]-basis.endpoint_map(value-delta,keys,jacobian=False)[0]).ravel()/2e-6
        np.testing.assert_allclose(jac[:,column],finite,rtol=2e-9,atol=2e-10)
        finite=(basis.native_chunk(value+delta,0,7,jacobian=False)[0]-basis.native_chunk(value-delta,0,7,jacobian=False)[0])/2e-6
        np.testing.assert_allclose(derivative[:,column],finite,rtol=2e-7,atol=2e-10)
    assert basis.endpoint_map(value,keys,jacobian=False)[1] is None
    assert basis.native_chunk(value,0,7,jacobian=False)[1] is None


def test_all_frozen_native_bytes_and_rows_stay_fixed_including_negative_zero():
    seed=np.zeros((7,2,3));seed[[0,3,6],:,1]=-0.;seed[3,0,0]=.2
    basis=NativeKeyBasis(**declaration(seed_controls=seed));value=np.linspace(-.3,.3,basis.size)
    result=basis.coefficients(value);actual,matrix=basis.endpoint_map(value,[6,3,0])
    assert result[[0,3,6]].tobytes()==seed[[0,3,6]].tobytes()
    assert actual.tobytes()==seed[[6,3,0]].tobytes() and not np.any(matrix)
    np.testing.assert_array_equal(basis.coefficients(np.zeros(basis.size)),seed)


def test_inputs_reports_weights_and_outputs_are_snapshots():
    args=declaration();basis=NativeKeyBasis(**args);value=np.zeros(basis.size)
    args['clock'][:]=9;args['nodes'][0]=9;args['seed_controls'][:]=9;args['knots'][:]=[9];args['frozen_keys'][:]=[9]
    report=basis.report;report['knots'][:]=[9];weights=basis.weights;weights[:]=9
    actual,jac=basis.endpoint_map(value,[1,2]);actual[:]=9;jac[:]=9
    assert basis.report['knots']==[0,2,3,4,6]
    np.testing.assert_array_equal(basis.coefficients(value),np.zeros((7,2,3)))
    assert basis.weights.max()==1 and basis.parameters[0]==(2,17,0)


def test_search_box_does_not_clip_or_replace_failed_native_balls():
    seed=np.zeros((7,2,3));seed[2]=.5;basis=NativeKeyBasis(**declaration(seed_controls=seed));value=np.full(basis.size,.5)
    result=basis.coefficients(value);rows,_=basis.native_chunk(value,0,7)
    assert np.any(rows<0) and result[2,0,0]==1
    with pytest.raises(ValueError,match='not clipped'):basis.export_coefficients(value)
    np.testing.assert_array_equal(basis.export_coefficients(np.zeros(basis.size)),seed)


def test_full_endpoint_budget_is_checked_before_dense_allocation(monkeypatch):
    basis=NativeKeyBasis(**declaration(),maximum_jacobian_bytes=1)
    def forbidden(*args,**kwargs):raise AssertionError('dense Jacobian allocated before budget admission')
    monkeypatch.setattr(np,'kron',forbidden)
    with pytest.raises(ValueError,match='budget'):basis.endpoint_map(np.zeros(basis.size),[1])
    with pytest.raises(ValueError,match='budget'):basis.native_chunk(np.zeros(basis.size),1,1)
    assert basis.endpoint_map(np.zeros(basis.size),[1],jacobian=False)[1] is None


@pytest.mark.parametrize('changes',[
    dict(clock=[0,0,1,2,3,4,5]),dict(clock=[0,1,2,3,4,5,float('inf')]),
    dict(clock=[0,1,2,3,4,5,float('nan')]),dict(clock=[False]*7),
    dict(clock=np.array([-1e308,0,1,2,3,4,1e308])),
    dict(nodes=[17,17]),dict(nodes=[True,3]),dict(nodes=[17,-1]),dict(nodes=(17,3)),
    dict(seed_controls=np.zeros((7,1,3))),dict(seed_controls=np.ones((7,2,3))),
    dict(seed_controls=np.full((7,2,3),float('nan'))),dict(seed_controls=np.full((7,2,3),-2**63,dtype=np.int64)),
    dict(knots=[0,3,2,4,6]),dict(knots=[0,2,2,3,4,6]),dict(knots=[0,2,4,6]),
    dict(knots=[0,2,3,4]),dict(knots=[0,2,3,4,True,6]),dict(frozen_keys=[0,3]),
    dict(frozen_keys=[0,1,3,6]),dict(frozen_keys=[0,2,3,4,6]),
    dict(maximum_jacobian_bytes=True),dict(maximum_jacobian_bytes=64*1024**2+1),
])
def test_invalid_or_incomplete_domain_rejected(changes):
    with pytest.raises(ValueError):NativeKeyBasis(**declaration(**changes))


def test_complete_control_budget_never_silently_drops_nodes():
    with pytest.raises(ValueError,match='budget'):
        NativeKeyBasis(**declaration(nodes=list(range(129)),seed_controls=np.zeros((7,129,3))))


@pytest.mark.parametrize('value',[[0],np.zeros(13),np.full(12,float('nan')),np.full(12,1.00001),np.ones(12,dtype=bool),np.full(12,-2**63,dtype=np.int64)])
def test_invalid_latent_rejected_by_every_entry_point(value):
    basis=NativeKeyBasis(**declaration())
    for call in [lambda:basis.coefficients(value),lambda:basis.endpoint_map(value,[1]),lambda:basis.native_chunk(value,0,1),lambda:basis.export_coefficients(value)]:
        with pytest.raises(ValueError):call()


@pytest.mark.parametrize('keys',[[],[1,1],[-1],[7],[True],(1,2)])
def test_invalid_endpoint_selection_rejected(keys):
    basis=NativeKeyBasis(**declaration())
    with pytest.raises(ValueError):basis.endpoint_map(np.zeros(basis.size),keys)


@pytest.mark.parametrize('start,count',[(True,1),(-1,1),(0,0),(0,65),(6,2),(0,1.5)])
def test_invalid_native_chunk_rejected(start,count):
    basis=NativeKeyBasis(**declaration())
    with pytest.raises(ValueError):basis.native_chunk(np.zeros(basis.size),start,count)


def test_explicit_derivative_mode_required():
    basis=NativeKeyBasis(**declaration())
    with pytest.raises(ValueError):basis.endpoint_map(np.zeros(basis.size),[1],jacobian=1)

