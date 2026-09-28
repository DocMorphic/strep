# Isolated grasp-pose feasibility diagnostics

The six-stage V13 clip still misses both strict 5 mm grip targets, with the worst errors at frame 60. These diagnostics remove temporal coupling and inspect that single frame. They preserve the original joint rotation-norm limits, root lift range, object geometry, grip points and normal targets. All 18,056 skin vertices are checked. Inferred support tracking, temporal smoothness, balance, self-collision and anatomical validity are outside this pose-only problem.

The existing paired-hand prototype uses different arm limits and component boxes, so it was not treated as a matched feasibility test. The new diagnostic reuses the clip solver's rotation, skeleton and skinning math. Its seed reconstructs V13 within 0.12 micrometres. Final poses are reconstructed separately with SciPy rotations and NumPy skinning; no optimizer success flag is accepted as a geometry pass.

## Sequential diagnostics

These variants were chosen sequentially from observed failures; they are not a preplanned one-factor study or independent action samples. No model was trained and no animation was promoted.

| Method / selected pose | Left grip error | Right grip error | Sphere penetration | Joint/root bounds | Full pose witness |
| --- | --- | --- | --- | --- | --- |
| V13 frame-60 seed | 19.949 mm | 26.077 mm | 1.623 mm | Pass | No |
| SLSQP, explicit nonlinear norm constraints | 643.368 mm | 1,047.963 mm | 0 mm | Fail | No |
| Hard bounded coordinates, exact maxima | 14.832 mm | 17.799 mm | 9.225 mm | Pass | No |
| Hard bounds, smooth conservative maxima | 13.197 mm | 17.024 mm | 9.987 mm | Pass | No |
| Same smooth problem, Jacobian scaling | 19.324 mm | 24.786 mm | 11.524 mm | Pass | No |
| Points only; geometry omitted from optimization | 5.000 mm | 5.000 mm | 26.666 mm | Pass | No |
| Points and geometry; normals omitted from optimization | 13.197 mm | 17.024 mm | 9.987 mm | Pass | No |
| Finger-only changes at point-reachable body pose | 5.000 mm | 5.000 mm | 25.786 mm | Pass | No |

The SLSQP attempt was stopped by its 240-second callback guard at 241.2 seconds. Its final pose also penetrates the floor by 355 mm and exceeds rotation-norm budgets; it is retained solely as a rejected diagnostic. Component clipping was not mistaken for a valid norm bound.

The bounded variants use the existing smooth rotation-ball map in physical-angle coordinates. All visited rotations stay within their budgets, and root lift stays within the original interval. The exact-max solve stopped after 43 evaluations; the smooth solve used its 300-evaluation limit; Jacobian scaling stopped after 219 evaluations. Their optimizer termination messages are not evidence of contact feasibility. The selected bounded candidate minimizes the maximum normalized violation among visited points, then the squared violation sum; the final solver candidate is retained separately.

For smoothing, `tau * logsumexp(g / tau)` with `tau=0.0001 m` upper-bounds the worst geometry violation. This makes the optimization surrogate conservative; exact final geometry gates remain unchanged. Directional derivatives of all smoothed geometric constraints agree with finite differences to less than 4e-8 in normalized units. The independent float32-pose audit allows only numerical reconstruction tolerances (1 micrometre for geometry and 0.0001 degrees for normals), not millimetre-scale relaxation of quality targets.

The points-only case establishes that the two requested grip points are reachable within the original edit limits. Its normals also happen to pass, but its 26.666 mm overlap makes it unusable. Removing normal constraints from the geometry-aware solve reproduces the earlier stalled compromise to numerical precision. Neither result proves the full pose problem infeasible; they locate the unresolved tradeoff in simultaneous grip and hand clearance.

## Conditional finger-only obstruction

The finger-only test freezes every body rotation and root translation at the point-reachable pose. A separate analytic displacement bound shows that finger edits alone cannot fix this particular pose under the existing budgets. This conclusion does not rely on local optimizer failure.

For a vertex influenced by bone `k`, its distance from ancestor joint `j` is at most the sum of intervening rigid bone lengths plus the length of its bind-space component relative to bone `k`. Changing joint `j` by at most angle `a` moves that component by at most `2*sin(a/2)` times this distance. Summing these bounds over edited ancestors and all eight positive skin weights bounds the total vertex displacement. The angular distance from the seed to any allowed correction is at most the seed edit norm plus the original edit limit, capped at pi. Body/root transforms are held fixed throughout this argument.

Vertex 11784 is 98.720% weighted to RightHandPinky1 and 1.280% to RightHandPinky2. At the point-reachable seed it is 22.223 mm inside the sphere. The conservative total finger displacement bound is 7.679 mm. Since sphere signed distance is 1-Lipschitz, even its best possible signed distance remains at most -14.541 mm, including a 2-micrometre numerical allowance. Thus at least 14.541 mm penetration remains in the recorded rigid-bone/LBS model when only those fingers change. This fails even the looser 10 mm penetration screen, as well as the solver's requested 2 mm outward clearance.

The conclusion is restricted to this frozen body pose and these finger budgets. It does not rule out a different wrist/body pose, different authored grip or a full jointly optimized animation. An earlier exact-zero-influence check found no obstruction and is retained as inconclusive. The finite-displacement bound is what supplies the conditional obstruction.

Tests cover a mixed-weight articulated chain and an exactly tight single-hinge endpoint case. An additional 100 seeded finger configurations on the actual asset all obey the bound; random sampling supplements the analytic argument and does not replace it. The maximum observed vertex displacement was 6.892 mm, below the 7.679 mm bound.

## Reproduction and next work

`grasp_pose_witness.py` runs the explicit-constraint diagnostic. `grasp_pose_witness_bounded.py` supports conservative smoothing, optional Jacobian scaling and explicitly labeled constraint relaxations. Its default uses every original constraint, and its final audit always checks the full targets even for a relaxed solve. `grasp_finger_pose_witness.py` freezes a supplied reachable body pose. `certify_finger_pose_clearance.py` records the restricted displacement certificate. Output directories are immutable and contain inputs, source snapshots, parameter histories and independent pose results.

```powershell
.venv\Scripts\python.exe scripts/grasp_pose_witness_bounded.py reports/sphere-floor-fit-v13 reports/new-pose-diagnostic --frame 60 --smooth-max-m 0.0001
.venv\Scripts\python.exe scripts/certify_finger_pose_clearance.py reports/sphere-floor-fit-v13 reports/grasp-pose-reachability-points-v1 reports/new-finger-certificate
```

Local reports are `grasp-pose-witness-v1`, `grasp-pose-witness-bounded-v1` through `v3`, `grasp-pose-reachability-points-v1`, `grasp-pose-reachability-geometry-v1`, `grasp-finger-pose-witness-v1`, `grasp-finger-clearance-certificate-v1`, and `grasp-pose-feasibility-integration-v1` under `reports/`. Seven focused tests pass. These are single poses, not engine-ready animation clips; no new engine or human-review approval is claimed.

Next work should coordinate wrist/body placement with finger clearance while preserving grip constraints, rather than attaching an independent finger cleanup pass to the point-only solution. Inspect the existing elastic-hand and feasible-descent machinery before adding another solver. All 14 release capabilities remain unapproved, and the broader action/rig/object/partner evaluation remains required.
