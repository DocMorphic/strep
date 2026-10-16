from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_depth_guarded_recourse import assemble
from native_scene_norms import NormRows
from native_scene_conic_sum import direction


def inputs():
    native=NormRows([[.999,0,0]],[1],[1]);contact=NormRows([[.0299,0,0],[1,0,0]],[.03,2],[.03,2])
    args=[native,sparse.csr_matrix([[.1],[0],[0]]),contact,sparse.csr_matrix([[.01],[0],[0],[.1],[0],[0]]),[0.],sparse.csr_matrix((1,1)),[-.02,-.01,-.01],sparse.csr_matrix([[1],[-2],[2]]),[0.],[-1.],[1.],.01]
    kw=dict(source_native_caps=[1],source_native_scales=[1],source_contact_caps=[.03,2],source_contact_scales=[.03,2],contact_kinds=['position','relative-speed'],depth_rows=[1],depth_limits_m=[.015])
    return args,kw


def test_original_bounds_and_contact_units_with_feasible_current_reserves():
    args,kw=inputs();rows,jac,info,reserve=assemble(*args,**kw)
    assert info['hard_rows']==5 and info['total_rows']==10
    np.testing.assert_allclose(reserve['native'],[.0005],rtol=0,atol=1e-15)
    np.testing.assert_allclose(reserve['contacts'],[.00005,0],rtol=0,atol=1e-15)
    assert rows.caps[2]==2 and np.all(rows.residual()[:info['hard_rows']]<=1e-8)
    np.testing.assert_array_equal(args[0].caps,[1]);np.testing.assert_array_equal(args[2].caps,[.03,2])
    assert jac.shape==(rows.vectors.size,1) and info['depth_source_row_indices']==[1]


def test_added_local_depth_guard_changes_sum_direction_without_dropping_rows():
    args,kw=inputs();args[0]=NormRows([[0,0,0]],[1],[1]);args[1]=sparse.csr_matrix((3,1));args[2]=None;args[3]=sparse.csr_matrix((0,1))
    kw.update(source_contact_caps=[],source_contact_scales=[],contact_kinds=[])
    guarded,jg,ig,_=assemble(*args,**kw);kw.update(depth_rows=[],depth_limits_m=[]);free,jf,iff,_=assemble(*args,**kw)
    dg,mg=direction(guarded,jg,[0],[-1],[1],.01,hard_rows=ig['hard_rows']);df,mf=direction(free,jf,[0],[-1],[1],.01,hard_rows=iff['hard_rows'])
    assert dg is not None and df is not None and mg['affine_hard_rows_pass'] and mf['affine_hard_rows_pass']
    assert .00249<dg[0]<.00251 and df[0]>.005
    assert -(-.01-2*dg[0])<=.015+1e-9
    assert ig['surface_rows']==iff['surface_rows']==3 and ig['total_rows']==iff['total_rows']+1


@pytest.mark.parametrize('fault',['reference','native','contact','floor','depth','indices','units','headroom','budget','shape'])
def test_invalid_reference_anchor_or_incomplete_population_rejects(fault):
    args,kw=inputs()
    if fault=='reference':kw['source_native_caps']=[1.1]
    elif fault=='native':args[0].vectors[0,0]=1.1
    elif fault=='contact':args[2].vectors[0,0]=.04
    elif fault=='floor':args[4]=[-.001]
    elif fault=='depth':kw['depth_limits_m']=[.005]
    elif fault=='indices':kw['depth_rows']=[True]
    elif fault=='units':kw['contact_kinds']=['position','unknown']
    elif fault=='headroom':kw['native_headroom']=True
    elif fault=='budget':kw['maximum_nonzeros']=1
    else:args[7]=args[7][:1]
    with pytest.raises(ValueError):assemble(*args,**kw)


def test_fixed_native_rows_keep_original_caps_and_empty_floors_are_explicit():
    args,kw=inputs();args[1]=sparse.csr_matrix((3,1));args[4]=[];args[5]=sparse.csr_matrix((0,1));rows,_,info,reserve=assemble(*args,**kw)
    assert reserve['native'][0]==0 and rows.caps[0]==1 and info['floor_rows']==0
