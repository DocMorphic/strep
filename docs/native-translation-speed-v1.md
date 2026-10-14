# Faster positional repair, including velocity

The retained humanoid correction now has zero positional speed or acceleration
failures. An optional translation search repairs six of its previous eight
native failures without introducing a new failure. Two angular acceleration
failures still reject the clip; original animations remain selected.

## Algorithm changes

`native_translation_stencil.rank` now supports two-sample speed proposals as
well as its existing three-sample acceleration mode. The local search keeps its
acceleration-only default. The optional interval search explicitly targets both
positional metrics, while all angular failures remain in its diagnostics.

The interval scorer first reconstructs the complete original positional
baseline from the observed matrices and rejects a mismatch. It then identifies
the exact nonzero native interpolation support and descendant joints. Rows
outside that support remain identical for every candidate and are accounted
once. The updated block includes two samples beyond either support edge, so
velocity and acceleration differences crossing those edges remain present.
Joint-major displacement and frame-major rate orders are preserved.

No row, candidate, cap, clock or correction allowance is removed. Each candidate
still receives a complete positional score plus the fixed unmodeled rows, then
must pass full fresh export/decoding, authoring and motion checks. Contacts and
geometry are separate gates. These methods do not approve an animation from a
prediction.

## Matched scoring comparison

The prior complete scorer is archived from Git revision `3ea8946`. Both scorers
receive the same freshly decoded eight-failure humanoid and the complete
729-candidate velocity-support population.

| Measurement | Previous scorer | Optimized scorer |
| --- | ---: | ---: |
| Scoring seconds | 2.759871 | 0.030611 |
| Positional rows accounted | 64,260 | 64,260 |
| Positional rows recomputed per candidate | 64,260 | 1,344 |
| Positional rows reused per candidate | 0 | 62,916 |

Maximum-error, failed-row and newly-failed-row arrays match exactly for every
candidate. Squared positive sums agree within the declared `1e-14` relative /
`1e-30` absolute comparison, with a maximum observed difference of
4.135903063e-25 from partitioned summation. This is about a 90-fold improvement
for this specific scoring comparison, not an end-to-end or universal speedup.
Raw score arrays and both source versions are retained locally. All 35 resource
observations independently replay.

## Actual continuation and replay

Starting from the verified eight-failure state, the same original source,
authoring, 63 controls, caps, clocks and one-neighbor/64-correction policy are
retained. The eight-stage/32-probe limits select the first exported proposal in
each of three stages. Stage zero ranks all 729 velocity proposals; the next two
rank all 19,683 acceleration proposals each. A fourth stage has no supported
positional failure left to target. Three neighbors and four full exports are
retained; the final correction list has 48 entries.

| Measurement | Returned seed | Partial best |
| --- | ---: | ---: |
| Intended motion failures | 0 | 0 |
| Native motion failures | 8 | 2 |
| Old failed rows repaired | — | 6 |
| New failures introduced | — | 0 |
| Worst normalized excess | 1.059917931e-6 | 4.963145832e-7 |
| Failed floor times | 0 / 2,017 | 0 / 2,017 |
| Peak floor depth | 4.998959799 mm | 4.998959799 mm |

The remaining rows are LeftArm angular acceleration at frame 259 and LeftForeArm
angular acceleration at frame 363. All 107,895 original conditions remain
required, and both complete sampled floor audits cover all 1,029 referenced
vertices under the unchanged 5-mm limit. The returned bytes remain the failed
seed; the partial best is not adopted as a passing motion.

Execution completes in 55.734 seconds with 73 resource observations. Fresh
best/returned numerical replay completes in 39.531 seconds with 57 observations.
Both traces independently replay against the unchanged 2,776,629,248-byte
admission requirement. Complete export bytes, worlds, native/norm/cap/scale/
control/clock arrays, original recomputed caps, intended motion, typed
continuations and all 2,017 floor observations reproduce. All four recorded
export/receipt/array hashes match; other neighbors are not numerically replayed.

## Source verification and next work

All 209 related checks pass in 58.32 seconds. Nine additional checks cover
velocity, cropping at either clip edge, unaffected joints, full row accounting,
fabricated baselines and a real high-rate GLB velocity failure. The retained
first run has 208 passes and a fixture failure: the original low-rate fixture
does not exceed the speed tolerance. A fresh high-rate constant source provides
the needed velocity failure while deriving its original caps normally. No
existing motion tolerance or failure assertion is weakened. Its corrected run's
76 resource observations independently replay; the failed run's 75 remain saved.

The focused Windows/Linux workflow passes all eight jobs for preceding commit
`3ea8946`. The earlier broad `c1c0bb9` run passes eleven jobs, including every
main source shard, but is incomplete: Windows material tests are canceled after
43 passes in 1,155.83 seconds. That job now retains every test, uses the existing
full-source 90-minute budget and prints test names/durations. New full hosted
verification remains outstanding; no green broad-suite claim is made.

Next, coordinate quaternion storage corrections against complete angular and
positional constraints, then continue broader actions, rigs, scene interactions,
styles, editing, transitions, engine and independent animator evaluation. No
weights, training, reserved held-out, live rendering/engine or human cleanup
evidence changes here. All fourteen release capabilities remain unapproved.
