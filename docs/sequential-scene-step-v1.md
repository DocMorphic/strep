# Retaining nonlinear scene steps without losing passing conditions

Development component, 2026-10-18. The preceding articulated trial reduced
worst overlap but lost contacts that already passed; a feasible linear model
was not a feasible motion. These changes keep that failed trial intact.

The conic minimax proposal now accepts a complete Boolean `protected_rows`
mask. Those rows remain in the complete minimax population and also receive
hard linear constraints without peak slack. A declared model-only search
reserve keeps them inside the predicted zero boundary. The original default
without protection remains supported. Every source-relative control-vector
ball remains mandatory; neither controls nor physical values are clipped.

`scripts/sequential_scene_step.py` adds `SceneStepGuard` for complete named
signed observations. Each supplied row's original physical pass boundary is
zero. A nonlinear proposal can be retained only if its control vectors stay
inside the original unit balls, every previously passing row remains
nonnegative, and the largest violation toward the declared search targets
strictly decreases. Newly passing conditions become protected after retention.
Average improvement, unchanged worst error, a lost contact of even 1e-15 or
partial/reordered row populations cannot replace those rules.

Search reserves tighten the target without changing the original boundary.
A step may pass an original physical row while still missing its interior
search target; both decisions remain visible. State owns its complete controls,
rows and reserves. Rejected steps cannot update it or rebase the edit budgets.
This guard compares caller-supplied observations; it does not prove source
binding, geometry coverage, exported motion, anatomy or release quality.

All **157 source cases** pass locally: the prior 142 plus protected conic and
nonlinear retention cases. Tests cover hard predicted contacts, preservation
of every supplied row, complete masks, tiny nonlinear regressions, newly
protected conditions, original control budgets, separate original/search
decisions, strict worst-error progress and owned state.

The same **157 cases pass on both hosted Windows and Ubuntu** at
`d306cc2435d659fb5b1b19839a423264e9b448e8`.

## Paired motion experiment

The unchanged native high-five inputs (seeds 77/88) were edited under the
previous explicit permissions: five degrees for eleven selected joints per
actor within frames 30..90, and two centimetres of root translation over the
complete 120-frame clock. Every continuation uses controls relative to those
original inputs. Neither the budgets nor the physical screens were rebased.

The twelve rows include both full-clock floor maxima, three original point
contacts, world and opposing palm normals, both tangents, and both directions
of full-mesh partner penetration at original contact frame 60. Search targets
sit 0.1 mm inside the original depth/point limits and 0.1 degree inside the
orientation limit. These are stricter optimization targets; the original
physical limits remain unchanged.

| Iteration | Tested fractions | Retained | Maximum normalized working violation |
| --- | --- | --- | --- |
| Original | None | Original | 1.716693254 |
| 1 | Full, half | Half | 1.494452875 |
| 2 | Full, half | Half | 1.387311302 |
| 3 | Full, half, quarter | No change | 1.387311302 |
| 4, smaller trust region | Full, half, quarter | No change | 1.387311302 |

Each proposal passes the predeclared directional derivative test over all
twelve rows. The first two full steps lose existing contacts; their half steps
are retained instead. All three point contacts pass after iteration two.
Later proposals lose contacts despite reducing collision error, so the guard
rejects them. Their exports repeat the retained second state exactly and do
not count as additional successful motions.

The original third worker stopped at the 600 MiB free-memory guard after
completing its linearization and derivative check. Its files remain intact.
A fresh candidate-only worker reused those pinned arrays and rechecked the
direction and source bindings, without another backward graph. It retained
the same 2 GiB process cap and 600 MiB reserve. All completed jobs have replayed
resource traces; a stopped worker is not counted as a completed iteration.

## Independent saved-file checks

A separate NumPy/mesh evaluator excludes Torch and the new solver, controls
and gradient modules. It replays the original and final retained clips for
both actors: four exports, 8,666,880 saved vertex-times, all eight skinning
influences, 36,108 triangles and 840 original metric rows per actor and
representation. The intermediate accepted first export has not received this
independent complete replay; the final retained second state has.

| Measurement | Original raw | Retained raw | Retained saved |
| --- | --- | --- | --- |
| Palm gap, 30 mm development screen | 33.282 mm | 29.535 mm | 29.535 mm |
| Deepest partner penetration at frame 60, 5 mm screen | 13.483 mm | 11.837 mm | 11.837 mm |
| Actor A maximum floor penetration, 5 mm screen | 10.430 mm | 6.283 mm | 6.283 mm |
| Actor B maximum floor penetration, 5 mm screen | 8.328 mm | 5.757 mm | 5.757 mm |

All three actual paired point contacts pass in raw and saved motion. Floor
and partner depth still fail. Source physical nonregression fails for both
actors; the original native motion ceilings also fail for actor A. No output
is adopted. These millimetre/degree screens are development diagnostics,
not calibrated realism or release thresholds.

Saved skin component error stays below 0.000651 mm, within the separate
1e-5 m serialization fidelity check. All original binary payload bytes,
284 unselected channels and 1,342 protected rotation keys remain byte-exact.
Saved maximum joint edits are 2.500279/0.925936 degrees and root shifts
4.147769/2.571226 mm, within the separately declared permissions.

Only partner collision at frame 60 was checked; the other 119 partner frames,
continuous motion, edge-only intersections, self-collision, physical forces,
action semantics, engine import and animator review remain unverified.
The default selection and qualified partial reference stay unchanged.

Evidence: `reports/sequential-scene-step-tests-v1`,
`reports/sequential-scene-correction-v1-iteration-001` through `004`,
`reports/sequential-scene-correction-v1-iteration-003-resume-v1`,
`reports/sequential-scene-replay-v1` and `reports/sequential-scene-progress-v3`.
Generated assets and detailed reports remain local and ignored.

Next strengthen the local contact model with complete contact vectors and
conic distance bounds. A linearized scalar distance creates a tangent
halfspace that permits sideways drift outside a contact sphere; exact
nonlinear retention correctly catches that failure. New proposals still
need unchanged raw/saved, motion, full-scene, engine and human gates.
The single entire-project goal remains active.
