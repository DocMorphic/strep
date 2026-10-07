"""Multi-time, mixed-unit placed meshes with complete original native stencils."""
import copy,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_pair_clearance_guides import linearize_pair_guides
from native_pair_clearance_guide import linearize_pair_guide
from native_scene_norms import rows
from test_native_pair_clearance_guide import setup,direct


def descriptors(guide):
    first=copy.deepcopy(guide);first.update(time_s=0.,scale_m=.02,clearance_m=0.)
    last=copy.deepcopy(guide);last.update(time_s=2.,actor_a='B',actor_b='A',
        vertices_a=[3],vertices_b=[0,1,2],axis_world=[-1.,0.,0.],scale_m=.07,clearance_m=.002)
    return [first,guide,last]


def test_every_time_pair_and_unit_matches_actual_worlds_with_one_complete_stencil_population(tmp_path):
    problem,x,decoded,guide=setup(tmp_path);guides=descriptors(guide);samples={};calls=[];original=problem.worlds
    def traced(value,quantized=True):
        if not quantized and np.count_nonzero(value-x)==1:calls.append(value.copy())
        return original(value,quantized=quantized)
    problem.worlds=traced
    model=linearize_pair_guides(problem,x,decoded,guides,stencil_sink=lambda c,s,v:samples.update({(c,s):v}))
    assert len(calls)==len(samples)==model.identity['column_proxy_evaluations']==2*len(x)
    assert model.identity['guide_row_offsets']==[0,6,12,15]
    assert model.identity['point_coordinate_offsets']==[0,15,30,42]
    for i,g in enumerate(guides):
        a,b=model.identity['guide_row_offsets'][i:i+2];p,q=model.identity['point_coordinate_offsets'][i:i+2]
        point,gap=direct(problem,decoded,g);np.testing.assert_array_equal(model.points[p:q],point)
        np.testing.assert_array_equal(model.gaps_m[a:b],gap)
        np.testing.assert_array_equal(model.guide_residual[a:b],(gap-g['clearance_m'])/g['scale_m'])
        single=linearize_pair_guide(problem,x,decoded,g)
        np.testing.assert_array_equal(model.guide_jacobian[a:b].toarray(),single.guide_jacobian.toarray())
        np.testing.assert_array_equal(model.native_jacobian.toarray(),single.native_jacobian.toarray())
        for k in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(model.native,k),getattr(single.native,k))
    for c in range(len(x)):
        for sign in (1,-1):
            value=x.copy();value[c]+=sign*.001;worlds=original(value,quantized=False);native=rows(problem,value,worlds)
            point,gap=zip(*(direct(problem,worlds,g) for g in guides));sample=samples[c,sign]
            np.testing.assert_array_equal(sample['points'],np.concatenate(point));np.testing.assert_array_equal(sample['gaps_m'],np.concatenate(gap))
            for k in ('vectors','caps','scales'):np.testing.assert_array_equal(sample[k],getattr(native,k))
    assert model.identity['all_original_caps_scales_unchanged'] and not model.identity['quality_approved'] and not model.identity['release_approved']
    guides[0]['vertices_a'].clear();assert model.identity['guides'][0]['vertices_a']==[0,1]


def test_boundary_uses_per_guide_continuous_origin_and_recorded_offsets(tmp_path):
    problem,x,_,guide=setup(tmp_path);guides=descriptors(guide);x[0]=problem.upper[0];decoded=problem.worlds(x)
    model=linearize_pair_guides(problem,x,decoded,guides)
    assert model.identity['actual_difference_offsets'][0]==[-.001]
    origin=problem.worlds(x,quantized=False);value=x.copy();value[0]-=.001;other=problem.worlds(value,quantized=False)
    for i,g in enumerate(guides):
        a,b=model.identity['guide_row_offsets'][i:i+2];_,base=direct(problem,origin,g);_,gap=direct(problem,other,g)
        np.testing.assert_array_equal(model.guide_jacobian.getcol(0).toarray()[a:b,0],(gap-base)/-.001/g['scale_m'])
    assert model.identity['one_sided_difference_columns']==1


