"""Decoded recentering retains every original parent cap and scalar lift."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_pair_key_guides import inputs
from test_native_material_depth_bounds import problem
from native_pair_material_recourse import recenter,search_reserve
from native_scene_norms import NormRows


@pytest.fixture(scope='module')
def cached(inputs):
    pair,_=problem(inputs);parent,jac,identity=pair.linearize(pair.initial,pair.source_worlds,.1)
    return pair,parent,jac,identity


def test_decoded_recenter_matches_actual_native_contacts_floor_and_guides(cached):
    pair,parent,_,identity=cached;value=pair.initial.copy();value[:]=np.tile([.01,-.02,.015],4);worlds=pair.worlds(value)
    rows,report=recenter(pair,value,worlds,parent,identity);native,contact=pair.norms(value,worlds)
    n=len(native.caps);c=len(contact.caps);f=identity['floor_rows'];g=pair.guide_gaps(value,worlds)
    np.testing.assert_array_equal(rows.vectors[:n],native.vectors);np.testing.assert_array_equal(rows.vectors[n:n+c],contact.vectors)
    np.testing.assert_array_equal(rows.caps,parent.caps);np.testing.assert_array_equal(rows.scales,parent.scales)
    floors=np.concatenate([pair.models[k].floor(worlds[k])[0]-np.minimum(0,pair.source_floor[k]) for k in pair.names])
    np.testing.assert_allclose(rows.residual()[n+c:],-np.r_[floors,g]/rows.scales[n+c:],atol=1e-10,rtol=0)
    assert report['actual_decoded_vectors'] and not report['cached_derivatives_recomputed'] and report['floor_rows']==f
    rows.caps[0]+=1;assert rows.caps[0]!=parent.caps[0]


def test_recenter_at_original_anchor_reproduces_all_cached_rows(cached):
    pair,parent,_,identity=cached;rows,_=recenter(pair,pair.initial,pair.source_worlds,parent,identity)
    np.testing.assert_array_equal(rows.vectors,parent.vectors);np.testing.assert_array_equal(rows.caps,parent.caps)


@pytest.mark.parametrize('fault',['layout','native-caps','lift-offset','clearance'])
def test_foreign_parent_layout_or_original_limits_reject(cached,fault):
    pair,parent,_,identity=cached;meta=copy.deepcopy(identity);rows=NormRows(parent.vectors.copy(),parent.caps.copy(),parent.scales.copy())
    if fault=='layout':meta['native_rows']-=1
    elif fault=='native-caps':rows.caps[0]+=.1
    elif fault=='lift-offset':meta['conversion']['offset_m'][0]+=.1
    else:meta['conversion']['clearance_m']=.001
    with pytest.raises(ValueError):recenter(pair,pair.initial,pair.source_worlds,rows,meta)


def test_search_reserve_only_tightens_copied_responsive_boundary_rows():
    rows=NormRows([[.010001,0,0],[.01,0,0],[.001,0,0],[.01,0,0]],[.01]*4,[.01]*4)
    j=sparse.csc_matrix(([1.,1.,1.],([0,3,6],[0,0,0])),shape=(12,1))
    before=rows.caps.copy();out,report=search_reserve(rows,j,reserve_m=2e-7)
    np.testing.assert_array_equal(rows.caps,before);np.testing.assert_array_equal(out.vectors,rows.vectors)
    np.testing.assert_array_equal(out.scales,rows.scales);assert report['tightened_rows']==[0,1]
    assert np.all(out.caps<=before) and out.caps[2]==out.caps[3]==.01


def test_failed_fixed_material_row_is_not_hidden_or_truncated():
    rows=NormRows([[.010001,0,0]],[.01],[.01])
    with pytest.raises(ValueError,match='Failed fixed'):search_reserve(rows,sparse.csc_matrix((3,1)))


@pytest.mark.parametrize('reserve',[True,0,-1,float('nan'),.001])
def test_unbounded_or_invalid_search_reserve_rejects(reserve):
    rows=NormRows([[.010001,0,0]],[.01],[.01])
    with pytest.raises(ValueError):search_reserve(rows,sparse.csc_matrix([[1.],[0],[0]]),reserve_m=reserve)
