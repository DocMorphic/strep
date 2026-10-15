# Moving region guides: retained failed high-five proposal

This source-native study tests whether different forearm/hand separation guides
at successive native animation keys can improve the earlier single-pose curve.
It uses the [previous-control objective](native-pose-reference-v1.md), keeping
each pose bound to its **current original source pose**. Previous controls are
an objective reference, never a replacement motion, displacement or rate bound.

The same explicitly selected right-forearm subtree and incident-triangle closure
are used as the [facet-plane study](facet-plane-contact-guidance-v1.md). At five
original keys, 34 through 38, all supplied region vertices participate in XYZ
plus complete returned hull-facet guidance. Each actor has the same four edited
nodes, 10-degree permissions and 45-mm proposal displacement bound inside the
original 50-mm clip limit. Geometry-derived directions are not anatomical labels.

All five fits pass for A; B passes the first three and fails the last two.
Failed fits retain the original zero key. The finite solver failures are saved,
not treated as proofs of global infeasibility. Controls are interpolated with
componentwise quintic weights between the declared controls and zero boundary
keys 30 and 48, then exported through the existing native quaternion tracks.
This curve is explicitly a rejected proposal, including its failed zero keys.

Actual serialized full-mesh diagnostics give:

| Native time (s) | Pair conditions | Surface outcomes | A inside B maximum | B inside A maximum |
| --- | --- | ---: | ---: | ---: |
| 1.1333333253860474 | Pass | 0 | 0 mm | 0 mm |
| 1.1666666269302368 | Pass | 0 | 0 mm | 0 mm |
| 1.2000000476837158 | Pass | 0 | 0 mm | 0 mm |
| 1.2333333492279053 | Fail | 116 | 14.568603 mm | 21.845506 mm |
| 1.2666666507720947 | Fail | 82 | 7.508728 mm | 12.216683 mm |

The two shared diagnostic times at 1.1666666 and 1.2000000 seconds previously
retained 266 and 310 surface outcomes in the single-pose curve. This does not
establish an overall improvement: the guide times, controls and fade timing
change together, and only five pair-geometry times are queried in this study.

All 2,017 declared motion/floor times are checked after serialization. No joint
displacement exceeds the original 50-mm limit: maxima A **45.000005 mm**, B
**45.000000 mm**. A has **one rotation-bound failure** in the decoded clip; B has
none. Original motion-rate rows fail **230 times for A / 194 for B**, compared
with 60 / 114 in the earlier curve. The source caps, scales and 1e-5 rate tolerance
remain exactly unchanged. Roots, endpoints and samples outside the edited
influence remain exactly unchanged. Both complete floor arrays exactly match
the bound cached source observations and fail all 2,017 times. The original
2-second contact arrays are also exactly unchanged and failed.

Every original rate failure in both curves is attributed by its original row,
metric, native joint, sample time, source cap and unchanged tolerance. The old
curve includes failures before the first source-bin boundary, but the new curve
still fails inside the active approach despite moving its fade boundary past
that boundary. Boundary placement alone therefore does not restore these rates.
The moving guides introduce incompatible temporal changes under the original
motion contract; a successful static fit is not a rate-feasible clip.

The 512 MiB CPU guard completes in **249.594 seconds**, peak sampled process-tree
RSS **346,353,664 bytes**, with all **247** resource observations replayed and
an additional 600 MiB free floor. All sources, controls, failed fits, complete
motion rows and five geometry diagnostics remain under ignored
`reports/high-five-moving-region-guides-v1`. All root Python methods are
snapshotted and checked unchanged before/after the study. No new engine or model
is run, and the original remains selected. No complete geometry-clock, floor,
meeting, physical, human-quality or release approval follows.

## Coupled shared-plane diagnostic

A separate diagnostic retains the prior axes, complete regions, original source
poses, 10-degree rotation permissions and 45-mm proposal displacement bounds at
keys 37 and 38. Both actors now solve together with one common plane-offset
variable, limited to 50 mm around the original halfway plane. Moving that
geometric guide does not move the characters' roots, source poses, world floor,
contact targets or original acceptance limits. Controls prefer the earlier
accepted key-36 controls; the plane coordinate has a separately declared small
objective weight. This tests joint fitting and a movable plane together, not an
offset-only ablation or a temporal solution.

All **25 analytic derivative columns** are compared with central differences at
a declared interior point for each pose. Maximum absolute row-derivative errors
are **2.2012e-7 / 2.5413e-7**, below the declared 1e-5 diagnostic threshold.
Successful proposals are independently checked through `KeyPose` with the
resulting fixed planes before querying the complete actor meshes.

At **1.2666666507720947 s**, joint fitting succeeds in **28 iterations / 91
calls**, moving the shared plane **1.343910 mm**. Both independent original pose
bounds pass, roots remain exactly unchanged, and full pair geometry has **zero
surface outcomes and zero inside-vertex depth**. The complete pose still fails
the original floor checks. At **1.2333333492279053 s**, the 42-iteration fit fails
its guide constraints; both actors retain their original poses. The failed
candidate controls are saved separately. The retained original pair has 222
surface outcomes at this time; it is a different fallback from the earlier
moving curve, which retains A's successful independent fit.

The coupled diagnostic's 512 MiB CPU guard completes in **80.282 s**, peak
sampled tree RSS **153,362,432 bytes**, with all **81** resource observations
replayed and the additional 600 MiB free floor. Records remain under ignored
`reports/high-five-shared-plane-pose-v1`. No curve is built or serialized from
these static fits, no temporal rates are established, and no original motion is
adopted. The diagnostic does not automatically enable a paired solver in Studio.

The next implementation needs joint constraints over the changing motion,
including the original rate contract, alongside separate ground/support and
meeting correction. Repeating a successful pose across a clip is insufficient.
Serialization, complete scene geometry, engine comparison and human review
remain required before adoption; broader actions, rigs and controls remain in
the single project-wide goal.
