"""Fixed-denominator replication across every diagnosed root-only conflict."""
import argparse
import ast
import os
import shutil
from pathlib import Path
import psutil
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from study_coupled_breadth_block import prepare as prepare_case
from study_coupled_breadth_conic import run as run_case


def selected_rows(diagnosis):
    rows = diagnosis['rows']
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Unique diagnosed cases required')
    if any(type(r.get('excluded_by_vertical_bound')) is not bool for r in rows):
        raise ValueError('Explicit bound outcome required for every case')
    selected = [r for r in rows if r['excluded_by_vertical_bound']]
    if not selected:
        raise ValueError('No diagnosed root-only conflicts')
    return selected


def snapshot(output):
    destination = output/'implementation'
    destination.mkdir()
    seen, pending = set(), [Path(__file__).name]
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        path = ROOT/'scripts'/name
        shutil.copyfile(path, destination/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            for module in modules:
                child = (module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).is_file():
                    pending.append(child)
    return {name: sha256(destination/name) for name in sorted(seen)}


def verify_completion(folder):
    done = read(folder/'completion.json')
    for field, name in [('request', 'request.json'), ('audit', 'audit.json'), ('engine', 'engine/verification.json')]:
        if done[field+'_sha256'] != sha256(folder/name):
            raise ValueError('Changed completed evidence: '+str(folder/name))
    audit = read(folder/'audit.json')
    if audit['candidate_sha256'] != sha256(folder/'take/candidate/character.glb'):
        raise ValueError('Changed completed candidate')
    if audit['source_sha256'] != sha256(folder/'source/candidate/character.glb'):
        raise ValueError('Changed completed source')
    return done


def prepare(template, output, previous=None):
    if output.exists():
        raise ValueError('Preserve previous population attempt')
    complete = verify_completion(template)
    if not complete['accepted']:
        raise ValueError('Audited useful pilot required before replication')
    old = read(template/'request.json')
    diagnosis = Path(old['diagnosis'])
    if sha256(diagnosis) != old['diagnosis_sha256']:
        raise ValueError('Diagnosis changed')
    previous_rows = {}
    if previous is not None:
        prior_done = read(previous/'completion.json')
        prior_request = read(previous/'request.json')
        if prior_done['request_sha256'] != sha256(previous/'request.json') or prior_done['results_sha256'] != sha256(previous/'results.json'):
            raise ValueError('Previous population changed')
        if prior_request['diagnosis_sha256'] != old['diagnosis_sha256'] or prior_done['failed']:
            raise ValueError('Complete matched previous population required')
        previous_rows = {r['id']: r for r in read(previous/'results.json')['rows']}
        if set(previous_rows) != {r['id'] for r in selected_rows(read(diagnosis))}:
            raise ValueError('Previous population denominator differs')
    cases = []
    for row in selected_rows(read(diagnosis)):
        source = ROOT/'reports/whole-support-breadth-v1/takes'/row['id']
        files = {name: sha256(source/name) for name in old['source_files']}
        if files['candidate/character.glb'] != row['source_sha256']:
            raise ValueError('Diagnosed source changed')
        reuse = row['id']==old['case']
        if reuse and files != old['source_files']:
            raise ValueError('Pilot reuse source differs')
        reuse_from = None
        prior = previous_rows.get(row['id'])
        if prior and prior['status']=='accepted':
            folder = Path(prior['folder'])
            done = verify_completion(folder)
            if not done['accepted'] or prior['completion_sha256'] != sha256(folder/'completion.json'):
                raise ValueError('Previous accepted candidate changed')
            if read(folder/'request.json')['source_files'] != files:
                raise ValueError('Previous accepted source differs')
            reuse_from = str(folder)
        cases.append(dict(id=row['id'], source=str(source), files=files, reuse_pilot=reuse, reuse_from=reuse_from))
    if sum(c['reuse_pilot'] for c in cases) != 1:
        raise ValueError('Pilot must appear once in the diagnosed population')
    output.mkdir(parents=True)
    request = dict(at=now(), template=str(template), template_completion_sha256=sha256(template/'completion.json'),
                   diagnosis=str(diagnosis), diagnosis_sha256=sha256(diagnosis), cases=cases,
                   resources=old['resources'], implementation=snapshot(output),
                   policy={name: old[name] for name in ['maxiter', 'trusts', 'fractions', 'method']},
                   scope='Every diagnosed root-only conflict, one five-frame peak block per case. Existing verified pilot reused once. No held-out or human approval.')
    if previous is not None:
        request.update(previous_population=str(previous), previous_completion_sha256=sha256(previous/'completion.json'),
                       scope='Same full diagnosed population; reuse independently accepted outputs and rerun only rejected cases from their original inputs. Direct physical anchor guard added; audit limits unchanged.')
    save(output/'request.json', request)
    save(output/'freeze.json', dict(request_sha256=sha256(output/'request.json')))
    save(output/'results.json', dict(rows=[dict(id=c['id'], status='pending') for c in cases], quality_approved=False))
    save(output/'pipeline.json', dict(status='prepared', at=now()))
    print('Prepared', len(cases), 'cases;', sum(bool(c['reuse_pilot'] or c['reuse_from']) for c in cases), 'verified outputs reused', flush=True)


def run(output):
    request = read(output/'request.json')
    if read(output/'freeze.json')['request_sha256'] != sha256(output/'request.json') or read(output/'pipeline.json')['status']!='prepared':
        raise ValueError('Fresh frozen population required')
    template = Path(request['template'])
    if sha256(template/'completion.json') != request['template_completion_sha256']:
        raise ValueError('Pilot completion changed')
    if sha256(Path(request['diagnosis'])) != request['diagnosis_sha256']:
        raise ValueError('Population diagnosis changed')
    if 'previous_population' in request and sha256(Path(request['previous_population'])/'completion.json') != request['previous_completion_sha256']:
        raise ValueError('Previous population completion changed')
    check_files(ROOT/'scripts', request['implementation'])
    check_files(output/'implementation', request['implementation'])
    check_files(Path('.'), request['resources'])
    save(output/'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
    results = read(output/'results.json')
    for case, row in zip(request['cases'], results['rows']):
        row['status'] = 'processing'
        save(output/'results.json', results)
        save(output/'pipeline.json', dict(status='processing', case=case['id'], at=now()))
        try:
            check_files(Path(case['source']), case['files'])
            reused = bool(case['reuse_pilot'] or case.get('reuse_from'))
            folder = Path(case['reuse_from']) if case.get('reuse_from') else template if case['reuse_pilot'] else output/'takes'/case['id']
            if not reused:
                folder.parent.mkdir(parents=True, exist_ok=True)
                prepare_case(Path(request['diagnosis']), folder, case_id=case['id'])
                child = read(folder/'request.json')
                if child['source_files'] != case['files']:
                    raise ValueError('Copied case differs from population freeze')
                child.update(request['policy'], parent=str(template), parent_completion_sha256=request['template_completion_sha256'],
                             resources=request['resources'], implementation=request['implementation'])
                for name in request['implementation']:
                    shutil.copyfile(output/'implementation'/name, folder/'implementation'/name)
                save(folder/'request.json', child)
                save(folder/'freeze.json', {n: sha256(folder/n) for n in ['request.json', 'envelope.json', 'preflight.json']})
                run_case(folder)
            done = verify_completion(folder)
            audit = read(folder/'audit.json')
            engine = read(folder/'engine/verification.json')
            row.update(status='accepted' if done['accepted'] else 'no_accepted_correction', reused=reused,
                       folder=str(folder), completion_sha256=sha256(folder/'completion.json'),
                       objective_before=audit['objective_before'], objective_after=audit['objective_after'],
                       root_peak_before_m_s2=audit['root_peak_before_m_s2'], root_peak_after_m_s2=audit['root_peak_after_m_s2'],
                       original_peak_m_s2=audit['original_peak_m_s2'], all_guards_passed=audit['all_guards_passed'],
                       remaining_root_failure_centers=audit['remaining_root_failure_centers'],
                       engine_actor_frames=sum(c['frames'] for c in engine['checks']))
        except Exception as exc:
            row.update(status='failed', error=str(exc))
        save(output/'results.json', results)
        print(case['id'], row['status'], flush=True)
    check_files(ROOT/'scripts', request['implementation'])
    check_files(Path('.'), request['resources'])
    if sha256(Path(request['diagnosis'])) != request['diagnosis_sha256']:
        raise ValueError('Population diagnosis changed during study')
    for case in request['cases']:
        check_files(Path(case['source']), case['files'])
    rows = results['rows']
    failed = sum(r['status']=='failed' for r in rows)
    save(output/'completion.json', dict(at=now(), request_sha256=sha256(output/'request.json'), results_sha256=sha256(output/'results.json'),
         planned=len(rows), accepted=sum(r['status']=='accepted' for r in rows), failed=failed,
         new_engine_actor_frames=sum(r.get('engine_actor_frames', 0) for r in rows if not r.get('reused', False)), quality_approved=False))
    save(output/'pipeline.json', dict(status='complete_with_failures' if failed else 'complete', at=now(), quality_approved=False))


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare', 'run'])
    parser.add_argument('output', type=Path)
    parser.add_argument('--template', type=Path)
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    if args.command=='prepare':
        prepare(args.template.resolve(), args.output.resolve(), args.previous.resolve() if args.previous else None)
    else:
        run(args.output.resolve())
