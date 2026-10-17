"""Independent relation, physical-threshold and finite-difference checks."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_grouped_pair_gap_rows as module
from native_grouped_pair_gap_rows import GroupedPairGapRows


def scene(**settings):
    a=np.array([[0.,0,0],[0,1,0],[0,0,1],[4,0,0],[4,1,0],[4,0,1],[9,9,9],[8,8,8]])
    b=a.copy();b[:6,0]+=1.
    pairs=np.array([[0,1,2],[3,4,5]])
    return a,b,GroupedPairGapRows(pairs,pairs,8,8,[1.,0,0],**settings)


def test_exact_cover_avoids_unrelated_cross_pairs_and_preserves_all_references():
    a,b,problem=scene();rows,ja,jb=problem.evaluate(a,b,smooth=False)
    np.testing.assert_allclose(rows,[99.998,99.998],atol=2e-14,rtol=0)
    assert ja is jb is None and problem.report['rows']==2
    assert b[:6,0].min()-a[:6,0].max()<0,'A global region envelope would reject this valid relation'
    result=problem.exact_pairs(a,b)
    np.testing.assert_array_equal(result['projected_gaps_m'],[1.,1.])
    assert result['passed'] and result['pair_references']==2
    assert not result['quality_approved'] and not result['release_approved']


@pytest.mark.parametrize('seed',range(6))
def test_complete_chained_derivatives_match_independent_point_perturbations(seed):
    rng=np.random.default_rng(700+seed)
    a=rng.normal(size=(8,3))*.01;b=rng.normal(size=(11,3))*.01
    left=np.array([[0,1,2],[1,2,3],[4,5,6]])
    right=np.array([[0,1,2],[2,3,4],[6,7,10]])
    n=rng.normal(size=3);n/=np.linalg.norm(n)
    problem=GroupedPairGapRows(left,right,8,11,n,temperature_m=.01)
    da=rng.normal(size=(8,3,3));db=rng.normal(size=(11,3,5))
    values,ja,jb=problem.evaluate(a,b,left_jacobian=da,right_jacobian=db)
    plain=problem.evaluate(a,b)[0];np.testing.assert_array_equal(values,plain)
    assert ja.shape==(len(values),3) and jb.shape==(len(values),5)
    step=1e-7
    for side,matrix,derivative in [(0,ja,da),(1,jb,db)]:
        for column in range(matrix.shape[1]):
            plus=[a,b];minus=[a,b]
            plus[side]=plus[side]+step*derivative[:,:,column]
            minus[side]=minus[side]-step*derivative[:,:,column]
            finite=(problem.evaluate(*plus)[0]-problem.evaluate(*minus)[0])/(2*step)
            np.testing.assert_allclose(matrix[:,column],finite,atol=5e-8,rtol=2e-7)
    expected=[]
    for ai,bi in zip(left,right):
        # All nine scalar comparisons, independent of grouping and gap helpers.
        expected.append(min(float((b[v]-a[u])@n) for u in ai for v in bi))
    np.testing.assert_allclose(problem.exact_pairs(a,b)['projected_gaps_m'],expected,atol=2e-17,rtol=0)
    assert problem.evaluate(a,b,smooth=False)[0].min()==pytest.approx((min(expected)-2e-5)/.01,abs=2e-14)
    assert values.min()<=problem.evaluate(a,b,smooth=False)[0].min()


def test_static_partner_and_zero_coordinate_derivatives_are_explicit():
    a,b,problem=scene();direction=np.zeros((8,3,1));direction[:,0,0]=1.
    values,ja,jb=problem.evaluate(a,b,left_jacobian=direction)
    np.testing.assert_allclose(ja,-100.,atol=2e-14,rtol=0);assert jb.shape==(2,0)
    full=problem.evaluate(a,b,left_jacobian=direction,right_jacobian=np.empty((8,3,0)))
    for first,last in zip((values,ja,jb),full):np.testing.assert_array_equal(first,last)


def test_threshold_is_strict_before_and_after_the_exact_boundary():
    p=GroupedPairGapRows([[0,0,0]],[[0,0,0]],1,1,[1,0,0])
    a=np.zeros((1,3));b=np.array([[2e-5,0.,0.]])
    assert p.exact_pairs(a,b)['passed']
    b[0,0]=np.nextafter(2e-5,-np.inf)
    assert not p.exact_pairs(a,b)['passed'] and p.evaluate(a,b,smooth=False)[0][0]<0


def test_native_translation_columns_include_every_tied_vertex():
    problem=GroupedPairGapRows([[0,1,2]]*3,[[0,1,2]]*3,3,3,[1,0,0],temperature_m=.01)
    a=np.zeros((3,3));b=np.zeros((3,3));b[:,0]=1.
    rows,left,right=problem.evaluate(a,b,left_jacobian=np.eye(9).reshape(3,3,9),right_jacobian=np.eye(9).reshape(3,3,9))
    assert len(rows)==1 and problem.report['pair_references']==3
    expected=np.tile([-100/3,0.,0.],3)[None,:]
    np.testing.assert_allclose(left,expected,atol=2e-14,rtol=0)
    np.testing.assert_allclose(right,-expected,atol=2e-14,rtol=0)


def test_constructor_snapshots_references_direction_and_report():
    ids=np.array([[0,1,2]]);normal=np.array([1.,0,0])
    p=GroupedPairGapRows(ids,ids,3,3,normal);a=np.zeros((3,3));b=a+[1,0,0]
    before=p.evaluate(a,b)[0];digest=p.report['pair_references_sha256']
    ids[:]=0;normal[:]=0;report=p.report;report['rows']=0
    np.testing.assert_array_equal(p.evaluate(a,b)[0],before)
    assert p.report['rows']==1 and p.report['pair_references_sha256']==digest


def test_exact_output_jacobian_budget_never_drops_groups():
    a,b,p=scene(maximum_jacobian_bytes=79)
    da=np.zeros((8,3,2));db=np.zeros((8,3,3))
    with pytest.raises(ValueError,match='Complete grouped Jacobian'):p.evaluate(a,b,left_jacobian=da,right_jacobian=db)
    _,_,p=scene(maximum_jacobian_bytes=80)
    _,ja,jb=p.evaluate(a,b,left_jacobian=da,right_jacobian=db)
    assert ja.nbytes+jb.nbytes==80 and p.report['rows']==2


@pytest.mark.parametrize('side',[0,1])
def test_unused_vertices_and_derivatives_still_require_complete_finite_inputs(side):
    a,b,p=scene();points=[a.copy(),b.copy()];points[side][7,0]=np.nan
    with pytest.raises(ValueError,match='Finite complete point'):p.evaluate(*points)
    with pytest.raises(ValueError,match='Finite complete point'):p.exact_pairs(*points)
    da=np.zeros((8,3,1));db=da.copy();derivatives=[da,db];derivatives[side][7,0,0]=np.nan
    with pytest.raises(ValueError,match='Finite complete vertex'):p.evaluate(a,b,left_jacobian=da,right_jacobian=db)


def test_empty_derivative_coordinates_are_not_an_exact_extrema_jacobian():
    a,b,p=scene()
    with pytest.raises(ValueError,match='not smooth derivatives'):
        p.evaluate(a,b,left_jacobian=np.empty((8,3,0)),smooth=False)


@pytest.mark.parametrize('jacobian',[
    np.zeros((7,3,1)),np.zeros((8,2,1)),np.zeros((8,3)),
    np.zeros((8,3,769)),np.zeros((8,3,1),dtype=bool),
    np.zeros((8,3,1),dtype=complex),np.full((8,3,1),np.inf),
])
def test_complete_derivative_shape_type_and_coordinate_limits(jacobian):
    a,b,p=scene()
    with pytest.raises(ValueError):p.evaluate(a,b,left_jacobian=jacobian)


def test_input_derivative_byte_limit_is_checked_before_output_allocation(monkeypatch):
    a,b,p=scene();monkeypatch.setattr(module,'MAXIMUM_INPUT_JACOBIAN_BYTES',191)
    with pytest.raises(ValueError,match='Complete bounded vertex'):
        p.evaluate(a,b,left_jacobian=np.zeros((8,3,1)))


@pytest.mark.parametrize('changes',[
    {'left_vertex_count':True},{'right_vertex_count':0},{'left_vertex_count':65537},
    {'normal_world':[0,0,0]},{'normal_world':[True,False,False]},
    {'normal_world':[np.nan,0,0]},{'normal_world':[1e308,0,0]},
    {'normal_world':[1,0,0,0]},{'minimum_gap_m':-1e-6},{'minimum_gap_m':.1001},
    {'minimum_gap_m':np.nan},{'length_scale_m':0},{'length_scale_m':1.01},
    {'temperature_m':0},{'temperature_m':np.inf},{'temperature_m':True},
    {'maximum_jacobian_bytes':True},{'maximum_jacobian_bytes':64*1024**2+1},
    {'left_triangles':[[0.,1.,2.]]},{'left_triangles':[[0,1,8]]},
    {'right_triangles':[[0,1,-1]]},{'right_triangles':[]},
])
def test_rejects_invalid_context_without_selecting_a_subset(changes):
    args=dict(left_triangles=[[0,1,2]],right_triangles=[[0,1,2]],
              left_vertex_count=8,right_vertex_count=8,normal_world=[1,0,0])
    args.update(changes)
    with pytest.raises(ValueError):GroupedPairGapRows(**args)


@pytest.mark.parametrize('points',[
    np.zeros((7,3)),np.zeros((8,2)),np.zeros((8,3),dtype=bool),
    np.zeros((8,3),dtype=complex),np.full((8,3),1e6+1),np.full((8,3),np.inf),
])
def test_rejects_wrong_or_unbounded_complete_point_populations(points):
    a,b,p=scene()
    with pytest.raises(ValueError):p.evaluate(points,b)


def test_units_scale_guidance_and_jacobians_but_never_physical_thresholds():
    a,b,first=scene();_,_,second=scene(length_scale_m=.02)
    derivative=np.zeros((8,3,1));derivative[:,0,0]=1.
    x=first.evaluate(a,b,left_jacobian=derivative);y=second.evaluate(a,b,left_jacobian=derivative)
    for original,scaled in zip(x,y):np.testing.assert_allclose(original,scaled*2,atol=2e-14,rtol=0)
    np.testing.assert_array_equal(first.exact_pairs(a,b)['projected_gaps_m'],second.exact_pairs(a,b)['projected_gaps_m'])
    assert first.exact_pairs(a,b)['minimum_gap_m']==second.exact_pairs(a,b)['minimum_gap_m']==2e-5
