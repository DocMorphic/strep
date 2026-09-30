# Time-indexed paired wrist paths

The first collision cluster now has zero measured vertex penetration at the
audited times. The full 148-time clock still has 15 failing samples in the later,
unchanged cluster. This is an experimental path, not an approved animation.

## Method

`plan_pair_waypoint_path.py` uses the completed single-waypoint temporal audit
to select ten planning times across the first approach window, 1.408333 to
1.875 seconds. Starting clips remain the accepted local correction in
`scene-pair-relinearized-completed-v2`, not the rejected temporal experiment.

For each of six signed scene axes, search 100 paired states: symmetric wrist
offsets of 0, 20, 40 or 60 mm, and independent elbow swivels of -30, -15, 0, 15 or
30 degrees. Reject unreachable poses and native edits exceeding 45 degrees.
Forearm capsules derived from affected skin vertices provide a node cost;
they do not certify full-body or continuous collision clearance.

Dynamic programming selects a connected path with zero endpoint controls.
Component guide-rate caps are 0.8 m/s and 300 degrees/s for each swivel. Node
costs sum a normalized squared capsule-overlap penalty and a small pose penalty;
edges add a time-weighted normalized squared guide-rate penalty. These are
finite search heuristics, not physical energy or actual joint-motion bounds.
All six routes are connected; Xplus has the lowest declared cost, 9.754992.
Its maximum guide rates are 0.685714 m/s and 257.142857 degrees/s per swivel.
Piecewise-linear guides do not provide acceleration continuity.

Before baking, `waypoint_path_evidence.py` binds the saved inputs, implementation
snapshots and lattice, independently recomputes every route, and verifies the
selected optimum. `fit_pair_wrist_waypoint.py --path-plan` fits the guide to
existing native upper-arm, forearm and wrist keys. Protected poses, clocks and
frozen keys remain exact. Original-relative motion limits are measured without
rebasing them to the candidate.

## Completed local evidence

| Measurement | Baseline | Candidate |
|---|---:|---:|
| Full local-clock maximum vertex depth | 22.426395 mm | 21.433380 mm |
| Samples exceeding 5 mm | 37 / 148 | 15 / 148 |
| Edited-window maximum vertex depth | 22.426395 mm | 0 mm |

All 22 failures in the first cluster clear, with no newly failing samples.
The remaining 15 occur from 1.966667 to 2.083333 seconds, before the protected
contact pose at 2.091723 seconds. The preceding single-waypoint experiment had
31 failing samples and introduced return-path collisions; this path clears
that return interval at the sampled times.

The full audit performs 96 fresh directional mesh queries and reuses 100 prior
times only after exact equality of both decoded actor world transforms and
verification of bound geometry inputs. Maximum floor increase is zero. This
vertex-based sampled audit does not certify triangle-only crossings, continuous
time, anatomy or naturalness.

Godot imports four clips and verifies 444 sampled actor-frames with 77 bones.
Maximum position discrepancy is 5.366924e-7 m and basis-element discrepancy is
6.851266e-7. Maximum native rotation edits are 16.307996 and 16.381376 degrees.

| Actor | Positional failures | Angular speed failures | Angular acceleration failures |
|---|---:|---:|---:|
| A | 301 | 64 | 39 |
| B | 194 | 69 | 38 |

Both actors have a maximum sampled wrist-guide error of 22.857143 mm. The ideal
guide ends at 1.875 seconds, but the final editable native key is at 1.791052;
the next key at 1.841163 is frozen because its interpolation support extends
beyond the allowed window. The baked motion returns to the source sooner than
the requested guide. This mismatch is retained in the report, not treated as
successful target tracking.

Next, make planning respect the actual native support boundaries and evaluate
actual joint rates, then address the later collision cluster. Do not widen
protected windows or relax limits silently. No Studio replacement or release
approval follows this experiment. All 14 release capabilities remain unapproved;
no model training or new model/data acquisition occurred.

## Reproduction and validation

Local ignored character/evidence inputs and the existing runtime are required.
Use fresh output directories and preserve prior artifacts.

```powershell
.venv/Scripts/python.exe -u scripts/plan_pair_waypoint_path.py reports/scene-pair-wrist-motion-v2 reports/scene-pair-waypoint-path-v1
.venv/Scripts/python.exe -u scripts/fit_pair_wrist_waypoint.py reports/scene-pair-wrist-waypoint-v1 reports/scene-pair-waypoint-path-motion-v1 --path-plan reports/scene-pair-waypoint-path-v1
```

The expanded focused suite passes 101 tests in both development and minimal
runtimes. Coverage includes exhaustive graph-search agreement, disconnected
paths, rate/domain rejection, independently replayed evidence tampering, and
native baking with shared samplers and protected keys. Both workers are terminal.

| Temporal artifact | SHA-256 |
|---|---|
| Request | `332056ffc0004131902cf92080716a4be85fa663709b5ea2b53904fb13c4a5df` |
| Decoded tracks/rates | `f5943aefc25ac9c9d70da3836dde5c17e2e28d3c3a1a7c23510b117e3eaa4cb6` |
| Local-clock geometry | `d0e6891f205868ae4de1bf20e41c12ea589fda49de3c6c693866a9f9175014c7` |
| Native engine verification | `20e84ca4d3bc4767c0baeaa364d21fdd9624f000fa63adbdb855fd095c58a112` |

See [the preceding single-waypoint experiment](paired-wrist-waypoint-v1.md).
