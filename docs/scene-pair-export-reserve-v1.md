# Export rounding explains the remaining motion failures

An empirical proposal margin produces a full-step candidate that passes the unchanged positional and angular limits after float32 export. Independent quaternion replay and Godot import also pass. Full sampled mesh validation is still running; no candidate is published or approved for release.

## Diagnosis

`diagnose_scene_export_rates.py` reconstructs all ten exports from the five failed [expanded-window attempts](scene-pair-expanded-fit-v1.md). It holds the row population and original caps fixed while comparing source, zero edit, affine prediction, nonlinear unrounded motion, rounded keys through the batch sampler, and final scalar GLB decoding.

| Fraction | Affine failures | Unrounded nonlinear failures | Rounded-key failures | Decoded failures |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0 | 5 | 9 | 9 |
| 1/2 | 0 | 0 | 6 | 6 |
| 1/4 | 0 | 0 | 5 | 5 |
| 1/8 | 0 | 0 | 8 | 8 |
| 1/16 | 0 | 0 | 8 | 8 |

Counts combine both actors and positional/angular metrics. The final decoder and rounded batch motion agree exactly in these observations. The largest world-matrix difference from rounding is 1.137701e-7. Small transform differences matter to strict finite-difference limits: the largest angular-acceleration vector change from rounding is 0.000720688 rad/s², and positional acceleration changes by up to 0.000350700 m/s². This establishes the source of these numerical failures; it does not establish a perceptual defect.

The zero edit matches the source in the measured motion rows. Four fractions pass before key rounding and fail afterward. Repeatedly halving a step therefore cannot be assumed to solve the problem.

## Proposal margins

`study_scene_pair_export_reserve.py` computes a separate margin for every motion row: twice the largest positive decoded-minus-predicted norm discrepancy among the five original attempts. It subtracts this margin from the proposal radius, rejecting a margin larger than its cap rather than clipping it. Edit budgets, original acceptance limits, surface constraints and trust limits remain unchanged. These are empirical margins for a new proposal, not certified error bounds.

| Constraint | Maximum subtracted proposal margin |
| --- | ---: |
| Positional speed | 0.0000123518 m/s |
| Positional acceleration | 0.000729690 m/s² |
| Angular speed | 0.0000244176 rad/s |
| Angular acceleration | 0.002334061 rad/s² |
| Original edit budget | 0 |

The new solve reports Solved after 46 iterations and 18.73 seconds. It passes affine hard checks and predicts 22.554845 mm peak depth. This remains a prediction until the candidate's geometry pass finishes.

| New fraction | Positional failures | Angular failures |
| --- | ---: | ---: |
| 1 | 0 | 0 |
| 1/2 | 2 | 1 |
| 1/4 | 0 | 4 |
| 1/8 | 5 | 7 |
| 1/16 | 6 | 3 |

The full step also passes retained-surface checks, quaternion preservation and original edit-budget checks. Independent all-joint positional replay covers 45,122 observations. A separate per-joint quaternion-composition implementation covers 45,122 angular observations, matches the saved matrix-delta reports and finds no limit exceedances. It checks finite proper rotations, uniform times, original half-open knot spans and ambiguous near-pi steps.

The full-step engine audit reconstructs the exact reviewed bytes and checks four clips over 444 actor frames in Godot 4.7.2. Maximum position error is 5.366925e-7 m and maximum basis-element error is 6.565566e-7. The full-mesh pass is evaluating all 148 source times and both actor directions, with unchanged per-time depth caps and floor checks. Engine success alone does not establish clearance or naturalness.

## Reproduction and evidence

Using the retained locally prepared inputs and fresh output directories:

```powershell
.venv\Scripts\python.exe scripts/diagnose_scene_export_rates.py reports/scene-pair-expanded-fit-v1 reports/scene-pair-export-rates-v1
.venv\Scripts\python.exe scripts/study_scene_pair_export_reserve.py reports/scene-pair-expanded-fit-v1 reports/scene-pair-export-reserve-v1
.venv\Scripts\python.exe scripts/audit_refined_pair_geometry.py reports/scene-pair-export-reserve-v1 reports/scene-pair-reserve-geometry-v1 --trial 0
```

The first two outputs are complete and bound to inputs, method snapshots and result hashes. The third preserves its worker identity, reconstructed clips, independent angular replay, engine evidence and incrementally written geometry. Do not restart it while its worker is live or overwrite earlier evidence. The existing Studio comparison remains unchanged.

Thirty-five focused tests pass across the diagnostic, empirical margins, independent angular replay and geometry-entry guards. No held-out prompt, human quality rating or cleanup-time evidence was used. All release capabilities remain unapproved. After mesh validation, the next decision depends on actual depth improvement and regressions; any publication must retain independent angular evidence.
