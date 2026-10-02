"""Experimental coupled fitting of explicit mesh contacts, including hands/body.

Targets retain their authored meaning and bounds. A lower objective is not
evidence of correct anatomy, a feasible target, or release-quality motion.
"""
import argparse
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits, threadpool_info
from rig_asset import RigAsset
from rig_trajectory_fit import TrajectoryFitter
from rig_coupled_pose import CoupledPoseFitter, window_basis
from target_rig_contact import baseline, audit
from rig_loop import encode
from inspect_rig_contacts import inspect
from strep import read, save, sha256, now
from rig_subframe_floor import inspect as inspect_subframe_floor


class MeshContactTrajectoryFitter(TrajectoryFitter):
    """The original contact/floor/edit objective evaluated across the clip.

Temporal terms count every adjacent edit difference once, plus the original
zero-edit prior before frame zero. Coordinate gradients include both neighbors.
No clearance or inferred support-height objective is added.
"""
    def __init__(self, rig, spec, local, envelope):
        if len(local) != spec['frames']:
            raise ValueError('Contact draft and trajectory length differ')
        super().__init__(rig, spec, local,
                         {k: np.zeros(len(local)) for k in spec['patches']},
                         envelope, [])

    def trajectory_pair(self, frame, values):
        points, jac = self.surface_jacobian(frame, values)
        obj = self.spec['objective']; identity = np.eye(len(values))
        parts = []; rows = []
        for c in self.active[frame]:
            ids = self.spec['patches'][c['patch']]['vertices']
            parts.append((points[ids].mean(axis=0)-c['target_position_m'])*obj['contact_weight'])
            rows.append(jac[ids].mean(axis=0)*obj['contact_weight'])
        parts.extend([np.minimum(points[:, 1], 0)*obj['floor_weight'],
                      values[:3]*obj['root_prior'],
                      values[3:]*obj['rotation_prior_m_per_radian']])
        rows.extend([jac[:, 1]*(points[:, 1]<0)[:, None]*obj['floor_weight'],
                     identity[:3]*obj['root_prior'],
                     identity[3:]*obj['rotation_prior_m_per_radian']])
        scale = np.r_[np.ones(3), np.full(len(values)-3, obj['rotation_prior_m_per_radian'])]*obj['temporal_weight']
        neighbors = [self.values[n] for n in (frame-1, frame+1) if 0<=n<len(self.values)]
        if frame == 0: neighbors.append(np.zeros_like(values))
        parts.extend((values-n)*scale for n in neighbors)
        rows.extend(identity*scale for _ in neighbors)
        return np.concatenate(parts), np.vstack(rows)

    def total_energy(self):
        obj = self.spec['objective']; p = self.positions; v = self.values
        result = float(np.sum((np.minimum(p[:, :, 1], 0)*obj['floor_weight'])**2))
        for c in self.spec['contacts']:
            track = p[c['start_frame']:c['end_frame_exclusive'],
                      self.spec['patches'][c['patch']]['vertices']].mean(axis=1)
            result += float(np.sum(((track-c['target_position_m'])*obj['contact_weight'])**2))
        result += float(np.sum((v[:, :3]*obj['root_prior'])**2)
                        + np.sum((v[:, 3:]*obj['rotation_prior_m_per_radian'])**2))
        scale = np.r_[np.ones(3), np.full(v.shape[1]-3, obj['rotation_prior_m_per_radian'])]*obj['temporal_weight']
        result += float(np.sum((np.diff(v, axis=0)*scale)**2)+np.sum((v[0]*scale)**2))
        return result


class CoupledMeshContactFitter(CoupledPoseFitter):
    def energy(self):
        return self.fitter.total_energy()


METHODS = ('rig_mesh_trajectory.py', 'rig_coupled_pose.py', 'rig_trajectory_fit.py',
           'rig_clearance_fit.py', 'target_rig_contact.py', 'rig_periodic_contact.py',
           'rig_asset.py', 'rig_loop.py', 'rig_transition.py', 'gltf_tools.py',
           'temporal_basis.py', 'mesh_contact_feasibility.py', 'mesh_contact_guarded_trials.py', 'inspect_rig_contacts.py',
           'rig_subframe_floor.py', 'native_support_clock.py', 'rig_clip_import.py', 'strep.py')


