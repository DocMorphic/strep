"""Explain retained geometric rejections without changing fitting guards."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import read, save, sha256
from study_coupled_breadth_block import make_problem
from rig_transition import localize


def inspect(problem, values):
    p = problem
    world = p.world.copy()
    for frame in p.frames:
        world[frame] = p.fitter.pose(int(frame), values[frame])[0]
    floor = []
    for end in sorted({f+d for f in p.frames for d in [0, 1] if 1 <= f+d < len(values)}):
        half = p.evaluator.half_pose(world[end-1], world[end], int(end-1))
        depth = np.maximum(0., -p.fitter.rig.vertices(half)[:, 1])
        old = np.maximum(0., -p.reference_skin[2*end-1, :, 1])
        vertex = int(np.argmax(depth-old))
        floor.append(dict(time_frame=float(end-.5), vertex=vertex, depth_increase_m=float((depth-old)[vertex])))
    serialized = np.array([p.evaluator.pose(w) for w in world])
    anchors = []
    for frame in p.frames:
        points = p.fitter.rig.vertices(serialized[frame])
        for side, patch in p.fitter.spec['patches'].items():
            guide = p.fitter.support_guides[side]
            if guide['weights'][frame] <= 0:
                continue
            ids = patch['vertices']
            target = np.asarray(guide['anchors_xz_m'][frame])
            before = np.linalg.norm(p.reference_skin[2*frame, ids].mean(0)[[0, 2]]-target)
            after = np.linalg.norm(points[ids].mean(0)[[0, 2]]-target)
            anchors.append(dict(frame=int(frame), side=side, increase_m=float(after-before)))
    local = localize(serialized, p.fitter.rig.parents)
    delta = local[:-1, :, :3, :3].transpose(0, 1, 3, 2)@local[1:, :, :3, :3]
    angles = Rotation.from_matrix(delta.reshape(-1, 3, 3)).magnitude().reshape(len(world)-1, -1)
    peak, p95 = angles.max(0)-p.rotation_peaks, np.percentile(angles, 95, axis=0)-p.rotation_p95
    checks = dict(half_floor=all(v['depth_increase_m'] <= p.position_eps for v in floor),
                  anchors=all(v['increase_m'] <= p.position_eps for v in anchors),
                  rotation_peak=bool(np.all(peak <= 1e-6)), rotation_p95=bool(np.all(p95 <= 1e-6)))
    assert all(checks.values()) == p.geometric_guard(values), 'Explanation differs from actual guard'
    return dict(checks=checks, worst_half_floor=max(floor, key=lambda v:v['depth_increase_m']),
                worst_anchor=max(anchors, key=lambda v:v['increase_m']) if anchors else None,
                peak=dict(node=int(peak.argmax()), increase_radians=float(peak.max())),
                p95=dict(node=int(p95.argmax()), increase_radians=float(p95.max())))


def run(folder, block, output):
    if output.exists():
        raise ValueError('Preserve earlier diagnostic')
    request = read(folder/'request.json')
    solver_path = folder/f'block-{block:02d}-solver.json'
    solver = read(solver_path)
    initial_path = folder/('starting-parameters.npz' if block==1 else f'block-{block-1:02d}-parameters.npz')
    initial = np.load(initial_path)['parameters']
    problem = make_problem(folder, {**request, 'frames':request['windows'][block-1]['frames']}, initial_parameters=initial)
    x = np.asarray(solver['final_coordinates'])
    last = solver['history'][-1]
    if last['accepted']:
        raise ValueError('A stopped block is required')
    rows = []
    with threadpool_limits(limits=1):
        for attempt in last['attempts']:
            if 'proposed_delta' not in attempt:
                continue
            delta = np.asarray(attempt['proposed_delta'])
            for trial in attempt['trials']:
                values = problem.values(x+trial['fraction']*delta)
                rows.append(dict(trust=attempt['trust'], fraction=trial['fraction'], objective=trial['objective'],
                                 measured=inspect(problem, values)))
    save(output, dict(folder=str(folder), block=block, solver_sha256=sha256(solver_path), initial_sha256=sha256(initial_path),
                      implementation_sha256=sha256(__file__), rows=rows, quality_approved=False))
    print([{k:v for k,v in row.items() if k!='measured'}|row['measured'] for row in rows[-3:]])


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    parser.add_argument('block', type=int)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.folder.resolve(), args.block, args.output.resolve())
