# First matched support/reference result

This is **one of ten** planned inputs, motion-006-rig-01, seed1301. The difficult second rig and remaining seeds are still running. `compare_support_reference.py` checks the same source clips, targets, support intervals, solver settings and edit limits before comparing completed candidates with actual engine evidence. Five tests reject changed sources, support guides, weights, sweep counts and root limits.

| Metric | Original correction | Revised correction |
|---|---:|---:|
| Worst foot predicted-support p95 speed | 0.02519 m/s | 0.02065 m/s |
| Whole/half-frame floor penetration | 0.7422 mm | 0.6895 mm |
| Predicted-support hover | 6.3374 mm | 6.3406 mm |
| Peak root acceleration | 4.6613 m/s² | 6.1719 m/s² |

Both candidates pass the existing numerical proxy screens and their edit/preservation limits. The revised input/candidate Godot group checks all19bones over150frames per clip:300actor-frames. The original comparison group checks450actor-frames. This is structural and proxy evidence, not approval of the motion.

Independent decoded time traces reproduce the recorded acceleration maxima. The revised peak moves from frame41 to45, with components approximately (1.78, -5.34, -2.53) m/s². At frame45 the left support draft is fading in with weight0.75; the right is fully weighted. This coincidence suggests inspecting the contact transition, but it does not prove causation or physical implausibility.

The p95 metric also hides an endpoint regression: maximum predicted-support left-foot speed is0.15644m/s for the original correction and0.27560m/s for the revised one, both on step148→149. The input's maximum is0.15543m/s on step44→45. The revised right-foot maximum rises from0.09056 to0.11233m/s. Report these tails even though the p95 proxy passes. Do not adjust thresholds after the fact to make the candidate pass or call the current p95 result sufficient for realistic motion.

Evidence: `reports/support-reference-comparison-v1` stores both captured result populations and all verified sources. `reports/support-reference-traces-v1` stores decoded root/foot traces; the inspected figure is `figures-v2/motion-006-rig-01.png`. The first plot is retained; v2 moves an overlapping annotation. Matplotlib3.10.7 ran through an isolated uv environment because neither project nor bundled Python supplied it. The frozen model runtime was not modified.

Next: finish the fixed ten-input study and compare every matched result. Investigate support transition and clip-end behavior before product promotion. Any endpoint-policy or temporal-objective change requires a new recorded comparison; do not change the running study's protocol.


## Second matched input and separate endpoint repair

`reports/support-reference-comparison-v2` now captures two of ten inputs; v1 is retained. On motion-006-rig-02 the revised p95 speed falls from 0.15370 to 0.04287 m/s, floor depth from 0.56172 to 0.50178 mm, and hover changes from 10.5635 to 10.6155 mm. Root acceleration increases from 7.36108 to 14.50424 m/s². Independent decoded traces place the new peak at frame60 with BOTH drafted supports fully weighted. This is not the same boundary-fade issue as the endpoint spike. A local parameter diagnostic (`reports/support-reference-traces-v2/rig-02-peak-diagnostic.json`) records correction curvature and coordinate-solver status around frames57–63; six-sweep convergence was not established.

The separate [controlled endpoint experiment](support-endpoint-v1.md) removes the tail spike on both completed rigs without changing their earlier motion or floor maxima. It leaves the acceleration regressions intact. Its ten-input batch consumes completed parent cases while this unchanged all-ten-input study continues.


## Six completed matched inputs (comparison v3)

`reports/support-reference-comparison-v3` verifies six of the ten declared input pairs; four remain unscored. All six revised p95 support speeds are lower than the original fit, but all six peak root accelerations are higher. Five of six meet the provisional floor/p95/hover proxy combination; motion-008-rig-02 still fails at 0.069756 m/s p95, versus 0.095499 previously, with root acceleration 6.2289 -> 11.6781 m/s². This is incomplete development evidence, not a 5/6 release success rate. The already-frozen whole-clip comparison tests the combined boundary/curvature correction across broader actions without tuning its protocol from these interim results.
