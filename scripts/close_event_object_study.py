"""Record tested package bytes, protected-worker state and development evidence."""
from pathlib import Path
import copy
import shutil
import zipfile
import psutil
from strep import ROOT, read, save, sha256, now


def run():
    package_dir=ROOT/'reports/godot-event-object-package-v1';package_dir.mkdir(exist_ok=False)
    source=Path('C:/Users/daved/AppData/Local/Temp/pytest-of-daved/pytest-191/test_repeated_loop_accumulates0/loop/character-animation.zip')
    target=package_dir/'character-animation.zip';shutil.copyfile(source,target)
    checked={}
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name,path in [('godot_event_object_body.gd',ROOT/'scripts/godot_event_object_body.gd'),('GODOT-OBJECT-EVENTS.md',ROOT/'integrations/godot/OBJECT-EVENTS.md')]:
            assert archive.read('transfer/'+name)==path.read_bytes()
            checked[name]=sha256(path)
        import json
        metadata=json.loads(archive.read('transfer/runtime-cycle.json'))
        assert metadata['playback']['object_consumer']['bindings_automatic'] is False
    save(package_dir/'verification.json',dict(at=now(),passed=True,package_sha256=sha256(target),embedded=checked,tests=[dict(command='python -m pytest tests/test_runtime_cycle.py -q',passed=5,seconds=1.58),dict(command="python -m pytest tests/test_rig_loop.py -k 'repeated_loop and travel' -q",passed=1,deselected=7,seconds=18.31,exec_session=74347,terminal_exit_code=0,terminal_handle_consumed=True)],scope='Real new loop export contains opt-in consumer and instructions; no event bindings or motion approval inferred.'))
    evidence=['docs/godot-event-object-v1.md','reports/godot-event-object-v2/verification.json','reports/godot-event-object-missing-velocity-v1/verification.json','reports/godot-event-object-faults-v2/verification.json','reports/godot-event-object-package-v1/verification.json']
    matrix_path=ROOT/'benchmarks/project-release-v1.json';matrix=read(matrix_path)
    for capability in matrix['capabilities']:
        if capability['id'] in ('object_scene_interactions','root_contact_event_export','game_engine_import'):
            for path in evidence:
                if path not in capability['development_evidence']: capability['development_evidence'].append(path)
        assert not capability['release_evidence']
    matrix['last_progress_at']=now()
    matrix['last_progress']='Actual Godot prop consumer and portable export: four fixture attach/release, physics, replay and recorded preview checks; dropped-velocity control detected, three fault paths contained. Developer review pending. No release gate promoted.'
    save(matrix_path,matrix)
    previous=ROOT/'reports/bounded-path-runtime-v64.json';runtime=copy.deepcopy(read(previous))
    runtime.update(at=now(),prior_runtime=str(previous.relative_to(ROOT)),prior_runtime_sha256=sha256(previous))
    worker=runtime['processes'][0];proc=psutil.Process(worker['pid'])
    assert abs(proc.create_time()-worker['created'])<.001
    protocol=read(ROOT/'reports/whole-support-breadth-v1/protocol.json')
    changed=[name for name,digest in protocol['implementation'].items() if sha256(ROOT/'scripts'/name)!=digest]
    assert not changed
    summary=read(ROOT/'reports/whole-support-breadth-interim-v22/summary.json')
    counts={}
    for row in summary['rows']: counts[row['status']]=counts.get(row['status'],0)+1
    worker.update(identity_match=True,cpu_seconds=sum(proc.cpu_times()[:2]),pipeline=read(ROOT/'reports/whole-support-breadth-v1/pipeline.json'),population_status=counts,implementation_files_verified=len(protocol['implementation']),changed_current_sources=changed)
    runtime['available_memory_gib']=psutil.virtual_memory().available/2**30
    runtime['scope']='Whole-support worker live, 22 complete/1 running/1 pending. New prop engine studies and tests finished. No new model inference, training, release rating or UI change.'
    runtime['gameplay_event_studies']={path:sha256(ROOT/path) for path in evidence if path.endswith('.json')}
    runtime['gameplay_event_preflight']=dict(path='reports/godot-event-object-v1',exec_session=32612,terminal_exit_code=1,terminal_handle_consumed=True,retained=True)
    runtime['gameplay_event_positive']=dict(path='reports/godot-event-object-v2',terminal_exit_code=0,returned_in_initial_exec=True)
    runtime['gameplay_event_control']=dict(path='reports/godot-event-object-missing-velocity-v1',terminal_exit_code=0,returned_in_initial_exec=True)
    runtime['gameplay_fault_preflight']=dict(path='reports/godot-event-object-faults-v1',terminal_exit_code=1,returned_in_initial_exec=True,retained=True)
    runtime['gameplay_fault_final']=dict(path='reports/godot-event-object-faults-v2',terminal_exit_code=0,returned_in_initial_exec=True)
    runtime['whole_support_summary']='reports/whole-support-breadth-interim-v22/summary.json'
    for item in [runtime['studio'], *runtime['studio'].get('children',[])]:
        process=psutil.Process(item['pid'])
        if 'created' in item: assert abs(process.create_time()-item['created'])<.001
    runtime['studio']['identity_checked_at']=now()
    save(ROOT/'reports/bounded-path-runtime-v65.json',runtime)
    print(dict(package_passed=True,worker=worker['population_status'],cpu_seconds=worker['cpu_seconds'],protected_files=len(protocol['implementation']),goal='active',release_gates_promoted=0))


if __name__=='__main__':run()
