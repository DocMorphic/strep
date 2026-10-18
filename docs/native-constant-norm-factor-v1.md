# Exact constant constraints in a bounded solver model

The complete 49-control temporal census requires **68,900** affine norm
constraints, beyond the existing solver's 65,536-cone limit. No solver started
from that oversized population. The rejected first census is preserved, and a
second completed census records the full counts and failed admission explicitly.

| Planned population | Norms |
| --- | ---: |
| Original native controls | 5,400 |
| Original observation pose bands | 23,880 |
| Affected exact-native-clock pose bands | 1,990 |
| Passing affected/required world guards | 33,594 |
| Original prop native and 2,017-time translation/rotation bounds | 4,036 |
| Total | 68,900 |

Every one of the 6,050 failed world rows remains an objective, including those
outside the temporal support. All 72 protected repairs remain explicit guards.
Of the original 383,617 world conditions, 35,615 are affected or required;
348,002 have exact endpoint-zero support. All 23,880 original observation pose
bands and all 35,504 original pair rows occur outside the profile support.
Their sampled inputs are structurally invariant in this search subspace. That
does not prove new collision clearance or permit skipping nonlinear postchecks.

`scripts/native_constant_norm_factor.py` supplies an equivalent representation
of a complete **affine** norm system. Every nonconstant cone is retained.
For exact constant cones, `norm(v + J*d) - r` is independent of `d` because
every coefficient in its complete three-row Jacobian is exactly zero. Their
conjunction is represented by the cone with the largest original-unit norm
excess. Its original vector and radius are copied unchanged. A failing constant
therefore remains failing; it cannot be hidden among passing constants.

All original rows map to the retained cones, and the representative's original
index and maximum constant excess remain explicit. Exact duplicate coefficients
are summed before detecting constants. Tiny nonzero coefficients, including a
coefficient in column 768, are retained. There is no normalization, near-zero
cutoff, physical tolerance change or selection by motion error. The helper has
an explicit 131,072-input-norm and 64 MiB working bound; the solver's 65,536-cone,
768-column and matrix/process bounds remain unchanged. Whole inputs are rejected
when admission fails.

This equivalence applies only to the supplied local affine system. A zero
Jacobian is not a proof of nonlinear invariance. The caller must retain the
complete unfactored vectors/matrix/radii, verify every original norm at the
returned direction, then run the original raw/saved motion, contact and changed
scene checks. Neither a factored feasible point nor a solver status approves an
animation or establishes nonlinear feasibility/infeasibility.

## Source verification

The final local run passes **97 tests**: 20 new cases and 77 existing sparse
solver regressions. Cases cover complete row maps, both sparse layouts, exact
duplicate cancellation, tiny nonzero final-column coefficients, failed final
constants, unchanged original inputs/radii, invalid sparse storage and whole
budget rejection. A real backend solve uses the factored form of 70,000 original
cones, then rechecks all 70,000 original inequalities. Other fixtures compare
the full and factored predicates over multiple directions.

The initial run retains a failed test-harness lookup: it expected a dictionary
where the existing solver returns a tuple. The corrected run changes no motion
or solver tolerance, and also covers explicit rejection of a one-dimensional
sparse array. Final recorded resource replay: 33.672 s, 152,432,640-byte peak
process tree RSS and 35 observations. These model-free source fixtures are not
motion-quality, engine, human-review or release evidence.
