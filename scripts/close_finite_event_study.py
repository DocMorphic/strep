"""Preserve actual finite export and update development-only project evidence."""
from pathlib import Path
import copy
import json
import shutil
import zipfile
import psutil
from strep import ROOT,read,save,sha256,now


def run():
    output=ROOT/'reports/godot-finite-package-v2';output.mkdir(exist_ok=False)
    source=Path('C:/Users/daved/AppData/Local/Temp/pytest-of-daved/pytest-194/test_studio_event_edit_exports0/finite/character-animation.zip')
    target=output/'character-animation.zip';shutil.copyfile(source,target)
    files={}
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name,path in [(n,ROOT/'scripts'/n) for n in ('godot_finite_adapter.gd','godot_cycle_adapter.gd','godot_event_object_body.gd')]+[(n,ROOT/'integrations/godot'/p) for n,p in [('GODOT-FINITE.md','FINITE.md'),('GODOT-OBJECT-EVENTS.md','OBJECT-EVENTS.md')]]:
            assert archive.read('transfer/'+name)==path.read_bytes();files[name]=sha256(path)
        metadata=json.loads(archive.read('transfer/runtime-finite.json'))
        assert metadata['markers'][0]['phase_frame']==metadata['frames']-1
    save(output/'verification.json',dict(at=now(),passed=True,package_sha256=sha256(target),embedded=files,tests=dict(command='python -m pytest tests/test_runtime_finite.py tests/test_runtime_cycle.py -q',passed=13,seconds=7.75,terminal_exit_code=0,returned_in_initial_exec=True),scope='Real finite Studio event edit and opt-in runtime export. Legacy corrected source hash/timing and tamper rejection also tested. No automatic prop bindings or motion approval.'))
    evidence=['docs/godot-finite-events-v1.md','reports/godot-finite-events-v4/verification.json','reports/godot-event-object-small-angle-v1/verification.json','reports/godot-finite-package-v2/verification.json']
    matrix=read(ROOT/'benchmarks/project-release-v1.json')
    for capability in matrix['capabilities']:
        if capability['id'] in ('game_engine_import','root_contact_event_export','object_scene_interactions'):
            for item in evidence:
                if item not in capability['development_evidence']: capability['development_evidence'].append(item)
        assert not capability['release_evidence']
    matrix.update(last_progress_at=now(),last_progress='Finite sampled runtime and actual prop physics: eight scenarios/three rigs/both root modes, terminal release and continuing physics pass. Real small-angle release spin bug fixed and cycle regression passed. Thirteen export tests pass, including legacy corrected-source provenance. No human or release gate promotion.')
    save(ROOT/'benchmarks/project-release-v1.json',matrix)
    previous=ROOT/'reports/bounded-path-runtime-v66.json';runtime=copy.deepcopy(read(previous))
    runtime.update(at=now(),prior_runtime=str(previous.relative_to(ROOT)),prior_runtime_sha256=sha256(previous))
    worker=runtime['processes'][0];process=psutil.Process(worker['pid'])
    assert abs(process.create_time()-worker['created'])<.001
    protocol=read(ROOT/'reports/whole-support-breadth-v1/protocol.json')
    changed=[n for n,h in protocol['implementation'].items() if sha256(ROOT/'scripts'/n)!=h]
    assert not changed
    worker.update(identity_match=True,cpu_seconds=sum(process.cpu_times()[:2]),pipeline=read(ROOT/'reports/whole-support-breadth-v1/pipeline.json'),implementation_files_verified=len(protocol['implementation']),changed_current_sources=changed)
    for item in [runtime['studio'],*runtime['studio']['children']]:
        process=psutil.Process(item['pid']);assert abs(process.create_time()-item['created'])<.001
    runtime['studio']['identity_checked_at']=now()
    runtime['available_memory_gib']=psutil.virtual_memory().available/2**30
    runtime['finite_events']=dict(evidence={p:sha256(ROOT/p) for p in evidence},attempts=[dict(path='reports/godot-finite-events-v1',exec_session=48291,terminal_exit_code=1,terminal_handle_consumed=True),dict(path='reports/godot-finite-events-v2',exec_session=71887,terminal_exit_code=0,terminal_handle_consumed=True),dict(path='reports/godot-finite-events-v3',exec_session=34176,terminal_exit_code=1,terminal_handle_consumed=True),dict(path='reports/godot-finite-events-v4',exec_session=1938,terminal_exit_code=0,terminal_handle_consumed=True)],cycle_regression=dict(path='reports/godot-event-object-small-angle-v1',terminal_exit_code=0,returned_in_initial_exec=True))
    runtime['scope']='Whole-support worker live; 30 protected source hashes unchanged. Finite gameplay/export studies and tests finished, no new model inference/training or UI changes. Goal active; no release gates approved.'
    save(ROOT/'reports/bounded-path-runtime-v67.json',runtime)
    print(dict(package_passed=True,protected_files=len(protocol['implementation']),worker=worker['pipeline'],worker_cpu_seconds=worker['cpu_seconds'],studio_identity_verified=True))


if __name__=='__main__':run()
