"""Archive/resource gates and actual-export eligibility before scientific work."""
import copy
from contextlib import contextmanager
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import sha256
import buffered_component_trial_preflight as gate
import run_buffered_component_trajectory_trial as runner


def write(path, value):
    path.write_text(json.dumps(value,allow_nan=False),encoding='utf-8')


def example(tmp_path):
    sources={}
    for role in gate.ROLES:
        folder=tmp_path/role;folder.mkdir();file=folder/'points.txt';file.write_text(role)
        report=dict(schema=gate.SCHEMAS[role],status='complete',original_selected=True,
            quality_approved=False,release_approved=False,inputs_sha256={})
        if role in ('model','trial','calibration'):
            report['files_sha256']={'points.txt':sha256(file)}
        else:
            flags=dict(model_reader=gate.MODEL_FLAGS,trial_reader=gate.TRIAL_FLAGS,
                calibration_reader=gate.CALIBRATION_FLAGS)[role]
            report.update({flag:True for flag in flags})
            report['producer_result_sha256']=sources[role.removesuffix('_reader')]['sha256']
        path=folder/'result.json';write(path,report)
        sources[role]=dict(path=str(path),sha256=sha256(path))
    request=tmp_path/'request.json';write(request,dict(schema='strep-buffered-component-trial-request-v1',sources=sources,output='new-trial'))
    return request


def disk(monkeypatch, free):
    monkeypatch.setattr(gate.shutil,'disk_usage',lambda path:SimpleNamespace(free=free))


def mutate(request,role,change):
    req=json.loads(request.read_text());path=Path(req['sources'][role]['path'])
    r=json.loads(path.read_text());change(r);write(path,r)
    req['sources'][role]['sha256']=sha256(path);write(request,req)


def passing_record():
    return dict(anchor_export_hashes_match=False,original_step_box_pass=True,native_conditions_pass=True,
        parameter_conditions_pass=True,actual_material_depth_ceiling_pass=True,
        actual_legacy_triangle_ceiling_pass=True,actual_integral_improved=True,reference_bounds=dict(passed=True),
        failed_native_rows=0,vector_norm_failures=0,failed_contact_rows=0,
        actual_guard_failures=0,actual_positive_component_failures=0,
        affine_empirical_material_conditions_pass=False)


def test_exact_storage_threshold_blocks_without_trial_creation_or_full_archive_work(tmp_path,monkeypatch):
    request=example(tmp_path);required=gate.DISK_RESERVE_BYTES+gate.ESTIMATED_OUTPUT_BYTES
    disk(monkeypatch,required)
    # A missing numerical member is deliberately untouched at the resource gate.
    (tmp_path/'model/points.txt').unlink()
    r=gate.preflight(request)
    assert r['status']=='blocked-insufficient-storage' and r['required_disk_free_bytes']==1755316224
    assert not r['scientific_work_started'] and not r['numerical_validation_complete'] and not r['output_created']
    assert not (tmp_path/'new-trial').exists()


def test_full_bound_population_verified_before_numerical_ready_state(tmp_path,monkeypatch):
    request=example(tmp_path);disk(monkeypatch,gate.DISK_RESERVE_BYTES+gate.ESTIMATED_OUTPUT_BYTES+1)
    r=gate.preflight(request)
    assert r['status']=='ready-for-numerical-validation' and r['bindings_checked']==10
    assert len(r['source_paths'])==6 and not r['numerical_validation_complete']
    assert not (tmp_path/'new-trial').exists() and not r['quality_approved'] and not r['release_approved']
    r['source_reports']['model'].clear()
    assert gate.preflight(request)['source_reports']['model']['status']=='complete'


@pytest.mark.parametrize('fault',['missing-role','extra-role','wrong-schema','bad-hash','missing-receipt',
    'changed-receipt','existing-output','missing-parent','source-output','same-receipt','partial',
    'approved','promoted','wrong-receipt-schema','wrong-producer','missing-reader-flag','numeric-reader-flag'])
