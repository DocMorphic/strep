# Original-axis self-surface proposal bounds

The supported high-five v4 clears localized hand and partner checks but
introduces ten B shoulder crossing pairs. The fixed midpoint introduces
eleven pairs and fails contact. These measured failures are retained in
[native-hand-reference-v1.md](native-hand-reference-v1.md). Minimizing wrist
rotation alone is insufficient; the solver needs self-surface guidance.

`scripts/native_self_separation_cuts.py` accepts a complete original vertex
population, original triangle topology and explicit unordered triangle pairs.
For each pair it uses the existing `separation_axis` function on the original
triangles, then retains all nine vertex-pair inequalities on that fixed axis.
Both sides use the same actor's actual posed vertices and derivatives.
Shared vertices, zero rows and shared-edge pairs remain included.

The lower bound is `min(clearance, original axis gap)`. An original overlap
keeps its negative gap and is explicitly reported as unresolved. It never
becomes positive clearance or a valid source solid. Neither warm starts nor
subsequent proposals recenter the reference. Candidate vertices and their
complete Jacobian are evaluated against the stored axes and lower bounds.

Bounds are 250,000 vertices, 100,000 triangles, 4,096 distinct pairs and an
explicit maximum of 100,000 rows. Every pair requires nine rows; exhaustion
rejects the complete request rather than returning a subset. Derivative
evaluation allows 1–192 controls, with an explicit 128-MiB input-Jacobian and
estimated temporary-workspace budget. These estimates do not replace the
process memory guard or guarantee third-party peak allocations.

Twenty-eight local tests cover complete pair rows, both moving sides,
directional differences, translation cancellation, rigid reference
transforms, source overlaps, shared vertices, input mutation, malformed
identities and exhausted row/Jacobian budgets. The guarded test run takes
18.281 s at 89,415,680 sampled bytes; all 20 resource observations replay.
The source inventories now contain 552 Python/45 Node suites, with 116/five
in the contact subset. These are inventory counts, not complete-inventory
passes.

