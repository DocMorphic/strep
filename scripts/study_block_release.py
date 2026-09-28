"""One frozen coupled-frame proposal for the remaining development release."""
import argparse
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from profile_support_surface import load
from sparse_support_surface import SparseSupportReferenceFitter
from serialized_pose import SerializedPose
from block_release_fit import BlockProblem, solve
from study_guarded_release import support_frames
from rig_loop import encode
from verify_breadth_contact import verify
from support_velocity_traces import run as trace
from support_release_metrics import measure
from study_support_release import compare
from study_whole_support_breadth import check_engine
from run_godot_rig_import import run as engine
from select_release_block import select_block
from check_piecewise_derivative import check_direction


def problem_for(request, envelope):
    held, source = Path(request['held']), Path(request['source'])
    fitter, _ = load(held, SparseSupportReferenceFitter)
    initial = np.load(source/'take/parameters.npz', allow_pickle=False)['parameters']
    animated = {c['target']['node'] for c in fitter.rig.document['animations'][0]['channels']}|set(fitter.nodes)
    oracle = SerializedPose(fitter.rig, animated, fitter.spec['root_node'], len(initial))
    free = [i for i in range(initial.shape[1]) if i not in envelope['protected_columns']]
    return BlockProblem(fitter, initial, oracle, request['frames'], free, envelope,
        envelope['safety_caps_m_s2'], request['target'])


