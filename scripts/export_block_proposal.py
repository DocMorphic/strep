"""Decode the already-retained rejected endpoint; never change its decision."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from study_block_release import problem_for
from rig_loop import encode
from verify_breadth_contact import verify
from support_velocity_traces import run as trace
from support_release_metrics import measure
from study_support_release import compare
from run_godot_rig_import import run as engine
from study_whole_support_breadth import check_engine


def run(source, output):
    if output.exists(): raise ValueError('Preserve diagnostic')
    request = read(source/'request.json'); done = read(source/'completion.json')
    for name, digest in done['files'].items():
        if sha256(source/name) != digest: raise ValueError('Completed trial changed')
    for path, digest in request['inputs'].items():
        if sha256(path) != digest: raise ValueError('Original evidence changed')
    output.mkdir(parents=True); (output/'implementation').mkdir()
    names = set(request['implementation'])|{'export_block_proposal.py'}
    for name in names: shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    inputs = dict(request['inputs'])
    for name in ['request.json', 'envelope.json', 'completion.json', 'take/solver.json']:
        inputs[str(source/name)] = sha256(source/name)
    protocol = dict(at=now(), held=request['held'], prior=request['prior'], source=str(source),
        protected_nodes=request['protected_nodes'], inputs=inputs,
        implementation={name: sha256(output/'implementation'/name) for name in sorted(names)},
        scope='Post-run diagnostic of retained full optimizer endpoint rejected by the original internal safeguards. No optimization, selection, tolerance change or promotion; original decision is preserved.', quality_approved=False)
    save(output/'request.json', protocol); save(output/'pipeline.json', dict(status='exporting', quality_approved=False))
    with threadpool_limits(limits=1):
        envelope = read(source/'envelope.json'); problem = problem_for(request, envelope)
        solver = read(source/'take/solver.json'); proposal = np.asarray(solver['proposed_coordinates'])
        values = problem.values(proposal); evaluation = problem.evaluate(proposal)
        take = output/'take'; take.mkdir(); held = Path(request['held']); prior = Path(request['prior'])
        shutil.copytree(held/'input', take/'input'); spec = problem.fitter.spec
        save(take/'spec.json', spec); save(take/'request.json', read(held/'request.json'))
        save(take/'fit-summary.json', envelope); np.savez_compressed(take/'parameters.npz', initial=problem.initial, parameters=values)
        save(take/'internal-rejection.json', dict(original_solver_status=solver['status'], original_accepted_fraction=solver['accepted_fraction'],
            objective=evaluation[0], minimum_normalized_constraint=float(evaluation[2].min()), geometric_guard=problem.geometric_guard(values),
            remains_rejected_by_original_safeguards=True, quality_approved=False))
        world = np.array([problem.fitter.pose(f, x)[0] for f, x in enumerate(values)])
        dest = take/'candidate'; dest.mkdir(); root = spec['root_node']
        times, export = encode(problem.fitter.rig, world, set(problem.evaluator.animated), root, dest/'character.glb', 'Rejected block endpoint diagnostic')
        shutil.copyfile(held/'input/contacts.json', dest/'contacts.json')
        save(dest/'root-motion.json', dict(times_s=times.tolist(), positions_m=world[:, root, :3, 3].tolist(), rotations_xyzw=Rotation.from_matrix(world[:, root, :3, :3]).as_quat().tolist()))
        proof = verify(take); traces = trace(take); dynamics = read(held/'release-dynamics.json')
        dynamics['candidate'] = measure(dest/'character.glb', spec, read(held/'request.json')['support']); save(take/'release-dynamics.json', dynamics)
        decision = compare(read(prior/'verification.json'), proof, read(prior/'traces.json'), traces, dynamics); save(take/'comparison.json', decision)
        group = output/'engine'; group.mkdir()
        checks = [dict(id=name, path=str(path), sha256=sha256(path), frames=spec['frames'], fps=spec['fps']) for name, path in
            [('raw', take/'input/character.glb'), ('held', held/'candidate/character.glb'), ('candidate', dest/'character.glb')]]
        save(group/'manifest.json', dict(cases=checks)); engine(group, group/'audit'); frames = check_engine(read(group/'audit/verification.json'), checks)
    for path, digest in inputs.items():
        if sha256(path) != digest: raise ValueError('Input changed during diagnostic')
    files = ['take/parameters.npz', 'take/fit-summary.json', 'take/internal-rejection.json', 'take/verification.json', 'take/traces.json',
        'take/release-dynamics.json', 'take/comparison.json', 'take/candidate/character.glb', 'engine/audit/verification.json']
    save(output/'completion.json', dict(at=now(), request_sha256=sha256(output/'request.json'), files={name: sha256(output/name) for name in files},
        passed_development_screen=decision['passes_development_screen'], engine_actor_frames=frames, original_internal_rejection_retained=True, quality_approved=False))
    save(output/'pipeline.json', dict(at=now(), status='complete', quality_approved=False))
    print(dict(full_comparison=decision['checks'], internal_rejection_retained=True))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('source', type=Path); p.add_argument('output', type=Path); a = p.parse_args(); run(a.source.resolve(), a.output.resolve())
