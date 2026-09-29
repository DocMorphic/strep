"""Measure collision-gradient coverage at a retained candidate pose.

Uses zero multipliers to compare the initial merits at that pose. This is not
the final fitted Lagrangian gradient or a proof of optimizer convergence.
"""
import argparse
from pathlib import Path
import numpy as np
import torch
from strep import read, save, sha256
from build_soma_preview import ASSET
from floor_contact import Surface
from scene_solver_context import context_primitives
from support_contact_v8 import (torch_primitive_clearance_violation,
                                object_constraint_residuals, object_constraint_merit)


def run(study, output):
    if output.exists():
        raise ValueError('Preserve earlier diagnostic')
    result = read(study / 'result.json')
    if result['status'] != 'complete':
        raise ValueError('Completed candidate required')
    for name, key in [('motion.npz', 'candidate_sha256'), ('recipe.json', 'recipe_sha256'),
                      ('protocol.json', 'protocol_sha256')]:
        if sha256(study / name) != result[key]:
            raise ValueError('Retained artifact changed')
    protocol, recipe = read(study / 'protocol.json'), read(study / 'recipe.json')
    for path, digest in protocol['inputs'].items():
        if sha256(path) != digest:
            raise ValueError('Original input changed')
    torch.set_num_threads(2)
    skin = dict(np.load(ASSET, allow_pickle=False))
    motion = dict(np.load(study / 'motion.npz', allow_pickle=False))
    surface = Surface(skin)
    v = torch.tensor(np.stack([surface.vertices(r, p) for r, p in
                     zip(motion['global_rot_mats'], motion['posed_joints'])]),
                     dtype=torch.float64, requires_grad=True)
    rows = []
    for geometry, obj in context_primitives(recipe['scene_context']):
        g = torch_primitive_clearance_violation(v, v.new_tensor(obj['positions_m']),
              v.new_tensor(obj['rotations']), geometry, recipe['config']['object_clearance_m'])
        modes = {}
        for mode in ['maximum', 'per_vertex']:
            residuals = object_constraint_residuals(g, mode)
            loss = object_constraint_merit(residuals, torch.zeros_like(residuals),
                                          2 * recipe['config']['object_collision_weight'], mode)
            grad = torch.autograd.grad(loss, v, retain_graph=True)[0]
            modes[mode] = dict(merit=float(loss.detach()),
                nonzero_vertex_gradients_per_frame=(grad.abs().sum(2) > 0).sum(1).tolist())
        rows.append(dict(object=obj['id'], shape=geometry.shape,
            violating_vertices_per_frame=(g > 0).sum(1).tolist(),
            maximum_violation_m=g.amax(1).detach().tolist(), modes=modes))
    save(output, dict(study=str(study), result_sha256=sha256(study / 'result.json'),
         implementation_sha256=sha256(__file__), solver_sha256=sha256(Path(__file__).with_name('support_contact_v8.py')),
         rows=rows, quality_approved=False, scope=__doc__.strip()))
    print(rows)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('study', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    run(a.study.resolve(), a.output.resolve())
