# Landing solver coordinate scaling

The completed [support comparison](native-support-breadth-v1.md) leaves a horizontal landing pin error above 5 mm. Height-only correction cannot resolve it. The existing joint-and-root solver can change the pose, but its constraint penalties increase substantially while the pin residual barely decreases. Its last three stages hit their iteration limits; the recorded optimizer pin error closely matches the decoded GLB error.

A read-only probe evaluates the objective and gradients once at each of two reconstructed warm starts, without taking an optimizer step or exporting a candidate. At the original warm start, rotation-control/root-height gradient infinity norms are 8.147/29.107; at the retained control they are 3.221/21.568. These derivatives have different coordinate units, so their ratio is not a condition-number estimate or proof of the cause. It motivates testing a different coordinate scale. Existing warm initialization raises very small free root heights to 22 micrometres; the probe preserves that existing behavior and records a maximum 22.054 micrometre round-trip joint difference. It does not claim to evaluate the exact original stored pose or the previous final-stage multipliers.

## Change under test

`BoxRootOptimizer` accepts an optional positive `root_scale_m`. SciPy sees `u = h / scale`, while the motion closure still sees physical height `h` in metres. The gradient returned to SciPy is multiplied by the scale and the box is transformed to `[0, original_limit / scale]`. Rotation coordinates, motion penalties, original physical budgets and final contact/rate/floor acceptance thresholds remain unchanged. The default scale is 1, preserving the previous optimizer coordinates.

The test scale is the existing 0.22 m root budget: the solver then sees a root fraction in `[0, 1]`. This is a numerical preconditioner, not an enlarged edit allowance or a hard contact-feasibility solver. A solver point outside its transformed box is rejected. An in-box product that rounds beyond the physical endpoint is clamped to that original endpoint. Accepted optimizer coordinates are restored after rejected line-search probes. Diagnostics separately record physical and solver-coordinate projected gradients so the units remain visible.

The [SciPy 1.15.3 L-BFGS-B documentation](https://docs.scipy.org/doc/scipy-1.15.3/reference/optimize.minimize-lbfgsb.html) defines distinct relative-objective and projected-gradient stopping criteria. Scaling changes the coordinates in which the gradient criterion is evaluated; successful solver termination still does not prove motion feasibility. Iteration limits, objective tolerances and independent acceptance checks remain explicit.

## Verification and matched experiment

Thirteen optimizer tests pass, including finite-difference chain-rule checks, original physical bounds under three coordinate scales, a known coupled constrained optimum, restoration after a rejected probe, invalid scales and rejection of a scale silently supplied to a different coordinate mode. Seventy-four focused tests pass across the optimizer, root coordinates, original edit budgets, held-pose preservation, root/export repair and support objectives. Seven existing Torch/HiGHS warnings remain. The study CLI exposes `--root-optimizer-scale-m`; Studio's default scale remains 1.

The local matched experiment is `reports/landing-root-scale-v1`. It runs scale 1 followed by scale 0.22 with identical original landing source, warm seed, checked request, four outer stages and 60 iterations per stage. Fixed-patch support is enabled and the optional native-body objective is disabled in both arms. Each mode retains native/BVH/GLB outputs, complete audits, engine playback and source/method hashes.

Before proceeding to the scaled arm, the unit-scale run must reproduce the previous support-enabled landing's NPZ, BVH, GLB and contact/body audits byte-for-byte. If it does not, the batch stops for diagnosis. Paired input/method snapshots and protocols must match except for the coordinate scale. Both arms are now terminal and independently verified. The completed results below establish compatibility and retained failures, not quality approval.

Local diagnostic evidence is `reports/landing-coordinate-diagnosis-v1/diagnosis.json`; generated study data remains excluded from the public repository. If the measured landing failure persists, a pose-capable feasibility restoration with complete original constraint checks remains necessary. This experiment does not replace broader action/rig/interaction coverage or human review.


## Default-coordinate compatibility verified

The unit-scale arm completed 381 evaluations in 324.98 seconds. Its saved NPZ, BVH, GLB, contact audit and body evaluation reproduce the prior support-enabled landing result byte-for-byte. Every original input, current/archived method and completion-artifact hash was independently rechecked, and its new engine run passes 284 pose observations and the authored event checks. The known pin/rate failures are unchanged; compatibility is not motion-quality approval.

Evidence is retained as `default-compatibility.json` and `unit-verification.json` in the batch directory. The scale-0.22 arm also completed from the same original warm seed and request. Methods remained frozen through the final paired verification below.


## Completed comparison: scaling does not resolve the landing failure

| Measurement | Scale 1 | Scale 0.22 |
| --- | ---: | ---: |
| Fit time, seconds | 324.98 | 385.37 |
| Objective evaluations | 381 | 449 |
| Maximum exported pin error, mm | 5.370261 | 5.353967 |
| Samples above the 5 mm limit / 61 | 2 | 3 |
| Approach speed excess, m/s | 0.000048219 | 0.000039498 |
| Approach acceleration excess, m/s² | 0.000060311 | 0.001900503 |
| Hold speed excess, m/s | 0.000035444 | 0 |
| Hold acceleration excess, m/s² | 0.002034130 | 0.000053459 |
| Release speed excess, m/s | 0.000250459 | 0.000285887 |
| Release acceleration excess, m/s² | 0.000254704 | 0.000461371 |
| Contact screen | Fail | Fail |

The scaled run reduces maximum pin error by about 0.0163 mm, but increases the number of failing samples and worsens approach acceleration and both release rates. Hold speed passes and hold acceleration improves. This is a mixed numerical result at greater evaluation cost, with no successful contact candidate. Keep the default scale at 1; further scale-only retries are not the next development step.

Independent verification completed on 2026-09-30. It rechecked original inputs, archived/current methods, all completion-artifact hashes, matched protocols and default compatibility. Replaying the full decoded GLB audit reproduces both saved reports exactly. Recomputed native support metrics match within 1e-10, and every measured support allowance passes. Global rate excess, added floor depth and all outside-window joint/basis/skin errors remain zero. Original physical budgets pass: maximum root lifts are 0.747263/0.747561 mm and maximum rotation edits are 0.672750/0.855884 degrees, respectively.

Both original engine captures pass 284 pose observations each, with authored pin events at frames 85 and 100, reverse/automatic playback, callback modes and unloading checks. The independent verifier rechecks those retained captures in separate output directories; it does not launch additional engine playback. Engine import is not contact or human-quality approval.

Evidence: `reports/landing-root-scale-v1/comparison.json` and `reports/landing-root-scale-verification-v1/verification.json`. The workers are terminal and the method freeze is accounted for. Failed candidates remain immutable. A separate exploratory vector-norm point-track relaxation found no verified incompatibility certificate; it does not establish that a rigged animation can satisfy the request. Next investigate pose-capable feasibility restoration with the original bounds and full export checks, alongside broader workflow validation. All fourteen release capabilities remain unapproved.
