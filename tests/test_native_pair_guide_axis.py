"""Complete finite axis ranking on real triangle patches and failures."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_pair_guide_axis import choose_axis


def patches():
    a=np.array([[0.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
    b=a+np.array([.01,0.,0.]);faces=np.array([[0,1,2]])
    return a,faces,b,faces.copy(),np.array([0.,1.,0.])


def test_rotated_wrong_baseline_is_replaced_and_every_test_scores_all_pairs():
    a,fa,b,fb,axis=patches();before=[v.copy() for v in (a,fa,b,fb,axis)]
    selected,report=choose_axis(a,fa,b,fb,axis)
    assert report['selected_squared_negative_part']==0. and report['baseline_squared_negative_part']>0.
    assert report['changed_direction'] and report['pair_rows']==9 and not report['quality_approved'] and not report['release_approved']
    for v,old in zip((a,fa,b,fb,axis),before):np.testing.assert_array_equal(v,old)
    scores=[]
    for record in report['tests']:
        normal=np.array(record['axis_world']);assert abs(np.linalg.norm(normal)-1)<1e-12
        gaps=np.array([float(y@normal)-float(x@normal) for x in a for y in b])
        negative=np.minimum((gaps-.0001)/.03,0.)
        assert record['squared_negative_part']==float(negative@negative) and record['minimum_gap_m']==float(gaps.min())
        scores.append((record['squared_negative_part'],-record['minimum_gap_m']))
    chosen=min(range(len(scores)),key=scores.__getitem__);assert chosen==report['selected_index']
    np.testing.assert_array_equal(selected,report['tests'][chosen]['axis_world'])
    assert report['complete_requested_axis_tests']==24 and len(report['tests'])==24-2*report['exact_zero_edge_crosses_omitted']


def test_already_separated_baseline_preserves_stable_first_tie():
    a,fa,b,fb,_=patches();baseline=np.array([1.,0.,0.]);selected,r=choose_axis(a,fa,b,fb,baseline)
    assert r['selected_index']==0 and not r['changed_direction'];np.testing.assert_array_equal(selected,baseline)


def test_contact_clearance_is_explicit_and_does_not_inherit_approval():
    a,fa,_,fb,_=patches();b=a.copy();selected,r=choose_axis(a,fa,b,fb,[1.,0.,0.],clearance_m=0.)
    assert r['selected_squared_negative_part']==0. and r['clearance_m']==0. and not r['quality_approved']
    _,positive=choose_axis(a,fa,b,fb,[1.,0.,0.],clearance_m=.0001)
    assert positive['selected_squared_negative_part']>0.


@pytest.mark.parametrize('fault',['points-nan','points-bool','points-shape','face-bool','face-float','face-range','face-duplicate',
    'face-degenerate','empty-faces','axis-bool','axis-nonunit','axis-nan','clearance-bool','scale-zero','budget-bool','budget-small'])
def test_invalid_or_incomplete_inputs_reject(fault):
    a,fa,b,fb,axis=patches();kw={}
    if fault=='points-nan':a[0,0]=np.nan
    elif fault=='points-bool':a=a.astype(bool)
    elif fault=='points-shape':a=a.ravel()
    elif fault=='face-bool':fa=fa.astype(bool)
    elif fault=='face-float':fa=fa.astype(float)
    elif fault=='face-range':fa[0,0]=100
    elif fault=='face-duplicate':fa[0,0]=1
    elif fault=='face-degenerate':a[2]=a[1]
    elif fault=='empty-faces':fa=np.zeros((0,3),int)
    elif fault=='axis-bool':axis=axis.astype(bool)
    elif fault=='axis-nonunit':axis=axis*2
    elif fault=='axis-nan':axis[0]=np.nan
    elif fault=='clearance-bool':kw['clearance_m']=True
    elif fault=='scale-zero':kw['scale_m']=0.
    elif fault=='budget-bool':kw['maximum_axis_tests']=True
    elif fault=='budget-small':kw['maximum_axis_tests']=23
    with pytest.raises(ValueError):choose_axis(a,fa,b,fb,axis,**kw)
