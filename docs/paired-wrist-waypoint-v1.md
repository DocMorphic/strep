# Wrist waypoints and a first temporal approach

All four audited wrist waypoints have **zero measured vertex penetration** at
1.675 s, the latest correction's worst pose. This improves on fixed-wrist swivel
planning, whose best tested pose still intersected by 15.342952 mm. The new
waypoints are static targets: temporal baking shows that reaching one clear pose
does not make the whole approach clear or preserve the old motion-rate limits.

## Kinematics and search

`two_bone_waypoint.py` solves a rigid two-bone reach using the elbow's intersection
circle. It transports the source bend plane to the target shoulder-to-wrist axis,
applies a swivel, and reconstructs upper-arm, forearm and wrist local rotations.
Bone lengths and hand world orientation are retained. Unreachable targets are
rejected rather than clamped. A zero wrist displacement reproduces the existing
swivel primitive exactly. This is a geometric solver, not an anatomical joint-limit
or natural-motion model.

The input remains the bound, latest local correction in
`reports/scene-pair-relinearized-completed-v2`. At its peak time, test zero offset
and symmetric offsets of 20, 40 and 60 mm along each sign of the three scene axes.
Each actor gets swivel choices -45, -30, 0, 30 and 45 degrees. This declares 475
paired targets. Of these, 288 are rejected for reach or the 45-degree native
joint-edit budget; 187 remain for proxy ranking. Every rejection is saved.

These are separately authored planning targets relative to the current clip.
They do not inherit acceptance from the earlier five-degree edit request. The
old request, source outputs and Studio comparison remain unchanged.

The same forearm capsule heuristic ranks candidates. It is deliberately loose:
all 187 have negative proxy clearance, so only the greatest-clearance branch of
the four-candidate selection contributes. A proxy overlap is not a mesh failure.
Full mesh queries are performed on the actual decoded static GLBs, in both
directions, for four selected targets only.

| Candidate | Actor A wrist offset | Actor B wrist offset | Swivels A/B | Full-mesh vertex depth |
|---|---|---|---|---:|
| 16-16 | -60 mm X | +60 mm X | -30 / -30 degrees | 0 mm |
| 76-76 | -60 mm Z | +60 mm Z | -30 / -30 degrees | 0 mm |
| 77-76 | -60 mm Z | +60 mm Z | 0 / -30 degrees | 0 mm |
| 76-78 | -60 mm Z | +60 mm Z | -30 / +30 degrees | 0 mm |

All four have 2.649304 mm maximum floor penetration, passing the 5 mm floor
screen. Actual decoded local rotations are independently checked against the
45-degree budget. Across all eight static pose files, maximum hand matrix-element
error relative to the translated target is 9.515137e-8 and maximum full-skin
position error against the ideal pose is 6.285018e-8 m. Self-collision, triangle-only
crossings, continuous time, anatomy and naturalness are not certified.

## Native motion experiment

Select 77-76 by lowest declared planning cost among decoded passing targets.
The original corrected motion has two collision clusters. This first bake edits
only the earlier cluster: a quintic envelope rises from zero at 1.408333 s to its
target at 1.675 s, then returns to zero at 1.875 s, midway through the clear gap
before the second cluster. The later cluster is deliberately retained and will
remain in the full-clock result. The contact pose at 2.091723 s is protected.

`wrist_waypoint_motion.py` computes the two-bone pose at eligible existing native
rotation keys. Only upper-arm, forearm and wrist tracks are written; shared
samplers are cloned. Key times and all frozen quaternion keys remain exact.
Key eligibility requires the entire interpolation support to lie inside the
allowed window and outside protected spans. The quintic guide has zero first
and second derivatives at its joins; this does **not** claim that baked glTF
SLERP has continuous acceleration.

The first run stopped after baking actor A because a joint-indexing expression
gave the rate checker a joint-major array. It is retained as
`reports/scene-pair-wrist-motion-v1/failure-observation.json`. The corrected
producer uses the existing tested position helper and runs in fresh v2.