def test_invalid_request_and_receipts_stop_even_with_low_disk(tmp_path,monkeypatch,fault):
    request=example(tmp_path);req=json.loads(request.read_text());disk(monkeypatch,0)
    if fault=='missing-role':req['sources'].pop('model')
    elif fault=='extra-role':req['sources']['other']=req['sources']['model']
    elif fault=='wrong-schema':req['schema']='other'
    elif fault=='bad-hash':req['sources']['model']['sha256']='a'
    elif fault=='missing-receipt':Path(req['sources']['model']['path']).unlink()
    elif fault=='changed-receipt':Path(req['sources']['model']['path']).write_text('{}')
    elif fault=='existing-output':(tmp_path/'new-trial').mkdir()
    elif fault=='missing-parent':req['output']='absent/new'
    elif fault=='source-output':req['output']='model'
    elif fault=='same-receipt':req['sources']['trial']=req['sources']['model']
    else:
        changes={
            'partial':('model',lambda r:r.update(status='processing')),
            'approved':('trial',lambda r:r.update(quality_approved=True)),
            'promoted':('model',lambda r:r.update(original_selected=False)),
            'wrong-receipt-schema':('model_reader',lambda r:r.update(schema='other')),
            'wrong-producer':('trial_reader',lambda r:r.update(producer_result_sha256='a'*64)),
            'missing-reader-flag':('calibration_reader',lambda r:r.pop(gate.CALIBRATION_FLAGS[-1])),
            'numeric-reader-flag':('model_reader',lambda r:r.update({gate.MODEL_FLAGS[0]:1}))}
        role,change=changes[fault];mutate(request,role,change)
        req=json.loads(request.read_text())
    write(request,req)
    with pytest.raises(ValueError):gate.preflight(request)


@pytest.mark.parametrize('fault',['missing-member','changed-member','escape-member','bad-input','missing-inputs'])
def test_every_archived_input_and_output_member_is_checked_before_ready(tmp_path,monkeypatch,fault):
    request=example(tmp_path);disk(monkeypatch,3<<30)
    if fault=='missing-member':(tmp_path/'model/points.txt').unlink()
    elif fault=='changed-member':(tmp_path/'trial/points.txt').write_text('changed')
    elif fault=='escape-member':
        outside=tmp_path/'outside.txt';outside.write_text('outside')
        mutate(request,'model',lambda r:r.update(files_sha256={'../outside.txt':sha256(outside)}))
        # Rebind the reader so containment, rather than producer mismatch, decides.
        h=json.loads(request.read_text())['sources']['model']['sha256']
        mutate(request,'model_reader',lambda r:r.update(producer_result_sha256=h))
    elif fault=='bad-input':mutate(request,'trial_reader',lambda r:r.update(inputs_sha256={str(tmp_path/'missing'):'a'*64}))
    elif fault=='missing-inputs':mutate(request,'model_reader',lambda r:r.pop('inputs_sha256'))
    with pytest.raises(ValueError):gate.preflight(request)


def test_complete_large_receipt_is_read_and_nonfinite_json_is_rejected():
    class SavedReceipt:
        def is_file(self):return True
        def stat(self):return SimpleNamespace(st_size=29_332_307)
        def open(self,**kwargs):return io.StringIO('{"complete":true}')
    assert gate._read(SavedReceipt())=={'complete':True}
    class BadReceipt(SavedReceipt):
        def open(self,**kwargs):return io.StringIO('{"x":NaN}')
    with pytest.raises(ValueError):gate._read(BadReceipt())
    class TooLarge(SavedReceipt):
        def stat(self):return SimpleNamespace(st_size=(64<<20)+1)
        def open(self,**kwargs):pytest.fail('Oversized receipt must reject whole')
    with pytest.raises(ValueError):gate._read(TooLarge())


def test_complete_receipt_population_budget_rejects_before_any_source_json_read(tmp_path,monkeypatch):
    request=example(tmp_path);monkeypatch.setattr(gate,'MAX_RECEIPT_POPULATION_BYTES',1)
    original=gate._read
    def read(path,*args,**kwargs):
        if path!=request:pytest.fail('Complete metadata budget must reject before source reads')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(gate,'_read',read)
    with pytest.raises(ValueError):gate.preflight(request)


