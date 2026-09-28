"""Frozen three-sweep pilot with individual dynamics envelopes."""
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
from guarded_release_fit import relax, acceleration_envelope_pair, support_envelope_pair
from foot_acceleration import acceleration_caps
from rig_loop import encode
from verify_breadth_contact import verify
from support_velocity_traces import run as trace
from support_release_metrics import measure
from study_support_release import compare
from run_godot_rig_import import run as engine
from study_whole_support_breadth import check_engine


def support_frames(folder, spec):
    active = np.zeros((spec['frames'], len(spec['patches'])), bool)
    for index, side in enumerate(spec['patches']):
        for interval in read(folder/'input/contacts.json')['intervals']:
            if interval['joint'] in (side+'Foot', side+'ToeBase'):
                active[interval['start_frame']:interval['end_frame_exclusive'], index] = True
    return active


def caps_from_baselines(folder, spec):
    baseline = read(folder/'release-dynamics.json')
    tracks = [np.stack([baseline[v]['feet'][side]['centroids_m'] for side in spec['patches']], axis=1)
              for v in ['input', 'prior']]
    return acceleration_caps(*tracks, spec['fps'])


def prepare(output, serialized=False, case_id='motion-036-rig-01'):
    if output.exists():
        raise ValueError('Preserve previous study')
    eligibility_path = ROOT/'reports/release-method-eligibility-v1.json'
    eligible = next((r for r in read(eligibility_path)['rows'] if r['case'] == case_id), None)
    if eligible is None or not eligible['eligible_for_current_fixed_root_method']:
        raise ValueError('Case is not eligible for this held-root development protocol')
    for name, digest in eligible['inputs'].items():
        if sha256(ROOT/name) != digest: raise ValueError('Eligibility evidence changed')
    held = ROOT/'reports/support-release-hold-v1/takes'/case_id
    prior = ROOT/'reports/whole-support-breadth-v1/takes'/case_id
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from rig_transition import localize
    from release_trial_selection import peak_joint, derivative_frames
    spec = read(held/'spec.json')
    if spec['fps'] != 30: raise ValueError('Current export protocol requires30fps')
    rig = RigAsset.load(held/'candidate/character.glb'); sampler = AnimationSampler(rig.document, rig.binary, 0)
    world = np.array([sampler.sample(float(np.float32(f/spec['fps']))) for f in range(spec['frames'])])
    selection = peak_joint(localize(world, rig.parents), [entry['node'] for entry in spec['edit_joints'].values()])
    selection['name'] = rig.document['nodes'][selection['node']].get('name')
    samples = derivative_frames(read(held/'release-dynamics.json'), spec['frames'])
    names = set(read(ROOT/'reports/support-acceleration-v1/request.json')['implementation'])
    names |= {'study_guarded_release.py', 'guarded_release_fit.py', 'profile_support_surface.py', 'sparse_support_surface.py', 'release_trial_selection.py'}
    paths = [folder/name for folder in [held, prior] for name in
        ['fit.npz', 'spec.json', 'request.json', 'input/character.glb', 'input/contacts.json',
         'verification.json', 'traces.json', 'candidate/character.glb']]
    paths += [held/'release-dynamics.json', ROOT/'reports/support-acceleration-protected-releases-v1.json',
              ROOT/'reports/support-acceleration-path-audit-v1.json', eligibility_path]
    if serialized:
        names.add('serialized_pose.py')
        oracle = ROOT/'reports/serialized-pose-proof-v1'
        proof = read(oracle/'completion.json')
        if not proof['passed'] or proof['results_sha256'] != sha256(oracle/'results.json'):
            raise ValueError('Completed serialized pose proof required')
        if read(oracle/'request.json')['implementation']['serialized_pose.py'] != sha256(ROOT/'scripts/serialized_pose.py'):
            raise ValueError('Pose evaluator changed after its proof')
        paths += [oracle/'request.json', oracle/'completion.json', oracle/'results.json']
    output.mkdir(parents=True); (output/'implementation').mkdir()
    for name in names:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    request = dict(at=now(), case=case_id, held=str(held), prior=str(prior), sweeps=3, maxiter=80, protected_nodes=selection['protected_nodes'],
        joint_selection=selection, derivative_sample_selection=samples,
        initialization='Original held support parameters; root and preselected peak-joint correction tracks unchanged.',
        method='Coordinate SLSQP on actual foot acceleration excess. Fixed per-center/foot max(raw,prior,held) acceleration envelopes; held per-step support speeds; integer floor5mm; per-frame support hover<=max10mm/held; original edit bounds. Eight fixed safeguard fractions; true local rotation peak guarded. Half-frame floor and original full screen checked after serialization.',
        acceptance='Original full raw/prior development comparison unchanged; independent fresh decoded envelopes and root/protected-track preservation required. No release approval.',
        scope='One previously inspected development clip, not held-out or equal-compute ablation. No convergence promise, no product promotion.',
        inputs={str(path): sha256(path) for path in paths},
        implementation={name: sha256(output/'implementation'/name) for name in sorted(names)}, quality_approved=False)
    request['serialized_pose_evaluation'] = serialized
    if serialized:
        request['method'] += ' Evaluate actual float32 TRS export poses for objective/constraint values and acceptance; smooth unquantized Jacobians only approximate proposals. Serialized half-frame clearance and rotation also gated on every accepted update.'
    save(output/'request.json', request)
    # Check the actual skin chain rule before permitting optimization.
    with threadpool_limits(limits=1):
        fitter, values = load(held, SparseSupportReferenceFitter)
        patches = [p['vertices'] for p in fitter.spec['patches'].values()]
        centers = np.array([[fitter.rig.vertices(fitter.pose(f, x)[0])[ids].mean(axis=0) for ids in patches]
                            for f, x in enumerate(values)])
        fps = fitter.spec['fps']
        caps = np.maximum(caps_from_baselines(held, fitter.spec), np.linalg.norm(np.diff(centers, n=2, axis=0)*fps**2, axis=2))
        active = support_frames(held, fitter.spec); steps = active[:-1]&active[1:]
        speeds = np.linalg.norm(np.diff(centers[:, :, [0, 2]], axis=0)*fps, axis=2)
        rng = np.random.default_rng(541); rows = []
        for frame in samples['frames']:
            x = values[frame]
            def pair(v):
                positions, jac = fitter.surface_jacobian(frame, v)
                points = np.array([positions[ids].mean(axis=0) for ids in patches])
                derivative = np.array([jac[ids].mean(axis=0) for ids in patches])
                a, aj = acceleration_envelope_pair(centers, frame, points, derivative, caps, fps)
                s, sj = support_envelope_pair(centers, frame, points, derivative, steps, speeds, fps)
                return np.r_[a, s], np.vstack([aj, sj])
            v, j = pair(x); errors = []
            for _ in range(3):
                direction = rng.normal(size=len(x)); direction /= np.linalg.norm(direction)
                difference = (pair(x+1e-6*direction)[0]-pair(x-1e-6*direction)[0])/2e-6
                error = float(np.abs(difference-j@direction).max())
                if error > 2e-4:
                    raise ValueError('Actual skin constraint derivative mismatch')
                errors.append(error)
            rows.append(dict(frame=frame, max_directional_error=max(errors), constraints=len(v)))
    save(output/'derivative-proof.json', dict(at=now(), rows=rows, passed=True, quality_approved=False,
        request_sha256=sha256(output/'request.json')))
    save(output/'pipeline.json', dict(at=now(), status='prepared', quality_approved=False))
    print(dict(prepared=True, max_derivative_error=max(r['max_directional_error'] for r in rows)))


