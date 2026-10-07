"""Complete skin/key support and native-gated finite material correction."""
from pathlib import Path
from types import SimpleNamespace as NS
import copy, sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import native_material_storage_search as searcher
from native_material_witness_guides import MaterialWitnessGuides
from native_rotation_storage_repair import StorageAdjustedEdits
from test_native_pair_clearance_guide import setup
from test_native_material_witness_guides import descriptors


def synthetic_observer(time=.4, bary=(.25, 0., .75)):
    # A multiweighted source and nonzero target corners in distinct branches.
    # Node3 has zero skin weight; node4 occurs only in the zero barycentric corner.
    parents=np.array([-1,0,0,-1,-1])
    nodes=np.array([[1,2,3],[4,3,3],[2,3,3]])
    weights=np.array([[.4,.6,0.],[1.,0.,0.],[1.,0.,0.]])
    actors={n:dict(rig=NS(parents=parents.copy()),skin=NS(nodes=nodes.copy(),weights=weights.copy())) for n in ('A','B')}
    tracks=[dict(node=n,path='rotation',clock=np.array([0.,.3,.5,1.]),ids=np.arange(4)) for n in range(5)]
    problem=NS(scene=NS(actors=actors),edits=NS(actors={n:dict(tracks=copy.deepcopy(tracks)) for n in actors}),times=np.array([time]))
    observer=object.__new__(MaterialWitnessGuides);observer.problem=problem
    observer.prepared=[('A',0,'B',np.array([0,1,2]),np.array(bary),0,np.array([1.,0.,0.]),.0001,.03)]
    observer.clearances=np.array([.0001])
    return observer


@pytest.mark.parametrize('time,keys',[(0.,{0}),(.3,{1}),(.4,{1,2}),(1.,{3})])
def test_complete_multiweight_ancestors_both_brackets_and_all_absolute_choices(time,keys):
    observer=synthetic_observer(time);options,failed=searcher.plan(observer,[1e-8],[])
    expected={(a,n,k,c,s) for a in ('A','B') for n in (0,1,2) for k in keys for c in range(4) for s in (-1,1)}
    actual={(o['actor'],o['node'],o['key_index'],o['component'],o['step']) for o in options}
    assert actual==expected and len(options)==len(expected)
    assert failed[0]['support']['B']==dict(vertex_ids=[0,2],influencing_ancestors=[0,1,2])
    assert [o['actor'] for o in options[:6]]==['A']*3+['B']*3


def test_passed_late_rows_dedup_zero_weight_corner_and_seed_isolation():
    observer=synthetic_observer();row=observer.prepared[0]
    observer.prepared=[row,row,row];seed=[dict(actor='A',node=1,key_index=1,component=3,step=1)]
    before=copy.deepcopy(seed);options,failures=searcher.plan(observer,[1e-8,-1.,2e-8],seed)
    assert [f['row'] for f in failures]==[2,0] and seed==before
    assert len(options)==96
    selected=[r['step'] for r in options if (r['actor'],r['node'],r['key_index'],r['component'])==('A',1,1,3)]
    assert selected==[0,-1] and {r['node'] for r in options}=={0,1,2}
    with pytest.raises(ValueError,match='no subset'):searcher.plan(observer,[1e-8,-1.,2e-8],seed,maximum_options=95)


def test_float32_near_key_is_not_a_float64_exact_witness_time():
    observer=synthetic_observer(.3375)
    for actor in observer.problem.edits.actors.values():
        for track in actor['tracks']:
            track['clock']=np.array([1/3,.3375,.3416666666666667,1.],np.float32)
    # Native storage rounds this authored Float64 time upward. Sampling needs
    # both surrounding stored keys, even when weak scalar promotion says equal.
    stored=float(np.float32(.3375));assert stored>.3375
    options,_=searcher.plan(observer,[1e-8],[])
    assert {r['key_index'] for r in options}=={0,1} and len(options)==96
    observer.problem.times[0]=stored
    options,_=searcher.plan(observer,[1e-8],[])
    assert {r['key_index'] for r in options}=={1} and len(options)==48


@pytest.mark.parametrize('fault',['cycle','invalid-parent','negative-weight','nonfinite-weight','invalid-node','unsorted-clock','empty-clock','duplicate-choice','bad-step'])
def test_bad_source_population_or_absolute_seed_rejects(fault):
    observer=synthetic_observer();actor=observer.problem.scene.actors['A'];seed=[]
    if fault=='cycle':actor['rig'].parents[0]=1
    elif fault=='invalid-parent':actor['rig'].parents[0]=-2
    elif fault=='negative-weight':actor['skin'].weights[0,0]=-.1
    elif fault=='nonfinite-weight':actor['skin'].weights[0,0]=np.nan
    elif fault=='invalid-node':actor['skin'].nodes[0,0]=5
    elif fault=='unsorted-clock':observer.problem.edits.actors['A']['tracks'][0]['clock']=np.array([0.,.5,.3])
    elif fault=='empty-clock':observer.problem.edits.actors['A']['tracks'][0]['clock']=np.array([])
    else:
        row=dict(actor='A',node=1,key_index=1,component=3,step=1)
        seed=[row,row.copy()] if fault=='duplicate-choice' else [dict(row,step=True)]
    with pytest.raises(ValueError):searcher.plan(observer,[1e-8],seed)


