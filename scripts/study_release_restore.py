"""Frozen linear feasibility restoration of the retained coupled endpoint."""
import argparse
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from study_block_release import problem_for
from linear_feasibility_restore import restore
from finalize_release_trial import finalize


def prepare(output):
    if output.exists(): raise ValueError('Preserve previous study')
    block = ROOT/'reports/block-release-v1'; proposal = ROOT/'reports/block-release-proposal-v1'
    original = read(block/'request.json'); completion = read(proposal/'completion.json')
    audit_path = ROOT/'reports/block-release-proposal-audit-v1.json'; audit = read(audit_path)
    if audit['completion_sha256'] != sha256(proposal/'completion.json') or audit['failed_full_checks'] or not all(audit['envelope_checks'].values()):
        raise ValueError('Fully audited original-screen passing endpoint required')
    for name, digest in completion['files'].items():
        if sha256(proposal/name) != digest: raise ValueError('Proposal artifact changed')
    envelope = read(block/'envelope.json'); target = original['target']
    caps = np.asarray(envelope['safety_caps_m_s2'])
    caps[np.asarray(target['centers'])-1, target['side_index']] = np.minimum(caps[np.asarray(target['centers'])-1, target['side_index']], target['limit_m_s2'])
    envelope['safety_caps_m_s2'] = caps.tolist()
    names = set(original['implementation'])|{'linear_feasibility_restore.py', 'study_release_restore.py', 'finalize_release_trial.py'}
    inputs = dict(original['inputs'])
    for p in [block/'request.json', block/'envelope.json', block/'take/solver.json', block/'completion.json',
              proposal/'request.json', proposal/'completion.json', proposal/'take/parameters.npz', audit_path]:
        inputs[str(p)] = sha256(p)
    request = dict(at=now(), held=original['held'], prior=original['prior'], source=original['source'], proposal=str(proposal),
        block=str(block), frames=original['frames'], target=target, protected_nodes=original['protected_nodes'],
        attempts=5, trust=1e-5, margin=1e-4, inputs=inputs,
        method='Linearized minimum-infinity-norm feasibility correction with HiGHS, at most5 attempts and8 fixed safeguard fractions per attempt. All original constraints retained; release target additionally hard. Serialized checks require zero target objective, geometry preserved and lower worst infeasibility. Frozen internal acceptance remains minimum>=-1e-8.',
        scope='Previously inspected development endpoint; interior search margin tightens proposals, never loosens acceptance. No old solver decision changed and no release approval.', quality_approved=False)
    output.mkdir(parents=True); (output/'implementation').mkdir()
    for name in names: shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    request['implementation'] = {name: sha256(output/'implementation'/name) for name in sorted(names)}
    save(output/'request.json', request); save(output/'envelope.json', envelope)
    with threadpool_limits(limits=1):
        problem = problem_for(request, envelope)
        start = np.asarray(read(block/'take/solver.json')['proposed_coordinates'])
        expected = np.load(proposal/'take/parameters.npz')['parameters']
        np.testing.assert_array_equal(problem.values(start), expected)
        initial = problem.evaluate(start)
        if initial[0] != 0. or not problem.geometric_guard(initial[5]): raise ValueError('Source target or geometry differs')
    save(output/'preflight.json', dict(at=now(), objective=initial[0], minimum_constraint=float(initial[2].min()), variables=len(start),
        proposal_parameters_verified=True, geometric_guard=True, quality_approved=False))
    save(output/'freeze.json', dict(request_sha256=sha256(output/'request.json'), envelope_sha256=sha256(output/'envelope.json'), preflight_sha256=sha256(output/'preflight.json')))
    save(output/'pipeline.json', dict(at=now(), status='prepared', quality_approved=False)); print(read(output/'preflight.json'))


def run(output):
    request = read(output/'request.json'); freeze = read(output/'freeze.json')
    if read(output/'pipeline.json')['status'] != 'prepared': raise ValueError('Preserve earlier run')
    p = psutil.Process(); save(output/'runner.json', dict(at=now(), pid=p.pid, created=p.create_time()))
    def phase(status, **kw):
        save(output/'pipeline.json', dict(at=now(), status=status, quality_approved=False, **kw)); print(status, kw, flush=True)
    def validate():
        for name, key in [('request.json', 'request_sha256'), ('envelope.json', 'envelope_sha256'), ('preflight.json', 'preflight_sha256')]:
            if sha256(output/name) != freeze[key]: raise ValueError('Protocol changed')
        for path, digest in request['inputs'].items():
            if sha256(path) != digest: raise ValueError('Input changed')
        for name, digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest: raise ValueError('Implementation changed')
    try:
        validate(); envelope = read(output/'envelope.json')
        with threadpool_limits(limits=1):
            problem = problem_for(request, envelope); start = np.asarray(read(Path(request['block'])/'take/solver.json')['proposed_coordinates'])
            phase('restoring')
            values, solver = restore(problem, start, request['attempts'], request['trust'], request['margin'],
                lambda record: phase('restoring', attempt=record['iteration'], lp_success=record['success'], selected_fraction=record['selected_fraction']))
            phase('verifying_and_engine', feasible=solver['feasible'])
            result = finalize(output, request, problem.fitter, problem.values(start), values, envelope, solver)
        validate()
        save(output/'completion.json', dict(at=now(), request_sha256=sha256(output/'request.json'), internally_feasible=solver['feasible'], **result, quality_approved=False))
        phase('complete', internally_feasible=solver['feasible'], passed_development_screen=result['passed_development_screen'])
    except BaseException as exc:
        phase('failed', error=str(exc), traceback=traceback.format_exc()); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('command', choices=['prepare', 'run']); p.add_argument('output', type=Path); a = p.parse_args(); (prepare if a.command == 'prepare' else run)(a.output.resolve())