def run(output):
    request = read(output/'request.json')
    if read(output/'pipeline.json')['status'] != 'prepared':
        raise ValueError('Preserve existing run')
    proc = psutil.Process(); save(output/'runner.json', dict(at=now(), pid=proc.pid, created=proc.create_time()))
    def phase(status, **kw):
        save(output/'pipeline.json', dict(at=now(), status=status, quality_approved=False, **kw))
        print(status, kw, flush=True)
    def validate():
        for path, digest in request['inputs'].items():
            if sha256(path) != digest: raise ValueError('Input changed: '+path)
        for name, digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest:
                raise ValueError('Implementation changed: '+name)
    try:
        validate(); held, prior = Path(request['held']), Path(request['prior'])
        take = output/'take'; take.mkdir(); shutil.copytree(held/'input', take/'input')
        with threadpool_limits(limits=1):
            fitter, initial = load(held, SparseSupportReferenceFitter)
            spec = fitter.spec; save(take/'spec.json', spec); save(take/'request.json', read(held/'request.json'))
            evaluator = None
            if request.get('serialized_pose_evaluation'):
                from serialized_pose import SerializedPose
                animated = {c['target']['node'] for c in fitter.rig.document['animations'][0]['channels']}|set(fitter.nodes)
                evaluator = SerializedPose(fitter.rig, animated, spec['root_node'], spec['frames'])
            phase('fitting')
            values, records, fit = relax(fitter, initial, caps_from_baselines(held, spec), support_frames(held, spec),
                request['protected_nodes'], request['sweeps'], request['maxiter'],
                lambda sweep, change, energy: phase('fitting', sweep=sweep, max_parameter_change=change, energy=energy),
                pose_evaluator=evaluator)
            save(take/'solver.json', records); save(take/'fit-summary.json', fit)
            np.savez_compressed(take/'parameters.npz', initial=initial, parameters=values)
            after = np.array([fitter.pose(f, x)[0] for f, x in enumerate(values)])
            dest = take/'candidate'; dest.mkdir()
            animated = {c['target']['node'] for c in fitter.rig.document['animations'][0]['channels']}|set(fitter.nodes)
            times, roundtrip = encode(fitter.rig, after, animated, spec['root_node'], dest/'character.glb', 'Guarded release development refit')
            shutil.copyfile(take/'input/contacts.json', dest/'contacts.json')
            root = spec['root_node']
            save(dest/'root-motion.json', dict(times_s=times.tolist(), positions_m=after[:, root, :3, 3].tolist(),
                rotations_xyzw=Rotation.from_matrix(after[:, root, :3, :3]).as_quat().tolist()))
            phase('verifying'); proof = verify(take); traces = trace(take)
            dynamics = read(held/'release-dynamics.json'); dynamics['candidate'] = measure(dest/'character.glb', spec, read(held/'request.json')['support'])
            save(take/'release-dynamics.json', dynamics)
            decision = compare(read(prior/'verification.json'), proof, read(prior/'traces.json'), traces, dynamics)
            save(take/'comparison.json', decision)
            checks = [dict(id=name, path=str(path), sha256=sha256(path), frames=spec['frames'], fps=spec['fps'])
                for name, path in [('raw', take/'input/character.glb'), ('held', held/'candidate/character.glb'), ('candidate', dest/'character.glb')]]
            group = output/'engine'; group.mkdir(); save(group/'manifest.json', dict(cases=checks)); phase('engine')
            engine(group, group/'audit'); frames = check_engine(read(group/'audit/verification.json'), checks)
        validate()
        files = ['take/parameters.npz', 'take/fit-summary.json', 'take/solver.json', 'take/verification.json',
                 'take/traces.json', 'take/release-dynamics.json', 'take/comparison.json', 'take/candidate/character.glb', 'engine/audit/verification.json']
        save(output/'completion.json', dict(at=now(), request_sha256=sha256(output/'request.json'),
            files={name: sha256(output/name) for name in files}, engine_actor_frames=frames,
            passed_development_screen=decision['passes_development_screen'], quality_approved=False))
        phase('complete', passed_development_screen=decision['passes_development_screen'])
    except BaseException as exc:
        phase('failed', error=str(exc), traceback=traceback.format_exc()); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('command', choices=['prepare', 'run']); parser.add_argument('output', type=Path); parser.add_argument('--serialized', action='store_true'); parser.add_argument('--case-id', default='motion-036-rig-01')
    args = parser.parse_args()
    if args.command == 'prepare': prepare(args.output.resolve(), args.serialized, args.case_id)
    else: run(args.output.resolve())
