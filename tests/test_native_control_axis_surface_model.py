"""Actual stored-centered scene integration and full derivative population."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_control_axis_surface_model import model
from native_stored_pair_model import centered_problem
from native_scene_norms import rows,linearize
from native_surface_model import surface_points
from test_native_stored_pair_model import arguments


def prepared(tmp_path):
    args,kwargs=arguments(tmp_path);centered,decoded,identity=centered_problem(*args,**kwargs)
    return args,centered,decoded


def test_actual_complete_model_preserves_original_norms_and_every_selected_pair(tmp_path):
    args,problem,decoded=prepared(tmp_path);before=rows(problem,args[1],decoded)
    progress=[]
    native,jac,guides,gaps,sj,info,points=model(problem,args[1],*args[3:],.02,decoded_worlds=decoded,
                                              progress=lambda c,n:progress.append((c,n)))
    for name in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(native,name),getattr(before,name))
    _,expected,_=linearize(problem,args[1],step=.001,difference_source='continuous',difference_scheme='central',base_worlds=decoded)
    np.testing.assert_array_equal(jac.toarray(),expected.toarray())
    assert progress==[(i+1,problem.size) for i in range(problem.size)]
    assert guides.count==len(gaps)==sj.shape[0] and sj.shape[1]==problem.size
    np.testing.assert_array_equal(gaps,guides.gaps(surface_points(problem,decoded)))
    assert info['point_derivative_elements']==sum(points[a+'_point_jacobian'].size for a in info['referenced_vertices'])
    assert len(info['actual_difference_offsets'])==problem.size and info['native_acceptance_unchanged']
    assert all(r['explicit_baseline_retained'] and r['all_nine_pairs_scored_per_direction'] for r in info['axis_choices'])
    assert not info['simultaneous_affine_feasibility_proven'] and not info['release_approved']
    # All point derivative columns are checked independently against the
    # continuous proposal worlds on the exact recorded stencils.
    for c,offsets in enumerate(info['actual_difference_offsets']):
        assert len(offsets)==2
        samples=[]
        for h in offsets:
            x=args[1].copy();x[c]+=h;samples.append(problem.worlds(x,quantized=False))
        for a,ids in info['referenced_vertices'].items():
            clock_ids=np.searchsorted(problem.times,points['times_s'])
            expected=(problem.skin_points(a,np.array(ids),samples[0],clock_ids,'vertices')-
                      problem.skin_points(a,np.array(ids),samples[1],clock_ids,'vertices'))/(offsets[0]-offsets[1])
            np.testing.assert_array_equal(points[a+'_point_jacobian'][...,c],expected)
        plus=guides.gaps(surface_points(problem,samples[0]));minus=guides.gaps(surface_points(problem,samples[1]))
        np.testing.assert_allclose(sj.toarray()[:,c],(plus-minus)/(offsets[0]-offsets[1]),atol=3e-12,rtol=0)


@pytest.mark.parametrize('setting',[dict(maximum_point_elements=1),dict(maximum_rows=1),dict(maximum_nonzeros=1),
                                    dict(step=True),dict(trust=.03),dict(progress=1)])
def test_no_budget_or_policy_failure_returns_partial_model(tmp_path,setting):
    args,problem,decoded=prepared(tmp_path);trust=setting.pop('trust',.02)
    with pytest.raises(ValueError):model(problem,args[1],*args[3:],trust,decoded_worlds=decoded,**setting)


def test_changed_decoded_anchor_cannot_be_used_as_continuous_model_origin(tmp_path):
    args,problem,decoded=prepared(tmp_path);decoded=copy.deepcopy(decoded);decoded['A'][:,:,0,3]+=.01
    with pytest.raises(AssertionError):model(problem,args[1],*args[3:],.02,decoded_worlds=decoded)