def test_original_containment_and_triangle_ceilings_every_row_strict():
    witnesses=[dict(descriptor_index=0,kind='penetrating-vertex'),dict(descriptor_index=1,kind='triangle-separation')]
    out=searcher.excess([-.004680465,.0001-.010291],[.0001,.0001],witnesses,.004680442,.010290916)
    np.testing.assert_allclose(out,[23e-9,84e-9],atol=2e-18,rtol=0)
    assert np.all(searcher.excess([-.004,.0001-.01],[.0001,.0001],witnesses,.004,.01)<=0)
    for changed in ([dict(witnesses[0],descriptor_index=True),witnesses[1]],[witnesses[0],dict(witnesses[1],kind='component-pair')]):
        with pytest.raises(ValueError):searcher.excess([0.,0.],[.0001,.0001],changed,.004,.01)


def selector(monkeypatch,materials,native=None,extra=None,budget=4):
    observer=synthetic_observer();p=observer.problem;p.size=1;p.lower=np.array([-1.]);p.upper=np.array([1.])
    p.edits.controls=lambda v:np.asarray(v,float);native=native or [-1.]*len(materials)
    p.constraints=lambda v,w:np.array([w['A'][0,0,0,1]])
    def norm_rows(p,v,w=None):
        r=np.array([-1.]) if w is None else p.constraints(v,w)
        return NS(caps=np.ones(1),scales=np.ones(1),residual=lambda:r)
    monkeypatch.setattr(searcher,'rows',norm_rows)
    monkeypatch.setattr(searcher,'StorageAdjustedEdits',lambda *a:NS(actors=['A'],values=lambda *a:None))
    observer.observe=lambda w:(np.zeros(12),np.array([-w['A'][0,0,0,0]]))
    choices=[dict(actor='A',node=1,key_index=i,component=0,step=1) for i in range(len(materials)-1)]
    monkeypatch.setattr(searcher,'plan',lambda *a:(copy.deepcopy(choices),[dict(row=0)]))
    seen=[];gates=[];extra=extra or [True]*len(materials)
    def decode(corrections,label):
        i=0 if label=='start' else corrections[-1]['key_index']+1
        worlds={n:np.zeros((1,5,4,4)) for n in ('A','B')}
        worlds['A'][0,0,0,0]=materials[i];worlds['A'][0,0,0,1]=native[i];seen.append(i)
        return p.constraints(None,worlds),worlds
    def gate(v,w,label):
        i=0 if label=='start' else int(label.split('-')[-1])+1;gates.append(i);return extra[i]
    result=searcher.search(p,[0.],{},[],observer,[dict(descriptor_index=0,kind='penetrating-vertex')],0.,0.,decode,gate,stages=1,probes_per_stage=budget)
    return result,seen,gates


@pytest.mark.parametrize('materials,native,extra,chosen',[
    ([90e-9,10e-9,20e-9,30e-9],None,None,0),
    ([90e-9,10e-9,10e-9,30e-9],None,None,0),
    ([90e-9,0.,20e-9,30e-9],[-1.,1e-15,-1.,-1.],None,1),
    ([90e-9,0.,20e-9,30e-9],None,[True,False,True,True],1),
    ([90e-9,100e-9,90e-9,110e-9],None,None,None),
])
def test_strict_best_material_improvement_keeps_native_extra_gates_and_stable_ties(monkeypatch,materials,native,extra,chosen):
    (corrections,report),seen,gates=selector(monkeypatch,materials,native,extra)
    assert seen==gates==[0,1,2,3] and report['tested_neighbors']==3
    assert (corrections[-1]['key_index'] if corrections else None)==chosen
    assert len(report['history'][0]['complete_options'])==3 and not report['material_conditions_pass']
    assert not report['geometry_assessed'] and not report['release_approved']


def test_declared_prefix_and_early_exit_only_on_all_gates(monkeypatch):
    (corrections,report),seen,gates=selector(monkeypatch,[90e-9,80e-9,70e-9,0.],budget=2)
    assert seen==gates==[0,1,2] and corrections[-1]['key_index']==1 and not report['material_conditions_pass']
    (corrections,report),seen,gates=selector(monkeypatch,[90e-9,80e-9,0.,-1e-8])
    assert seen==gates==[0,1,2] and report['material_conditions_pass']
    (_,report),seen,gates=selector(monkeypatch,[-1e-8,0.])
    assert seen==gates==[0] and report['history']==[]


