# First breadth result: waving passes its pin but misses a rate ceiling

The first case from the [eight-case frozen study](contact-breadth-v1.md), wave seed 11, has completed fitting, root-repair attempt, decoded export audit and actual Godot playback. The other seven cases are not included in this result; the original batch has advanced to crawling.

The authored foot point stays within **3.927542 mm** of its target at all 81 checked times, below the unchanged 5 mm limit. The exported full mesh has zero floor penetration at all 477 sample times. All 80 outside-window observations preserve the source within numerical tolerance. The existing body/support comparison reports no flags. These measurements do not establish action correctness or naturalness.

The exported point's approach speed is **0.020978876744 m/s**, slightly above its unchanged **0.020978116942 m/s** ceiling: an excess of **7.5980e-7 m/s**. All other phase speed/acceleration limits pass. This small excess remains a recorded failure; no acceptance padding was introduced. Global joint speed and acceleration remain below their original ceilings.

## Fit and attempted repair

Pose fitting and its evaluation took 1,482.07 seconds, with 1,789 objective evaluations. The four stages used 120, 120, 120 and 55 iterations, with 450, 505, 688 and 142 evaluations plus accepted-point recomputations. The last stage stopped on relative objective reduction while its projected-gradient infinity norm was 0.95445. An optimizer success flag did not establish contact feasibility.

The speed violation already exists before export: 1.3766e-7 m/s in the fitted record, 2.4832e-7 m/s in the float32 candidate's export proxy, then 7.5980e-7 m/s in the decoded GLB. Export increases it, but is not its only cause.

The fixed root-height repair rejected its first linear proposal as infeasible and preserved the fitted candidate exactly. It changed no root coordinates. Its independent cache and derivative checks passed. Repair preparation, attempted solve, body evaluation and export audit took another 31.84 seconds. The whole recorded case, including orchestration checks, took 1,528.13 seconds before the separate engine test.

## Why the linear repair rejected the step

A read-only analysis of the retained subproblem identifies one decisive row: the already-passing global joint-speed constraint centered at frame **48.875**. Its normalized slack is **1.75405e-5**. Even the best independent linear improvement permitted by the original root bounds and 10-micrometre trust box can raise that row's slack only to **1.80395e-5**. The repair requires **1e-4** extra interior slack on every movable row. That stronger search target is unreachable for this row, even before coupling it to the other inequalities.

This proves the configured linear subproblem cannot meet its extra margin; it does **not** prove the original motion constraints are infeasible. As a diagnostic only, retaining the same constraints, Jacobian and coordinate bounds while using zero extra margin gives a feasible linear proposal with a maximum coordinate step of 1.03823e-7 m. That initial diagnostic did not evaluate the proposal nonlinearly or export it. The separate numerical follow-up below also leaves the frozen batch result unchanged.

Horizontal point-rate lower bounds also stay below the original ceilings for all three phases and both derivative orders. They do not prove feasibility, but they do not establish a root-only impossibility here. After the frozen batch finishes, a justified follow-up is to distinguish preservation of already-passing rows from the additional numerical headroom sought on failed rows, then validate every nonlinear and exported constraint. Uniform extra margins should not be confused with the original acceptance limits.

## Engine evidence and remaining scope

Actual Godot playback passes **284 pose observations**, two requested-boundary marker events, four callback-mutation rejections, forward/reverse playback and unloading. Maximum actor matrix component error is 1.17e-6. Global exported peaks are 3.866853 m/s and 455.565282 m/s² against original ceilings of 3.866922 and 455.601356. These global references do not certify realistic per-joint dynamics.

Local immutable fit/repair evidence is under `reports/contact-jobs/contact-breadth-v1-wave-11-fit` and `reports/contact-jobs/contact-breadth-v1-wave-11-repair`. The case record is `reports/contact-breadth-v1/cases/wave-11.json`; engine evidence and the retained-subproblem diagnosis are in `engine/wave-11/verification.json` and `wave-11-root-diagnosis.json` beneath that suite. Source, implementation, asset and output hashes were checked throughout.

No fitting source, fixed protocol, original limits or candidate artifact changed during this analysis. No new test execution is claimed beyond the preceding 34 workflow tests. No browser rendering, HTTP interaction or human review was performed. The contact screen remains failed. The current cohort status is recorded in the breadth study; Studio defaults remain unchanged and no release capability is approved.


## Zero-margin numerical follow-up

A later diagnostic evaluated that same linear proposal in memory. It preserves every previously passing row but leaves two small nonlinear speed violations: minimum normalized slack is -4.4019e-8. Independent full interpolation/skin evaluation agrees. Casting the hypothetical pose to float32 happens to flip those rows to passing, with only 1.3350e-9 m/s of approach-speed headroom. No NPZ, GLB or BVH was written, and no replacement was accepted.

This rules out treating linear feasibility as sufficient. Rounding can change the classification in either direction; the float32 proxy alone does not prove the actual export will pass. The evidence supports testing targeted interior headroom with full nonlinear and decoded-export checks, rather than simply deleting every margin. The retained diagnostic is `reports/contact-breadth-v1/wave-11-zero-margin-diagnosis.json`; it binds the original input, seed, prior diagnosis and its own implementation.
