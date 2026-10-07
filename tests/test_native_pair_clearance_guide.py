"""Full native model fidelity and real placed-skin guidance integration."""
import copy,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_pair_clearance_guide import linearize_pair_guide
from native_scene_norms import linearize,rows
from native_stored_pair_model import centered_problem
from test_native_stored_pair_model import arguments


def setup(tmp_path):
    args,kw=arguments(tmp_path);problem,decoded,_=centered_problem(*args,**kw)
    guide=dict(actor_a='A',vertices_a=[0,1],actor_b='B',vertices_b=[0,2,3],
               time_s=1.,axis_world=[.6,0.,.8],clearance_m=.0001,scale_m=.03)
    return problem,args[1],decoded,guide


def direct(problem,worlds,guide):
    frame=int(np.flatnonzero(problem.times==guide['time_s'])[0]);points=[]
    for name,ids in ((guide['actor_a'],guide['vertices_a']),(guide['actor_b'],guide['vertices_b'])):
        a=problem.scene.actors[name];p,r=a['placement']
        points.append(a['rig'].vertices(worlds[name][frame])[ids]@r.T+p)
    left=points[0]@guide['axis_world'];right=points[1]@guide['axis_world']
    return np.concatenate(points).ravel(),np.tile(right,len(left))-np.repeat(left,len(right))


def test_complete_original_model_and_all_placed_pairs_share_every_full_stencil(tmp_path):
    problem,x,decoded,guide=setup(tmp_path);samples={}
    model=linearize_pair_guide(problem,x,decoded,guide,stencil_sink=lambda c,s,v:samples.update({(c,s):v}))
    original,jac,identity=linearize(problem,x,step=.001,difference_source='continuous',difference_scheme='central',base_worlds=decoded)
    for k in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(model.native,k),getattr(original,k))
    np.testing.assert_array_equal(model.native_jacobian.toarray(),jac.toarray())
    point,gap=direct(problem,decoded,guide)
    np.testing.assert_array_equal(model.points,point);np.testing.assert_array_equal(model.gaps_m,gap)
    np.testing.assert_array_equal(model.guide_residual,(gap-.0001)/.03)
    assert model.guide_jacobian.shape==(6,len(x)) and len(samples)==2*len(x)
    for c in range(len(x)):
        pair=[]
        for h,s in ((.001,1),(-.001,-1)):
            value=x.copy();value[c]+=h;worlds=problem.worlds(value,quantized=False);pt,gaps=direct(problem,worlds,guide)
            actual=rows(problem,value,worlds);sample=samples[c,s]
            for k in ('vectors','caps','scales'):np.testing.assert_array_equal(sample[k],getattr(actual,k))
            np.testing.assert_array_equal(sample['controls'],value);np.testing.assert_array_equal(sample['points'],pt);np.testing.assert_array_equal(sample['gaps_m'],gaps)
            pair.append(gaps)
        np.testing.assert_array_equal(model.guide_jacobian.getcol(c).toarray().ravel(),(pair[0]-pair[1])/.002/.03)
    assert model.identity['column_proxy_evaluations']==identity['column_proxy_evaluations']
    assert model.identity['guide_point_counts']==[2,3] and model.identity['additional_world_stencils_for_guide']==0
    assert model.identity['all_original_native_norm_rows_retained'] and model.identity['all_original_caps_scales_unchanged']
    assert not model.identity['quality_approved'] and not model.identity['release_approved']
    guide['vertices_a'].clear();assert model.identity['guide']['vertices_a']==[0,1]


def test_boundary_column_uses_recorded_one_sided_origin_without_outside_queries(tmp_path):
    problem,x,_,guide=setup(tmp_path);x[0]=problem.upper[0];decoded=problem.worlds(x);samples={}
    model=linearize_pair_guide(problem,x,decoded,guide,stencil_sink=lambda c,s,v:samples.update({(c,s):v}))
    assert model.identity['actual_difference_offsets'][0]==[-.001] and model.identity['one_sided_difference_columns']==1
    origin_point,origin=direct(problem,problem.worlds(x,quantized=False),guide)
    value=x.copy();value[0]-=.001;_,gap=direct(problem,problem.worlds(value,quantized=False),guide)
    np.testing.assert_array_equal(model.continuous_origin_points,origin_point)
    np.testing.assert_array_equal(model.guide_jacobian.getcol(0).toarray().ravel(),(gap-origin)/-.001/.03)
    assert (0,1) not in samples and len(samples)==2*len(x)-1
    assert all(np.all(v['controls']>=problem.lower) and np.all(v['controls']<=problem.upper) for v in samples.values())


def test_observation_sink_cannot_mutate_model_and_sink_failure_does_not_replace_problem_method(tmp_path):
    problem,x,decoded,guide=setup(tmp_path);before=problem.worlds
    def mutate(c,s,v):
        for a in v.values():a.fill(np.nan)
    model=linearize_pair_guide(problem,x,decoded,guide,stencil_sink=mutate)
    assert np.isfinite(model.native_jacobian.data).all() and np.isfinite(model.guide_jacobian.data).all()
    assert problem.worlds==before
    def failure(c,s,v):raise RuntimeError('observation failure')
    with pytest.raises(RuntimeError,match='observation failure'):
        linearize_pair_guide(problem,x,decoded,guide,stencil_sink=failure)
    assert problem.worlds==before


@pytest.mark.parametrize('fault',['extra','missing','same-actor','actor','ids-bool','ids-duplicate','ids-range',
    'ids-empty','time-bool','time-off-clock','axis-bool','axis-nonunit','axis-nonfinite','clearance-bool','scale-nonfinite','sink'])
def test_invalid_guidance_rejects_before_any_world_query(tmp_path,fault):
    problem,x,decoded,guide=setup(tmp_path);sink=None
    if fault=='extra':guide['extra']=True
    elif fault=='missing':guide.pop('scale_m')
    elif fault=='same-actor':guide['actor_b']='A'
    elif fault=='actor':guide['actor_b']='unknown'
    elif fault=='ids-bool':guide['vertices_a']=[True]
    elif fault=='ids-duplicate':guide['vertices_a']=[0,0]
    elif fault=='ids-range':guide['vertices_a']=[10000]
    elif fault=='ids-empty':guide['vertices_b']=[]
    elif fault=='time-bool':guide['time_s']=True
    elif fault=='time-off-clock':guide['time_s']=.1234567
    elif fault=='axis-bool':guide['axis_world']=[True,0.,0.]
    elif fault=='axis-nonunit':guide['axis_world']=[2.,0.,0.]
    elif fault=='axis-nonfinite':guide['axis_world']=[np.nan,0.,0.]
    elif fault=='clearance-bool':guide['clearance_m']=True
    elif fault=='scale-nonfinite':guide['scale_m']=np.inf
    elif fault=='sink':sink=True
    def unexpected(*a,**kw):raise AssertionError('must not query invalid guidance')
    problem.worlds=unexpected
    with pytest.raises(ValueError):linearize_pair_guide(problem,x,decoded,guide,stencil_sink=sink)


def test_oversized_complete_pair_population_rejects_before_geometry(tmp_path):
    problem,x,decoded,guide=setup(tmp_path)
    for name in ('A','B'):problem.scene.actors[name]['skin']=SimpleNamespace(vertex_references=np.zeros((65,3)))
    guide['vertices_a']=list(range(65));guide['vertices_b']=list(range(65))
    def unexpected(*a,**kw):raise AssertionError('must not query oversized guidance')
    problem.worlds=unexpected
    with pytest.raises(ValueError,match='4096-row'):linearize_pair_guide(problem,x,decoded,guide)