def test_low_storage_cannot_enter_scientific_code(tmp_path,monkeypatch):
    request=example(tmp_path);disk(monkeypatch,0)
    monkeypatch.setattr(runner,'_execute',lambda r:pytest.fail('Scientific code must not run'))
    r=runner.run(request);assert r['status']=='blocked-insufficient-storage'


def test_second_preflight_inside_lock_catches_lost_storage_before_execution(monkeypatch):
    responses=iter([dict(status='ready-for-numerical-validation'),dict(status='blocked-insufficient-storage')])
    calls=[]
    monkeypatch.setattr(runner,'preflight',lambda r:next(responses))
    @contextmanager
    def lock():calls.append('acquire');yield;calls.append('release')
    monkeypatch.setattr(runner,'worker_lock',lock)
    monkeypatch.setattr(runner,'_execute',lambda r:pytest.fail('Storage lost before launch'))
    assert runner.run('request')['status']=='blocked-insufficient-storage' and calls==['acquire','release']


def test_second_authenticated_state_is_the_one_executed(monkeypatch):
    responses=iter([dict(status='ready-for-numerical-validation',identity='first'),
        dict(status='ready-for-numerical-validation',identity='second')])
    monkeypatch.setattr(runner,'preflight',lambda r:next(responses))
    @contextmanager
    def lock():yield
    monkeypatch.setattr(runner,'worker_lock',lock)
    monkeypatch.setattr(runner,'_execute',lambda r:r)
    assert runner.run('request')['identity']=='second'


def test_cli_saves_fresh_blocked_receipt_and_never_overwrites_it(tmp_path,monkeypatch):
    request=example(tmp_path);disk(monkeypatch,0);receipt=tmp_path/'receipt.json'
    assert runner.main(['--request',str(request),'--preflight-only','--receipt',str(receipt)])==2
    before=receipt.read_bytes();assert json.loads(before)['status']=='blocked-insufficient-storage'
    with pytest.raises(ValueError):runner.main(['--request',str(request),'--receipt',str(receipt)])
    assert receipt.read_bytes()==before and not (tmp_path/'new-trial').exists()


def test_optimized_python_cannot_launch_assertion_based_science():
    r=subprocess.run([sys.executable,'-O',str(Path(runner.__file__)),'--request','absent'],capture_output=True,text=True)
    assert r.returncode!=0 and 'Scientific assertions must be enabled' in r.stderr


def test_affine_empirical_margin_is_not_a_replacement_actual_acceptance_gate():
    r=passing_record();assert runner.eligible(r)
    r['affine_empirical_material_conditions_pass']=True;r['native_conditions_pass']=False
    assert not runner.eligible(r)


@pytest.mark.parametrize('fault',['anchor','box','native','parameter','depth','triangle','integral','reference',
    'scalar','vector','contact','mesh','positive','numeric-pass','bool-count'])
def test_each_actual_failure_independently_prevents_full_scene_entry(fault):
    r=passing_record()
    if fault=='anchor':r['anchor_export_hashes_match']=True
    elif fault=='reference':r['reference_bounds']['passed']=False
    elif fault=='numeric-pass':r['native_conditions_pass']=1
    elif fault=='bool-count':r['vector_norm_failures']=False
    else:
        key={'box':'original_step_box_pass','native':'native_conditions_pass','parameter':'parameter_conditions_pass',
            'depth':'actual_material_depth_ceiling_pass','triangle':'actual_legacy_triangle_ceiling_pass',
            'integral':'actual_integral_improved','scalar':'failed_native_rows','vector':'vector_norm_failures',
            'contact':'failed_contact_rows','mesh':'actual_guard_failures','positive':'actual_positive_component_failures'}[fault]
        r[key]=1 if fault in ('scalar','vector','contact','mesh','positive') else False
    r['affine_empirical_material_conditions_pass']=True
    assert not runner.eligible(r)
