# Bounded proposals for coordinated root and leg correction

This development follow-up uses the same measured beckoning failure, source clip, five editable frames and preservation envelope as the [coupled SLSQP pilot](coupled-breadth-block-v1.md). It changes proposal selection, not what qualifies as an acceptable animation.

The existing conic descent solver retains affine foot-speed, foot-acceleration, root-acceleration and adjacent-edit vectors inside norm constraints. The new adapter replaces its inherited 5 mm floor allowance with the unchanged per-vertex source depth and adds drafted anchor distances and the 1 cm source-relative root radius. Original parameter bounds remain enforced. Each proposal is checked again through serialized poses and the existing half-frame floor and joint rotation guards. A small predicted constraint error is not an accepted edit.

The fixed budget is at most twelve accepted steps, with coordinate trust bounds of 1e-4, 1e-5 and 1e-6 attempted in that order and eight fixed fractions per proposal. These trust values use metres for root coordinates and radians for joint edits. The independent decoded audit, minimum useful improvement of 0.1%, original edit limits and engine checks remain unchanged. Every failed proposal is retained. The same source is used from the start, so corrections do not accumulate an additional edit budget.

## Completed pilot

The first attempt, `reports/coupled-breadth-conic-v1`, found improving steps but failed while serializing a NumPy counter in its solver record. It produced no completed candidate audit and remains a failed attempt. The counter now uses a native integer; an actual-rig proposal serialization test covers the failure. The unchanged trial was repeated in a new directory, `reports/coupled-breadth-conic-v2`.

The completed repeat accepts five steps. The independent decoded audit measures objective **46.839763 â†’ 46.051886**, a **1.6821% reduction**, and root peak **5.442488 â†’ 5.421484 m/sÂ²**. All eleven preservation checks pass under the original tolerances. Measured floor-depth increase is zero; the largest joint rotation-step peak increase is 4.50e-7 radians, inside the frozen 1e-6 allowance. The useful-improvement threshold passes. Both source and candidate pass 300 actual Godot actor-frames across 65 bones, with maximum position error below 0.470 Âµm.

This is a small improvement, not restored motion quality: all 21 previously failing root centers still exceed the original reference, whose peak is 0.709601 m/sÂ². The sixth step stops because the three conic proposals report numerical error or insufficient progress. No extra iterations or loosened limits were substituted. All source files, implementation snapshots, solver proposals, engine resources and independent output evidence are retained.

Twenty-one focused tests pass across the existing conic path, custom constraint dispatch, actual-rig source-depth/anchor/radius derivatives, serialization, independent export guards and population selection. The custom-provider test verifies that a declared fixed coordinate actually survives both proposal generation and full solve dispatch. Five provenance tests reject changed requests, audits, engine proofs and source/candidate motion before reusing a pilot. Two retained-candidate regressions also check the physical anchor guard described below. These checks do not establish physical balance or perceptual quality.

## Population follow-up

`reports/coupled-breadth-population-v1` freezes **all nine** independently diagnosed root-only conflicts: backpedal rigs 02/03, beckon rigs 01/02/03, kneel rig 01, tie-shoe rig 01, and exhausted-walk rigs 02/03. Each receives a block of up to five frames at its measured root peak, clipped to retain the two fixed frames at each endpoint, under the same method and acceptance limits. The existing verified pilot is reused once, with no rerun counted as new evidence.

The study completes with **7/9 accepted numerical corrections**, two independent anchor rejections and zero execution errors. It adds 2,880 actual Godot actor-frames; including the reused pilot, all nine source/candidate pairs have 3,180 frame checks. Every proposed clip still exceeds its original root-acceleration peak. The table reports proposed candidates even when rejected; none is promoted automatically.

| Action / rig | Target objective reduction | Source → candidate root peak, m/s² | Independent result |
| --- | ---: | ---: | --- |
| Backpedal / 02 | 0.568% | 11.6733 → 11.6611 | Accept |
| Backpedal / 03 | 26.076% | 12.1490 → 11.4420 | Accept |
| Beckon / 01 | 0.291% | 1.8455 → 1.8412 | Accept |
| Beckon / 02 | 1.287% | 1.1325 → 1.1298 | Reject anchor drift |
| Beckon / 03 | 1.682% | 5.4425 → 5.4215 | Accept; reused pilot |
| Kneel / 01 | 4.753% | 3.8592 → 3.8306 | Accept |
| Tie shoe / 01 | 0.966% | 1.4093 → 1.4032 | Accept |
| Exhausted walk / 02 | 5.379% | 7.2864 → 7.2086 | Reject anchor drift |
| Exhausted walk / 03 | 3.082% | 7.4129 → 7.3467 | Accept |

## Physical anchor acceptance

The two rejected candidates expose a unit mismatch in internal step selection. Its normalized residual tolerance of 1e-8 permits physical anchor increases of 1.001300 and 1.032664 µm, exceeding the independent 1 µm allowance. Direct comparison confirms that the serialized internal poses and saved exports agree to below 2e-17 m on these anchor errors: export conversion is not the cause. The independent audit correctly rejects both.

The step geometry guard now additionally compares actual serialized anchor distances in metres against the same unchanged source allowance. Both saved failures fail this guard while their source poses pass; no audit tolerance was widened. `reports/coupled-breadth-population-v2` reuses the seven verified outputs and reruns only these two rejected cases from their original inputs under the same iteration/edit budgets. The follow-up completes with both retries accepted and zero execution errors, adding 720 actual engine actor-frames. Beckon / 02 now has target objective 0.186837 → 0.184413 and root peak 1.132548 → 1.129734 m/s². Exhausted walk / 02 has objective 19.735619 → 18.682119 and peak 7.286397 → 7.208610 m/s². All eleven independent guards pass on both. The combined population therefore has 9/9 accepted numerical improvements, retaining all earlier rejected files, but 0/9 recovered original whole-clip root peaks. Acceptance here establishes only the declared numerical correction and export checks.

These are development measurements, not held-out motions, full-clip recovery, animator approval or release readiness. All fourteen project capabilities remain unapproved.
