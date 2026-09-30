# Paired correction limits and curve refinement

The published scene correction still leaves 37 of 126 sampled times over the 5 mm screen. The next investigation uses its immutable source linearization to distinguish restricted step size, motion limits, surface protections and curve flexibility. No production acceptance limit has changed.

## Matched constraint comparisons

The baseline has 72 controls, 4,287 surface rows and 15,087 norm rows. Its source peak is 22.568796 mm. Both diagnostic profiles reproduce the saved original solver controls exactly. The table contains **affine predictions**, not measured candidate mesh penetration.

| Diagnostic change | Predicted peak, mm |
| --- | ---: |
| Original 0.1-degree trust radius | 22.561182 |
| Double trust radius | 22.552135 |
| Tenfold trust radius | 22.525636 |
| Omit speed limits | 22.560709 |
| Omit acceleration limits | 22.560358 |
| Omit both motion limits | 22.560436 |
| Omit retained surface-distance norms | 22.561051 |
| Omit motion and surface-distance norms | 22.560317 |
| Reduce regularization from 1e-4 to 1e-8 | 22.560042 |
| Replace per-time scalar caps with the original global peak | 22.561182 |
| Replace scalar caps and omit surface-distance norms | 22.423893 |
| Retain only trust/edit norms and the global scalar cap | 22.366326 |

The last two variants deliberately remove protection against worsening individual times. Their maximum predicted violation of the original scalar depth caps is **0.665533 mm** and **1.102718 mm**, respectively. They also violate 14 and 19 original surface-distance norms. The last variant additionally violates 31 speed and 96 acceleration constraints. These diagnostic relaxations are not usable corrections.

The scalar and full-vector surface caps overlap: removing only one leaves the other active. Together they explain much more of the measured restriction than the motion limits alone. The data does not establish a globally optimal nonlinear solution or prove that the existing joint/window choices can clear the interaction.

The diagnostic also computes an optimistic affine lower bound from independent three-component control balls. For each surface row it allows that row its own best direction and ignores all competing constraints. The maximum remaining row depth is a necessary peak floor, not an attainable motion. At the original radius this floor is 21.582429 mm, from a different row than the deepest source collision. Even that optimistic one-step calculation is far above 5 mm.

## More flexible curves with the same safety limits

The refinement inserts a midpoint into every original knot interval: five knots become nine, and 72 controls become 168. Every original curve embeds into the refined basis by interpolation. Native editable keys, protected contact poses, original-reference budgets, sample times, surface witnesses and source values remain unchanged.

Crucially, **motion limits keep the original knot-span maxima and row membership**. Rebuilding those limits around the denser knots would change the comparison. The implementation retains the original rate policy while differentiating the new motion basis.

The real fixture reproduces an embedded coarse curve to within 6.94e-18 in decoded world matrices. All original source vectors, radii and kinds match. Projected derivative discrepancies are recorded separately; their maximum across positional rate derivatives is 3.997e-5, and their effect at the declared trust radius stays below the diagnostic tolerance. A separate refined-direction surface derivative check differs by 1.64e-12 metres.

With all original constraints, the refined solve predicts a peak of **22.534817 mm**, a 0.033980 mm improvement versus 0.007615 mm for the coarse solve. That is about 4.46 times the predicted improvement, still small in absolute terms. The objective also penalizes control magnitude, and adding controls changes that penalty's parameterization; this is evidence of a useful feasible direction, not a proof of optimal benefit from refinement.

## Actual export screening

Five fractions of the refined direction are exported and preserved. A separate all-joint rate replay checks **191,730 observations** against the original knot-span limits and agrees with the fitter's failure counts.

| Fraction | Actor A rate failures | Actor B rate failures | Preliminary checks |
| --- | ---: | ---: | --- |
| 1 | 1 | 2 | Fail; retained surface caps also fail |
| 1/2 | 0 | 1 | Fail |
| 1/4 | 0 | 0 | Pass |
| 1/8 | 26 | 2 | Fail |
| 1/16 | 0 | 0 | Pass |

The full step exceeds a retained surface-distance allowance by 2.130 micrometres, beyond the unchanged 1-micrometre comparison tolerance. The quarter step has no positive motion-cap excess and retains protected decoded poses exactly; maximum joint edits are 0.023408 degrees for A and 0.021292 degrees for B. Every attempted export keeps the protected poses.

Passing is not monotonic with the step fraction after native quaternion serialization and interpolation. This observation requires checking each export; it does not by itself attribute every discrepancy to rounding. The quarter-step pair is the next candidate for **complete fresh mesh/floor queries and engine import**, neither of which this export screen performs. It has not replaced the published Studio comparison.

## Reproduction and limits

```powershell
.venv\Scripts\python.exe scripts/diagnose_scene_pair_limits.py reports/scene-pair-fit-v2 reports/<new-norm-diagnostic>
.venv\Scripts\python.exe scripts/diagnose_scene_pair_limits.py reports/scene-pair-fit-v2 reports/<new-cap-diagnostic> --profile surface-caps
.venv\Scripts\python.exe scripts/diagnose_scene_pair_refinement.py reports/scene-pair-fit-v2 reports/<new-refinement>
.venv\Scripts\python.exe scripts/audit_scene_pair_refinement.py reports/<new-refinement> reports/<new-export-audit>
```

Local records are `scene-pair-limits-v1`, `scene-pair-limits-v2`, `scene-pair-refinement-v1` and `scene-pair-refinement-export-v1`, under ignored `reports/`. Each study binds inputs and method snapshots and preserves previous results. Reproduction requires the licensed development fixture and pinned local solver; these payloads are not in the public source repository.

Seventeen new model-free tests cover constraint grouping, omitted-limit reporting, trust bounds, tampered study rejection, nested interpolation and preservation of native protected keys. Together with four existing constraint tests, 21 focused checks pass. The new tests join Windows/Linux CI.

These studies do not broaden action or rig coverage, certify angular rates/forces/balance, establish naturalness, or approve any release capability. No held-out prompt, new learned model or human review is involved.
