"""Bind continuing solver coordinates to the independently verified start clip."""
import numpy as np
from strep import sha256
from verify_authored_root_correction import samples


def verify_start(problem, path):
    _, world = samples(path, len(problem.initial))
    reconstructed = np.asarray([problem.evaluator.pose(w) for w in problem.world])
    error = float(np.abs(reconstructed-world[::2]).max())
    if not np.isfinite(error) or error > 1e-6:
        raise ValueError('Starting parameters do not reconstruct the verified start clip')
    return dict(starting_sha256=sha256(path), frames=len(problem.initial), max_matrix_error=error,
                tolerance=1e-6, matched=True)