def test_single_descriptor_preserves_existing_builder_numerical_results(tmp_path):
    problem,x,decoded,guide=setup(tmp_path);a=linearize_pair_guides(problem,x,decoded,[guide]);b=linearize_pair_guide(problem,x,decoded,guide)
    for key in ('points','gaps_m','guide_residual','continuous_origin_points'):np.testing.assert_array_equal(getattr(a,key),getattr(b,key))
    for key in ('native_jacobian','guide_jacobian'):np.testing.assert_array_equal(getattr(a,key).toarray(),getattr(b,key).toarray())
    assert a.identity['actual_difference_offsets']==b.identity['actual_difference_offsets']


@pytest.mark.parametrize('fault',['empty','not-list','too-many','duplicate','extra','missing','actor','same-actor',
    'ids-bool','ids-duplicate','ids-range','time-bool','time-off-clock','axis-bool','axis-nonunit','axis-nonfinite',
    'clearance-bool','scale-nonfinite','sink','point-budget','point-budget-bool','native-budget','step'])
def test_invalid_last_descriptor_or_total_budget_rejects_before_any_world_query(tmp_path,fault):
    problem,x,decoded,guide=setup(tmp_path);guides=descriptors(guide);g=guides[-1];kw={}
    if fault=='empty':guides=[]
    elif fault=='not-list':guides=tuple(guides)
    elif fault=='too-many':guides=[guide]*65
    elif fault=='duplicate':guides.append(copy.deepcopy(guides[0]))
    elif fault=='extra':g['extra']=True
    elif fault=='missing':g.pop('scale_m')
    elif fault=='actor':g['actor_a']='missing'
    elif fault=='same-actor':g['actor_b']=g['actor_a']
    elif fault=='ids-bool':g['vertices_a']=[True]
    elif fault=='ids-duplicate':g['vertices_b']=[0,0]
    elif fault=='ids-range':g['vertices_b']=[10000]
    elif fault=='time-bool':g['time_s']=True
    elif fault=='time-off-clock':g['time_s']=.1234567
    elif fault=='axis-bool':g['axis_world']=[True,0.,0.]
    elif fault=='axis-nonunit':g['axis_world']=[2.,0.,0.]
    elif fault=='axis-nonfinite':g['axis_world']=[np.nan,0.,0.]
    elif fault=='clearance-bool':g['clearance_m']=True
    elif fault=='scale-nonfinite':g['scale_m']=np.inf
    elif fault=='sink':kw['stencil_sink']=True
    elif fault=='point-budget':kw['maximum_point_elements']=1
    elif fault=='point-budget-bool':kw['maximum_point_elements']=True
    elif fault=='native-budget':kw['maximum_elements']=0
    elif fault=='step':kw['step']=True
    def unexpected(*a,**kw):raise AssertionError('must not query before every descriptor and budget validate')
    problem.worlds=unexpected
    with pytest.raises(ValueError):linearize_pair_guides(problem,x,decoded,guides,**kw)


def test_total_pair_budget_is_enforced_across_individually_valid_guides(tmp_path):
    problem,x,decoded,guide=setup(tmp_path)
    for n in ('A','B'):problem.scene.actors[n]['skin']=SimpleNamespace(vertex_references=np.zeros((17,3)))
    guides=[]
    for i in range(16):
        g=copy.deepcopy(guide);g.update(vertices_a=list(range(17)),vertices_b=list(range(17)),clearance_m=i*.0001);guides.append(g)
    def unexpected(*a,**kw):raise AssertionError('must not query oversized complete guide population')
    problem.worlds=unexpected
    with pytest.raises(ValueError,match='total 4096-row'):linearize_pair_guides(problem,x,decoded,guides)


def test_sink_copies_and_failure_leave_original_problem_method_unchanged(tmp_path):
    problem,x,decoded,guide=setup(tmp_path);before=problem.worlds
    def mutate(c,s,v):
        for a in v.values():a.fill(np.nan)
    model=linearize_pair_guides(problem,x,decoded,descriptors(guide),stencil_sink=mutate)
    assert np.isfinite(model.native_jacobian.data).all() and np.isfinite(model.guide_jacobian.data).all() and problem.worlds==before
    def failure(c,s,v):raise RuntimeError('multi guide observer failure')
    with pytest.raises(RuntimeError,match='observer failure'):linearize_pair_guides(problem,x,decoded,descriptors(guide),stencil_sink=failure)
    assert problem.worlds==before
