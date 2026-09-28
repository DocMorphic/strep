"""Common export, decoded comparison and engine proof for isolated trials."""
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read, save, sha256
from rig_loop import encode
from verify_breadth_contact import verify
from support_velocity_traces import run as trace
from support_release_metrics import measure
from study_support_release import compare
from study_whole_support_breadth import check_engine
from run_godot_rig_import import run as engine


def finalize(output, request, fitter, initial, values, envelope, solver):
    held, prior = Path(request['held']), Path(request['prior']); spec = fitter.spec
    take = output/'take'; take.mkdir(); shutil.copytree(held/'input', take/'input')
    save(take/'spec.json', spec); save(take/'request.json', read(held/'request.json'))
    save(take/'fit-summary.json', envelope); save(take/'solver.json', solver)
    np.savez_compressed(take/'parameters.npz', initial=initial, parameters=values)
    world = np.array([fitter.pose(f, x)[0] for f, x in enumerate(values)])
    dest = take/'candidate'; dest.mkdir(); root = spec['root_node']
    animated = {c['target']['node'] for c in fitter.rig.document['animations'][0]['channels']}|set(fitter.nodes)
    times, export = encode(fitter.rig, world, animated, root, dest/'character.glb', 'Release feasibility restoration development')
    shutil.copyfile(held/'input/contacts.json', dest/'contacts.json')
    save(dest/'root-motion.json', dict(times_s=times.tolist(), positions_m=world[:, root, :3, 3].tolist(), rotations_xyzw=Rotation.from_matrix(world[:, root, :3, :3]).as_quat().tolist()))
    proof = verify(take); traces = trace(take); dynamics = read(held/'release-dynamics.json')
    dynamics['candidate'] = measure(dest/'character.glb', spec, read(held/'request.json')['support']); save(take/'release-dynamics.json', dynamics)
    decision = compare(read(prior/'verification.json'), proof, read(prior/'traces.json'), traces, dynamics); save(take/'comparison.json', decision)
    group = output/'engine'; group.mkdir()
    checks = [dict(id=name, path=str(path), sha256=sha256(path), frames=spec['frames'], fps=spec['fps']) for name, path in
        [('raw', take/'input/character.glb'), ('held', held/'candidate/character.glb'), ('candidate', dest/'character.glb')]]
    save(group/'manifest.json', dict(cases=checks)); engine(group, group/'audit'); frames = check_engine(read(group/'audit/verification.json'), checks)
    files = ['take/parameters.npz', 'take/fit-summary.json', 'take/solver.json', 'take/verification.json', 'take/traces.json',
        'take/release-dynamics.json', 'take/comparison.json', 'take/candidate/character.glb', 'engine/audit/verification.json']
    return dict(files={name: sha256(output/name) for name in files}, passed_development_screen=decision['passes_development_screen'], engine_actor_frames=frames)