def prepare(output, source=None, audit_path=None):
    if output.exists(): raise ValueError('Preserve previous trial')
    source = (source or ROOT/'reports/guarded-release-serialized-v1').resolve()
    source_request = read(source/'request.json'); held = Path(source_request['held'])
    audit_path = (audit_path or ROOT/'reports/guarded-release-serialized-audit-v1.json').resolve(); audit = read(audit_path)
    if audit['completion_sha256'] != sha256(source/'completion.json') or not all(audit['envelope_checks'].values()):
        raise ValueError('Independently audited guarded starting point required')
    for name, digest in read(source/'completion.json')['files'].items():
        if sha256(source/name) != digest: raise ValueError('Completed starting artifact changed')
    spec = read(source/'take/spec.json'); base = read(held/'release-dynamics.json')
    initial_dynamics = read(source/'take/release-dynamics.json')['candidate']
    envelope = read(source/'take/fit-summary.json')
    envelope = {key: envelope[key] for key in ['safety_caps_m_s2', 'support_speed_caps_m_s', 'support_steps',
        'hover_caps_m', 'protected_columns', 'rotation_cap_radians']}
    envelope['active_frames'] = support_frames(held, spec).tolist()
    caps = np.asarray(envelope['safety_caps_m_s2']); releases = []
    for index, side in enumerate(spec['patches']):
        global_cap = max(base[v]['feet'][side]['global_acceleration_max_m_s2'] for v in ['input', 'prior'])+1e-5
        caps[:, index] = np.minimum(caps[:, index], global_cap)
        tracks = [base[v]['feet'][side]['releases'] for v in ['input', 'prior']]+[initial_dynamics['feet'][side]['releases']]
        if len({len(t) for t in tracks}) != 1: raise ValueError('Release population differs')
        for raw, prior, initial in zip(*tracks):
            if len({r['release_frame'] for r in [raw, prior, initial]}) != 1: raise ValueError('Release clocks differ')
            limit = max(raw['acceleration_max_m_s2'], prior['acceleration_max_m_s2'])+1e-5
            protection = max(limit, initial['acceleration_max_m_s2'])
            centers = np.asarray(initial['acceleration_frames'])
            caps[centers-1, index] = np.minimum(caps[centers-1, index], protection)
            releases.append(dict(side=side, release_frame=initial['release_frame'], centers=centers.tolist(),
                original_limit_m_s2=limit, frozen_protection_m_s2=protection))
    envelope['safety_caps_m_s2'] = caps.tolist(); envelope['release_protection'] = releases
    selection = select_block(audit['events'], releases, spec['frames'])
    target = dict(centers=selection['centers'], side_index=list(spec['patches']).index(selection['side']),
        limit_m_s2=selection['limit_m_s2'], release_frame=selection['release_frame'])
    names = set(source_request['implementation'])|{'study_block_release.py', 'block_release_fit.py', 'select_release_block.py', 'check_piecewise_derivative.py'}
    inputs = dict(source_request['inputs'])
    for path in [source/'request.json', source/'completion.json', source/'take/parameters.npz', source/'take/fit-summary.json',
                 source/'take/release-dynamics.json', source/'take/candidate/character.glb', audit_path]:
        inputs[str(path)] = sha256(path)
    request = dict(at=now(), held=str(held), prior=source_request['prior'], source=str(source), source_audit=str(audit_path), frames=selection['frames'], selection=selection,
        protected_nodes=source_request['protected_nodes'], maxiter=80, target=target, inputs=inputs,
        method='One coupled temporal-block SLSQP proposal on free leg coordinates, initialized from completed serialized candidate. Audited worst release selected before fitting. Serialized values, smooth proposal Jacobians,8fixed safeguard fractions. Same root/protected tracks and original support/floor/hover/edit/rotation limits. Original global caps and no-new-release protection additionally frozen.',
        acceptance='Original full comparison and independent decoded envelope/root/protected checks unchanged; retain source and failed proposal. No held-out, equal-compute, convergence or quality claim.', quality_approved=False)
    output.mkdir(parents=True); (output/'implementation').mkdir()
    for name in names: shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    request['implementation'] = {name: sha256(output/'implementation'/name) for name in sorted(names)}
    save(output/'request.json', request); save(output/'envelope.json', envelope)
    with threadpool_limits(limits=1):
        problem = problem_for(request, envelope)
        x = problem.initial[np.ix_(problem.frames, problem.free)].ravel()
        rng = np.random.default_rng(733); rows = []
        def signature(y):
            values = problem.values(y); active = []
            for frame in problem.frames:
                positions = problem.fitter.surface_jacobian(int(frame), values[frame])[0]
                active.extend(int(ids[np.argmin(positions[ids, 1])]) for side, ids in enumerate(problem.patches)
                    if envelope['active_frames'][frame][side])
            return active
        for _ in range(3):
            direction = rng.normal(size=len(x)); direction /= np.linalg.norm(direction)
            rows.append(check_direction(lambda y: problem.evaluate(y, quantized=False), signature, x, direction))
        if not all(row['passed'] for row in rows):
            save(output/'failed-derivative-proof.json', dict(at=now(), rows=rows, passed=False))
            save(output/'pipeline.json', dict(at=now(), status='preparation_failed', reason='Smooth-branch derivative proof failed', quality_approved=False))
            raise ValueError('Real block smooth proposal derivative mismatch')
        initial = problem.evaluate(x)
        if initial[2].min() < -1e-7 or not problem.geometric_guard(problem.initial):
            raise ValueError('Block initial serialized constraints fail')
    save(output/'derivative-proof.json', dict(at=now(), rows=rows, passed=True, initial_objective=initial[0],
        initial_minimum_constraint=float(initial[2].min()), variables=len(x), constraints=len(initial[2]),
        scope='Actual skin smooth block Jacobian proof, same2e-4 error threshold. Fixed diagnostic steps1e-6 then1e-7 only if the hover minimum vertex changes; both perturbations must share the base active branch. Not a derivative of float quantization.', quality_approved=False))
    save(output/'freeze.json', dict(request_sha256=sha256(output/'request.json'), envelope_sha256=sha256(output/'envelope.json'), derivative_sha256=sha256(output/'derivative-proof.json')))
    save(output/'pipeline.json', dict(at=now(), status='prepared', quality_approved=False)); print(read(output/'derivative-proof.json'))


