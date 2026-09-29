"""Affine conic proposals for the source-preserving root/leg experiment.

The proposal keeps vector norms intact. Serialized nonlinear checks still decide
acceptance, including half-frame floor and local rotation guards.
"""
import numpy as np
from conic_root_descent import affine_constraints


def constraints(problem, x, quantized=True):
    p = problem
    linear, jacobian, cones = affine_constraints(p, x, quantized)
    values = p.values(x)
    index = 0
    for block, frame in enumerate(p.frames):
        positions, derivative = p.fitter.surface_jacobian(int(frame), values[frame])
        if quantized:
            positions = p.fitter.rig.vertices(p.evaluator.pose(p.fitter.pose(int(frame), values[frame])[0]))
        source = p.reference_skin[2*frame]
        count = len(positions)
        linear[index:index+count] = (positions[:, 1]+np.maximum(0., -source[:, 1])+p.position_eps)/.005
        index += count+sum(p.envelope['active_frames'][frame])
        sl = slice(block*len(p.free), (block+1)*len(p.free))
        for side, ids in enumerate(p.patches):
            name = list(p.fitter.spec['patches'])[side]
            guide = p.fitter.support_guides[name]
            if guide['weights'][frame] <= 0:
                continue
            anchor = np.asarray(guide['anchors_xz_m'][frame])
            vector = positions[ids].mean(0)[[0, 2]]-anchor
            cap = np.linalg.norm(source[ids].mean(0)[[0, 2]]-anchor)+p.position_eps
            row = np.zeros((2, p.width))
            row[:, sl] = derivative[ids].mean(0)[[0, 2]][:, p.free]
            cones.append(dict(vector=vector, jacobian=row, cap=cap, scale=max(cap, .01), kind='anchor'))
        row = np.zeros((3, p.width))
        for column, free in enumerate(p.free):
            if free < 3:
                row[free, block*len(p.free)+column] = 1.
        cones.append(dict(vector=values[frame, :3]-p.initial[frame, :3], jacobian=row,
                          cap=p.radius, scale=p.radius, kind='root_radius'))
    return linear, jacobian, cones
