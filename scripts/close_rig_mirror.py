"""Record the completed mirror study and shipped Studio work, without release promotion."""
import copy
import difflib
from pathlib import Path
import psutil
from strep import ROOT,read,save,sha256,now


def run():
    dest=ROOT/'reports/bounded-path-runtime-v71.json'
    if dest.exists():raise ValueError('Preserve runtime history')
    study=ROOT/'reports/rig-mirror-v3';proof=ROOT/'reports/rig-mirror-studio-v1'
    assert read(study/'pipeline.json')['status']=='complete'
    assert read(proof/'verification.json')['passed']
    assert '22 passed' in (proof/'tests.txt').read_text()
    protocol=read(study/'protocol.json');changes={}
    for name,digest in protocol['implementation'].items():
        assert sha256(study/'implementation'/name)==digest
        if sha256(ROOT/'scripts'/name)!=digest:
            changes[name]=dict(snapshot_sha256=digest,current_sha256=sha256(ROOT/'scripts'/name),
                diff=''.join(difflib.unified_diff((study/'implementation'/name).read_text().splitlines(True),(ROOT/'scripts'/name).read_text().splitlines(True))))
    save(proof/'study-source-diff.json',dict(changes=changes,note='Core validation extracted for Studio API after completed study; UI-created wave, original comparison, ZIP and actual engine import verified on shipped code. Earlier immutable study snapshot retained.'))
    paths=['docs/rig-mirror-v1.md','reports/rig-mirror-v3/protocol.json','reports/rig-mirror-v3/summary.json',
        'reports/rig-mirror-v3/engine/verification.json','reports/rig-mirror-studio-v1/verification.json',
        'reports/rig-mirror-studio-v1/tests.txt','reports/rig-mirror-studio-v1/study-source-diff.json']
    matrix=read(ROOT/'benchmarks/project-release-v1.json')
    for cap in matrix['capabilities']:
        if cap['id'] in ('rough_clip_editing','style_and_capability_controls','root_contact_event_export','game_engine_import','reproducible_failure_reporting'):
            for path in paths:
                if path not in cap['development_evidence']:cap['development_evidence'].append(path)
        assert not cap['release_evidence']
    matrix.update(last_progress_at=now(),last_progress='Explicit whole-clip mirror editing shipped in Studio. Nine multi-action/three-rig exports plus UI-created wave verified;1,770 actual Godot actor-frames. Contact/scene intent requires review and source floor defects remain. No human or release promotion.')
    save(ROOT/'benchmarks/project-release-v1.json',matrix)
    previous=ROOT/'reports/bounded-path-runtime-v70.json';state=copy.deepcopy(read(previous));studio=read(proof/'main-server.json')
    for item in [studio,*studio['children']]:
        p=psutil.Process(item['pid']);assert abs(p.create_time()-item['created'])<.001
    studio['identity_checked_at']=now()
    from action_worker_lock import worker_busy
    assert not worker_busy()
    state.update(at=now(),prior_runtime=str(previous.relative_to(ROOT)),prior_runtime_sha256=sha256(previous),studio=studio,
        available_memory_gib=psutil.virtual_memory().available/2**30,
        mirror_edit=dict(evidence={p:sha256(ROOT/p) for p in paths},study=dict(exec_session=99450,terminal_exit_code=0,terminal_handle_consumed=True,cases=9,frames=1530,midpoint_and_key_samples=3051),
            ui_job=read(proof/'job-identity.json')['id'],ui_engine_actor_frames=240,test_session=dict(exec_session=18143,terminal_exit_code=0,terminal_handle_consumed=True),
            initial_failed_test_session=dict(exec_session=75891,terminal_exit_code=1,terminal_handle_consumed=True,reason='Mock recipe missing label; fixture repaired;22 final tests pass'),
            failed_attempts=['reports/rig-mirror-v1','reports/rig-mirror-v2'],temporary_server_stopped=read(proof/'temporary-server-stopped.json')),
        scope='All studies terminal; no inference/training or human ratings. Main Studio restarted with mirror API and static editor; temporary8774 server stopped. Broad project goal active; no release approval.')
    save(dest,state)
    print(dict(runtime=str(dest),goal='active',studio_pid=studio['pid'],engine_actor_frames=1770,human_reviews=0))


if __name__=='__main__':run()