@pytest.mark.parametrize('fault',['starting-native','starting-extra','nonboolean-extra'])
def test_invalid_start_and_nonboolean_gates_reject(monkeypatch,fault):
    with pytest.raises(ValueError):
        selector(monkeypatch,[1e-8,0.],native=[1.,-1.] if fault=='starting-native' else None,
                 extra=[False,True] if fault=='starting-extra' else [1,True] if fault=='nonboolean-extra' else None)


@pytest.mark.parametrize('kwargs',[dict(stages=True),dict(stages=0),dict(stages=9),dict(probes_per_stage=True),dict(probes_per_stage=0),dict(probes_per_stage=65)])
def test_bad_budgets_reject_before_decode(kwargs):
    with pytest.raises(ValueError):searcher.search(None,None,None,None,None,None,None,None,None,None,**kwargs)


def test_undeclared_centered_editing_permission_rejects_before_export(tmp_path):
    problem,x,decoded,_=setup(tmp_path);observer=MaterialWitnessGuides(problem,descriptors())
    policy=dict(schema='strep-native-rotation-storage-repair-v1',authoring_sha256='unused',
                maximum_component_steps=1,maximum_corrections=64,acknowledge_storage_adjustment=True)
    with pytest.raises(ValueError,match='boundary authoring'):
        searcher.search(problem,x,policy,[],observer,[dict(descriptor_index=i,kind='triangle-separation') for i in range(2)],0.,1.,
                        lambda *a:pytest.fail('unapproved export'),lambda *a:True)


@pytest.mark.parametrize('fault',[None,'missing-actor','missing-time','nonfinite-world','false-residual','changed-cap','extra-gate'])
def test_complete_real_stored_glb_native_and_material_checks(tmp_path,fault):
    from test_native_stored_pair_model import fixture
    from native_rotation_storage_repair import authoring_digest
    from native_scene_norms import rows
    from native_scene_boundary_edit import BoundarySceneEdits
    from native_scene_contacts import SceneContacts
    from native_scene_fit import SceneProblem
    from strep import save,sha256
    original,_,_,spec,_,_=fixture(tmp_path)
    spec['contacts'][0].update(mode='touch',interval_s=[1.,1.],limits=dict(position_m=1e-6),
        target=dict(space='world',points_m=original.scene.actor_points('A',original.scene.rows[0]['ids'],np.array([1.]))[0].tolist()))
    path=tmp_path/'checked-contacts.json';save(path,spec);request=copy.deepcopy(original.edits.base.request)
    request['permissions']['contacts_sha256']=sha256(path)
    scene=SceneContacts(spec,tmp_path);base=BoundarySceneEdits(request,scene,sha256(path),rotation_storage_policy='source-scale')
    problem=SceneProblem(scene,base)
    x=problem.initial.copy();observer=MaterialWitnessGuides(problem,descriptors());seen=[]
    policy=dict(schema='strep-native-rotation-storage-repair-v1',authoring_sha256=authoring_digest(problem.edits),
                maximum_component_steps=1,maximum_corrections=64,acknowledge_storage_adjustment=True)
    witnesses=[dict(descriptor_index=i,kind='triangle-separation') for i in range(2)]
    def decode(choices,label):
        path=tmp_path/(label+'-checked.glb');editor=StorageAdjustedEdits(problem.edits,policy,choices)
        editor.export('A',x,path);assert editor.audit('A',path,0,value=x)['passed'];seen.append(label)
        residual,worlds=problem.decoded({'A':path},x)
        if fault=='missing-actor':worlds.pop('B')
        elif fault=='missing-time':worlds['B']=worlds['B'][:-1]
        elif fault=='nonfinite-world':worlds['B'][0,0,0,0]=np.nan
        elif fault=='false-residual':residual=np.zeros_like(residual)
        elif fault=='changed-cap':problem.caps['A'].caps[0]+=1;residual=problem.constraints(x,worlds)
        return residual,worlds
    if fault:
        with pytest.raises(ValueError):searcher.search(problem,x,policy,[],observer,witnesses,0.,1.,decode,lambda *a:fault!='extra-gate')
    else:
        choices,report=searcher.search(problem,x,policy,[],observer,witnesses,0.,1.,decode,lambda *a:True)
        assert choices==[] and seen==['start'] and report['material_conditions_pass'] and report['tested_neighbors']==0
        assert report['records'][0]['native_conditions_pass'] and report['records'][0]['complete_extra_gates_pass']
        assert len(rows(problem,x).caps)>100 and len(observer.prepared)==2
