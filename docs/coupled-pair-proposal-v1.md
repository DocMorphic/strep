# Coupled high-five proposal and exported-motion validation

The first simultaneous two-actor approach proposal makes a small measured clearance improvement while preserving the existing motion checks. It **does not solve the interaction**: 25 of 57 sampled times still exceed the 5 mm partner-penetration screen, and inherited floor failures remain. No release capability or human-quality approval is granted.

## Method

The [moving-partner model](paired-approach-coupling-v1.md) supplies 72 controls, 3,045 surface witnesses and 5,434 native-edit/motion norm rows. A pinned Clarabel 0.11.1 second-order cone solve minimizes the largest predicted penetration with a 0.2-degree trust radius per three-dimensional control knot. Both actors contribute to each moving-triangle gap. Original-reference edit vectors are affine constraints; joint speed and acceleration vectors are linearized with source-relative per-joint caps across overlapping approach, event and boundary windows.

Each sampled time retains its own allowance: the larger of its existing penetration and 5 mm. This is a proposal nonregression rule, not clearance approval. The original 5-degree edit limit retains its separately declared 0.0001-degree export tolerance; decoded motion comparisons retain their existing 1e-5 numerical tolerance. Neither acceptance threshold was loosened.

The solver reports Solved after 37 iterations and 1.37 seconds. Its full step predicts maximum penetration falling from 23.556264 to 22.955925 mm. Independent affine checks pass, but exported nonlinear motion determines whether a step can proceed to geometry review.

## Exported line search

Every retained proposal is decoded at 597 quarter-frame times per actor. Checks cover all 77 joints, six windows, original-reference edits, exact unedited keys and channels, preserved fingers, and protected contact/release samples. Independent finite-difference replay verifies 14,784 peak values with maximum discrepancy 1.75e-13.

| Step fraction | Actor A rate failures | Actor B rate failures | Outcome |
| --- | ---: | ---: | --- |
| 1 | 1 | 6 | Rejected |
| 1/2 | 1 | 0 | Rejected |
| 1/4 | 1 | 8 | Rejected |
| 1/8 | 0 | 0 | Selected for geometry review |

The selected step has a maximum knot update of 0.025 degrees. Both actors remain within the declared original edit tolerance. Four clips (two inputs, two candidates) pass 600 fresh Godot actor-frame import observations; maximum position error is 4.52e-7 m. Successful import is not a realism rating.

## Complete sampled mesh comparison

Fresh candidate queries cover both directions at all 57 quarter times from frames 63 through 77, for 114 directional queries. Source queries are reused only after matching exact GLB identities, placements and the complete time population. Each query considers all 18,056 source vertices with conservative broadphase filtering against the partner mesh.

- Maximum penetration decreases from **23.556264 to 23.481228 mm**, about **0.075 mm**.
- Both source and candidate still fail the 5 mm screen at **25/57 times**.
- One time has a depth increase above 1 micrometre: **7.344 micrometres**, still inside its 5 mm allowance. Maximum per-time allowance excess is only 8.91e-9 m, below the audit's 1e-6 m numerical comparison tolerance.
- Maximum floor depth does not increase; existing floor failures remain.
- Contact frame 75 remains unchanged: 21/17 regional vertices within 3 mm, opposing-normal error 5.199358 degrees, and maximum partner penetration 1.896658 mm.

These are sampled vertex-to-mesh checks. They do not certify continuous collision freedom, triangle intersections, self-collision, force balance or naturalness. The candidate remains an unapproved research artifact.

## Why smaller proposals can still fail

A separate replay compares ideal float64 nonlinear kinematics with the actual serialized GLBs at identical times. The full step has genuine nonlinear rate regressions. At half and quarter steps, export rounding additionally introduces failures that the ideal kinematics do not have: one for A at each step and eight for B at the quarter step. Both representations pass at one eighth.

Maximum measured acceleration-peak shifts from serialization range up to 0.0002454 m/s2 across these trials and are not monotonic in step size. This evidence is not a universal quantization bound. A next experiment may use measured fitting reserves for curvature and export effects, while retaining unchanged final decoded acceptance gates and fresh geometry checks. Repeated tiny steps alone do not establish a usable solution.

## Reproduction and retained evidence

Completed local studies are `reports/coupled-pair-proposal-v1`, `reports/coupled-pair-engine-v1`, `reports/coupled-pair-geometry-v1` and `reports/coupled-pair-export-error-v1`. Rejected trials, input hashes and implementation snapshots remain available locally. The public repository contains source and this result summary; reproducing the experiment requires the separately acquired licensed fixture, pinned research solver and preceding evidence files. Use fresh output folders.

```powershell
.venv\Scripts\python.exe scripts/study_coupled_pair_proposal.py reports/paired-approach-witnesses-v1 reports/<new-proposal>
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/<new-proposal> --output reports/<new-engine>
.venv\Scripts\python.exe scripts/audit_coupled_pair_geometry.py reports/<new-proposal> reports/paired-approach-witnesses-v1 reports/<new-engine> reports/<new-geometry>
.venv\Scripts\python.exe scripts/audit_coupled_pair_export_error.py reports/<new-proposal> reports/paired-approach-witnesses-v1 reports/<new-export-audit>
```

Pure constraint tests join model-free Windows/Linux CI. Solver integration tests additionally require the locally pinned research solver and skip when its bootstrap evidence is unavailable. No new learned checkpoint or held-out evaluation is claimed.
