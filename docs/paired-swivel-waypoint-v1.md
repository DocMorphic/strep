# Wrist-preserving approach waypoint planning

The first geometric waypoint experiment reduces the latest correction's worst
sample from **22.426395 mm to 15.342952 mm** while keeping both wrist transforms
fixed. This is a static planning result, not an accepted animation: all four
audited poses still fail the 5 mm vertex-penetration screen. None replaces the
existing Studio comparison.

## Why a different parameterization

The [six local direction objectives](scene-pair-directional-v1.md) did not produce
a usable replacement. Here the planner uses the redundant motion of a two-bone
arm: rotate its elbow about the shoulder-to-wrist line, then compensate at the
wrist to preserve the hand's world orientation. This moves the forearm without
asking an optimizer to rediscover the fixed-hand constraint through a penalty.

Constrained trajectory planning separates task constraints from obstacle
avoidance. Relevant primary references are CMU's [goal-set constrained trajectory
optimization](https://publications.ri.cmu.edu/manipulation-planning-with-goal-sets-using-constrained-trajectory-optimization)
and Berkeley's [TrajOpt documentation](https://rll.berkeley.edu/trajopt/doc/sphinx_build/html/).
They motivate testing alternate feasible configurations rather than treating one
local minimum as exhaustive. This project has not installed or reproduced those
planners, and their robotics results do not establish animation naturalness.

`elbow_swivel.py` implements the independent kinematic primitive. It requires a
direct upper-arm/elbow/wrist chain with rigid transforms. It preserves bone
lengths, changes only upper-arm and wrist local rotations, and preserves the
entire wrist subtree in world space. Other branches under the upper arm move
with it; branches outside that subtree stay fixed. Cyclic hierarchies, coincident
shoulder/wrist positions, scaling and shearing are rejected. No anatomical joint
limit, muscle, balance or self-collision model is implied.

## Fixed experiment

Input is the accepted local candidate in
`reports/scene-pair-relinearized-completed-v2`, with bound clips, geometry,
source files and implementation snapshots. The selected time is the **latest
candidate's measured peak**, sample 34 at 1.675 s, not a newly chosen favorable
frame. Both chains are `LeftArm / LeftForeArm / LeftHand`.

For each actor, test swivels of -45, -30, -15, 0, 15, 30 and 45 degrees. These are
**new pose-planning candidates relative to the current correction**. They are not
within the previous five-degree edit request and do not inherit its motion-rate
acceptance. That request, its exports and its evaluation remain unchanged.

Rank all 49 pairs using finite forearm-segment distance minus the two capsule
radii. Each radius encloses the sampled vertices with any positive influence
from the forearm joint, including mixed skinning weights. This deliberately
loose volume is only a ranking heuristic: it does not replace full-body queries,
and overlapping capsules do not prove mesh intersection. All 49 pairs have
negative proxy clearance, so no proxy-free candidate is found.

The declared selection alternates least squared swivel angle among pairs with
at least 2 mm proxy clearance and greatest proxy clearance, keeping four unique
pairs. Here only the latter list contributes. Full mesh tests therefore cover
four ranked poses, **not the complete 49-pair grid**.

For each selected pair, serialize separate static GLBs with no animation tracks
and a planning-only flag. Decode their node transforms and skin vertices, verify
the retained hand transforms and fully hand-influenced vertices, then query both
full character meshes. These files are waypoint references, not playable clips.

## Measured results

| Actor A swivel | Actor B swivel | Full-mesh maximum vertex depth | 5 mm screen |
|---:|---:|---:|---|
| -45 degrees | -45 degrees | 15.342952 mm | Fail |
| -30 degrees | -45 degrees | 22.167253 mm | Fail |
| -45 degrees | -30 degrees | 22.103107 mm | Fail |
| -15 degrees | -45 degrees | 22.942765 mm | Fail |

All four have maximum floor depth 2.649304 mm; the largest measured floor
increase is 3.611117e-8 m. The best pair changes the upper-arm and wrist local
rotations by approximately 45 degrees each relative to its starting pose.

Across eight decoded pose files, the maximum full-skin position discrepancy
against the ideal kinematic pose is 5.893473e-8 m. The maximum retained hand
matrix-element discrepancy is 1.014292e-7; maximum error over 2,735 fully
hand-influenced vertices per actor is 5.893473e-8 m. This does not assert that every
mixed wrist/forearm vertex is fixed.

Both deepest vertices in each of the four pairs have 100% `LeftForeArm` skin
weight. This is skin influence attribution, not independent anatomical labeling.
The residual collision is not explained away as a changed hand-contact point.

No whole-clip or continuous-time collision audit, positional/angular motion
approval, engine import, animator rating, cleanup timing or release approval has
been performed for these targets. The finite angle grid and proxy selection do
not prove that every fixed-wrist configuration is infeasible.

The next experiment should author **pre-contact wrist waypoints**, preserving
the contact pose and timing while allowing the approach to route around the
partner. Fit the two-bone reach and elbow branch to these targets, then evaluate
the resulting temporal trajectory and actual exported geometry. Do not spend a
whole-clip audit on the failed static poses above or silently relax the earlier
request's bounds.

## Reproduction and evidence

These commands require the ignored local character/evidence inputs. They are
not a standalone reproduction from the public source snapshot alone.

```powershell
.venv/Scripts/python.exe -u scripts/plan_pair_swivel_pose.py reports/scene-pair-relinearized-completed-v2 reports/scene-pair-swivel-pose-v1
.venv/Scripts/python.exe -m pytest -q tests/test_elbow_swivel.py tests/test_timed_rotation_edit.py tests/test_directional_pair_proposal.py tests/test_pair_direction_peak.py
```

Sixty-two focused tests pass in both development and minimal runtimes. New tests
cover local-transform reconstruction, reversible swivels, exact wrist-subtree
preservation, unsupported inputs, finite-segment distance edge cases, capsule end
caps, deterministic candidate selection, duplicate rejection and static pose
serialization without source mutation. The real pose worker is terminal.
Candidate-input validation and static-export validation were strengthened after
that run; its original method snapshots remain unchanged.

Local evidence:

- `reports/scene-pair-swivel-pose-v1/request.json`: protocol and input bindings.
- `proxy-candidates.json`: all 49 candidates and edit magnitudes.
- `audits.json`: all four decoded full-mesh outcomes, including failures.
- `reports/scene-pair-swivel-pose-v1-attribution.json`: hash-bound deepest-vertex
  influence attribution for every audited pair.

| Artifact | SHA-256 |
|---|---|
| Request | `9d0fee592ba62ad2707be19135cc7fb23d9fc22cacb3d19027d95f159c95a8cb` |
| Proxy candidates | `945895e428af16e9d530f9d2dd6539c388698e3623b0160d1be1696fe4d1f9a0` |
| Full-mesh audits | `39679bbc0cf76bad9007c1649e01f6f7b49ddf0d0266feaf831c2afe8affe728` |

All 14 release capabilities remain unapproved. No new model, training data or
third-party dependency was acquired.
