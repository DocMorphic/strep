"""Lift explicit pose rotations into existing native editable animation curves.

Hard knot-vector balls bound native key edits. Matching poses never establishes
contact, rate, collision, engine or animation quality acceptance.
"""
import time
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from native_scene_contacts import scalar
from native_contact_pose import ContactPose
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset


def knot_balls(raw, size):
    value = np.asarray(raw, float)
    if (value.shape != (size,) or size % 3 or not np.isfinite(value).all()
            or np.max(abs(value), initial=0) > 20):
        raise ValueError('Complete finite bounded native lift coordinates required')
    vectors = value.reshape(-1, 3)
    return (vectors / np.sqrt(1 + np.sum(vectors*vectors, axis=1))[:, None]).ravel()


def local_basis(world, node, parents):
    parent = parents[node]
    local = np.linalg.solve(world[parent], world[node]) if parent >= 0 else world[node]
    basis = local[:3, :3]
    if (not np.allclose(basis @ basis.T, np.eye(3), atol=1e-8, rtol=0)
            or not np.isclose(np.linalg.det(basis), 1., atol=1e-8, rtol=0)):
        raise ValueError('Proper rigid pose bases required')
    return basis


class PoseLift:
    def __init__(self, edits, targets):
        if edits.size > 96 or not edits.size:
            raise ValueError('Choose complete native lift permissions up to 96 components')
        if not isinstance(targets, list) or not 1 <= len(targets) <= 32:
            raise ValueError('Choose 1-32 explicit pose targets')
        pairs = {(name,e['node']) for name,a in edits.actors.items() for e in a['tracks']}
        if any(e['path'] != 'rotation' for a in edits.actors.values() for e in a['tracks']):
            raise ValueError('Pose lifting requires explicitly permitted rotation tracks only')
        self.edits = edits; self.scene = edits.scene; self.size = edits.size; self.targets = []
        self.scene.check_inputs(); previous = -1.
        for declaration in targets:
            if not isinstance(declaration, tuple) or len(declaration) != 2 or not isinstance(declaration[0], ContactPose):
                raise ValueError('Each target must explicitly pair a ContactPose and its controls')
            pose, controls = declaration
            if pose.scene is not self.scene:
                raise ValueError('Pose and curve must share the exact source scene instance')
            if pose.time <= previous:
                raise ValueError('Distinct increasing pose target times required')
            previous = pose.time
            if {(e['actor'],e['node']) for e in pose.edits} != pairs:
                raise ValueError('Pose and native permissions must retain the same complete track population')
            worlds, _ = pose.worlds(controls); records = []
            for name, actor in edits.actors.items():
                if not actor['window'][0] < pose.time < actor['window'][1]:
                    raise ValueError('Pose targets must be interior to every edited actor window')
                for entry in actor['tracks']:
                    records.append(dict(actor=name, node=entry['node'], unit=entry['unit'],
                        basis=local_basis(worlds[name],entry['node'],self.scene.actors[name]['rig'].parents)))
            self.targets.append(dict(time_s=pose.time, records=records, pose_controls=np.asarray(controls,float).copy()))

    def measurements(self, worlds):
        residual = []; records = []
        for i,target in enumerate(self.targets):
            for row in target['records']:
                name,node = row['actor'],row['node']
                basis = local_basis(worlds[name][i],node,self.scene.actors[name]['rig'].parents)
                delta = Rotation.from_matrix(row['basis'].T @ basis).as_rotvec()
                residual.extend(delta / row['unit'])
                records.append(dict(time_s=target['time_s'], actor=name, node=node,
                    angular_error_degrees=float(np.rad2deg(np.linalg.norm(delta))),
                    native_change_limit_degrees=float(np.rad2deg(row['unit']))))
        return np.asarray(residual), dict(targets=records,
            maximum_angular_error_degrees=max(r['angular_error_degrees'] for r in records),
            original_selected=True, contact_conditions_checked=False, temporal_constraints_checked=False,
            full_geometry_checked=False, engine_playback_checked=False, quality_approved=False, release_approved=False)

    def measure(self, raw, *, quantized=False):
        value = knot_balls(raw,self.size); times = [t['time_s'] for t in self.targets]
        worlds = {n:self.edits.worlds(n,value,times,quantized=quantized) for n in self.edits.actors}
        return self.measurements(worlds)

    def decoded(self, files):
        if set(files) != set(self.edits.actors):
            raise ValueError('Complete independently saved actor file population required')
        worlds = {}; audits = {}; times = [t['time_s'] for t in self.targets]
        for name,path in files.items():
            index = self.scene.actors[name]['animation_index']
            audits[name] = self.edits.audit(name,path,index)
            rig = RigAsset.load(path); sampler = NativeSupportSampler(rig.document,rig.binary,index)
            worlds[name] = np.array([sampler.sample(t) for t in times])
        residual, report = self.measurements(worlds)
        report['native_edit_audits'] = audits
        report['native_payload_and_edit_limits_pass'] = all(a['passed'] for a in audits.values())
        self.scene.check_inputs()
        return residual, report


def fit(problem, *, evaluations=60, maximum_calls=3000, maximum_seconds=120.):
    if type(evaluations) is not int or not 1 <= evaluations <= 300:
        raise ValueError('Choose 1-300 explicit native lift evaluations')
    if type(maximum_calls) is not int or not 1 <= maximum_calls <= 10000:
        raise ValueError('Choose an explicit native lift measurement budget')
    maximum_seconds = scalar(maximum_seconds,1.,3600.,'native lift time budget')
    problem.scene.check_inputs(); started = time.monotonic(); history = []; best = None; best_score = None
    class BudgetExhausted(Exception): pass
    def objective(raw):
        nonlocal best,best_score
        if history and (len(history) >= maximum_calls or time.monotonic()-started >= maximum_seconds):
            raise BudgetExhausted()
        residual, report = problem.measure(raw)
        angles = np.linalg.norm(residual.reshape(-1,3),axis=1)
        score = float(angles.max()), float(residual @ residual)
        if best_score is None or score < best_score: best=raw.copy(); best_score=score
        history.append(dict(call=len(history)+1,score=list(score),raw=raw.tolist()))
        return np.r_[residual,1e-6*raw]
    try:
        result = least_squares(objective,np.zeros(problem.size),bounds=(-20.,20.),max_nfev=evaluations,
            ftol=1e-10,xtol=1e-10,gtol=1e-10)
        metadata = dict(solver_success=bool(result.success),solver_message=str(result.message),evaluations=int(result.nfev),
            evaluation_budget_exhausted=bool(result.status==0),time_or_call_budget_exhausted=False)
    except BudgetExhausted:
        metadata = dict(solver_success=False,solver_message='Explicit lift time or measurement budget exhausted',evaluations=None,
            evaluation_budget_exhausted=False,time_or_call_budget_exhausted=True)
    _,continuous = problem.measure(best); _,quantized = problem.measure(best,quantized=True)
    value = knot_balls(best,problem.size)
    problem.scene.check_inputs()
    return value,dict(**metadata,budget_exhausted=bool(metadata['evaluation_budget_exhausted'] or metadata['time_or_call_budget_exhausted']),
        elapsed_s=time.monotonic()-started,objective_calls=len(history),history=history,retained_raw=best.tolist(),
        continuous_target_report=continuous,quantized_target_report=quantized,
        maximum_knot_norm=float(np.linalg.norm(value.reshape(-1,3),axis=1).max()),
        hard_native_key_vector_bounds=True,original_selected=True,quality_approved=False,release_approved=False)
