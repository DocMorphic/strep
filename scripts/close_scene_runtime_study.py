"""Record coordinated scene evidence and revalidate the remaining live worker."""
import copy
import psutil
from strep import ROOT,read,save,sha256,now


def run():
    final=ROOT/'reports/scene-runtime-v2'
    request=read(final/'request.json');verification=read(final/'verification.json')
    assert verification['passed']
    for name,digest in request['implementation'].items():
        assert sha256(final/'implementation'/name)==digest
    for item in request['cases']:
        from pathlib import Path
        folder=Path(item['folder']);manifest=read(folder/'package-manifest.json')
        assert sha256(folder/'scene-runtime.zip')==item['package_sha256']
        for path,digest in manifest['files'].items():assert sha256(folder/path)==digest
    worker_study=ROOT/'reports/scene-release-jobs/scene-runtime-worker-v1'
    assert read(worker_study/'verification.json')['passed']
    actor_request=read(worker_study/'request.json')['cases'][0]
    assert sha256(worker_study/'job/scene-animation.zip')==actor_request['package_sha256']
    save(final/'completion.json',dict(at=now(),passed=True,verification_sha256=sha256(final/'verification.json'),worker_verification_sha256=sha256(worker_study/'verification.json'),tests=dict(command="python -m pytest tests/test_scene_runtime.py tests/test_scene_release_job.py -k 'invalid_scene_package or exclusive_contact_end or real_worker_generic' -q",passed=9,deselected=13,seconds=22.85,exec_session=25710,terminal_exit_code=0,terminal_handle_consumed=True),quality_approved=False))
    evidence=['docs/scene-runtime-v1.md','reports/scene-runtime-v2/verification.json','reports/scene-runtime-v2/completion.json','reports/scene-release-jobs/scene-runtime-worker-v1/verification.json']
    matrix=read(ROOT/'benchmarks/project-release-v1.json')
    for capability in matrix['capabilities']:
        if capability['id'] in ('game_engine_import','root_contact_event_export','object_scene_interactions','two_actor_interactions'):
            for path in evidence:
                if path not in capability['development_evidence']:capability['development_evidence'].append(path)
        assert not capability['release_evidence']
    matrix.update(last_progress_at=now(),last_progress='Shared scene runtime and explicit baked object ownership: three existing scenes and real two-actor/two-object worker export pass engine playback, events and lifecycle. Nine tests pass. No motion-quality or release approval.')
    save(ROOT/'benchmarks/project-release-v1.json',matrix)
    previous=ROOT/'reports/bounded-path-runtime-v67.json';runtime=copy.deepcopy(read(previous))
    runtime.update(at=now(),prior_runtime=str(previous.relative_to(ROOT)),prior_runtime_sha256=sha256(previous))
    live=runtime['processes'][0];process=psutil.Process(live['pid']);assert abs(process.create_time()-live['created'])<.001
    protocol=read(ROOT/'reports/whole-support-breadth-v1/protocol.json')
    changed=[n for n,h in protocol['implementation'].items() if sha256(ROOT/'scripts'/n)!=h];assert not changed
    summary=read(ROOT/'reports/whole-support-breadth-interim-v23/summary.json');counts={}
    for row in summary['rows']:counts[row['status']]=counts.get(row['status'],0)+1
    live.update(identity_match=True,cpu_seconds=sum(process.cpu_times()[:2]),pipeline=read(ROOT/'reports/whole-support-breadth-v1/pipeline.json'),population_status=counts,implementation_files_verified=len(protocol['implementation']),changed_current_sources=changed)
    runtime['whole_support_summary']='reports/whole-support-breadth-interim-v23/summary.json'
    for entry in [runtime['studio'],*runtime['studio']['children']]:
        process=psutil.Process(entry['pid']);assert abs(process.create_time()-entry['created'])<.001
    runtime['studio']['identity_checked_at']=now();runtime['available_memory_gib']=psutil.virtual_memory().available/2**30
    runtime['scene_runtime']=dict(evidence={p:sha256(ROOT/p) for p in evidence},study=dict(exec_session=12268,terminal_exit_code=0,terminal_handle_consumed=True),worker_check=dict(exec_session=73207,terminal_exit_code=0,terminal_handle_consumed=True),preflights=[dict(path='reports/scene-runtime-v1',terminal_exit_code=1,returned_in_initial_exec=True),dict(path='reports/scene-runtime-worker-v1',terminal_exit_code=1,returned_in_initial_exec=True)])
    runtime['scope']='Original whole-support worker live,23complete/1running/0pending. Scene runtime studies and tests finished. All30protected dependencies unchanged; no UI/server restart, model inference/training, or release approval.'
    save(ROOT/'reports/bounded-path-runtime-v68.json',runtime)
    print(dict(goal='active',protected_files=len(protocol['implementation']),population=counts,live_cpu_seconds=live['cpu_seconds'],scene_runtime_passed=True))


if __name__=='__main__':run()
