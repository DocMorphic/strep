# Refreshed local margins and a second bounded continuation

Refreshing the fitting margins at the stalled pose gets the coupled high-five correction past its [previous exhausted line search](coupled-pair-continuation-v1.md). The resumed run accepts all 12 permitted additional steps and stops at its step budget. Progress becomes small near the end, and a fresh closest-feature diagnostic finds that several original surface bindings are now substantially conservative. This is further local progress, not a cleared animation or convergence claim.

## Updated margins without changed acceptance limits

The calibration uses the five retained rejected exports from the previous ninth direction. For every motion row it takes the larger of the old margin and twice the largest observed positive exported-minus-affine norm error. No margin is reduced; native edit margins remain zero and an overlarge margin cannot be silently clipped to a cap.

Margins increase in **954 speed rows and 1,159 acceleration rows**. Their overall maxima remain 0.000199321 m/s and 0.017740950 m/s2 respectively: the change is distributed among rows whose original margins were too small. The source motion caps, original 5-degree edit budget, existing export tolerance, per-time depth allowances and final numerical comparison tolerances remain unchanged.

An independent arithmetic replay checks all **5,434 rows and 26,730 motion observations**, reproducing the updated margins exactly. The calibration is bound to the exact cumulative control values and local linearization at the exhausted direction. At the first retry, every regenerated linearization array must match that saved center exactly. The margins remain empirical estimates, not certified error bounds for future directions.

## Resume preserves the original reference

The checkpoint loader distinguishes the latest accepted controls from the original reference clips and cap layout. Resuming from a continuation preserves the original full-vector study as the reference; it does not turn the latest candidate into a new zero-edit baseline. The runner reconstructs the starting GLBs byte-for-byte before taking another step. Each candidate still receives complete decoded motion, original edit, finger, protected-key and retained-surface checks.

The run keeps the same 12-step, 900-second resource guard, 0.2-degree knot trust radius, line factors and minimum retained-distance improvement as before. The new history verifier supports cumulative checkpoints and verifies each increment against the original cap arrays.

## Completed continuation and engine checks

The resumed run finishes in **126.81 seconds**, with **12 accepted steps from 17 attempts**. The first four steps pass at full size; steps five through nine require a half step; the last three pass at full size. Five rejected full steps remain preserved. Termination is `maximum_steps`, not convergence.

The worst retained fixed-barycentric distance decreases from **22.804379 to 22.586554 mm**, a reduction of 0.217825 mm. This is distinct from actual nearest-surface penetration. Final original-reference edits are 5.000050470 and 5.000049264 degrees, within the unchanged 0.0001-degree export allowance around the 5-degree limit.

The history accounts for **66,528 independently replayed motion peak values**. A separate final replay checks another 3,696 values with discrepancy at most 5.69e-14, reconstructs the final clips byte-for-byte and verifies all 3,045 full CPU-skin witness vectors within 1.12e-15 m. Fresh Godot import validation passes **600 actor-frame observations**, with maximum position error below 4.16e-7 m and original rig, duration and nonlooping import behavior preserved.

## Complete sampled mesh result: lower peak, one lost clearance

The completed final audit covers all **57 quarter-frame times and 114 directional queries** across frames 63-77, considering all 18,056 vertices per actor with conservative broadphase filtering. Original source queries are reused only with exact identity, placement and sample-clock bindings.

| Measure | Fixed original source | Resume start | Final candidate |
| --- | ---: | ---: | ---: |
| Maximum partner penetration | 23.556264 mm | 22.753871 mm | 22.503084 mm |
| Times exceeding 5 mm | 25/57 | 24/57 | 25/57 |

The worst depth improves by another **0.250787 mm**, and no sampled depth or floor value increases against the fixed original source. Relative to the resume start, however, 18 times have depth increases above 1 micrometre, up to 1.372928 mm. **Frame 69 loses its clearance pass**, increasing from 3.939619 to 5.124175 mm. Original-source allowances permit that backslide because the original depth at that time was already above 5 mm. A lower maximum therefore does not establish an unqualified improvement over the preceding pair.

