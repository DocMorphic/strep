"""Complete sampled positional ranking includes support edges; exports decide."""
import copy,sys
from pathlib import Path
import numpy as np,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_translation_interval_rank as interval
import native_translation_stencil_search as local
from native_component_storage_repair import ComponentAdjustedEdits
from native_scene_fit import SceneProblem
from test_native_component_storage import fixture


def observations():
    candidates=np.zeros((2,3,3));candidates[1,:,1]=1
    current=np.zeros((3,3));weights=np.zeros((5,3));weights[1:4]=np.eye(3)
    parent=np.repeat(np.eye(3)[None],5,axis=0);points=np.zeros((5,2,3));affected=np.array([True,False])
    speed=np.full((4,2),2.);acceleration=np.zeros((3,2))
    baseline=np.r_[np.full(10,-1.),np.full(8,-1.005),np.full(6,-10.)]
    return [candidates,current,weights,parent,points,points.copy(),affected,speed,acceleration,baseline,np.array([.4,-.3])]


def score(args,**kwargs):return interval.scores(*args,dt=1.,displacement=10.,tolerance=.01,**kwargs)


def test_edges_and_all_joints_prevent_a_false_local_acceleration_pass():
    args=observations();result=score(args)
    # Translation is constant across the three center samples, so the old
    # local target score would see zero acceleration. Both support edges fail.
    assert result['failed_rows'].tolist()==[1,3]
    assert result['introduced_positional_rows'].tolist()==[0,2]
    assert result['maximum_excess'].tolist()==pytest.approx([.4,990.])
    assert result['positional_rows']==24 and result['fixed_rows']==2
    assert result['proposal_only'] and not result['geometry_assessed'] and not result['release_approved']
    literal=args[4].copy();literal[1:4,0,1]=1
    dynamic=np.r_[((np.linalg.norm(literal-args[5],axis=2)-10)/10).T.ravel(),
        ((np.linalg.norm(np.diff(literal,axis=0),axis=2)-args[7]-.01)/np.maximum(args[7],.001)).ravel(),
        ((np.linalg.norm(np.diff(literal,n=2,axis=0),axis=2)-args[8]-.01)/np.maximum(args[8],.001)).ravel()]
    whole=np.r_[args[-1],dynamic];positive=np.maximum(whole,0)
    assert result['squared_positive'][1]==pytest.approx(float(positive@positive))


def test_chunking_and_detached_observations_preserve_complete_scores():
    args=observations();copies=[a.copy() for a in args]
    first=score(args,chunk_size=1);second=score(args,chunk_size=128)
    for key in ('maximum_excess','squared_positive','failed_rows','introduced_positional_rows'):
        np.testing.assert_array_equal(first[key],second[key])
    for actual,expected in zip(args,copies):np.testing.assert_array_equal(actual,expected)


def test_joint_major_displacement_does_not_invent_a_new_failure():
    points=np.zeros((5,2,3));points[2,0,1]=2
    source=np.zeros_like(points);speed=np.full((4,2),100.);acc=np.full((3,2),100.)
    baseline=np.r_[(np.linalg.norm(points,axis=2)-1).T.ravel(),
        ((np.linalg.norm(np.diff(points,axis=0),axis=2)-speed)/speed).ravel(),
        ((np.linalg.norm(np.diff(points,n=2,axis=0),axis=2)-acc)/acc).ravel()]
    result=interval.scores(np.zeros((1,1,3)),np.zeros((1,3)),np.zeros((5,1)),np.repeat(np.eye(3)[None],5,axis=0),
        points,source,np.array([True,False]),speed,acc,baseline,np.array([]),dt=1.,displacement=1.,tolerance=0.)
    assert result['failed_rows'].tolist()==[1] and result['introduced_positional_rows'].tolist()==[0]


@pytest.mark.parametrize('index,value',[
    (0,np.zeros((0,3,3))),(0,np.zeros((19684,3,3))),(1,np.zeros((2,3))),
    (2,np.full((5,3),1.)),(3,np.full((5,3,3),np.nan)),(4,np.zeros((2,2,3))),
    (6,np.array([1,0])),(7,np.full((4,2),-1.)),(8,np.zeros((4,2))),
    (9,np.zeros(23)),(10,np.array([np.nan])),
])
def test_incomplete_or_nonfinite_observations_reject(index,value):
    args=observations();args[index]=value
    with pytest.raises(ValueError):score(args)


@pytest.mark.parametrize('chunk',[True,0,129])
def test_unbounded_or_implicit_chunk_budget_rejects(chunk):
    with pytest.raises(ValueError):score(observations(),chunk_size=chunk)


def test_real_full_decode_repairs_jitter_and_preserves_original_caps(tmp_path):
    base,policy,row,*_=fixture(tmp_path);problem=SceneProblem(base.scene,base);value=base.initial.copy();caps=[c.copy() for c in problem.caps['A'].caps];seen=[]
    def decode(corrections,label):
        edits=ComponentAdjustedEdits(base,policy,corrections);path=tmp_path/(label+'.glb');edits.export('A',value,path)
        assert edits.audit('A',path,0,value=value)['passed']
        residual,worlds=problem.decoded({'A':path},value);seen.append(residual.copy());return residual,worlds
    _,report=interval.search(problem,value,policy,[row],decode,stages=1,probes_per_stage=4)
    assert np.any(seen[0]>0) and report['native_conditions_pass'] and np.all(seen[-1]<=0)
    target=next(r for r in report['history'][0]['original_rate_failures'] if 'translation_stencil' in r)
    ranking=target['translation_stencil']['interval_ranking']
    assert ranking['complete_population']==report['history'][0]['planned_options']
    assert ranking['positional_rows']==(3*len(problem.uniform)-3)*len(base.scene.actors['A']['rig'].joints)
    assert ranking['contacts_and_geometry_not_updated'] and ranking['proposal_only']
    assert not report['geometry_assessed'] and not report['quality_approved'] and not report['release_approved']
    for actual,expected in zip(problem.caps['A'].caps,caps):np.testing.assert_array_equal(actual,expected)


@pytest.mark.parametrize('fault',['duplicate','omit','float'])
def test_rank_hook_cannot_drop_repeat_or_forge_population_indices(tmp_path,fault):
    base,policy,row,*_=fixture(tmp_path);problem=SceneProblem(base.scene,base)
    editor=ComponentAdjustedEdits(base,policy,[row]);path=tmp_path/'seed.glb';editor.export('A',base.initial,path)
    _,worlds=problem.decoded({'A':path},base.initial)
    def invalid(*args):
        count=args[-1]['population'];order=np.arange(count)
        if fault=='duplicate':order[-1]=0
        elif fault=='omit':order=order[:-1]
        else:order=order.astype(float)
        return order,{}
    with pytest.raises(ValueError,match='permutation'):
        local.plan(problem,worlds,[row],base.initial,policy,_ranker=invalid)
