# Batch transform lifetime and simultaneous motion limits

The batched transform evaluator no longer retains its input and output arrays
in a recursive closure until cyclic garbage collection runs. An iterative
parent-chain traversal preserves multiplication order, unordered parents,
multiple roots and cycle rejection. It also avoids Python's recursion limit
for long valid chains. Production garbage-collection settings are unchanged.

## Actual humanoid lifetime comparison

The reference function is extracted from committed `cf78005` source. Four local
matrix batches reconstructed from the retained humanoid's 2,017-time, 61-node
observations are evaluated by both functions. All four outputs match
**bit-for-bit**. Each matrix batch occupies 15,748,736 bytes.

Cyclic GC is disabled only for this controlled lifetime measurement. After
deleting caller references, weak references show eight old input/output arrays
still alive, totaling **125,989,888 bytes (about 120.15 MiB)**. The new function
retains none of those arrays. Collection is restored afterward. This proves
array release, not immediate OS allocator reclamation or overall model RAM.
The guard completes in 1.015 seconds execution; all 19 recorded resource
observations and bindings replay. The brief allocation peak is not guaranteed
to be captured by resource polling, so it is not inferred from sampled RSS.

Six new tests cover immediate release without cyclic collection, independent
matrix-product parity for unordered forests, a 1,500-node chain and three
cyclic graphs. Together with existing scene, clip-edge, norm, paired-storage and
surface checks, **140 tests pass** in 32.88 seconds. Guard execution takes
33.422 seconds; all 51 resource observations replay. The declared inventory is
now 479 Python modules / 42 Node suites, with 41 focused modules. No existing
test is removed or weakened.

## Why one-row correction is insufficient

The saved floor-passing development curve still has one intended angular
acceleration violation at original row 98,195 and 24 native export violations.
The original one-row correction uses an archived full vector Jacobian and its
current radial direction. All 63 control components remain available. Its
1.25, 2 and 4 multipliers move the control vector by about 1.000e-6, 1.600e-6
and 3.200e-6, all inside the declared 0.001 proposal-step budget.

Every probe passes all sampled floor times at 4.998972 mm peak depth but fails
unchanged motion acceptance. The original angular row is repaired; a different
position-speed row, 27,325, becomes positive. The four-times probe additionally
introduces displacement/angular-speed failures. Full counts are:

| Multiplier | Intended failures | Native failures | Failed floor times |
| --- | ---: | ---: | ---: |
| 1.25 | 1 | 23 | 0 |
| 2 | 1 | 25 | 0 |
| 4 | 8 | 29 | 0 |

The worker completes at 46.781 seconds / 64 replayed observations. A fresh
scalar gradient study then evaluates every original condition at central
offsets of 1e-5 over **all 63 controls**, using the current curve rather than
the archived anchor. Gradient norms agree to about 1.6e-8 relative; all three
exported GLBs, decoded worlds, joint/rate rows and floor samples reproduce exactly.
The controls, intended rows and 119 passing control-bound rows differ slightly;
the largest control-bound discrepancy is 2.264001e-11. Both control-bound
populations still pass strictly. Counts
and the newly failed speed row remain the same. Stale derivatives therefore
do not explain the failed correction: shared controls must protect simultaneous
constraints across different times and condition groups.

The fresh study completes at 53.813 seconds / 71 replayed observations and
sampled tree RSS peaks at 266,448,896 bytes. This is measured whole-job behavior
for this study, not a matched RSS comparison with the older full-Jacobian
experiment. Original source, control permissions, caps, clocks, 1,029 referenced
surface vertices, 2,017 geometry times and 5 mm floor tolerance remain unchanged.
Original clips remain selected; no candidate is admitted.

## Retained conditioning experiment

Multiplying the retry's quadratic objective by 79,549.587525 preserves its
mathematical minimizer because its linear objective is zero; this follows from
the [documented quadratic problem format](https://clarabel.org/stable/python/getting_started_py/).
It changes neither constraint matrices nor bounds. In this measured case it
does not help: the retry remains `InsufficientProgress`, hard affine excess
becomes 3.037393e-6 and soft excess becomes 2.817806e-8. The original unscaled
secondary has passing hard rows and 5.050774e-9 soft excess. The scaled result
is rejected and no objective-scaling change enters production. This diagnostic
completes in 10.141 seconds / 28 replayed observations. Solver statuses describe
termination, not full animation acceptance; see [Clarabel's result definitions](https://clarabel.org/stable/python/getting_started_py/#Results).

Local ignored evidence is retained under `reports/fk-lifetime-validation-v1`,
`reports/fk-lifetime-matched-v1`, `reports/crawl-local-norm-projection-v1`,
`reports/crawl-current-norm-projection-v1` and
`reports/native-secondary-scaling-v1`. Matrix parity and resource audits share
repository arithmetic; they do not certify engine playback, continuous/self
collision, dynamics, semantic realism, learned quality or animator cleanup.

Next use simultaneous original norm constraints for near-feasible correction,
then complete native export/mesh checks and bounded storage repair. The single
whole-project goal and all 14 unapproved capabilities remain intact, including
arbitrary actions, object/partner interaction, rig transfer, editing/style,
transitions, engine imports and independent review. No new model training,
generation, reserved held-out evaluation, live rendering or human approval is
performed by these experiments.