def _run(source, draft, output, spacing=10, max_iterations=60, feasibility=False, floor_iterations=30, guarded_trials=False, _owned_output=None):
    source, draft, output = map(lambda p: Path(p).resolve(), (source, draft, output))
    if type(spacing) is not int or not 1<=spacing<=120:
        raise ValueError('Control spacing must be 1–120 frames')
    if type(max_iterations) is not int or not 1<=max_iterations<=200:
        raise ValueError('Iteration budget must be 1–200')
    if type(feasibility) is not bool:raise ValueError('Explicit feasibility choice required')
    if type(guarded_trials) is not bool or guarded_trials and not feasibility:raise ValueError('Guarded trials require explicit feasibility mode')
    if type(floor_iterations) is not int or not 1<=floor_iterations<=200:
        raise ValueError('Floor iteration budget must be 1–200')
    inputs = {str(source): sha256(source), str(draft): sha256(draft)}
    spec = read(draft)
    if inputs[str(source)] != spec['glb_sha256']: raise ValueError('Contact draft source changed')
    output.mkdir(parents=True, exist_ok=False)
    if _owned_output is not None:_owned_output['created']=True
    shutil.copyfile(source, output/'original.glb'); shutil.copyfile(draft, output/'contact-spec.json')
    for saved, original in ((output/'original.glb',source),(output/'contact-spec.json',draft)):
        if sha256(saved)!=inputs[str(original)]:raise ValueError('Mesh contact input changed while snapshotting')
    spec=read(output/'contact-spec.json');rig=RigAsset.load(output/'original.glb')
    if len(rig.document.get('animations', [])) != 1: raise ValueError('One animation required')
    before, local = baseline(rig, spec['frames'])
    fitter = MeshContactTrajectoryFitter(rig, spec, local, np.ones(spec['frames']))
    coupled = CoupledMeshContactFitter(fitter, window_basis(fitter.envelope, spacing))
    snapshot = output/'implementation'; snapshot.mkdir()
    methods = {}
    for name in METHODS:
        path = Path(__file__).with_name(name); shutil.copyfile(path, snapshot/name)
        methods[name] = sha256(path)
    save(output/'request.json', dict(at=now(), inputs=inputs, implementation=methods,
         spacing_frames=spacing, max_iterations=max_iterations, controls=coupled.shape,
         feasibility=feasibility,floor_iterations=floor_iterations if feasibility else None,
         guarded_trials=guarded_trials,
         decoded_floor_sampling_hz=120,
         objective=('Restore floor, then pursue contact feasibility with floor held hard; original energy reported only'
                    if feasibility else 'Original mesh contact/floor/edit priors and adjacent edit differences, all frames coupled'),
         extra_rotation_step_allowance_degrees=fitter.settings['rotation_step_allowance_degrees'],
         quality_approved=False))
    with threadpool_limits(limits=1):
        save(output/'numerical-runtime.json', dict(pools=threadpool_info()))
        if feasibility:
            from mesh_contact_feasibility import MeshContactFeasibility
            values,trace,summary=MeshContactFeasibility(coupled,guarded_trials).solve(output,floor_iterations,max_iterations)
        else:values, trace, summary = coupled.solve(output, max_iterations=max_iterations)
    evidence = audit(rig, spec, before, fitter.world, values, [dict(success=summary['solver_success'])])
    animated = {c['target']['node'] for c in rig.document['animations'][0]['channels']} | set(fitter.nodes)
    times, roundtrip = encode(rig, fitter.world, animated, spec['root_node'],
                              output/'candidate.glb', 'Experimental coupled mesh contact candidate')
    decoded_spec = copy.deepcopy(spec); decoded_spec['glb_sha256'] = sha256(output/'candidate.glb')
    independent = inspect(output/'candidate.glb', decoded_spec)
    subframe_floor = inspect_subframe_floor(output/'candidate.glb', spec['screen']['floor_depth_m'])
    save(output/'subframe-floor-inspection.json', subframe_floor)
    if independent['floor_frames_failed'] or independent['failed_intervals']:
        evidence['numerical_screen_passed'] = False
        evidence['flags'].append('decoded_mesh_contact_screen_failed')
    if not subframe_floor['sampled_floor_passed']:
        evidence['numerical_screen_passed'] = False
        evidence['flags'].append('decoded_subframe_floor_screen_failed')
    if summary['constraint_min'] < -1e-8:
        evidence['numerical_screen_passed'] = False; evidence['flags'].append('coupled_constraint_failed')
    np.savez_compressed(output/'fit.npz', before=before, after=fitter.world,
                        parameters=values, local_before=local, basis=coupled.basis, times_s=times)
    save(output/'optimizer-trace.json', trace); save(output/'solver.json', summary)
    save(output/'audit.json', evidence); save(output/'independent-inspection.json', independent)
    root = fitter.world[:, spec['root_node']]
    save(output/'root-motion.json', dict(space='Target pelvis world transform, Y-up metres',
         times_s=times.tolist(), positions_m=root[:, :3, 3].tolist(),
         rotations_xyzw=Rotation.from_matrix(root[:, :3, :3]).as_quat().tolist()))
    for path, digest in inputs.items():
        if sha256(path) != digest: raise ValueError('Source or draft changed during fitting')
    if sha256(output/'original.glb')!=inputs[str(source)] or sha256(output/'contact-spec.json')!=inputs[str(draft)]:
        raise ValueError('Mesh contact snapshot changed during fitting')
    for name, digest in methods.items():
        if sha256(Path(__file__).with_name(name)) != digest or sha256(snapshot/name) != digest:
            raise ValueError('Fitting implementation changed')
    result = dict(at=now(), status='complete', quality_approved=False,
                  numerical_screen_passed=evidence['numerical_screen_passed'],
                  retained_input=not evidence['numerical_screen_passed'],
                  selected_file='candidate.glb' if evidence['numerical_screen_passed'] else 'original.glb',
                  roundtrip=roundtrip, solver=summary,
                  outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file() and p.name!='pipeline.json'})
    save(output/'result.json', result)
    save(output/'pipeline.json', dict(status='complete', quality_approved=False))
    print(evidence['after'], evidence['flags'], summary, flush=True)
    return result


def run(source, draft, output, spacing=10, max_iterations=60, feasibility=False, floor_iterations=30, guarded_trials=False):
    output=Path(output).resolve();owned={}
    try:return _run(source,draft,output,spacing,max_iterations,feasibility,floor_iterations,guarded_trials,owned)
    except Exception as exc:
        if owned.get('created'):
            save(output/'failure.json',dict(at=now(),error_type=type(exc).__name__,error=str(exc),quality_approved=False))
            save(output/'pipeline.json',dict(status='failed',quality_approved=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--spacing', type=int, default=10)
    parser.add_argument('--iterations', type=int, default=60)
    parser.add_argument('--feasibility',action='store_true')
    parser.add_argument('--floor-iterations',type=int,default=30)
    parser.add_argument('--guarded-trials',action='store_true')
    args = parser.parse_args()
    from action_worker_lock import worker_lock
    with worker_lock(): run(args.source, args.spec, args.output, args.spacing, args.iterations,args.feasibility,args.floor_iterations,args.guarded_trials)
