"""Matched bounded-step follow-up to the completed coupled SLSQP pilot."""
import argparse
import ast
import shutil
from pathlib import Path
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from study_coupled_breadth_block import prepare as prepare_source, run as run_source
from coupled_breadth_conic import constraints
from conic_root_descent import solve


def prepare(parent, output):
    old = read(parent/'request.json')
    complete = read(parent/'completion.json')
    if complete['request_sha256'] != sha256(parent/'request.json'):
        raise ValueError('Parent request changed')
    for name in ['audit', 'engine']:
        path = parent/('audit.json' if name=='audit' else 'engine/verification.json')
        if complete[name+'_sha256'] != sha256(path):
            raise ValueError('Parent proof changed')
    diagnosis = Path(old['diagnosis'])
    if sha256(diagnosis) != old['diagnosis_sha256']:
        raise ValueError('Original diagnosis changed')
    prepare_source(diagnosis, output)
    request = read(output/'request.json')
    for field in ['case', 'frames', 'target', 'source_files']:
        if request[field] != old[field]:
            raise ValueError('Matched comparison differs: '+field)
    if sha256(output/'envelope.json') != sha256(parent/'envelope.json'):
        raise ValueError('Preservation envelope differs')
    request.update(parent=str(parent), parent_completion_sha256=sha256(parent/'completion.json'),
                   method='Bounded conic descent with full source-depth, anchor and radius constraints; unchanged nonlinear acceptance.',
                   maxiter=12, trusts=[1e-4, 1e-5, 1e-6], fractions=[.5**i for i in range(8)])
    pending = [Path(__file__).name]
    seen = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        path = ROOT/'scripts'/name
        shutil.copyfile(path, output/'implementation'/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            for module in modules:
                child = (module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).is_file():
                    pending.append(child)
    request['implementation'] = {p.name: sha256(p) for p in (output/'implementation').glob('*.py')}
    resources = [ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe',
                 ROOT/'scripts/godot_import_audit.gd', ROOT/'reports/conic-solver-bootstrap-v1.json']
    bootstrap = read(resources[-1])
    resources.extend(Path(bootstrap['vendor'])/name for name in bootstrap['files'])
    request['resources'] = {str(p): sha256(p) for p in resources}
    save(output/'request.json', request)
    save(output/'freeze.json', {n: sha256(output/n) for n in ['request.json', 'envelope.json', 'preflight.json']})


def run(output):
    request = read(output/'request.json')
    check_files(Path('.'), request['resources'])
    if sha256(Path(request['parent'])/'completion.json') != request['parent_completion_sha256']:
        raise ValueError('Parent completion changed')
    def fit(problem, steps, progress):
        values, record = solve(problem, steps, tuple(request['trusts']), progress,
                               constraint_builder=constraints)
        record['accepted_fraction'] = 1. if any(row['accepted'] for row in record['history']) else None
        return values, record
    run_source(output, solver_function=fit)
    check_files(Path('.'), request['resources'])


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare', 'run'])
    parser.add_argument('output', type=Path)
    parser.add_argument('--parent', type=Path)
    args = parser.parse_args()
    if args.command=='prepare':
        prepare(args.parent.resolve(), args.output.resolve())
    else:
        try:
            run(args.output.resolve())
        except Exception as exc:
            save(args.output/'failure.json', dict(at=now(), error=str(exc), quality_approved=False))
            raise
