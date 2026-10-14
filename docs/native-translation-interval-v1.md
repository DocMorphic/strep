# Ranking motion across the complete affected interval

An optional translation ranking now considers every uniform displacement,
speed and acceleration row on the selected actor, including neighboring joints
and the native support edges. On the retained crawl development case it repairs
22 of 30 native failures without introducing a new failure. Eight failures
remain, so the original animation stays selected.

## Method

`scripts/native_translation_interval_rank.py` uses the existing complete
translation-stencil population: all absolute negative-neighbor, nearest-value
and positive-neighbor choices on one to three consecutive native keys. The
largest population remains 19,683. Existing default searches stay unchanged.

For each candidate, the observed parent's linear transform maps the change in
local translation to the world positions of descendant joints. Native
interpolation weights cover the entire uniform clock. The score includes all
joint displacements, velocities and accelerations, including differences
crossing either edge of the changed support. Original source caps, tolerance
and normalization stay fixed. Candidates are processed in 32-item chunks, with
an explicit maximum of 128, rather than materializing every candidate's entire
motion simultaneously.

The established audit stores displacement rows by joint and rate rows by frame.
The new scorer preserves both orders. Its first test run catches an incorrect
axis layout before the development study starts; that failed run is retained.
A separate regression verifies that a joint-major displacement failure is not
misreported as a new row.

Ranking prefers no new predicted positional failures, then the complete motion
merit and fewer absolute corrections. Unmodeled rows are fixed in this heuristic:
contacts, geometry and serialization still need their own complete checks.
The optional rank hook must return a complete integer permutation; dropped,
duplicated or fabricated population indices reject.

The checked search exports and independently decodes every tested candidate,
then verifies every original condition, cap, scale, control and authoring bound.
A passing prediction is never animation acceptance. This remains an optional
research search, with no production fitting-default change.

## Matched development result

The comparison starts from the same freshly replayed 30-failure crawl seed as
the [local target search](native-translation-stencil-search-v1.md). Both retain
the same source, authoring, 63 controls, clocks, caps, one-neighbor/64-correction
policy and eight-stage/32-probe limits.

| Measurement | Seed | Local target ranking | Full positional interval ranking |
| --- | ---: | ---: | ---: |
| Native failures | 30 | 30 | 8 |
| Old failed rows repaired | — | 1 | 22 |
| New failures introduced | — | 1 | 0 |
| Worst normalized excess | 1.090261849e-5 | 8.580816014e-6 | 1.059917931e-6 |
| Changed neighbors exported | — | 61 | 8 |
| Execution seconds | — | 293.110 | 617.000 |
| Failed floor times | 0 / 2,017 | 0 / 2,017 | 0 / 2,017 |

The new method is slower in this version because it scores all 64,260 positional
rows across the complete 19,683-entry proposal population at every stage. All
eight stages select their first complete export. Nine exports, including the
seed, are retained. The remaining 43,635 motion rows are fixed in proposal
ranking and are independently recomputed after each export. All 107,895 original
conditions remain required.

The best output still has one positional speed failure, five positional
acceleration failures and two angular acceleration failures. The hip acceleration
failure at frame 279 is repaired. The five positional acceleration rows cluster
at frames 195 and 259. The speed failure is LeftHandIndex3 at frame 111; angular
acceleration failures are LeftArm at frame 259 and LeftForeArm at frame 363.
Both best and returned outputs pass all 2,017 sampled floor times over all 1,029
referenced vertices, with unchanged 4.998959799-mm peak depth under the original
5-mm limit. The intended curve still has zero failures. Returned bytes remain
identical to the failed seed.

## Verification and limits

All 200 related tests pass in 60.46 seconds, including 21 new interval-edge,
joint/row-order, chunk equivalence, real native export and population-preservation
checks. This overlaps the previous 179-test population and is not summed as
distinct coverage. Its 78 resource observations independently replay. The
retained first validation run has one failure and 198 passes, with all 74
resource observations replayed.

The development study completes with 626 resource observations and a sampled
413,429,760-byte peak process-tree RSS. Fresh best/returned numerical replay
completes in 39.546 seconds with 57 observations. Both resource traces replay
against the unchanged 2,776,629,248-byte admission policy. Complete export bytes,
worlds, native/norm/cap/scale/control/clock arrays, original recomputed caps,
intended motion, typed continuations and every floor sample reproduce. All nine
receipt/array/file hashes match; the other neighbors are not numerically replayed.

Next, address the remaining positional, speed and angular failures and improve
ranking cost without dropping the accounted row population. Sampled development
results on one action/rig do not establish continuous collision freedom,
semantic realism, engine playback, held-out generalization or animator approval.
No model/checkpoint, training, reserved held-out, live renderer/engine or human
cleanup study changes here. All fourteen release capabilities remain unapproved
under the single whole-project goal.
