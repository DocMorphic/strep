"""Three-key/component changes remain atomic, bounded and fully decoded."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_component_triple_search as triple
from test_native_component_pair_search import choice
from test_native_component_storage import fixture
from native_component_storage_repair import ComponentAdjustedEdits
from native_scene_fit import SceneProblem


def test_complete_signed_populations_and_detached_options():
    options=[choice(key=k,component=c,step=s) for k in (5,6,7) for c in (0,1,2) for s in (-1,1)]
    before=copy.deepcopy(options);bundles=triple.triple_options(options)
    assert len(bundles)==48 and len({tuple(tuple(r.items()) for r in b['choices']) for b in bundles})==48
    for bundle in bundles:triple.apply_triple([],bundle)
    bundles[0]['choices'][0]['step']=0;assert options==before


def test_families_interleave_across_actors_without_crossing_them():
    options=[choice(actor=a,component=c) for a in ('A','B') for c in (0,1,2)]
    bundles=triple.triple_options(options);assert [b['choices'][0]['actor'] for b in bundles]==['A','B']
    assert all(len({r['actor'] for r in b['choices']})==1 for b in bundles)


def test_zero_absolute_choice_restores_without_accumulation():
    seed=[choice(key=k) for k in (5,6,7)];before=copy.deepcopy(seed)
    out=triple.apply_triple(seed,dict(choices=[choice(key=5,step=0),choice(key=6,step=-1),choice(key=7)]))
    assert out==[choice(key=6,step=-1),choice(key=7)] and seed==before


@pytest.mark.parametrize('fault',['duplicate','bool','path','component','key-gap','actor','node','two','four','extra'])
def test_invalid_triples_reject_without_mutating_seed(fault):
    rows=[choice(key=k) for k in (5,6,7)];seed=[choice(component=0)];before=copy.deepcopy(seed)
    if fault=='duplicate':rows[1]=copy.deepcopy(rows[0])
    elif fault=='bool':rows[0]['step']=True
    elif fault=='path':rows[0]['path']='scale'
    elif fault=='component':rows[0]['component']=3
    elif fault=='key-gap':rows[-1]['key_index']=8
    elif fault=='actor':rows[0]['actor']='B'
    elif fault=='node':rows[0]['node']=2
    elif fault=='two':rows.pop()
    elif fault=='four':rows.append(choice(key=8))
    else:rows[0]['other']=1
    with pytest.raises(ValueError):triple.apply_triple(seed,dict(choices=rows))
    assert seed==before


@pytest.mark.parametrize('budget',[True,0,65537,1])
def test_budget_rejects_whole_population_without_clipping(budget):
    options=[choice(key=k,component=c) for k in (5,6,7) for c in (0,1,2)]
    with pytest.raises(ValueError):triple.triple_options(options,maximum_candidates=budget)


def test_duplicate_absolute_options_reject():
    with pytest.raises(ValueError):triple.triple_options([choice(),choice()])


def test_real_export_changes_three_components_and_preserves_intended_curve(tmp_path):
    base,policy,row,*_=fixture(tmp_path);value=base.initial.copy();rows=[dict(row,component=c) for c in (0,1,2)]
    edits=ComponentAdjustedEdits(base,policy,triple.apply_triple([],dict(choices=rows)))
    original=base.values('A',value);changed=edits.values('A',value);expected=original[0,'translation'].copy()
    for r in rows:expected[r['key_index'],r['component']]=np.nextafter(np.float32(expected[r['key_index'],r['component']]),np.float32(np.inf))
    np.testing.assert_array_equal(changed[0,'translation'],expected)
    for key,array in base.values('A',value,quantized=False).items():np.testing.assert_array_equal(edits.values('A',value,quantized=False)[key],array)
    asset=tmp_path/'triple.glb';edits.export('A',value,asset);assert edits.audit('A',asset,0,value=value)['passed']
    residual,worlds=SceneProblem(base.scene,base).decoded({'A':asset},value);assert np.isfinite(residual).all() and len(worlds['A'])>0


def test_original_correction_count_still_limits_atomic_triples(tmp_path):
    base,policy,row,*_=fixture(tmp_path);policy['maximum_corrections']=2
    corrections=triple.apply_triple([],dict(choices=[dict(row,component=c) for c in (0,1,2)]))
    with pytest.raises(ValueError,match='Bounded'):ComponentAdjustedEdits(base,policy,corrections)


def test_complete_actual_decode_receipts_and_forged_rows_reject(tmp_path):
    base,policy,row,*_=fixture(tmp_path);problem=SceneProblem(base.scene,base);value=base.initial.copy();seen=[]
    def decode(corrections,label):
        seen.append((label,copy.deepcopy(corrections)));edits=ComponentAdjustedEdits(base,policy,corrections)
        asset=tmp_path/(label+'.glb');edits.export('A',value,asset);return problem.decoded({'A':asset},value)
    corrected,report=triple.search(problem,value,policy,[row],decode,stages=1,probes_per_stage=4)
    assert report['schema']=='strep-native-component-triple-search-v1' and report['original_native_caps_scales_unchanged']
    assert report['continuous_controls_unchanged'] and not report['geometry_assessed']
    assert [(r['label'],r['corrections']) for r in report['records']]==seen
    def forged(corrections,label):
        worlds=problem.worlds(value);return np.zeros_like(problem.constraints(value,worlds)),worlds
    with pytest.raises(ValueError,match='Reported residual'):triple.search(problem,value,policy,[row],forged,stages=1,probes_per_stage=1)
