# Complete vertex pair surface guidance

The new proposal model retains every triangle vertex-pair derivative and every original native motion/contact norm. The full saved scene produces 277,410 scalar surface rows, but its solve stops with `InsufficientProgress` and returns no correction. Independent replay confirms the complete model, and a directly checked feasible affine point rules out interpreting this status as infeasibility.

## Complete affine representation

The compact guide represented each triangle pair by `min(A dot n) - max(B dot n)`. That nonlinear expression uses all six vertices, but its finite difference can lose opposing slopes when support vertices tie. The new `scripts/native_pair_surface_model.py` expands every block into all nine fixed-axis scalar functions before differentiation. It retains block order and left-then-right vertex order, along with every other containment, object and plane witness.

Central differences use the intended continuous curve. The base gaps and native vectors are anchored to decoded stored motion, including the existing explicit Float32 component corrections. Sparse columns omit exact zeros only. Finite row and nonzero budgets reject the complete request when exceeded; no subset is returned. Existing producers and Studio jobs remain unchanged.

`scripts/native_pair_surface_conic.py` keeps every original native norm hard and encodes every surface halfspace directly in a nonnegative cone. Surface violation receives a common nonnegative minimax penalty. This representation avoids artificial three-vector surface norms. Fixed or whole-affine-box-passing native cones may be omitted only under the existing conservative arithmetic bound; no scalar surface rows are omitted.

Both the axes and the affine derivatives remain local approximations. Exported motion must still pass original native/contact conditions, cumulative reference bounds and complete geometry. A passing local solve would not certify mesh separation, realistic animation or release readiness.

## Retained scene experiment

The starting point is the previous native-passing stored-key repair. Its complete exported payload and decoded world arrays are reproduced exactly. The study preserves thirty original controls, all nine source-rate arrays, the original reference motion, original contact limits, 1,707 native times and 1,673 geometry times.

| Model population | Count |
| --- | ---: |
| Original hard native norms | 29,290 |
| Triangle records | 30,508 |
| Expanded triangle vertex pairs | 274,572 |
| Other surface witnesses | 2,838 |
| Total scalar surface rows | 277,410 |
| Actor/object queries | 3,346 |
| Surface Jacobian nonzeros | 3,326,196 |

Each actor retains its complete 152-vertex, 228-triangle generated fixture topology. The explicit proposal clearance is zero; original geometry/contact acceptance limits are unchanged. The affine control trust is 0.02, with central-difference step 0.001.

Clarabel 0.11.1 stops after thirty-nine iterations with `InsufficientProgress`. It has 1,167 active native cones, 25,259 fixed-passing native norms and 2,864 native norms proven passing over the affine trust box. All 277,410 scalar rows are encoded. No direction, additional exported probe or geometry correction is produced. The starting clip retains its previously measured geometry failure and remains unselected.

## Independent replay and feasible witness

A separate consumer imports neither new pair module. It rebuilds the complete witness population using the unchanged earlier producer, expands each scalar function independently and checks all thirty derivative columns. The maximum scalar derivative difference is `3.3306690738754696e-13`. Original native vectors/caps/scales match byte-for-byte, the full native Jacobian matches exactly, and the original stored component corrections, complete decoded starting worlds and cumulative reference measurements replay.

A separate numerical check constructs a feasible point of the saved affine model: zero control change with soft penalty `2.1382444494069452`. Every original hard native norm passes, every scalar halfspace passes with positive slack, and every control bound passes. This does not resolve geometry: a positive soft penalty permits surface violations. It establishes that the reported solver failure is not an infeasibility certificate.

Recorded nonzero scaled coefficients span approximately `5.33e-12` to `9.28`. This is a coefficient-range observation, not a measured condition number or a proven cause of nonconvergence. Further solver work must preserve the complete equivalent affine conditions and original external acceptance.

Twenty-four new software tests pass, including tied opposing slopes, complete real-fixture populations, unchanged native caps, equivalence with the earlier lifted norm formulation, a twenty-micrometre hard bound and budget rejection. Fifty-two existing focused cases also pass. The initial combined run exposed one incomplete mock fixture; correcting it and rerunning the new suites leaves all seventy-six distinct focused cases passing with zero skips. Parsed CI adds only the two new suites; hosted CI is not asserted green.

| Local receipt | SHA256 |
| --- | --- |
| `reports/pair-surface-model-probe-v1/result.json` | `32103abf42cda175fea38180520812254f87949ecb8f8097247f0f01d948ed08` |
| `reports/pair-surface-independent-v1/result.json` | `6e3f8a40582081ef85155ef92bd3d977e7e45c8ac8bcbb5ff7b0d9d20847ddc2` |
| `reports/pair-surface-feasible-witness-v1/result.json` | `54ab079531832d21c45a495c3caee3a296a645d41c2886df3ae615b6be737c40` |

All three CPU drivers exit zero with worker locks free. Inputs and current/archived numerical methods remain unchanged. Generated outputs stay outside Git. This fixture study supplies numerical proposal evidence, not production motion, anatomy, engine readback, physics, rendered/GPU quality or human cleanup review. Broad actions, rigs, objects, partners and all fourteen release evidence gates remain open. The full-project goal stays active.
