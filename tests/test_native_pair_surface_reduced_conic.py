"""Equivalent solver rows retain tight hard caps and full predicted checks."""
from pathlib import Path
import sys
import numpy as np
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_norms import NormRows
from native_pair_surface_conic import direction as full_direction
from native_pair_surface_reduced_conic import direction


def test_equivalent_solve_matches_full_model_with_original_twenty_micron_cap():
    native=NormRows([[0.,0,0]],[2e-5],[.0001]);nj=sparse.csc_matrix([[1.],[0.],[0.]])
    gaps=np.arange(9)*.002-.01;sj=sparse.csc_matrix(np.ones((9,1)))
    full,old=full_direction(native,nj,gaps,sj,[0.],[-1.],[1.],.02,clearance=0.)
    reduced,info,certificate=direction(native,nj,gaps,sj,[0,9],[0.],[-1.],[1.],.02,clearance=0.)
    assert full is not None and reduced is not None and len(certificate.retained)==1
    np.testing.assert_allclose(full,reduced,atol=1e-9,rtol=0)
    assert abs(reduced[0])<=2e-5+1e-9 and native.residual(nj,reduced).max()<1e-7
    assert info['complete_surface_rows']==9 and info['equivalent_encoded_surface_rows']==1
    assert info['all_original_affine_surface_rows_evaluated'] and info['certificate']['affine_equivalent']
    assert abs(info['affine_optimum']-old['affine_optimum'])<1e-7


def test_competing_tied_slopes_are_not_replaced_by_a_single_minimum():
    native=NormRows([[0.,0,0]],[.01],[1.]);nj=sparse.csc_matrix([[1.],[0.],[0.]])
    gaps=np.full(9,-.002);sj=sparse.csc_matrix(np.array([1,1,1,-1,-1,-1,0,0,0])[:,None])
    delta,info,certificate=direction(native,nj,gaps,sj,[0,9],[0.],[-1.],[1.],.02,clearance=0.)
    assert delta is not None and len(certificate.retained)==3
    assert abs(delta[0])<1e-7 and abs(info['full_affine_surface_excess']-.4)<1e-7
