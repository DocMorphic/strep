"""One-use closeout of the complete midpoint population and review UI."""
import copy
import psutil
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from compare_midpoint_support import verified


def run():
    dest=ROOT/'reports/bounded-path-runtime-v70.json'
    if dest.exists(): raise ValueError('Preserve completed closeout')
    study=ROOT/'reports/midpoint-support-boundaries-v2'
    protocol,complete=verified(study)
    assert len(complete['rows'])==24 and sum(r['status']=='candidate_preserved' for r in complete['rows'])==13
    assert complete['engine_actor_frames']==4800
    quarter=ROOT/'reports/midpoint-support-quarter-audit-v2'
    qc=read(quarter/'completion.json');check_files(quarter,qc['files'])
    assert sha256(quarter/'protocol.json')==qc['protocol_sha256']
    assert read(quarter/'protocol.json')['completion_sha256']==sha256(study/'completion.json')
    assert qc['evaluated_cases']==13 and qc['evaluated_times']==4774 and qc['cases_with_worsened_samples']==9
    package=ROOT/'reports/rig-jobs/midpoint-support-review-v2'
    pp=read(package/'package-verification.json');check_files(package,pp['files'])
    assert pp['cases']==24 and pp['variants']==72
    review=read(ROOT/'reports/midpoint-support-review-ui-v2/verification.json');assert review['passed']
    feedback=read(ROOT/'reports/developer-feedback-ui-v1/verification.json');assert feedback['passed'] and feedback['human_reviews_collected']==0
    previous=ROOT/'reports/bounded-path-runtime-v69.json';state=copy.deepcopy(read(previous))
    entry=next(p for p in state['processes'] if p['study']==study.name)
    if psutil.pid_exists(entry['pid']):assert abs(psutil.Process(entry['pid']).create_time()-entry['created'])>=.001
    entry.update(identity_match=False,terminal_exit_code=0,terminal_handle_consumed=True,
        pipeline=read(study/'pipeline.json'),completion_sha256=sha256(study/'completion.json'),
        implementation_files_verified=len(protocol['implementation']),changed_current_sources=[],
        source_change_note='Complete; immutable snapshots retained. Exec4892 consumed exit0.')
    check_files(ROOT/'scripts',protocol['implementation'])
    evidence=['docs/midpoint-support-final-v1.md','reports/midpoint-support-summary-v2/summary.json',
        'reports/midpoint-support-extension-v1.json','reports/midpoint-support-quarter-audit-v2/completion.json',
        'reports/rig-jobs/midpoint-support-review-v2/package-verification.json','reports/midpoint-support-review-ui-v2/verification.json',
        'docs/developer-feedback-v1.md','reports/developer-feedback-ui-v1/verification.json']
    matrix=read(ROOT/'benchmarks/project-release-v1.json')
    for capability in matrix['capabilities']:
        if capability['id'] in ('target_rig_import_and_transfer','explicit_contact_authoring','reproducible_failure_reporting'):
            for path in evidence:
                if path not in capability['development_evidence']:capability['development_evidence'].append(path)
        if capability['id']=='blind_review_and_cleanup_study':
            for path in evidence[-2:]:
                if path not in capability['development_evidence']:capability['development_evidence'].append(path)
        assert not capability['release_evidence']
    matrix.update(last_progress_at=now(),last_progress='Full24 review available with72 versions;13 leg/root numerical improvements,10 remaining foot-peak cases,9 quarter-time floor residuals.4,800 engine actor-frames pass. Local source-bound developer notes/export/import verified with synthetic data only. No release promotion.')
    save(ROOT/'benchmarks/project-release-v1.json',matrix)
    for item in [state['studio'],*state['studio']['children']]:
        process=psutil.Process(item['pid']);assert abs(process.create_time()-item['created'])<.001
    state['studio']['identity_checked_at']=now()
    state.update(at=now(),prior_runtime=str(previous.relative_to(ROOT)),prior_runtime_sha256=sha256(previous),
        available_memory_gib=psutil.virtual_memory().available/2**30,
        midpoint_full_population=dict(evidence={p:sha256(ROOT/p) for p in evidence},
            quarter_audit=dict(exec_session=96580,terminal_exit_code=0,terminal_handle_consumed=True),
            comparison=dict(exec_session=50081,terminal_exit_code=0,terminal_handle_consumed=True),
            review_package=dict(exec_session=66259,terminal_exit_code=0,terminal_handle_consumed=True)),
        scope='All study workers terminal; all current handles consumed. Studio unchanged process, updated static bundle. Full24 review and developer notes verified. No model inference/training, actual human feedback or release approval.')
    save(dest,state)
    print(dict(goal='active',study='complete',review_cases=24,variants=72,files=len(pp['files']),human_reviews=0,live_study_workers=0))


if __name__=='__main__':run()
