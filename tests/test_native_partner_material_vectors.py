from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_pair_contact_objectives import separated
from test_native_surface_key_jacobian import fixture
from native_partner_surface_rows import SurfaceRows
from native_scene_geometry import faces_for
from native_partner_material_vectors import evaluate,linearize,insert_guards
from native_scene_norms import NormRows
from native_scene_conic_sum import direction


def setup(models):
    base,layouts=fixture(models);face=faces_for(base.scene.actors['B']['rig'])[0][0].tolist();rows=[]
    for key in (2,3,4):rows.append(dict(kind='penetrating-vertex',time_s=float(models['A'].clock[key]),normal_world=[1.,0,0],constant_m=0.,left=dict(actor='A',vertices=[0],weights=[1.]),right=dict(actor='B',vertices=face,weights=[.2,.3,.5]),target_triangle=0))
    return SurfaceRows(base.scene,rows,{}),layouts


@pytest.mark.parametrize('nonzero',[False,True])
def test_vector_derivative_matches_independent_native_material_points(separated,nonzero):
    models,_=separated;surface,layouts=setup(models);size=sum(m.size for m in models.values());point=np.tile([.05,-.03,.02],4) if nonzero else np.zeros(size)
    def actual(value):
        offset=0;worlds={}
        for name,m in models.items():worlds[name]=m.worlds(value[offset:offset+m.size],quantized=False);offset+=m.size
        def vertices(name,t):
            m=models[name];i=int(np.flatnonzero(m.times==t)[0]);p,r=surface.scene.actors[name]['placement'];return m.rig.vertices(worlds[name][i])@r.T+p
        result=[]
        for row in surface.rows:
            a,b=row['left'],row['right'];t=row['time_s'];result.append(vertices(a['actor'],t)[a['vertices'][0]]-np.asarray(b['weights'])@vertices(b['actor'],t)[b['vertices']])
        return np.asarray(result),vertices
    vectors,jac,meta=linearize(surface,[0,1,2],layouts,value=point);native,callback=actual(point)
    np.testing.assert_allclose(vectors,native,atol=1e-12,rtol=0);np.testing.assert_allclose(evaluate(surface,[0,1,2],callback),native,atol=1e-12,rtol=0)
    columns=[]
    for i in range(size):
        step=np.eye(size)[i]*1e-6;columns.append(((actual(point+step)[0]-actual(point-step)[0])/2e-6).ravel())
    np.testing.assert_allclose(jac.toarray(),np.stack(columns,axis=1),atol=3e-9,rtol=2e-7)
    assert jac[:3].nnz==0 and meta['canonical_target_faces_verified'] and meta['native_pose_vertex_maximum_error_m']<=1e-12


def test_fixed_normal_can_miss_increased_depth_but_material_norm_bounds_it():
    angle=.1;p=np.array([.49,0,0]);normal=np.array([np.cos(angle),np.sin(angle),0]);q=.5*normal
    old_limit=.01;scalar_depth=-(p-q)[0];nearest_depth=.5-p@normal;material_distance=np.linalg.norm(p-q)
    assert scalar_depth<old_limit<nearest_depth<=material_distance


def test_roundoff_weight_sum_is_normalized_without_mutating_source(separated):
    models,_=separated;surface,_=setup(models);row=surface.rows[0];weights=np.array([.2,.3,.5])*(1+5e-11);row['right']['weights']=weights.tolist()
    def vertices(name,t):return np.tile([1.,2.,3.] if name=='A' else [4.,5.,6.],(len(surface.scene.actors[name]['skin'].nodes),1))
    np.testing.assert_allclose(evaluate(surface,[0],vertices),[[-3.,-3.,-3.]],atol=2e-15,rtol=0)
    np.testing.assert_array_equal(row['right']['weights'],weights)


@pytest.mark.parametrize('fault',['face','vertices','weights','sum','nan','source','same-actor','indices','budget','time'])
def test_incomplete_or_non_surface_declaration_rejects(separated,fault):
    models,_=separated;surface,layouts=setup(models);row=surface.rows[1];ids=[1];kwargs={}
    if fault=='face':row['target_triangle']=999999
    elif fault=='vertices':row['right']['vertices'].reverse()
    elif fault=='weights':row['right']['weights']=[-.1,.6,.5]
    elif fault=='sum':row['right']['weights']=[.2,.3,.6]
    elif fault=='nan':row['right']['weights']=[np.nan,.5,.5]
    elif fault=='source':row['left']['weights']=[.5,.5];row['left']['vertices']=[0,1]
    elif fault=='same-actor':row['left']['actor']='B'
    elif fault=='indices':ids=[True]
    elif fault=='budget':kwargs['maximum_nonzeros']=1
    else:row['time_s']+=.00001
    with pytest.raises(ValueError):linearize(surface,ids,layouts,**kwargs)


def test_inserted_vector_norm_guard_keeps_base_rows_and_all_components():
    base=NormRows([[0,0,0],[2,0,0]],[1,0],[1,1]);jac=sparse.csr_matrix([[0],[0],[0],[-1],[0],[0]])
    guarded,j,meta=insert_guards(base,jac,1,[[.01,0,0]],sparse.csr_matrix([[1],[0],[0]]),[.015])
    np.testing.assert_array_equal(guarded.vectors[[0,2]],base.vectors);np.testing.assert_array_equal(guarded.caps[[0,2]],base.caps)
    delta,info=direction(guarded,j,[0],[-1],[1],1.,hard_rows=meta['hard_rows'])
    assert delta is not None and .00499<delta[0]<.00501 and info['affine_hard_rows_pass']
    assert meta['all_original_rows_caps_scales_retained'] and meta['hard_rows']==2


def test_insert_guard_cannot_exclude_anchor_or_truncate_matrix():
    base=NormRows([[0,0,0],[2,0,0]],[1,0],[1,1]);jac=sparse.csr_matrix([[0],[0],[0],[-1],[0],[0]]);gj=sparse.csr_matrix([[1],[0],[0]])
    with pytest.raises(ValueError):insert_guards(base,jac,1,[[.01,0,0]],gj,[.005])
    with pytest.raises(ValueError):insert_guards(base,jac,1,[[.01,0,0]],gj,[.015],maximum_nonzeros=1)
