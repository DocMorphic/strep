# Preserving every arm joint across the fitting window

The coupled fit now passes all 88 per-joint angular comparisons across frames 115–125, both exported hand release-speed comparisons, all 245 grasp samples and all 717 geometry/edit-limit samples. This removes the window-join regressions found in the [speed-preserving fit](sphere-region-coupled-speed-v1.md). The release improvement is smaller, and the later whole-clip acceleration regression remains. No release or human-quality approval follows.

## Method

The nine fitted keys, eight arm joints, frozen non-arm/root motion and original limits are unchanged. The added fitting term measures each joint's difference between consecutive local relative-rotation rate vectors at all eleven affected centers. The source's own value supplies each comparison limit. Fitting uses 99% of that value to leave a numerical reserve, with a 0.001 rad/s residual scale; the exported preservation comparison uses the original source value.

`angular_join.py` computes the matrix logarithm through the skew vector and `atan2`, with a small-angle series. It supports differentiating the local rate-step objective without calling the independent SciPy decoder. Near-pi local increments are explicitly rejected rather than silently assigning an unstable axis. Tests cover zero/small and noncommuting rotations, directional derivatives, finite identity derivatives and that unsupported case. These local-coordinate rate-step differences remain continuity diagnostics, not inertial angular acceleration.

The independent audit reconstructs all source caps with SciPy and verifies the declared frames, joints and 99% fitting fraction. The boundary audit then decodes the re-exported input and candidate, compares every arm joint at every declared center, and records each result. Its numerical comparison allowance is 1e-5 rad/s. In this result, all 88 values strictly decrease; none relies on that allowance to hide an increase. The smallest reduction is 0.000141862 rad/s.

A test deliberately improves the largest joint while worsening a smaller one and verifies that the per-joint comparison rejects it. Aggregate maximum comparisons would miss that case.

## Result

| Largest arm rate-step difference | Input | Candidate |
| --- | ---: | ---: |
| Frame 115, entering the fitted window | 0.087161 rad/s | 0.086299 rad/s |
| Frame 121, release boundary | 1.351084 rad/s | 1.337668 rad/s |
| Frame 125, leaving the fitted window | 0.295188 rad/s | 0.295046 rad/s |

The release improvement is about 1%, compared with roughly 13% in the previous variant that introduced other angular regressions. This is a constrained tradeoff, not a claim of a perceptually large change. The later frame-145 endpoint is untouched.

Both hand release-speed comparisons still pass: left 0.086946→0.086006 m/s and right 0.168194→0.167315 m/s. The exact pre-fit spatial source is re-exported alongside the candidate, and its GLB hash matches the earlier spatial study.

All 245 grasp samples are revalidated, including the six changed grasp keys. The full 717-sample export audit records no object/floor or original edit-budget failures. Minimum floor height remains 2.001973 mm, sphere clearance 2.069914 mm, and maximum joint edit 38.564717 degrees. Non-arm physical parameters/root and all 171 outside frames stay exact.

The fit has 216 variables and 1,359 residuals. Its full real-character directional Jacobian check has maximum scaled discrepancy 0.000187539, within the declared 0.0002 check; the relatively close margin is recorded. Squared fitting residual decreases from 1,111.258120 to 559.907175. It reaches the 20-evaluation limit without convergence, taking 57.203 seconds including preflight and output. Solver termination is not used as feasibility evidence.

Whole-clip peak speed remains 1.364917 m/s and acceleration 40.041065 m/s². The frame-132 acceleration peak is outside this fit and still exceeds the original V13 comparison's 38.516182 m/s². These comparisons also do not establish skin acceleration, anatomical comfort, balance, forces, self-collision, continuous/triangle-interior clearance or naturalness.

Forty-five focused tests pass. Godot matches all 180 frames with 77 bones within 0.311 micrometres in position. The developer review question for the earlier spatial clip remains pending; no rating or cleanup time is invented.

## Next work and scope

The next motion correction should address the later torso/arm acceleration while preserving the newly passing per-hand and per-joint comparisons. It needs explicit provenance for any additional correction stage and coordinated upper-body controls, rather than assuming that an arm-only boundary fit solves a later torso-driven peak. Broad action, rig, object, partner, editing/style and human evaluation requirements remain open; all 14 release capabilities are unapproved.

Evidence is retained under `reports/sphere-region-coupled-angular-v1`, its `-audit` sibling, `reports/sphere-region-coupled-angular-boundaries-v1` and `reports/sphere-region-coupled-angular-engine-v1`. Raw earlier failures remain immutable. No model, training data, held-out trial, Studio default or acceptance-gate changes were made. The original fixed-point grasp condition remains distinct and unsolved.

## Reproduction

Existing local fixtures and licensed dependencies are required. Use fresh output directories.

```powershell
.venv\Scripts\python.exe scripts/coupled_release.py reports/sphere-region-spatial-v1 reports/new-angular-fit --cartesian-curvature-scale-m .0005 --release-speed-reserve-m-s .001 --preserve-angular-joins
.venv\Scripts\python.exe scripts/audit_region_grasp_track.py reports/sphere-region-track-v2 reports/new-angular-audit --approach-patch reports/sphere-region-approach-v1 --floor-patch reports/sphere-region-floor-v1 --release-patch reports/sphere-region-release-v1 --spatial-patch reports/sphere-region-spatial-v1 --coupled-patch reports/new-angular-fit
.venv\Scripts\python.exe scripts/audit_region_boundary_rates.py reports/new-angular-audit reports/new-angular-boundaries
```
