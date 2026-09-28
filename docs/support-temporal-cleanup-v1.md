# Whole-clip support and transition cleanup

Development study, 2026-09-28. The single project-wide goal stays active. This work does not approve animation quality or close a release gate.

The frozen 19-case support analysis found increased foot-speed peaks near predicted support boundaries in 11 cases. The previous correction objective penalized curvature of correction offsets; that does not guarantee smooth delivered motion. This study instead minimizes squared acceleration of the actual world root trajectory and constrains the actual foot-patch trajectories.

`scripts/support_temporal_cleanup.py` adapts the existing whole-clip convex root solver. It keeps the source pose channels fixed and proposes at most 1 cm of additional root movement, inside the original total edit limits. The first and last two frames remain fixed. Every root and foot-patch acceleration sample has a no-increase constraint. Floor depth is preserved at keys and midpoints. Drafted support anchors and supported foot heights cannot worsen. Horizontal foot speed is guarded during support, on entry and release edges, and on their immediately adjacent edges.

These are constraints on the achieved source correction. They do not assert that its predicted contacts are correct, that the existing floor/contact errors pass a quality threshold, or that root-only changes can resolve every failure. Joint motion, semantics, physical balance and raw-model shortcomings remain separate problems.

`scripts/verify_support_temporal_cleanup.py` decodes each exported GLB independently of the proposal matrices. It checks the original root budgets and unchanged pose channels, root and patch acceleration, floor, anchors, foot heights, and boundary speed. A retained candidate must reduce actual root acceleration energy by more than both the absolute floor and 0.1 percent. Export allowances remain explicit: 1 micrometre for position, 0.0036 m/s² for acceleration, and 0.00006 m/s for guarded speed. The speed allowance corresponds to two 1-micrometre position errors across a 30 Hz edge; it is not a realism threshold.

The study freezes every completed case from `whole-support-breadth-interim-v19`: 19 completed cases and 5 unfinished rows out of the original 24. It does not select only favorable actions or rigs. Each eligible case receives one convex proposal and at most four fixed exported fractions (1, 1/2, 1/4, 1/8). Rejected candidates are retained, and the source stays selected when no meaningful feasible improvement exists. Real Godot import checks both the input and selected result. Selected packages contain their GLB, root track, unchanged predicted contacts, and provenance identifying inherited unapproved status.

Five tests passed in 25.23 seconds. They cover merged foot/toe intervals, boundary-edge coverage without wrapping, unchanged-motion rejection as a meaningless edit, an actual exported release spike outside stance, and a supported foot-height regression despite improved floor clearance. The population run is recorded in `reports/support-temporal-cleanup-v1`; read its completion and pipeline files for actual results rather than treating a queued run as evidence.

The original whole-support study continues with its original frozen implementation. No completed baseline or live dependency was overwritten.

## Completed result

The run completed with 14 retained corrections, 5 unchanged inputs, no failed jobs, and the 5 unfinished source rows still included in the 24-case denominator. All 38 input/selected clips passed actual Godot import and playback checks, totaling 6,900 actor-frames. The full frozen accounting is `reports/support-temporal-cleanup-summary-v1/summary.json`; its `comparison.md` presents each action and rig.

Accepted corrections reduce root acceleration energy by 1.831–14.697 percent across six action families. For the grapevine dance on rig 03, peak root acceleration falls from 21.436 to 17.033 m/s² with the preservation checks passing. This is a numerical smoothness result, not an animator rating.

Relative to the original raw-motion reporting bins, root-peak regressions decrease from 14 to 11 cases. All 11 cases with foot-peak regressions still have at least one such regression. The exhausted-walk input is retained unchanged: its right-foot peak remains 0.190239 m/s versus the raw 0.061934 m/s, despite the earlier floor improvement. Root-only cleanup therefore does not resolve the boundary problem. The next correction needs joint motion as well as root translation and must retain this complete comparison population instead of rerunning tiny root-only improvements.
