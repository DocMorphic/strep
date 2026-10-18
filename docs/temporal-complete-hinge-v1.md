# Complete temporal point-model solver attempt

Development evidence, 2026-10-18. The
[coordinate-boundary correction](temporal-coordinate-boundaries-v1.md) preserves
the saved Float64 model byte-for-byte. That model is then consumed by the
existing sparse conic hinge solver, with **all 6,984 rows and 216 controls**.
Unlike the earlier hard-feasibility projection, every selected point participates
in the objective. No point or control column is dropped to fit memory.

The caller keeps 499 mandatory cuts: original required conditions, currently
passing retained-raw conditions and existing mandatory point cuts. Original
control-vector balls, separate step balls and physical affine vector norms are
all present. Root offsets remain constant and retain their two-centimetre cap;
selected-joint edits retain the five-degree cap and protected frames. The
model's center is the earlier qualified point, with the latest retained pose
used as an acceptance reference, not falsely treated as a refreshed center.

The objective minimizes the sum of all positive linear deficits, with a
normalized model-peak ceiling of five. That ceiling is a partial search target,
**not** the five-millimetre physical depth screen or physical approval. Tighter
1e-8 search interiors remain explicit. A separate outer check requires original
norms, hard rows, delta boxes and the peak ceiling to pass strictly; the kernel's
raw numerical admission tolerances cannot waive physical conditions.

The existing sparse kernel first passes **77 focused local cases**, separately
from the 358 coordinate/core cases. Six complete-model searches then run:

| Normalized joint step radius | Solver status | Usable strict direction |
| ---: | --- | --- |
| 0.0625 | PrimalInfeasible | No |
| 0.125 | PrimalInfeasible | No |
| 0.25 | MaxTime | No |
| 0.5 | MaxTime | No |
| 1 | MaxTime | No |
| 2 | AlmostPrimalInfeasible | No |

Every solve retains its original 20-second solver time limit. The three time
limits and the almost-infeasible status are **inconclusive**, not verified
infeasibility or completion. The whole job
finishes normally in 139.234 seconds including admission, with sampled process
tree peak 354,439,168 bytes under its 512 MiB cap. The declared 64 MiB sparse
matrix budget and 600 MiB free-memory reserve remain unchanged. No nonlinear
motion is evaluated or selected because no strict direction is available.

The hinge formulation introduces one deficit variable per model row. Next
evaluate a compact peak-deficit formulation while preserving every point,
norm, author bound and mandatory cut; do not obtain a faster result by reducing
the physical population or relabeling a time limit. Existing motion failures,
full-system release conditions and genuine human review remain open.

Local evidence: `reports/temporal-sparse-kernel-tests-v1` and
`reports/temporal-complete-hinge-v1`. Source clips, exports, model weights,
training data, Studio selection and the qualified reference remain unchanged.