V2 produces two native clips with maximum rotation edits of 17.200459 degrees
and 33.137746 degrees. Outside-window and protected poses have zero measured
matrix discrepancy; frozen native quaternion keys compare exactly. Maximum
sampled wrist-target position errors after interpolation are 2.602665 and
2.964454 mm.

The prior clip's original-bin rate limits are still reported, without relaxing
them to call the new motion accepted:

| Actor | Positional failures | Angular speed failures | Angular acceleration failures |
|---|---:|---:|---:|
| A | 355 | 19 | 30 |
| B | 261 | 97 | 42 |

Godot successfully imports and checks the two sources and two candidates:
444 sampled actor-frames, 77 bones each. Maximum position discrepancy is
5.465223e-7 m and maximum basis-element discrepancy is 6.851267e-7. This is engine
interoperability evidence, not motion quality approval.

The full 148-time local geometry audit queries changed poses and reuses a prior
sample only when both actors' decoded world matrices are exactly identical and
the bound input clips, geometry bytes and query implementation remain verified.
The completed audit contains 96 fresh directional mesh queries and 100 verified
unchanged-time reuses. There is no floor increase.

| Metric | Baseline | Candidate |
|---|---:|---:|
| Maximum local-clock vertex depth | 22.426395 mm | 21.973774 mm |
| Samples exceeding 5 mm | 37 / 148 | 31 / 148 |
| Depth at the original worst time, 1.675 s | 22.426395 mm | 0 mm |

The improvement is not uniform: ten original failing samples (26-35) clear, but
four previously passing samples (48-51) now fail. Twenty-seven failures remain
at their original times, including the unchanged later cluster. The new peak is
at 1.758333 s as the first approach leaves its waypoint. Report both removed and
introduced failures; the aggregate count alone hides that regression.

This candidate fails both the 5 mm geometry screen and the old motion-rate
limits. No Studio replacement or release approval follows. The next experiment
needs time-indexed approach and return targets with reach/collision evaluation
across the path; one static waypoint and a smooth scalar envelope are inadequate.
Both the static planner and successful v2 motion worker are terminal. The failed
v1 remains preserved separately.

## Reproduction

Local ignored character/evidence inputs and the existing runtime are required.
Preserve previous outputs; use fresh output directories.

```powershell
.venv/Scripts/python.exe -u scripts/plan_pair_swivel_pose.py reports/scene-pair-relinearized-completed-v2 reports/scene-pair-wrist-waypoint-v1 --wrist-waypoints
.venv/Scripts/python.exe -u scripts/fit_pair_wrist_waypoint.py reports/scene-pair-wrist-waypoint-v1 reports/scene-pair-wrist-motion-v2
```

New tests cover rigid reach and orientation preservation, exact zero-offset
equivalence, continuity near zero, straight-arm reach boundaries, rejection of
unreachable targets, guide endpoint derivatives, collision-cluster window
selection, and a real native GLB bake with protected keys and a shared sampler.
Eighty-two focused tests pass in both development and minimal runtimes. All 14 release capabilities remain
unapproved, and no training or model/data acquisition occurred.

| Static artifact | SHA-256 |
|---|---|
| Request | `10e6ca747c95420a84d96372c7ea5be1fbe9f57213f32febfba056568e98b958` |
| Proxy candidates | `6cd10c9f665d835c87dbbe67ad3e8b98a454db1ea5351106463c0bbdcd97fde4` |
| Rejected candidates | `e6183312ebec9aa648fe5c2ed02d8db87fc4e8b777413aa91eeb6787443aece9` |
| Decoded mesh audits | `3c4de14df98170f5b1c5c5067b5b80864bad123479c8f249de497f14a47ee3e5` |

| Temporal artifact | SHA-256 |
|---|---|
| Request | `66b4e9765ad51703a69e2bad27614a77abbfebe306d181a1d77843516de3635f` |
| Decoded tracks/rates | `455d1d6eee67d8204f6f6199d6bb8c3f8cf463f2ad1f4ace86c3c177d44eb6cf` |
| Local-clock geometry | `143316f141c11ed37fd365a80e5a5da7f953f9b30e0967b4293b106219dd150b` |
| Native engine verification | `ab33988a0669a4fa44ed316b935f36336bff29d98f8abe2993518fb807636148` |
