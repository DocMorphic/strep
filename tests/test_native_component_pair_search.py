"""Coordinated proposals preserve absolute neighbor/actor/key/storage contracts."""
import copy,sys
from pathlib import Path
import numpy as np,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_component_pair_search as pair
from native_component_storage_repair import ComponentAdjustedEdits
from native_scene_fit import SceneProblem
from test_native_component_storage import fixture


def choice(key=5,component=1,step=1,**updates):
    r=dict(actor='A',node=0,path='translation',key_index=key,component=component,step=step);r.update(updates);return r


def test_complete_pair_family_and_no_cancellation_or_cross_track():
    options=[choice(step=-1),choice(step=1),choice(component=2,step=-1),choice(component=2,step=1),choice(6),choice(6,step=-1),choice(node=2),choice(actor='B')]
    before=copy.deepcopy(options);bundles=pair.pair_options(options)
    assert len(bundles)==8 and options==before
    assert {tuple(tuple(r.values()) for r in b['choices']) for b in bundles}=={
        tuple(tuple(options[i].values()) for i in (a,b)) for a,b in ((0,2),(0,3),(1,2),(1,3),(0,4),(0,5),(1,4),(1,5))}
    assert bundles[0]['choices']==[options[0],options[2]] and bundles[1]['choices']==[options[0],options[4]]
    bundles[0]['choices'][0]['step']=0;assert options==before


def test_interleaving_retains_all_actor_track_groups():
    options=[choice(component=0),choice(component=1),choice(component=2),choice(actor='B',component=0),choice(actor='B',component=1)]
    b=pair.pair_options(options)
    assert [r['choices'][0]['actor'] for r in b]==['A','B','A','A'] and len(b)==4


@pytest.mark.parametrize('fault',['duplicate','step-bool','component-bool','path','translation-w','key-negative','extra','budget-small','budget-bool'])
def test_invalid_or_incomplete_population_rejects(fault):
    options=[choice(),choice(component=2)];budget=65536
    if fault=='duplicate':options.append(copy.deepcopy(options[0]))
    elif fault=='step-bool':options[0]['step']=True
    elif fault=='component-bool':options[0]['component']=True
    elif fault=='path':options[0]['path']='scale'
    elif fault=='translation-w':options[0]['component']=3
    elif fault=='key-negative':options[0]['key_index']=-1
    elif fault=='extra':options[0]['other']=1
    elif fault=='budget-small':options.append(choice(component=0));budget=1
    else:budget=True
    with pytest.raises(ValueError):pair.pair_options(options,maximum_candidates=budget)


@pytest.mark.parametrize('other',[choice(step=-1),choice(key=7),choice(node=1),choice(actor='B'),choice(path='rotation')])
def test_nonlocal_or_duplicate_pair_rejects(other):
    with pytest.raises(ValueError):pair.apply_pair([],dict(choices=[choice(),other]))


def test_absolute_restore_and_replace_are_detached():
    seed=[choice(),choice(key=6,step=-1)];before=copy.deepcopy(seed)
    result=pair.apply_pair(seed,dict(choices=[choice(step=0),choice(key=6,step=1)]))
    assert result==[choice(key=6,step=1)] and seed==before


def test_actual_export_changes_both_components_and_preserves_intended_motion(tmp_path):
    base,policy,row,*_=fixture(tmp_path);value=base.initial.copy()
    choices=[row,dict(row,component=2)];corrections=pair.apply_pair([],dict(choices=choices));edits=ComponentAdjustedEdits(base,policy,corrections)
    source=base.values('A',value);actual=edits.values('A',value);expected=source[0,'translation'].copy()
    for r in choices:
        k,c=r['key_index'],r['component'];expected[k,c]=np.nextafter(np.float32(expected[k,c]),np.float32(np.inf))
    for key,array in actual.items():np.testing.assert_array_equal(array,expected if key==(0,'translation') else source[key])
    for key,array in base.values('A',value,quantized=False).items():np.testing.assert_array_equal(edits.values('A',value,quantized=False)[key],array)
    path=tmp_path/'pair.glb';edits.export('A',value,path);assert edits.audit('A',path,0,value=value)['passed']
    problem=SceneProblem(base.scene,base);residual,worlds=problem.decoded({'A':path},value)
    assert np.isfinite(residual).all() and np.any(residual>0)  # Added raw-key jitter is not a motion pass.


def test_pair_over_capacity_rejects_before_export(tmp_path):
    base,policy,row,*_=fixture(tmp_path);policy['maximum_corrections']=1
    corrections=pair.apply_pair([],dict(choices=[row,dict(row,component=2)]))
    with pytest.raises(ValueError,match='Bounded'):ComponentAdjustedEdits(base,policy,corrections)


def test_search_archives_complete_original_conditions_and_rejects_forged_decode(tmp_path):
    base,policy,row,*_=fixture(tmp_path);problem=SceneProblem(base.scene,base);value=base.initial.copy();seen=[]
    def decode(corrections,label):
        seen.append((label,copy.deepcopy(corrections)));edits=ComponentAdjustedEdits(base,policy,corrections);path=tmp_path/(label+'.glb');edits.export('A',value,path)
        return problem.decoded({'A':path},value)
    result,report=pair.search(problem,value,policy,[row],decode,stages=1,probes_per_stage=4)
    assert report['schema']=='strep-native-component-pair-search-v1' and report['original_native_caps_scales_unchanged']
    assert report['continuous_controls_unchanged'] and report['geometry_assessed'] is False and seen[0][0]=='start'
    assert len(report['records'])==len(seen) and all(r['label']==s[0] and r['corrections']==s[1] for r,s in zip(report['records'],seen))
    def forged(corrections,label):
        edits=ComponentAdjustedEdits(base,policy,corrections);worlds=problem.worlds(value,quantized=True)
        return np.zeros_like(problem.constraints(value,worlds)),worlds
    with pytest.raises(ValueError,match='Reported residual'):pair.search(problem,value,policy,[row],forged,stages=1,probes_per_stage=1)