The event retains 21/17 regional vertices within 3 mm, 5.199358-degree opposing-normal error and 1.896658 mm penetration. Inherited full-clip floor failures remain. The candidate is **not promoted**; both it and the preceding pair remain available as measured research alternatives. The next policy should also preserve already-cleared times explicitly, rather than assuming fixed original allowances protect every intermediate success. Any new stricter policy must be reported as a new comparison, not applied retroactively to relabel this run.

## Why refreshing surface bindings is the next comparison

The retained-distance improvement per full step falls from roughly 50 micrometres early in the run to about 3 micrometres at the end. Ten control knots reach the trust radius in the first proposal; only one does so in the final proposal. These observations do not prove a cause or infeasibility, but do not justify simply increasing iteration or step budgets.

A declared diagnostic queries the 12 largest retained fixed-point distances plus the six tightest retained constraints, deduplicated to **15 vertices**. Fresh queries against the complete target meshes find **nine closest-triangle changes**, target-point drift up to **41.447 mm**, and fixed-distance overestimation of actual penetration up to **2.677668 mm**.

For example, actor B vertex 14523 at frame 67.75 has a retained distance of 21.396325 mm against a 21.395991 mm cap, while its actual penetration is 18.718658 mm. Its nearest triangle changed from 8305 to 8338. The old bound remains conservative but is almost active despite substantial actual clearance relative to that time's allowance.

Next compare freshly selected closest-surface bindings, retaining the original caps as upper ceilings and explicitly protecting already-cleared times. Keep the cumulative edit origin and decoded-motion gates unchanged. Merely changing a binding can lower a conservative distance without changing the animation; that must not be counted as motion improvement. Actual exported signed-distance checks and the complete sampled geometry audit remain required. The 15-vertex diagnostic is not proof that binding conservatism is the only remaining limitation.

## Evidence, tests and reproduction

Local evidence folders under ignored `reports/` are `coupled-pair-local-reserve-v1`, `coupled-pair-local-reserve-review-v1`, `coupled-pair-local-continuation-v1`, `coupled-pair-local-continuation-review-v1`, `coupled-pair-local-continuation-engine-v1`, `coupled-pair-local-continuation-geometry-v1` and `coupled-pair-local-bindings-v1`. Source, rejected trials, updated margin arrays, original references and implementation snapshots remain preserved.

**50 focused tests pass.** New tests cover conservative margin updates, unchanged native edit margins, selected checkpoint fractions, preservation of the original reference across repeated resumes and rejection of a modified reference. They join model-free Windows/Linux CI. Licensed assets, weights, generated GLBs and bulky reports remain excluded from GitHub.

```powershell
.venv\Scripts\python.exe scripts/refresh_coupled_continuation_reserve.py reports/coupled-pair-continuation-v1 reports/coupled-pair-continuation-limits-v1 reports/<new-reserve>
.venv\Scripts\python.exe scripts/verify_coupled_margin_refresh.py reports/<new-reserve> reports/coupled-pair-continuation-limits-v1 reports/<new-reserve-review>
.venv\Scripts\python.exe scripts/study_coupled_pair_continuation.py reports/coupled-pair-continuation-v1 reports/coupled-pair-continuation-geometry-v1 reports/paired-approach-witnesses-v1 reports/<new-continuation> --reserve reports/<new-reserve>
.venv\Scripts\python.exe scripts/verify_coupled_continuation.py reports/<new-continuation> reports/paired-approach-witnesses-v1 reports/<new-review>
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/<new-continuation> --output reports/<new-engine>
.venv\Scripts\python.exe scripts/audit_coupled_pair_geometry.py reports/<new-continuation> reports/paired-approach-witnesses-v1 reports/<new-engine> reports/<new-geometry>
.venv\Scripts\python.exe scripts/audit_coupled_surface_bindings.py reports/<new-continuation> reports/paired-approach-witnesses-v1 reports/<new-bindings-review>
```

Use fresh output paths. Reproduction requires the separately acquired licensed fixture, locally pinned solver and preceding evidence. No held-out generation, learned checkpoint, rendered or human review, or release approval is claimed. All fourteen release capabilities remain unapproved.
