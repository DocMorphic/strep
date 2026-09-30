# Rotation-rate evidence for the refined paired candidate

The quarter-step [curve refinement](scene-pair-limits-v1.md) passes the existing positional motion and retained-surface screens, but its angular motion is not unchanged. A separate decoded audit finds the following increases beyond each original joint's peak in the original knot span:

| Actor and metric | Exceeding observations | Largest increase | Joint at largest increase |
| --- | ---: | ---: | --- |
| A angular speed | 6 | 0.000619197 rad/s | LeftArm |
| A angular acceleration | 2 | 0.261183181 rad/s² | LeftForeArm |
| B angular speed | 7 | 0.000278891 rad/s | LeftShoulder |
| B angular acceleration | 11 | 0.039785586 rad/s² | LeftShoulder |

The declared comparison tolerances are 1e-5 rad/s and 1e-5 rad/s². They are diagnostic numerical thresholds, not validated perceptual or physiological limits. The largest A acceleration change is from 45.821971447 to 46.083154628 rad/s². These measurements expose a missing constraint; they do not establish that a person would see worse animation.

## Method and solver rows

`joint_angular_rates.py` computes interval rotation logs from `R_next R_previousᵀ`, expressed in a common world frame. Their norms measure sampled angular speed; successive interval-vector differences divided by the sample period measure sampled angular acceleration. Comparisons cover every joint and stencil on the saved 120 Hz clock, using the original half-open knot spans and halo samples. Source and candidate use the same rig and clock.

The implementation rejects nonfinite, scaled, reflected or sheared rotation matrices, nonuniform clocks and ambiguous steps near π. Quaternion sign changes do not change the matrices or the measurements. This is a sampled calculation; it cannot detect an unsampled full revolution or prove continuous dynamics, torques, balance or naturalness.

`AngularMotionRows` builds source-relative angular speed and acceleration norm rows. Its influence selection includes the edited joint itself and all descendants. This is different from positional motion: rotating a leaf or wrist can leave its origin fixed. Every changed stencil is included, with caps computed before any refinement changes the edit curve's knots.

Finite differences through the world rotations supply derivatives for the existing three-vector conic interface. Synthetic tests check the independent native-motion directional prediction, affected-stencil coverage, stationary-origin rotation and zero effect from translation derivatives. These rows are **not yet connected to the production paired fitter or used in a new real conic solve**. They must undergo matched solver, exported-clip and geometry validation before any acceptance-policy change is claimed.

## Engine and mesh review

The new geometry runner reconstructs the quarter-step GLBs exactly from their saved controls before importing them. Godot verifies both originals and both candidates: **four clips, 444 actor-frame observations**, 77 bones each, one skinned surface, original duration and nonlooping playback. Maximum position error is 6.574707e-7 m; maximum basis-element error is 6.565565e-7.

The complete 126-time, 252-direction mesh/floor audit is still running in `reports/scene-pair-refinement-geometry-v1`. Its engine evidence is complete, but partial geometry rows do not establish a final result. The live worker identity and command session are tracked separately from its progress file. The candidate has not replaced the existing Studio comparison. A local geometry pass also cannot erase the new angular observations.

## Reproduction

```powershell
.venv\Scripts\python.exe scripts/audit_refined_pair_geometry.py reports/scene-pair-refinement-export-v1 reports/<new-geometry-review> --trial 2
.venv\Scripts\python.exe scripts/audit_scene_pair_angular.py reports/scene-pair-refinement-export-v1 reports/<new-angular-review>
```

The completed angular study is `reports/scene-pair-refinement-angular-v1`. It preserves all five fractions, source identity, original timing, decoder hashes and explicit numerical thresholds. The geometry runner holds the shared worker lock; the angular audit reads existing clips and does not edit or regenerate them. No live geometry-worker dependency was changed.

Twenty-four new model-free tests pass: 11 review-gate checks, 10 rotation-rate checks and three angular-row checks. They join Windows/Linux CI. All release capabilities remain unapproved; no held-out action or human rating has been used.
