"""Between-key floor rows for conic proposals; serialized acceptance stays strict."""
import time
import numpy as np
from scipy.spatial.transform import Rotation
from serialized_pose import SerializedPose
from rig_transition import localize
from coupled_breadth_conic import constraints as key_constraints


class ContinuousPose(SerializedPose):
    """Continuous TRS surrogate for derivatives before float32 serialization."""
    def channels(self, world):
        local = localize(np.asarray(world)[None], self.parents)[0]
        return local[self.animated, :3, 3], Rotation.from_matrix(local[self.animated, :3, :3]).as_quat()


def setup(problem, x):
    p = problem
    values = p.values(x)
    world = p.world.copy()
    for frame in p.frames:
        world[frame] = p.fitter.pose(int(frame), values[frame])[0]
    edges = sorted({int(f+d) for f in p.frames for d in [0, 1] if 1 <= f+d < len(values)})
    smooth = ContinuousPose(p.fitter.rig, p.evaluator.animated, p.root, len(values), sample_clock=p.evaluator.sample_clock)
    return values, world, edges, smooth


def half_floor_values(problem, x, quantized=True):
    p = problem
    _, world, edges, smooth = setup(p, x)
    evaluator = p.evaluator if quantized else smooth
    positions = np.asarray([p.fitter.rig.vertices(evaluator.half_pose(world[e-1], world[e], e-1))[:, 1] for e in edges])
    depth = np.maximum(0., -p.reference_skin[np.asarray(edges)*2-1, :, 1])
    return ((positions+depth+p.position_eps)/.005).ravel()


def half_floor_rows(problem, x, quantized=True, difference_step=1e-5):
    if not np.isfinite(difference_step) or difference_step <= 0:
        raise ValueError('Positive finite derivative step required')
    p = problem
    if not np.isfinite(x).all():
        raise ValueError('Finite coordinates required')
    values, world, edges, smooth = setup(p, x)
    evaluator = p.evaluator if quantized else smooth
    positions = np.asarray([p.fitter.rig.vertices(evaluator.half_pose(world[e-1], world[e], e-1))[:, 1] for e in edges])
    depth = np.maximum(0., -p.reference_skin[np.asarray(edges)*2-1, :, 1])
    jacobian = np.zeros((*positions.shape, p.width))
    # A key influences only the two neighboring half frames. Differentiate the
    # continuous pre-serialization model; margins above use actual saved poses.
    for block, frame in enumerate(p.frames):
        neighbors = [(i, e) for i, e in enumerate(edges) if frame in (e-1, e)]
        for column, free in enumerate(p.free):
            perturbed = []
            for sign in [-1., 1.]:
                coordinates = values[frame].copy()
                coordinates[free] += sign*difference_step
                pose = p.fitter.pose(int(frame), coordinates)[0]
                rows = []
                for _, edge in neighbors:
                    left = pose if frame==edge-1 else world[edge-1]
                    right = pose if frame==edge else world[edge]
                    rows.append(p.fitter.rig.vertices(smooth.half_pose(left, right, edge-1))[:, 1])
                perturbed.append(rows)
            derivative = (np.asarray(perturbed[1])-np.asarray(perturbed[0]))/(2*difference_step*.005)
            for row, (index, _) in zip(derivative, neighbors):
                jacobian[index, :, block*len(p.free)+column] = row
    margins = ((positions+depth+p.position_eps)/.005).ravel()
    if not np.isfinite(jacobian).all() or not np.isfinite(margins).all():
        raise ValueError('Nonfinite half-floor model')
    return margins, jacobian.reshape(-1, p.width), dict(edges=edges, rows=len(margins), difference_step=difference_step,
        derivative_model='Continuous TRS before serialization; central differences; same sample clock as actual guard')


class HalfFloorConstraints:
    def __init__(self, base_builder=key_constraints, difference_step=1e-5):
        self.base_builder = base_builder
        self.difference_step = difference_step
        self.problem = None
        self.x = None
        self.cached = None
        self.builds = []

    def __call__(self, problem, x, quantized=True):
        if quantized and self.problem is problem and self.x is not None and np.array_equal(x, self.x):
            return self.cached
        started = time.perf_counter()
        c, j, cones = self.base_builder(problem, x, quantized)
        hc, hj, record = half_floor_rows(problem, x, quantized, self.difference_step)
        result = (np.r_[c, hc], np.vstack([j, hj]), cones)
        record.update(elapsed_s=time.perf_counter()-started)
        self.builds.append(record)
        if quantized:
            self.problem, self.x, self.cached = problem, np.asarray(x).copy(), result
        return result