The same 28 tests pass on Ubuntu (0.64 s) and Windows (1.03 s) in
[hosted run 38984947572](https://github.com/DocMorphic/strep/actions/runs/38984947572),
source `c642868`. This is focused helper evidence, not a full-inventory or
motion-quality pass.

This helper only guides a solve for its explicit pairs. It does not discover
new intersections, prove nonlinear feasibility, certify a mesh/solid, or
approve an animation. Complete actual-surface checks must follow every
candidate, including newly introduced pairs and unedited source defects.
No physical acceptance threshold or original animation is changed.

## High-five application and distinct guide epochs

The first trial collects every newly introduced B pair from the v4 and
midpoint full-body scans, plus all five wrist pairs from the 150-mm-finger
pose. Original triangle identities remove pairs already crossing in the
configured source. The resulting 19 pairs contribute 171 rows: twelve
original-axis gaps are positive and seven are zero/unresolved. Shared
topology is retained. These rows supplement all 6,130 previous pose rows.

Guide residuals use a declared 1-mm normalization and 1e-12-m arithmetic
cushion. Their search reserve is zero so shared-vertex rows remain possible;
the existing pose rows retain their 0.001 normalized search reserve. This is
a numerical convention for proposal guidance. The actual physical contact,
containment and triangle-crossing policies remain unchanged and are checked
separately. Original control rotations and joint-displacement bounds always
refer to the unchanged native sampler, never the current proposal.

With A frozen and B's arm/forearm/wrist active, the original-axis trial ends
with 61 negative rows. Partner checks find zero crossings, hand self scans
zero records, and B's complete self scan 70 transverse pairs. Thus clearing
the measured surfaces does not establish contact feasibility.

A second condition adds B's RightShoulder with an explicit 10-degree local
edit allowance; its world displacement remains capped at 60 mm. Other
angular permissions and the 150-mm-finger / 60-mm-wrist-and-body bands remain
unchanged. B now has twelve active controls; A still has nine frozen controls.
This is a different authoring permission, not a pass of the arm-only trial.
It leaves 15 negative rows: one material-frame, six hand-support, three
paired-frame and five original-axis guide rows. Its direct gap/opposition/
tangent errors are 5.764153 mm / 5.764530 degrees / 17.308186 degrees.
Partner and localized hand checks pass at 2 s. Complete B self-pair comparison
retains 70 original pairs, removes 65 and introduces zero. This candidate is
still rejected because contact fails.

Independent replay of this second condition reproduces every saved world,
vertex and all 6,302 inequalities exactly, including the failures. Material
frame directional error is at most 1.031641e-9; normalized self-cut
directional error is at most 1.986000e-8. The guard takes 146.094 s at
261,906,432 bytes (145 resource observations replayed); array replay takes
38.828 s at 192,086,016 bytes (40 observations replayed).

Fixed axes can overconstrain a locally valid surface as its pose changes.
A distinct trial therefore constructs guide axes and their lower bounds
from the second condition's explicitly pinned, fully scanned B pose. The
pure helper's reference is the vertex array supplied by its caller; in
this condition that array is previous-candidate guide geometry. Its input
qualifies this vocabulary explicitly. The original motion, zero-control
epoch, edit limits and physical acceptance tests remain separate and
unchanged. This is not a pass of the original-axis guide condition.

The first attempt stops before fitting because its warm pose falls slightly
below the optimizer's 0.001 protected-row search reserve. Its failed guard
is retained and independently replayed: 33.625 s, 247,070,720 bytes,
35 observations. A fresh attempt verifies a B-only scaling ray toward the
unchanged zero controls, retaining A exactly; fraction 0.9999 brings every
protected row above the same reserve. It completes with 25 negative rows,
zero partner crossings, zero localized hand records and 70 complete B
self-crossing pairs. This is another rejected proposal, not global
infeasibility. Its guard takes 145.172 s at 249,995,264 bytes
(144 observations replayed).

The latter fit reaches B's chosen 10-degree shoulder allowance. A separately
declared 15-degree shoulder condition retains the same measured guide,
all other authoring permissions and the unchanged physical policies. Warm
shoulder controls are rescaled from the 10-degree chart to the 15-degree
chart, verifying the same world pose to 1e-12 before the B-only reserve ray.
This changes an explicit authoring allowance, not any collision/contact
acceptance threshold. This condition leaves 18 negative rows, with zero
partner crossings, zero localized hand records and 70 complete B self pairs.
Its guard takes 140.094 s at 254,038,016 bytes (139 observations replayed).

## Coupled fitting and strict numerical restoration

The next condition activates A's existing nine body controls alongside B's
twelve. All source-relative angular caps, displacement bands, guide geometry,
171 B guide rows and physical tests remain unchanged. This removes a local
diagnostic freeze; it does not change either actor's edit limits. Complete
self scans now cover both actors after fitting.

The coupled fit ends with only two negative rows. Both are numerical guide
bounds: minimum normalized residual -1.1318671100470703e-13, corresponding to
raw guide margin -1.0001131867110047e-12 m against the already declared
1e-12-m arithmetic cushion. All 6,131 non-guide pose rows pass. The strict
whole-row decision remains false; these negatives are not rounded away.
Partner checks and both localized hand scans pass. Complete self scans find
A 131 / B 70 transverse pairs. Its guard takes 184.938 s at 247,820,288 bytes
(183 observations replayed).

A separate fixed-segment proposal moves from those coupled controls toward
the exact guide-pose controls, expressed in the same 15-degree shoulder
chart. It evaluates every unchanged inequality for each tested fraction.
Fractions zero and 1e-12 retain two negative rows; fraction 1e-11 passes all
6,302 rows with minimum normalized value 4.2016829986592933e-14. The optimizer
is not rerun, references are not recentered, and no tolerance is increased.
This tiny search-bound margin does not establish robustness. Fresh complete
self/partner checks and independent reconstruction cover this separately
saved proposal as follows.

At 2 s, partner checks find zero triangle crossings and zero legacy signed
depth. Both localized hand self scans have zero records. Complete
36,108-triangle-per-actor self scans find 131 A and 70 B transverse pairs.
Comparison by original triangle identity retains 131/removes 101/introduces
zero for A, and retains 70/removes 65/introduces zero for B. These inherited
source pairs remain defects; the result is not a collision-free character
or valid-solid certificate. Pair-set comparison does not prove continuous
behavior or clearance.

The final native pose has a 4.997499-mm material-origin gap, 2.950924-degree
normal opposition error and 14.750263-degree tangent disagreement, against
the unchanged 5-mm / 5-degree / 15-degree limits. Its guard takes 167.078 s
at 231,813,120 bytes, with all 166 resource observations replayed.

Independent replays reconstruct every saved world, vertex and inequality
exactly for all completed conditions, including their failed rows. The
failed initialization's resource trace is audited separately. The final
replay also rebuilds every stored guide axis and bound from the explicitly
pinned reference geometry, and checks sampled material-frame and self-cut
derivatives. This does not rerun the triangle collision predicates.

| Condition | Failed rows | Replay seconds | Peak sampled bytes | Resource observations |
| --- | ---: | ---: | ---: | ---: |
| Original axes, arm-only | 61 | 33.594 | 186,421,248 | 35 |
| Original axes, B shoulder 10 degrees | 15 | 38.828 | 192,086,016 | 40 |
| Candidate axes, B shoulder 10 degrees | 25 | 37.641 | 194,736,128 | 39 |
| Candidate axes, B shoulder 15 degrees | 18 | 36.578 | 195,026,944 | 38 |
| Coupled fit, before strict restoration | 2 | 37.656 | 192,688,128 | 39 |
| Verified final segment | 0 | 38.719 | 189,366,272 | 40 |

The final replay's maximum sampled directional errors are 2.172044e-9 for
material frames and 1.643336e-8 for normalized self-cut rows. All replay
resource traces are independently audited. These are sampled derivative and
saved-result checks, not a proof over every control or every time.

These are single-pose studies. None establishes native-key animation,
rates, complete-clock geometry, engine behavior, anatomical intent, semantic
high-five quality or animator cleanup time. Inherited source self pairs
remain visible, and original assets remain selected.

A static three-view comparison renders all original CPU-skinned triangles
for the source, first-character-fixed condition and final coupled candidate.
Assistant visual inspection checks plot framing and identifies the raised
open-hand contact; it is not independent human or anatomical review. The
first plot clips feet because it centers by vertex mean, and is retained
with a failed layout note (39.703 s, 203,341,824 bytes, 41 resource observations
replayed). A fresh plot uses projected bounds and an explicit content area;
heads and feet fit all nine panels. Its guard takes 38.953 s at 204,443,648
bytes (40 observations replayed). No model geometry changes in that repair.
