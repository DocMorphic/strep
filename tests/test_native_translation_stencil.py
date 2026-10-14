import itertools
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_translation_stencil import rank
from native_support_clock import NativeSupportSampler


def fixture():
    nearest=np.array([[.5,.3,-.2],[.51,.29,-.19],[.53,.27,-.18]],np.float32)
    clock=np.array([0,.03,.06],np.float32);times=np.array([.02,.03,.04])
    weights=np.zeros((3,3))
    for key in range(3):
        basis=np.zeros((3,3));basis[key,0]=1
        weights[:,key]=[NativeSupportSampler.value('translation',clock,basis,'LINEAR',float(t))[0] for t in times]
    current=np.array([NativeSupportSampler.value('translation',clock,nearest.astype(float),'LINEAR',float(t)) for t in times])
    # A scaled/rotated parent is permitted: these are full affine linear parts.
    parent=np.repeat(np.array([[0,-2,0],[1,0,0],[0,0,.7]])[None],3,axis=0)
    points=np.einsum('tij,tj->ti',parent,current)+np.array([.2,.4,.6])
    return nearest,current,weights,parent,points,dict(cap=1.,dt=.01,tolerance=1e-5)


def test_complete_population_matches_independent_literal_native_interpolation():
    nearest,current,weights,parent,points,kwargs=fixture()
    result=rank(nearest,current,weights,parent,points,**kwargs)
    expected=list(itertools.product((-1,0,1),repeat=9))
    np.testing.assert_array_equal(result['absolute_steps'],expected)
    assert result['population']==19683 and len(set(expected))==19683
    clock=np.array([0,.03,.06],np.float32);times=[.02,.03,.04]
    for i in [0,37,9841,19682,int(result['order'][0])]:
        candidate=nearest.copy()
        for j,step in enumerate(expected[i]):
            if step:candidate.flat[j]=np.nextafter(nearest.flat[j],np.float32(np.inf if step>0 else -np.inf))
        sampled=np.array([NativeSupportSampler.value('translation',clock,candidate.astype(float),'LINEAR',t) for t in times])
        literal=points+np.einsum('tij,tj->ti',parent,sampled-current)
        np.testing.assert_array_equal(result['candidate_key_values'][i],candidate)
        np.testing.assert_allclose(result['predicted_points'][i],literal,atol=1e-15,rtol=0)
        acceleration=np.linalg.norm((literal[2]-2*literal[1]+literal[0])/.01**2)
        assert result['predicted_excess'][i]==pytest.approx(acceleration-1-1e-5,abs=3e-11)
    assert result['proposal_only'] and not result['geometry_assessed']
    assert not result['quality_approved'] and not result['release_approved']
    np.testing.assert_array_equal(np.sort(result['order']),np.arange(19683))
    assert np.all(np.diff(result['predicted_excess'][result['order']])>=0)


def test_population_budget_rejects_before_materializing(monkeypatch):
    args=fixture()
    monkeypatch.setattr(itertools,'product',lambda *a,**kw:pytest.fail('Population should not materialize'))
    with pytest.raises(ValueError,match='exceeds'):rank(*args[:5],**args[5],maximum_population=19682)


@pytest.mark.parametrize('count',[1,2])
def test_smaller_complete_support_population(count):
    nearest=np.full((count,3),.5,np.float32);weights=np.full((3,count),1/count)
    result=rank(nearest,np.full((3,3),.5),weights,np.repeat(np.eye(3)[None],3,axis=0),np.zeros((3,3)),cap=0.,dt=.01,tolerance=0.)
    assert result['population']==3**(3*count)
    assert np.min(result['predicted_excess'])==0
    assert not result['release_approved']


@pytest.mark.parametrize('field,value',[
    ('maximum_population',True),('maximum_population',19684),('maximum_population',0),
    ('cap',True),('cap',-1.),('dt',0.),('dt',float('inf')),('tolerance',-1.),
])
def test_invalid_budgets_and_original_scalars(field,value):
    args=fixture();kwargs=args[5]|{field:value}
    with pytest.raises(ValueError):rank(*args[:5],**kwargs)


@pytest.mark.parametrize('index,value',[
    (0,np.full((3,3),.1)),(0,np.zeros((4,3),np.float32)),
    (0,np.full((3,3),np.finfo(np.float32).max,np.float32)),
    (1,np.zeros((2,3))),(2,np.ones((3,3))),
    (3,np.full((3,3,3),np.nan)),(4,np.zeros((3,4))),
])
def test_incomplete_nonfinite_or_non_nearest_inputs_reject(index,value):
    args=list(fixture());args[index]=value
    with pytest.raises(ValueError):rank(*args[:5],**args[5])


def test_input_observations_are_not_mutated_and_results_are_detached():
    args=fixture();copies=[x.copy() for x in args[:5]]
    result=rank(*args[:5],**args[5]);result['candidate_key_values'][:]=100
    for actual,expected in zip(args,copies):np.testing.assert_array_equal(actual,expected)
