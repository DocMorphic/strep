from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from angular_chain import correction_chain, completed_files, implementation_closure
from strep import read,save,sha256


def execute(tmp_path,states,*,blocks=2,fail_repair=False):
    calls=[];queue=iter(states)
    def inspect(source,audit):return next(queue)
    def repair(trial,source,audit,out):
        calls.append(trial)
        if fail_repair:raise ValueError('independent export audit rejected candidate')
    result=correction_chain(Path('original'),Path('original-audit'),tmp_path/'chain',blocks,inspect,repair,lambda:None)
    assert read(tmp_path/'chain/completion.json')==result
    return result,calls


def state(score):return dict(eligible=True,peaks_complete=score==0,excess_score=score)


def test_no_op_and_ineligible_never_launch_solver(tmp_path):
    for index,value in enumerate([state(0),dict(eligible=False,failed_checks=['contact_release'])]):
        result,calls=execute(tmp_path/str(index),[value])
        assert not calls and result['final_source']=='original'
        assert result['status']==('already_passed' if index==0 else 'ineligible')


def test_multiblock_chaining_only_uses_verified_candidates(tmp_path):
    result,calls=execute(tmp_path,[state(3),state(1),state(0)])
    assert result['status']=='numerical_pass' and len(calls)==2
    assert result['history'][1]['source']==str(calls[0])
    assert result['final_source']==str(calls[-1]) and not result['quality_approved']


@pytest.mark.parametrize('after,status',[(state(3),'no_progress'),(dict(eligible=False,failed_checks=['floor']),'preservation_failed')])
def test_rejected_candidate_cannot_replace_last_verified_source(tmp_path,after,status):
    result,calls=execute(tmp_path,[state(3),after])
    assert result['status']==status and len(calls)==1 and result['final_source']=='original'


def test_budget_exhaustion_retains_partial_result_without_success(tmp_path):
    result,calls=execute(tmp_path,[state(3),state(2),state(1)])
    assert result['status']=='budget_exhausted' and len(calls)==2
    assert result['final_source']==str(calls[-1])


def test_audit_exception_stops_and_retains_failure(tmp_path):
    result,calls=execute(tmp_path,[state(3)],fail_repair=True)
    assert result['status']=='failed' and result['final_source']=='original'
    assert result['history'][0]['status']=='failed' and 'audit rejected' in result['error']


def test_frozen_input_failure_is_fatal_not_a_case_success(tmp_path):
    def reject():raise ValueError('Frozen input changed')
    with pytest.raises(ValueError,match='Frozen input changed'):
        correction_chain(Path('s'),Path('a'),tmp_path/'chain',2,lambda *_:state(0),lambda *_:None,reject)


def test_changed_completed_output_is_rejected_even_with_unchanged_certificate(tmp_path):
    save(tmp_path/'request.json',dict(test=True));save(tmp_path/'pipeline.json',dict(status='complete'))
    (tmp_path/'motion.glb').write_bytes(b'original')
    save(tmp_path/'completion.json',dict(request_sha256=sha256(tmp_path/'request.json'),files={'motion.glb':sha256(tmp_path/'motion.glb')}))
    completed_files(tmp_path)
    (tmp_path/'motion.glb').write_bytes(b'changed')
    with pytest.raises(ValueError,match='artifact changed'):completed_files(tmp_path)


def test_dependency_snapshot_includes_engine_script_and_python_imports():
    files=implementation_closure({'godot_import_audit.gd','angular_source.py'})
    assert {'godot_import_audit.gd','angular_source.py','legacy_angular_source.py','strep.py'}<=set(files)