def run(output):
    request = read(output/'request.json'); frozen = read(output/'freeze.json')
    if read(output/'pipeline.json')['status'] != 'prepared': raise ValueError('Preserve prior run')
    p = psutil.Process(); save(output/'runner.json', dict(at=now(), pid=p.pid, created=p.create_time()))
    def phase(status, **kw):
        save(output/'pipeline.json', dict(at=now(), status=status, quality_approved=False, **kw)); print(status, kw, flush=True)
    def validate():
        for name, key in [('request.json', 'request_sha256'), ('envelope.json', 'envelope_sha256'), ('derivative-proof.json', 'derivative_sha256')]:
            if sha256(output/name) != frozen[key]: raise ValueError('Protocol changed')
        for path, digest in request['inputs'].items():
            if sha256(path) != digest: raise ValueError('Input changed')
        for name, digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest: raise ValueError('Implementation changed: '+name)
    try:
        validate(); envelope = read(output/'envelope.json'); held, prior = Path(request['held']), Path(request['prior'])
        with threadpool_limits(limits=1):
            problem = problem_for(request, envelope); phase('fitting')
            values, solver = solve(problem, request['maxiter'], lambda item: phase('fitting', **item))
            take = output/'take'; take.mkdir(); shutil.copytree(held/'input', take/'input')
            spec = problem.fitter.spec; save(take/'spec.json', spec); save(take/'request.json', read(held/'request.json'))
            save(take/'solver.json', solver); save(take/'fit-summary.json', {**envelope, 'block_solver': solver})
            np.savez_compressed(take/'parameters.npz', initial=problem.initial, parameters=values)
            # Retain the optimizer's proposed endpoint even if acceptance rejects it.
            world = np.array([problem.fitter.pose(f, x)[0] for f, x in enumerate(values)])
            dest = take/'candidate'; dest.mkdir(); animated = set(problem.evaluator.animated)
            times, export = encode(problem.fitter.rig, world, animated, spec['root_node'], dest/'character.glb', 'Coupled release development correction')
            shutil.copyfile(held/'input/contacts.json', dest/'contacts.json'); root = spec['root_node']
            save(dest/'root-motion.json', dict(times_s=times.tolist(), positions_m=world[:, root, :3, 3].tolist(), rotations_xyzw=Rotation.from_matrix(world[:, root, :3, :3]).as_quat().tolist()))
            phase('verifying'); proof = verify(take); traces = trace(take)
            dynamics = read(held/'release-dynamics.json'); dynamics['candidate'] = measure(dest/'character.glb', spec, read(held/'request.json')['support'])
            save(take/'release-dynamics.json', dynamics)
            decision = compare(read(prior/'verification.json'), proof, read(prior/'traces.json'), traces, dynamics); save(take/'comparison.json', decision)
            group = output/'engine'; group.mkdir()
            checks = [dict(id=name, path=str(path), sha256=sha256(path), frames=spec['frames'], fps=spec['fps']) for name, path in
                [('raw', take/'input/character.glb'), ('held', held/'candidate/character.glb'), ('candidate', dest/'character.glb')]]
            save(group/'manifest.json', dict(cases=checks)); phase('engine'); engine(group, group/'audit'); frames = check_engine(read(group/'audit/verification.json'), checks)
        validate()
        files = ['take/parameters.npz', 'take/fit-summary.json', 'take/solver.json', 'take/verification.json', 'take/traces.json', 'take/release-dynamics.json', 'take/comparison.json', 'take/candidate/character.glb', 'engine/audit/verification.json']
        save(output/'completion.json', dict(at=now(), request_sha256=sha256(output/'request.json'), files={name: sha256(output/name) for name in files},
            engine_actor_frames=frames, passed_development_screen=decision['passes_development_screen'], quality_approved=False))
        phase('complete', passed_development_screen=decision['passes_development_screen'])
    except BaseException as exc:
        phase('failed', error=str(exc), traceback=traceback.format_exc()); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('command', choices=['prepare', 'run']); p.add_argument('output', type=Path)
    p.add_argument('--source', type=Path); p.add_argument('--audit', type=Path); a = p.parse_args()
    if a.command == 'prepare': prepare(a.output.resolve(), a.source, a.audit)
    else:
        if a.source is not None or a.audit is not None: p.error('Source and audit are frozen at preparation')
        run(a.output.resolve())
