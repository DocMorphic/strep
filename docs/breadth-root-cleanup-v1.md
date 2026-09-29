# Root cleanup across eight actions and three rigs

This development comparison applies bounded root-translation cleanup to **all 24 completed whole-support candidates**, preserving their original order, eight actions, three rigs and seed 1301. It does not regenerate motion or use the reserved release set. The source population includes backpedalling, grapevine dance, beckoning, a broad jump, kneeling/rising, tying a shoe, exhausted walking and jab-cross-retreat. Scene-dependent motions remain in the broader project scope but are not evaluated by this floor-only study.

The prior correction improved floor clearance but raised peak root acceleration in 18/24 clips and peak predicted-support foot speed in 13/24. This comparison tests whether the existing convex root cleanup can reduce acceleration without sacrificing the achieved contact proxies. Original transfers and corrected clips remain immutable. The original transfer's acceleration is retained separately: improving an already regressed candidate does not prove recovery to the original.

## Frozen method

`scripts/study_breadth_root_cleanup.py` snapshots both GLBs, foot patches, original root budgets, predicted contact labels and drafted horizontal anchors. Its request freezes 62 Python source files, the conic solver bootstrap and the engine binary. Every case receives the same policy: a 1 cm additional root displacement radius, the original 4 cm horizontal / 12 cm vertical root budgets and 15 mm adjacent-edit budget, fixed first/last two frames, a 150-iteration / 60-second solver budget, and safeguard fractions 1, 1/2, 1/4 and 1/8. It requires at least 0.1% reduction in summed squared root acceleration.

Rotation channels stay unchanged. The reused solver constrains per-frame root acceleration, whole-clip foot-patch acceleration, full-skin floor depth at keys and midpoints, and original edit limits. Additional constraints preserve each predicted-support step's horizontal centroid speed, each active foot's hover and each drafted anchor distance. Skin-weight sums are used as serialized; local root offsets are transformed into world space. The low foot vertex is a sufficient hover witness, not a fixed contact correspondence or a claim of physical support.

Every saved proposal is decoded by the existing separate root audit plus a new support audit that recomputes skin positions without solver maps. Existing metre/acceleration serialization tolerances remain explicit (1 µm position; 0.0036 m/s² acceleration; 0.00006 m/s for a two-endpoint support-speed difference). Rejected proposals remain in the result. A failed or unchanged outcome remains in the 24-case denominator. The selected output of each nonfailed case then receives actual all-frame Godot import verification.

Three focused tests pass. They cover interval unions, actual exported skin displacement versus the affine map, unchanged-source acceptance, and deliberate hover/sliding violations. An initial test caught nonunit float32 weight sums and a rotated parent axis; both were corrected before the study freeze. No acceptance threshold was loosened.

The retained study is `reports/breadth-root-cleanup-v1`. Consult its terminal pipeline, per-case attempts, completion hashes and engine proof before interpreting it as finished. This document's population and policy do not imply successful motion quality. Foot support is still model-predicted; action correctness, knee/hand support, balance, scene/partner interactions and human cleanup-time evidence remain unverified. No default correction or release gate is promoted by this experiment.

## Completed comparison

All 24 cases finished: 21 retained cleanup candidates, three retained prior clips, and no execution failures. Every accepted candidate passes the separate root and support checks. The three rejected cases are CesiumMan beckon, kneel/rise and jab-cross-retreat; every safeguard fraction fails the unchanged 0.1% energy-improvement requirement while its preservation checks pass. Those failures remain in the population.

| Action | Cleanup accepted | Original root-peak level recovered |
|---|---:|---:|
| locomotion-backpedal-check | 3/3 | 1/3 |
| dance_and_performance-grapevine | 3/3 | 3/3 |
| gestures_and_expression-beckon-left | 2/3 | 0/3 |
| parkour-broad-jump-stick | 3/3 | 2/3 |
| ground_and_recovery-kneel-rise | 2/3 | 0/3 |
| everyday_tasks-tie-shoe | 3/3 | 2/3 |
| stylized_and_capability-exhausted-walk | 3/3 | 0/3 |
| combat-jab-cross-retreat | 2/3 | 1/3 |

The energy reduction ranges from 0.68% to 15.74% among accepted candidates. Dance root peaks fall from 11.0685 / 20.9454 / 21.4357 to 9.6873 / 18.0827 / 17.0950 m/s² across the three rigs. Several other peaks are unchanged despite lower total energy. Only 9/24 selected clips meet the original raw-transfer peak level within the existing numerical tolerance; 15 still exceed it. Predicted-support and geometric preservation must not be described as full motion-quality recovery.

All 24 selected GLBs pass actual Godot import at all 4,320 frames. Maximum joint-position discrepancy is 1.56 µm and maximum basis-element discrepancy is 4.02e-6. Engine checks establish playback fidelity, not naturalness.

`reports/breadth-root-cleanup-summary-v1` verifies the full denominator, source snapshots, selected GLB hashes, separate audit records and engine population. Five additional summary tests reject missing cases, changed exports, wrong engine sources and unsupported promotion. Together with the three adapter tests, eight focused tests pass. No browser test, new generation, training or human review is claimed.

Next: inspect the remaining peak regressions and their active contact/edit constraints before choosing coupled root/joint correction. Preserve the original source comparison; repeated root-only smoothing is not evidence that those failures are solved.
