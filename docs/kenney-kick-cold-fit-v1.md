# Feasible-origin correction and controlled storage screen

The existing seed-77 Kenney kick is a development fixture for the general native
surface correction path. This study starts from its original motion, which passes
the original motion/contact conditions but penetrates the declared floor. It
does not use the previously rejected static pose as an initial animation.

Permissions retain nine body rotation tracks and add the measured left shin,
foot and toe tracks (nodes 51, 52, 53). Root translation and rotation remain
uneditable. Adding the measured peak time, 0.7333333492279053 seconds, to the
three original edit knots gives 72 controls. The 30-degree track limit,
220-mm all-joint displacement limit, original source-rate arrays and 1e-5 rate
tolerance remain unchanged. These are edit-preservation limits, not anatomical
or style calibration. No contact intent is invented.

One primary surface-vector iteration uses minimum-envelope guidance, a 0.02
trust fraction, unit quaternion storage and up to three measured-cap restoration
attempts. All probes receive actual serialization/decoding and complete declared
geometry checks: 2,017 times, 1,029 triangle-referenced vertices and 1,604 faces,
against the original Y=0 / 5-mm floor policy.

## Measured outcome

No changed export is accepted. All ten proposal fractions fail original motion
conditions and the floor screen. The largest fraction reduces peak penetration
from **49.727615 to 49.086401 mm**, and failed floor times from 234 to 232.
This 0.641214-mm improvement is insufficient: it fails 28 original native rows
and remains well beyond the 5-mm floor limit. The original zero-control motion
stays selected, passing the 108,471 native conditions and failing geometry.

The proposal solve reports `AlmostSolved`; its minimum-norm phase reports
`InsufficientProgress`. The first decoded measured-cap restoration model reports
`PrimalInfeasible`, yielding no repair direction. These are local model outcomes,
not proofs that the full motion problem or action is infeasible.

The job completes under the unchanged 900-second execution limit. Its last
execution observation is 468.406 seconds; all 474 resource observations replay.
The final root pose is exact at all 120 original keys. Source-cap arrays match
the earlier root-fixed study exactly. Raw outputs, rejected proposals, solver
records and resource traces remain under the ignored local study directory.

## Same ten controls, two storage policies

A separate screen re-exports every changed proposal using the existing `unit`
and `source-scale` policies. It runs no optimizer. Every unit export reproduces
the original proposal bytes exactly, then receives fresh native decoding. Both
modes retain all original caps, controls and root poses at all 2,017 geometry
times. Each output is screened against all 108,471 original native conditions.

| Proposal | Unit failed rows | Source-scale failed rows |
| --- | ---: | ---: |
| 1-0 | 28 | 39 |
| 1-1 | 45 | 38 |
| 1-2 | 80 | 42 |
| 1-3 | 69 | 63 |
| 1-4 | 65 | 66 |
| 1-5 | 67 | 43 |
| 1-6 | 60 | 37 |
| 1-7 | 56 | 31 |
| 1-8 | 89 | 88 |
| 1-9 | 64 | 47 |

Neither storage policy passes any changed proposal. The alternate geometry
evaluations are therefore **not measured**; no claim about their floor depths
or complete geometry pass follows from this screen. The default policy remains
unchanged. All 147 resource observations independently replay with archived
bindings intact. No motion, engine, support, semantic, human-review, training
target or release approval is granted.

Local records: `reports/kenney-kick-cold-peak-fit-v1` and
`reports/kenney-kick-cold-storage-screen-v1`. The next engineering experiment
rebuilds an optional local repair model at an actual rejected export while
retaining the original acceptance limits and complete geometry authority.
That [candidate-centered trial](native-surface-recentered-v1.md) also completes
without an accepted correction; its rebuilt local model returns no direction.
