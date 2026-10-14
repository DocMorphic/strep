"""Local rankings never replace complete decoded motion or authoring gates."""
import copy,sys
from pathlib import Path
import numpy as np,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_translation_stencil_search as stencil
from native_component_storage_repair import ComponentAdjustedEdits
from native_scene_fit import SceneProblem
from test_native_component_storage import fixture


def bundle(keys=(4,5,6),step=1):
    return dict(choices=[dict(actor='A',node=0,path='translation',key_index=key,component=c,step=step) for key in keys for c in range(3)])


@pytest.mark.parametrize('keys',[(5,),(4,5),(4,5,6)])
def test_absolute_all_axis_restore_is_atomic_and_detached(keys):
    seed=bundle(keys)['choices'];saved=copy.deepcopy(seed)
    assert stencil.apply_stencil(seed,bundle(keys,step=0))==[] and seed==saved
    result=stencil.apply_stencil(seed,bundle(keys,step=-1))
    assert all(r['step']==-1 for r in result) and seed==saved


@pytest.mark.parametrize('fault',['duplicate','gap','actor','node','rotation','component','step-bool','missing-axis','extra'])
def test_incomplete_cross_track_or_nonlocal_bundle_rejects(fault):
    value=bundle()
    if fault=='duplicate':value['choices'][-1]=copy.deepcopy(value['choices'][0])
    elif fault=='gap':
        for r in value['choices'][-3:]:r['key_index']=7
    elif fault=='actor':value['choices'][0]['actor']='B'
    elif fault=='node':value['choices'][0]['node']=1
    elif fault=='rotation':
        for r in value['choices']:r['path']='rotation'
    elif fault=='component':value['choices'][0]['component']=3
    elif fault=='step-bool':value['choices'][0]['step']=True
    elif fault=='missing-axis':value['choices'].pop()
    else:value['unused']=1
    with pytest.raises(ValueError):stencil.apply_stencil([],value)


def test_complete_decode_repairs_real_stored_root_jitter_without_rebasing(tmp_path):
    base,policy,row,*_=fixture(tmp_path);problem=SceneProblem(base.scene,base);value=base.initial.copy()
    caps=[c.copy() for c in problem.caps['A'].caps];before=value.copy();observed=[]
    def decode(corrections,label):
        edits=ComponentAdjustedEdits(base,policy,corrections);path=tmp_path/(label+'.glb');edits.export('A',value,path)
        assert edits.audit('A',path,0,value=value)['passed']
        residual,worlds=problem.decoded({'A':path},value);observed.append((label,copy.deepcopy(corrections),residual.copy()))
        return residual,worlds
    result,report=stencil.search(problem,value,policy,[row],decode,stages=1,probes_per_stage=4)
    assert report['schema']=='strep-native-translation-stencil-search-v1'
    assert np.any(observed[0][2]>0) and report['native_conditions_pass']
    assert np.all(observed[-1][2]<=0) and len(observed)==len(report['records'])
    assert report['continuous_controls_unchanged'] and report['original_native_caps_scales_unchanged']
    assert not report['geometry_assessed'] and not report['quality_approved'] and not report['release_approved']
    target=[r for r in report['history'][0]['original_rate_failures'] if 'translation_stencil' in r]
    assert len(target)==1 and target[0]['translation_stencil']['proposal_only']
    assert target[0]['translation_stencil']['complete_population']==report['history'][0]['planned_options']
    np.testing.assert_array_equal(value,before)
    for actual,expected in zip(problem.caps['A'].caps,caps):np.testing.assert_array_equal(actual,expected)
    for key,original in base.values('A',value,quantized=False).items():
        np.testing.assert_array_equal(ComponentAdjustedEdits(base,policy,result).values('A',value,quantized=False)[key],original)


def test_forged_complete_decoded_observations_reject(tmp_path):
    base,policy,row,*_=fixture(tmp_path);problem=SceneProblem(base.scene,base)
    def forged(corrections,label):
        editor=ComponentAdjustedEdits(base,policy,corrections);path=tmp_path/(label+'.glb');editor.export('A',base.initial,path)
        residual,worlds=problem.decoded({'A':path},base.initial);return np.minimum(residual,0),worlds
    with pytest.raises(ValueError,match='residual differs'):
        stencil.search(problem,base.initial,policy,[row],forged,stages=1,probes_per_stage=1)


def test_original_correction_envelope_still_rejects_large_bundle(tmp_path):
    base,policy,row,*_=fixture(tmp_path);policy['maximum_corrections']=2
    corrected=stencil.apply_stencil([],bundle((5,)))
    with pytest.raises(ValueError,match='Bounded'):ComponentAdjustedEdits(base,policy,corrected)


def test_other_rate_families_and_disallowed_translations_remain_unsolved(monkeypatch):
    failures=[dict(actor='A',node=0,metric=3,frame=1,excess=.01)]
    monkeypatch.setattr(stencil,'single_plan',lambda *a,**kw:([],copy.deepcopy(failures)))
    assert stencil.plan(None,None,[],None,None)==([],failures)
    assert stencil.plan(None,None,[],None,None,allowed_paths=('rotation',))==([],failures)
