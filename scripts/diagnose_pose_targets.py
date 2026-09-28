"""Posthoc anchor probes; not animation candidates or feasibility certificates."""
import argparse
import copy
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares, minimize
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_pose_trajectory import PoseTrajectoryFitter


def run(case, output):
    folder = ROOT/'reports/pose-trajectory-v1'/case
    if read(folder/'pipeline.json')['status'] != 'complete':
        raise ValueError('Only diagnose a completed, preserved fit')
    if output.exists():
        raise ValueError('Preserve prior diagnostic output')
    request, spec = read(folder/'request.json'), read(folder/'spec.json')
    rig = RigAsset.load(folder/'original.glb')
    with np.load(folder/'fit.npz', allow_pickle=False) as archive:
        data = {k: archive[k] for k in archive.files}
    goal = copy.deepcopy(request['joint_goal'])
    # A dimensionless diagnostic objective scales position/orientation by the
    # study screens. It intentionally omits surface, support and edit priors.
    goal['position_weight'] = 1/.005
    goal['rotation_weight'] = float(1/(np.sqrt(2)*np.radians(5)))
    fitter = PoseTrajectoryFitter(rig, spec, data['local_before'],
        {k: np.array(v) for k,v in request['targets_m'].items()},
        request['envelope'], request['supports'], [goal])
    for f, x in enumerate(data['parameters']):
        fitter.accept(f, x)
    frame, node = goal['frame'], goal['node']
    initial = fitter.values[frame].copy()
    bounds = fitter.bounds*fitter.envelope[frame]
    def pair(x):
        return fitter.goal_pair(frame, x)
    def objective(x):
        r, _ = pair(x)
        return float(r@r)
    def gradient(x):
        r, j = pair(x)
        return 2*j.T@r
    def measure(x):
        world, _ = fitter.pose(frame, x)
        p, r = world[node,:3,3], world[node,:3,:3]
        position = float(np.linalg.norm(p-goal['position_m']))
        orientation = float(np.degrees(Rotation.from_matrix(
            np.linalg.solve(np.array(goal['rotation_matrix']), r)).magnitude()))
        constraint_min = float(fitter.constraints(frame, x)[0].min())
        return dict(position_error_m=position, orientation_error_degrees=orientation,
            anchor_skin_floor_depth_m=max(0., -float(rig.vertices(world)[:,1].min())),
            neighbor_constraint_min=constraint_min,
            neighbors_feasible=constraint_min >= -1e-7,
            box_bounds_feasible=bool(np.all(np.abs(x)<=bounds+1e-9)),
            target_screen_passed=position<=.005 and orientation<=5,
            normalized_goal_cost=objective(x))
    with threadpool_limits(limits=1):
        free = least_squares(lambda x: pair(x)[0], initial,
            jac=lambda x: pair(x)[1], bounds=(-bounds,bounds),
            max_nfev=200, ftol=1e-10, xtol=1e-10, gtol=1e-10)
        fixed = minimize(objective, initial, jac=gradient, method='SLSQP',
            bounds=list(zip(-bounds,bounds)),
            constraints={'type':'ineq','fun':lambda x:fitter.constraints(frame,x)[0],
                         'jac':lambda x:fitter.constraints(frame,x)[1]},
            options={'maxiter':200,'ftol':1e-10})
    output.mkdir(parents=True)
    np.savez_compressed(output/'probes.npz', initial=initial,
                        bounds_only=free.x, fixed_neighbors=fixed.x)
    rows = {'retained_candidate':measure(initial)}
    for name, result in [('bounds_only',free),('fixed_neighbors',fixed)]:
        rows[name] = dict(measure(result.x), solver_success=bool(result.success),
                         solver_status=int(result.status), nfev=int(result.nfev))
    save(output/'diagnostic.json',dict(created_at=now(), case=case, frame=frame,
        source_hashes={name:sha256(folder/name) for name in
                      ['original.glb','fit.npz','request.json','spec.json']},
        implementation_sha256=sha256(Path(__file__)), probes=rows,
        quality_approved=False,
        scope='Posthoc local target-only optimization. Bounds-only ignores temporal constraints; fixed-neighbor probe retains them. Both omit surface/support objectives. Solver failure or a missed target does not prove global infeasibility. No probe is an approved animation candidate.'))
    print(case, rows, flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('case',choices=['jump-land','dance','get-up'])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.case,args.output)
