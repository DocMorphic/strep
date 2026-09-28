"""One-use closeout of the complete support population and live extension."""
import copy
import psutil
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from compare_support_cleanup_extension import verified
from study_whole_support_breadth import validate


def run():
    output = ROOT/'reports/bounded-path-runtime-v69.json'
    if output.exists():
        raise ValueError('Preserve prior closeout')
    previous = ROOT/'reports/bounded-path-runtime-v68.json'
    state = copy.deepcopy(read(previous))
    study = ROOT/'reports/whole-support-breadth-v1'
    plan = validate(study)
    summary = read(ROOT/'reports/whole-support-breadth-final-v1/summary.json')
    assert summary['population'] == dict(planned=24, complete=24, failed=0, pending=0)
    assert not summary['partial']
    assert read(study/'completion.json')['results_sha256'] == sha256(study/'results.json')
    old = state['processes'][0]
    if psutil.pid_exists(old['pid']):
        assert abs(psutil.Process(old['pid']).create_time()-old['created']) >= .001
    old.update(identity_match=False, terminal_exit_code=0, terminal_handle_consumed=True,
        pipeline=read(study/'pipeline.json'), population_status=dict(complete=24),
        completion_sha256=sha256(study/'completion.json'), implementation_files_verified=len(plan['implementation']),
        changed_current_sources=[], source_change_note='Completed immutable population. Exec73214 terminal exit0 consumed.')
    root = ROOT/'reports/support-temporal-cleanup-v2'
    rp, rd = verified(root)
    assert all(r['status'] in ('candidate_preserved', 'input_retained') for r in rd['rows'])
    repeated = read(ROOT/'reports/support-temporal-extension-v1.json')
    assert repeated['all_repeated_selections_identical'] and repeated['repeated_cases'] == 19
    owner = read(root/'runner.json')
    state['processes'].append(dict(study=root.name, **owner, exec_session=85999,
        terminal_exit_code=0, terminal_handle_consumed=True, identity_match=False,
        pipeline=read(root/'pipeline.json'), completion_sha256=sha256(root/'completion.json'),
        implementation_files_verified=len(rp['implementation'])))
    running = ROOT/'reports/midpoint-support-boundaries-v2'
    cp, owner = read(running/'protocol.json'), read(running/'runner.json')
    assert sha256(running/'protocol.json') == read(running/'freeze.json')['protocol_sha256']
    check_files(ROOT/'scripts', cp['implementation']); check_files(running/'implementation', cp['implementation'])
    process = psutil.Process(owner['pid']); assert abs(process.create_time()-owner['created']) < .001
    state['processes'].append(dict(study=running.name, **owner, exec_session=4892,
        identity_match=True, cpu_seconds=sum(process.cpu_times()[:2]), pipeline=read(running/'pipeline.json'),
        planned=24, targeted=13, implementation_files_verified=len(cp['implementation']), changed_current_sources=[]))
    evidence = ['docs/whole-support-final-v1.md', 'reports/whole-support-breadth-final-v1/summary.json',
        'reports/whole-support-regressions-final-v1/summary.json', 'reports/support-temporal-cleanup-v2/completion.json',
        'reports/support-temporal-summary-v2/summary.json', 'reports/support-temporal-extension-v1.json']
    matrix = read(ROOT/'benchmarks/project-release-v1.json')
    for capability in matrix['capabilities']:
        if capability['id'] in ('target_rig_import_and_transfer', 'explicit_contact_authoring', 'reproducible_failure_reporting'):
            for path in evidence:
                if path not in capability['development_evidence']: capability['development_evidence'].append(path)
        assert not capability['release_evidence']
    matrix.update(last_progress_at=now(), last_progress='Full24 support population complete and verified; root cleanup retains18 improvements and6 inputs,8,640 engine actor-frames. Prior19 selections reproduce exactly. Full-population midpoint correction running; no quality/release promotion.')
    save(ROOT/'benchmarks/project-release-v1.json', matrix)
    for entry in [state['studio'], *state['studio']['children']]:
        process = psutil.Process(entry['pid']); assert abs(process.create_time()-entry['created']) < .001
    state['studio']['identity_checked_at'] = now()
    state.update(at=now(), prior_runtime=str(previous.relative_to(ROOT)), prior_runtime_sha256=sha256(previous),
        whole_support_summary='reports/whole-support-breadth-final-v1/summary.json',
        whole_support_final=dict(evidence={p:sha256(ROOT/p) for p in evidence}),
        available_memory_gib=psutil.virtual_memory().available/2**30,
        scope='Original whole worker and24-case root cleanup terminal,handles consumed. Full-population midpoint correction live. No UI/server restart, model inference/training, human scores or release approval.')
    save(output, state)
    print(dict(whole_support='24/24 complete', root_cleanup='18 candidates /6 inputs', midpoint_pid=owner['pid'],
        midpoint_cpu_seconds=state['processes'][-1]['cpu_seconds'], protected_files=len(cp['implementation'])))


if __name__ == '__main__': run()
