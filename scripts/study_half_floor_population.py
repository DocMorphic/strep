"""Matched replication over all nine previously diagnosed correction conflicts."""
import argparse
import ast
import os
import shutil
from pathlib import Path
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from action_worker_lock import worker_lock
from study_coupled_clip_sequence import verify_sequence, fit_case, metrics
from study_coupled_breadth_block import make_problem
from coupled_half_floor import HalfFloorConstraints, half_floor_rows, half_floor_values


METHODS = ('keys_only', 'keys_and_halves')


def completed(folder):
    done = read(folder/'completion.json')
    for key in ('request', 'results'):
        if done[key+'_sha256'] != sha256(folder/(key+'.json')):
            raise ValueError('Changed completed population')
    if done['failed']:
        raise ValueError('Complete population without execution failures required')
    return done


def snapshot(folder):
    dest = folder/'implementation'
    dest.mkdir()
    seen, pending = set(), [Path(__file__).name]
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        path = ROOT/'scripts'/name
        shutil.copyfile(path, dest/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            for module in modules:
                child = (module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).is_file():
                    pending.append(child)
    return {name:sha256(dest/name) for name in sorted(seen)}


def preflight(folder, request):
    values = np.load(folder/'starting-parameters.npz')['parameters']
    with threadpool_limits(limits=1):
        p = make_problem(folder, {**request, 'frames':request['windows'][0]['frames']}, initial_parameters=values)
        x = values[np.ix_(p.frames,p.free)].ravel()
        _, j, model = half_floor_rows(p,x,False)
        rng = np.random.default_rng(954)
        errors = []
        for _ in range(3):
            d = rng.normal(size=len(x));d /= np.linalg.norm(d)
            finite = (half_floor_values(p,x+1e-6*d,False)-half_floor_values(p,x-1e-6*d,False))/2e-6
            errors.append(float(np.max(np.abs(finite-j@d))))
        record = dict(derivative_errors=errors, derivative_threshold=2e-4,
                      minimum_serialized_half_margin=float(half_floor_values(p,x).min()),
                      actual_geometry=p.geometric_guard(values), model=model)
    if max(errors)>2e-4 or record['minimum_serialized_half_margin'] < -1e-8 or not record['actual_geometry']:
        raise ValueError('Half-floor preflight failed')
    return record


def prepare(parent, pilot, output):
    if output.exists():
        raise ValueError('Preserve previous attempt')
    completed(parent);completed(pilot)
    prior = read(pilot/'request.json')
    if prior['parent_completion_sha256'] != sha256(parent/'completion.json'):
        raise ValueError('Pilot must have same parent')
    rows = read(parent/'results.json')['rows']
    if len(rows)!=9 or len({r['id'] for r in rows})!=9 or any(r['status']!='accepted' for r in rows):
        raise ValueError('All nine verified parent cases required')
    output.mkdir(parents=True)
    cases, preflights = [], {}
    for row in rows:
        source = Path(row['selected_folder'])
        if not verify_sequence(source)['accepted'] or sha256(source/'completion.json')!=row['completion_sha256']:
            raise ValueError('Changed accepted source')
        old = read(source/'request.json')
        reuse = source.resolve()==Path(prior['source']).resolve()
        for method in METHODS:
            folder = output/'takes'/row['id']/method
            folder.mkdir(parents=True)
            shutil.copytree(source/'source',folder/'source')
            shutil.copyfile(source/'parameters.npz',folder/'starting-parameters.npz')
            shutil.copyfile(source/'take/candidate/character.glb',folder/'starting.glb')
            spec = read(folder/'source/spec.json')
            acceleration,before = metrics(folder/'starting.glb',spec['frames'],spec['root_node'],old['target']['limit_m_s2'])
            envelope = read(source/'envelope.json')
            envelope['root_safety_caps_m_s2'] = np.minimum(envelope['root_safety_caps_m_s2'],acceleration+.0036).tolist()
            save(folder/'envelope.json',envelope)
            touched = sorted(set(old['frames'])|{f for w in old['windows'] for f in w['frames']})
            request = {**old,'frames':touched,'windows':[old['windows'][0]],'starting_metrics':before,
                       'maxiter':6,'method':method,'sample_clock':'float32','half_derivative_step':1e-5}
            save(folder/'request.json',request)
            files = {n:sha256(folder/n) for n in ['request.json','envelope.json','starting.glb','starting-parameters.npz']}
            record = dict(id=row['id']+'/'+method,case=row['id'],method=method,files=files,
                          source=str(source),source_completion_sha256=sha256(source/'completion.json'))
            if reuse:
                reused = pilot/'takes'/method
                verify_sequence(reused);check_files(reused,files)
                check_files(reused/'source',request['source_files'])
                record.update(reuse_folder=str(reused),reuse_completion_sha256=sha256(reused/'completion.json'))
            elif method=='keys_and_halves':
                preflights[row['id']] = preflight(folder,request)
            cases.append(record)
        print('Prepared',row['id'],'reused' if reuse else 'preflight passed',flush=True)
    if sum('reuse_folder' in c for c in cases)!=2:
        raise ValueError('Exactly one matched pilot pair must be reused')
    check_files(pilot,read(pilot/'freeze.json'))
    preflights['reused_pilot'] = dict(path=str(pilot/'preflight.json'),sha256=sha256(pilot/'preflight.json'))
    save(output/'preflights.json',preflights)
    save(output/'request.json',dict(at=now(),parent=str(parent),parent_completion_sha256=sha256(parent/'completion.json'),
        pilot=str(pilot),pilot_completion_sha256=sha256(pilot/'completion.json'),cases=cases,
        resources=read(parent/'request.json')['resources'],implementation=snapshot(output),
        scope='All nine original root-only conflicts, five action types and three rigs; one original peak window each from latest verified clips, paired key-only/half-floor methods, six iterations and unchanged budgets. Reuse existing matched pilot. Development, not held-out or equal-runtime evidence.'))
    save(output/'freeze.json',{n:sha256(output/n) for n in ['request.json','preflights.json']})
    save(output/'results.json',dict(rows=[dict(id=c['id'],case=c['case'],method=c['method'],status='pending') for c in cases],quality_approved=False))
    save(output/'pipeline.json',dict(status='prepared',at=now()))


def pair_results(rows):
    if len(rows)!=18 or len({r['id'] for r in rows})!=18 or len({r['case'] for r in rows})!=9:
        raise ValueError('All eighteen unique results required')
    pairs = []
    for case in sorted({r['case'] for r in rows}):
        variants = [r for r in rows if r['case']==case]
        if len(variants)!=2 or {r['method'] for r in variants}!=set(METHODS):
            raise ValueError('Both matched methods required')
        by_method = {r['method']:r for r in variants}
        a,b = [by_method[m] for m in METHODS]
        pair = dict(case=case,status='execution_failed' if any(r['status']=='failed' for r in variants) else 'complete')
        if pair['status']=='complete':
            if any(r['status'] not in ('accepted','no_accepted_correction') for r in variants) or a['before']!=b['before']:
                raise ValueError('Completed matched starts required')
            pair.update(methods={r['method']:dict(status=r['status'],objective=r['after']['objective'],peak_m_s2=r['after']['peak_m_s2'],
                          failing_centers=r['after']['failing_centers'],accepted_steps=r['accepted_steps']) for r in variants},
                        half_minus_keys_objective=b['after']['objective']-a['after']['objective'],
                        both_preserved=all(r['all_guards_passed'] and r['preserve_starting_root'] for r in variants),
                        added_failures={r['method']:sorted(set(r['after']['failing_centers'])-set(r['before']['failing_centers'])) for r in variants})
        pairs.append(pair)
    return dict(pairs=pairs,quality_approved=False)


def run(output):
    request = read(output/'request.json')
    if read(output/'pipeline.json')['status']!='prepared':
        raise ValueError('Fresh prepared population required')
    check_files(output,read(output/'freeze.json'))
    for key in ('parent','pilot'):
        if sha256(Path(request[key])/'completion.json')!=request[key+'_completion_sha256']:
            raise ValueError('Changed frozen parent')
    check_files(ROOT/'scripts',request['implementation']);check_files(output/'implementation',request['implementation'])
    check_files(Path('.'),request['resources'])
    save(output/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
    results = read(output/'results.json')
    with worker_lock(),threadpool_limits(limits=1):
        for case,row in zip(request['cases'],results['rows']):
            folder = output/'takes'/case['id']
            save(output/'pipeline.json',dict(status='processing',case=case['id'],at=now()))
            row['status']='processing';save(output/'results.json',results)
            try:
                if sha256(Path(case['source'])/'completion.json')!=case['source_completion_sha256']:
                    raise ValueError('Changed source completion')
                check_files(folder,case['files']);child=read(folder/'request.json');check_files(folder/'source',child['source_files'])
                if case.get('reuse_folder'):
                    selected = Path(case['reuse_folder'])
                    done = verify_sequence(selected);check_files(selected,case['files']);check_files(selected/'source',child['source_files'])
                    if sha256(selected/'completion.json')!=case['reuse_completion_sha256']:
                        raise ValueError('Changed reused result')
                    comparison = read(selected/'comparison.json');blocks=read(selected/'blocks.json')
                    row.update(status='accepted' if done['accepted'] else 'no_accepted_correction',
                               before=comparison['before'],after=comparison['after'],
                               all_guards_passed=read(selected/'audit.json')['all_guards_passed'],
                               preserve_starting_root=comparison['preserve_starting_root'],
                               accepted_steps=sum(b['accepted_steps'] for b in blocks),engine_actor_frames=0)
                else:
                    selected = folder
                    row.update(fit_case(folder,child,proposal_builder_factory=HalfFloorConstraints if case['method']=='keys_and_halves' else None))
                row.update(selected_folder=str(selected),reused=bool(case.get('reuse_folder')),completion_sha256=sha256(selected/'completion.json'))
                check_files(folder,case['files']);check_files(folder/'source',child['source_files'])
            except Exception as exc:
                row.update(status='failed',error=str(exc))
            save(output/'results.json',results)
            print(case['id'],row['status'],flush=True)
    check_files(ROOT/'scripts',request['implementation']);check_files(Path('.'),request['resources'])
    save(output/'comparison.json',pair_results(results['rows']))
    save(output/'completion.json',dict(at=now(),request_sha256=sha256(output/'request.json'),results_sha256=sha256(output/'results.json'),
         comparison_sha256=sha256(output/'comparison.json'),failed=sum(r['status']=='failed' for r in results['rows']),
         new_engine_actor_frames=sum(r.get('engine_actor_frames',0) for r in results['rows']),quality_approved=False))
    save(output/'pipeline.json',dict(status='complete_with_failures' if any(r['status']=='failed' for r in results['rows']) else 'complete',at=now()))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['prepare','run'])
    parser.add_argument('output',type=Path)
    parser.add_argument('--parent',type=Path)
    parser.add_argument('--pilot',type=Path)
    args=parser.parse_args()
    if args.command=='prepare':
        prepare(args.parent.resolve(),args.pilot.resolve(),args.output.resolve())
    else:
        run(args.output.resolve())
