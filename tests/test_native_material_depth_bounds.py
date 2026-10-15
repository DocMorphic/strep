"""Full material distances bound tracked depth despite scalar projection tradeoffs."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
import trimesh
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_pair_key_guides import inputs
from native_pair_key_guides import PairKeyGuides
from native_partner_surface_rows import SurfaceRows
from native_scene_geometry import faces_for
from native_scene_norms import NormRows
from native_material_depth_bounds import MaterialDepthBounds,append_hard


def problem(inputs,*,regional=False,extra=False):
    models,guides=inputs;face=faces_for(models['B'].rig)[0][0].tolist()
    row=dict(kind='penetrating-vertex',time_s=guides[0]['time_s'],normal_world=[1.,0.,0.],constant_m=0.,clearance_m=.0005,
        left=dict(actor='A',vertices=[face[0]],weights=[1.]),right=dict(actor='B',vertices=face,weights=[.2,.3,.5]),target_triangle=0)
    rows=[row]
    if extra:
        second=copy.deepcopy(row);second['left']['vertices']=[face[1]];rows.append(second)
        reverse=copy.deepcopy(row);reverse['left']['actor']='B';reverse['right']['actor']='A';reverse['right']['weights']=[.05,.15,.8];rows.append(reverse)
    surface=SurfaceRows(models['A'].scene,rows,dict(rows=len(rows)))
    pair=PairKeyGuides(models,guides if regional else [],surface_rows=surface)
    return pair,MaterialDepthBounds(pair,pair.source_worlds)


def test_scalar_projection_can_improve_while_material_distance_grows():
    normal=np.array([0.,0.,1.]);before=np.array([0.,0.,-.01]);after=np.array([.03,0.,-.009])
    assert after@normal>before@normal and np.linalg.norm(after)>np.linalg.norm(before)


def test_material_point_is_on_actual_moving_triangle_and_bounds_nearest_distance(inputs):
    pair,bounds=problem(inputs);value=pair.initial.copy();value[:]=np.tile([.01,-.02,.015],4);worlds=pair.worlds(value)
    vectors=bounds.vectors(worlds);g=bounds.groups[0];target=pair.models[g['target']];stamp=g['stamp']
    p,r=target.actor['placement'];vertices=target.rig.vertices(worlds[g['target']][stamp])@r.T+p
    q=g['weights'][0]@vertices[g['right'][0]]
    source=pair.models[g['source']].points(worlds[g['source']],g['left'],np.array([stamp]))[0]
    np.testing.assert_allclose(vectors[0],source[0]-q,atol=1e-12,rtol=0)
    mesh=trimesh.Trimesh(vertices,faces_for(target.rig)[0],process=False)
    _,nearest,_=trimesh.proximity.closest_point(mesh,source)
    assert nearest[0]<=np.linalg.norm(vectors[0])+1e-12


def test_group_depth_bounds_keep_actor_direction_and_time_references_separate(inputs):
    pair,bounds=problem(inputs,extra=True);lengths=np.linalg.norm(bounds.reference_vectors,axis=1)
    assert len(bounds.groups)==2 and bounds.labels[0][1:]!=bounds.labels[1][1:]
    assert bounds.caps[0]==bounds.caps[1]==max(lengths[:2]) and bounds.caps[2]==lengths[2]
    assert np.all(bounds.rows(pair.source_worlds).residual()<=0)


def test_sparse_material_derivatives_match_full_native_continuous_differences(inputs):
    pair,bounds=problem(inputs,regional=True);base,jac,info=bounds.linearize(pair.initial,pair.source_worlds,step=.0001)
    columns=[];h=1e-6
    for column in range(pair.size):
        step=np.zeros(pair.size);step[column]=h
        columns.append(((bounds.vectors(pair.worlds(step,quantized=False))-bounds.vectors(pair.worlds(-step,quantized=False)))/(2*h)).ravel())
    expected=np.stack(columns,axis=1)
    np.testing.assert_allclose(jac.toarray(),expected,atol=1e-5,rtol=0)
    assert len(info['structurally_zero_columns'])>0 and pair.size-1 in info['structurally_zero_columns']
    for column in info['structurally_zero_columns']:np.testing.assert_array_equal(expected[:,column],0.)
    assert jac[:,:pair.sizes[0]].nnz and jac[:,pair.sizes[0]:sum(pair.sizes)].nnz
    np.testing.assert_array_equal(base.vectors,bounds.reference_vectors)


def test_material_reference_caps_cannot_be_raised_after_construction(inputs):
    pair,bounds=problem(inputs);bounds.caps[0]+=1.
    with pytest.raises(ValueError,match='reference bounds changed'):bounds.rows(pair.source_worlds)


@pytest.mark.parametrize('fault',['missing-face','boolean-face','wrong-face','source-not-vertex','row-budget'])
def test_material_bound_requires_actual_canonical_target_face(inputs,fault):
    pair,bounds=problem(inputs);row=pair.surface.rows[0]
    if fault=='missing-face':row.pop('target_triangle')
    elif fault=='boolean-face':row['target_triangle']=True
    elif fault=='wrong-face':row['target_triangle']=999999
    elif fault=='source-not-vertex':row['left'].update(vertices=row['right']['vertices'],weights=[.2,.3,.5])
    if fault=='row-budget':
        with pytest.raises(ValueError):MaterialDepthBounds(pair,pair.source_worlds,maximum_rows=0)
    else:
        with pytest.raises(ValueError):MaterialDepthBounds(pair,pair.source_worlds)


def test_material_jacobian_budget_rejects_complete_model_instead_of_truncating(inputs):
    pair,bounds=problem(inputs)
    with pytest.raises(ValueError,match='none discarded'):bounds.linearize(pair.initial,pair.source_worlds,maximum_nonzeros=1)


def test_hard_material_composition_retains_all_parent_native_and_soft_rows():
    old=NormRows([[0.,0,0],[1.02,0,0]],[1.,1.],[1.,.001]);j=sparse.csc_matrix(np.arange(12).reshape(6,2))
    new=NormRows([[.01,.02,0]],[.03],[.03]);mj=sparse.csc_matrix([[1.,0],[0.,1.],[0,0]])
    system,jac,info=append_hard(old,j,1,new,mj)
    assert info['hard_rows']==2 and info['material_hard_rows']==1
    for key in ('vectors','caps','scales'):
        np.testing.assert_array_equal(getattr(system,key)[[0,2]],getattr(old,key))
        np.testing.assert_array_equal(getattr(system,key)[1:2],getattr(new,key))
    np.testing.assert_array_equal(jac.toarray()[np.r_[0:3,6:9]],j.toarray())
    np.testing.assert_array_equal(jac.toarray()[3:6],mj.toarray())
    with pytest.raises(ValueError,match='none discarded'):append_hard(old,j,1,new,mj,maximum_nonzeros=1)


@pytest.mark.parametrize('hard',[0,True,-1,3])
def test_invalid_parent_hard_prefix_rejects(hard):
    old=NormRows([[0.,0,0],[1.,0,0]],[1.,1.],[1.,1.]);j=sparse.csc_matrix((6,1))
    new=NormRows([[.01,0,0]],[.02],[.02])
    with pytest.raises(ValueError):append_hard(old,j,hard,new,sparse.csc_matrix((3,1)))


def threshold_problem(inputs):
    pair,_=problem(inputs);m=pair.models['B'];stamp=pair.surface.rows[0]['time_s'];index=int(np.searchsorted(pair.times,stamp))
    p,r=m.actor['placement'];vertices=m.rig.vertices(pair.source_worlds['B'][index])@r.T+p;faces=faces_for(m.rig)[0]
    edge=vertices[faces[:,1]]-vertices[faces[:,0]];triangle=int(np.linalg.norm(edge,axis=1).argmax());length=np.linalg.norm(edge[triangle]);assert length>.012
    rows=[]
    for depth in (.004,.0049,.012):
        row=copy.deepcopy(pair.surface.rows[0]);row['target_triangle']=triangle;row['left']['vertices']=[int(faces[triangle,0])]
        row['right'].update(vertices=faces[triangle].tolist(),weights=[1-depth/length,depth/length,0.]);rows.append(row)
    surface=SurfaceRows(pair.scene,rows,dict(rows=len(rows)));pair=PairKeyGuides(pair.models,[],surface_rows=surface)
    return pair,edge[triangle]/length


def test_individual_threshold_blocks_shallow_crossing_allowed_by_group_peak(inputs):
    pair,direction=threshold_problem(inputs);old=MaterialDepthBounds(pair,pair.source_worlds)
    bounds=MaterialDepthBounds(pair,pair.source_worlds,penetration_limit_m=.005)
    np.testing.assert_allclose(bounds.caps,[.005,.005,.012],atol=1e-12,rtol=0)
    assert np.all(bounds.rows(pair.source_worlds).residual()<=0)
    worlds={n:w.copy() for n,w in pair.source_worlds.items()};worlds['A'][:,:,:3,3]-=.0004*direction
    assert old.rows(worlds).residual()[1]<0 and bounds.rows(worlds).residual()[1]>0
    assert bounds.rows(worlds).residual()[0]<0 and bounds.rows(worlds).residual()[2]>0


def test_individual_threshold_retains_group_ceiling_and_zero_limit_reference(inputs):
    pair,_=threshold_problem(inputs);old=MaterialDepthBounds(pair,pair.source_worlds)
    loose=MaterialDepthBounds(pair,pair.source_worlds,penetration_limit_m=.1)
    zero=MaterialDepthBounds(pair,pair.source_worlds,penetration_limit_m=0)
    np.testing.assert_array_equal(loose.caps,old.caps)
    np.testing.assert_array_equal(zero.caps,np.linalg.norm(zero.reference_vectors,axis=1))
    np.testing.assert_array_equal(zero.reference_vectors,old.reference_vectors)
    assert np.all(zero.rows(pair.source_worlds).residual()<=0)


def test_threshold_changes_caps_only_and_records_explicit_derivative_policy(inputs):
    pair,_=threshold_problem(inputs);old=MaterialDepthBounds(pair,pair.source_worlds)
    bounds=MaterialDepthBounds(pair,pair.source_worlds,penetration_limit_m=.005)
    a,ja,_=old.linearize(pair.initial,pair.source_worlds);b,jb,info=bounds.linearize(pair.initial,pair.source_worlds)
    np.testing.assert_array_equal(a.vectors,b.vectors);np.testing.assert_array_equal(ja.toarray(),jb.toarray())
    assert info['penetration_limit_m']==.005 and info['bound_policy']=='individual_reference_or_threshold_with_group_ceiling'
    assert np.all(b.caps<=a.caps) and np.any(b.caps<a.caps)


@pytest.mark.parametrize('threshold',[True,-.001,.100001,float('nan'),float('inf'),'0.005'])
def test_invalid_individual_threshold_rejects(inputs,threshold):
    pair,_=problem(inputs)
    with pytest.raises(ValueError,match='penetration threshold'):MaterialDepthBounds(pair,pair.source_worlds,penetration_limit_m=threshold)
