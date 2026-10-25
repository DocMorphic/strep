# Complete-region separation guidance and retained wave failures

The new blocked separation objective evaluates every vertex pair in two moving
regions without allocating a pair-by-control Jacobian. Its 88 focused regression
checks pass. On the retained wave fixture, it reduces target proper crossings
from 35 to eight, but the exported motion still fails geometry and correction
speed checks. This is development evidence, not an accepted animation repair.

## Wider native-key control

Following [the two-key experiments](wave-native-key-repair-v1.md), V4 permits
right-arm nodes 14–16 at native keys 51–60. The residual allowance remains five
degrees, total edit allowance remains 25 degrees relative to the immutable
floor-corrected source, and correction speed remains 40 degrees/second. The left
arm, translations and all other keys remain fixed.

Three current-triangle direction rounds retain 35 target crossings and all fail
native correction-speed limits. Independent serialization measures 40.052960,
40.002756 and 40.002756 degrees/second. Each reaches its 60-iteration limit;
none is selected. The unchanged diagnostic export fails geometry at 13 of 46
affected-interval times. All 439 dense floor/angular/speed observations and all
46 complete before/after geometry audits independently replay. These finite
search failures do not prove infeasibility.

## Complete moving regions within a memory budget

At 1.8593750149011612 seconds, use every vertex of faces with dominant skin node
16 (right hand) or 21 (head): 65 hand and 2,115 head vertices, or 137,475 pairs.
This explicit grouping guides a proposal; it does not replace complete surface
audits or establish anatomical labels for other rigs.

The first plane experiment stops before fitting because 13 head-region vertices
also have positive right-arm skin influence. Treating that region as fixed would
give incorrect derivatives. The second includes both moving regions but stops
before allocating an estimated 395,928,000-byte expanded derivative array, above
its 256 MiB workspace allowance. Both failures remain archived.

`pair_hinge_objective` sums squared negative projected clearance deficits over
all pairs in blocks and returns gradients for both vertex sets. The caller
chains these gradients through its native pose derivatives. No points or pairs
are discarded. Unit-normal, finite-coordinate, pair-count and workspace checks
reject unsupported requests; the method is neither a collision predicate nor a
feasibility certificate.

The helper estimates 412,160 bytes of temporary workspace for this fixture,
excluding the caller's pose/control Jacobian. This estimate is not a whole-job
memory measurement. Expanded scalar loss and both vertex gradients agree in the
fixture comparison. Tests cover dense expanded control gradients, finite
differences, block boundaries, shared vertices, symmetry, unchanged inputs and
invalid/budget-limited requests. Both existing focused suites complete with
88 passes; they are already registered in full and focused CI inventories.
No new hosted CI result is claimed.

## Exported plane proposal

Choose the best initial direction among both signs of all nondegenerate head
face normals and the centroid direction. Keep it fixed during fitting and seek
3 mm projected clearance. The initial minimum projected gap is -52.495 mm;
the final gap is -1.325 mm, still short of clearance. SLSQP stops after 197
iterations with a positive-directional-derivative failure.

The proposal passes the native-key bounds used for diagnostic selection and
reduces the target count to eight. All eight remaining proper pairs are still
in the hand/head dominant-node grouping. They are different triangle pairs from
the input at that time. Selection within this experiment does not approve the
clip or replace the project's original animation.

Across all 46 affected geometry times, failures fall from 13 to six, and proper
pair observations fall from 437 to 77. All 77 are newly introduced pair
observations relative to their corresponding input times. They therefore remain
explicit failures despite the lower aggregate count. Ambiguous surface flags
are retained, not exempted.

The 439-sample dense audit measures 4.644 mm peak floor depth and right-arm edits
within the original 25-degree caps. Predicted/exported skin positions agree to
9.19e-16 m. However, peak sampled correction speed is 40.135596 degrees/second,
which exceeds the unchanged 40-degree/second limit. Passing native-key speed
checks is insufficient to establish speed between keys. The production worker
completes with 144,506,880 bytes sampled peak process-tree RSS, and all 253
resource observations replay. No engine or human quality approval is asserted.

## Retained evidence and next work

Ignored development-checkout reports retain `wave-native-key-repair-v4`,
`wave-native-key-replay-v3`, all three `wave-hand-head-plane` experiments and
`wave-hand-head-plane-replay-v1`. Source assets and prior failed proposals remain
unchanged. Independent plane-proposal serialization reproduces the candidate
byte for byte, verifies unchanged unpermitted channels/keys, and replays all
46 complete before/after surface audits and all 439 dense observations. It
confirms native-key correction speed of 39.996055 degrees/second while the
between-key dense result fails at 40.135596 degrees/second. All 199 replay-worker
resource observations verify. Across the wider search, its replay, two stopped
plane experiments, final plane experiment and its replay, 1,044 resource
observations verify; four workers complete and two retain explicit failures.

The next repair must constrain the actual interpolated correction rate and
separation across affected times together, while preserving original pose caps,
resting-arm/action targets and newly clear surfaces. A single target frame's
improvement cannot approve a clip. Broader actions, rigs, objects, partners,
engine import and developer/animator review remain part of the project-wide
goal; no release criterion or capability status changes here.
