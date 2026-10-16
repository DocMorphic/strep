# Reusable paired native contact/surface fitting

`scripts/native_interval_pair_fit_job.py` turns the source-zero paired fitting
experiment into a recipe-driven offline command. It uses supplied native rigs,
contacts, geometry and explicit edit permissions. It does not generate prompts,
select an animation or grant motion-quality approval. It is a backend component;
Studio integration and full release validation remain pending.

## Restoring a current candidate without changing source bounds

`scripts/native_interval_pair_restore_job.py` adds one bounded relinearization
at an exported candidate. Its `strep-native-interval-pair-restore-v1` recipe
contains pinned `source_recipe`, `reference` and `current_contacts` files, the
complete absolute original-source `value`, and explicit `trust`,
`difference_step`, `rate_headroom` and `maximum_nonzeros` settings. The reference
is the original fit's `start-observations.npz`; the source recipe still uses
original zero controls. Run it inside an owned resource guard:

```text
python scripts/native_interval_pair_restore_job.py restore.json fresh-output
```

Before linearizing, the job exactly replays original source vectors, caps,
scales, contact bounds, times and floor arrays. It verifies that the current
export matches the supplied controls, original static rig and unedited tracks,
and unchanged scene/contact contract. Source pins are retained across validation
and loading. Fresh surface witnesses use current decoded vertices; the scene
and interval models retain their original source epoch.

The `rate_headroom` setting tightens responsive native search rows by the
smaller of that dimensionless fraction of their normalization scale and one
percent of their original cap. It is a search heuristic, not a certified
nonlinear error bound. Actual acceptance always uses original caps. Position
contact search reserves retain their original units and policy. Surfaces remain
soft objectives. Complete decoded native motion, floor, contact and geometry
validation is still required after a passing affine proposal.

`direction.npz` stores absolute original-source controls under the legacy
`delta` key for staged validator compatibility; `controls.npz` separately
stores the absolute point and local step. Results explicitly state that
meaning. Original motion remains selected and quality/release approval remains
false, including no-op and unsuccessful solver outcomes.

The combined restoration, current-point derivative and fit suites pass all 47
checks locally in 134.39 seconds. The guarded run takes 151.234 seconds,
peaks at 163,786,752 process-tree bytes and independently replays all 151
resource observations. These checks cover original-cap replay, changed inputs,
control/export mismatch, rig metadata, contact contracts, immutable result
directories and unsuccessful/no-op outcomes. They do not establish successful
restoration of a production animation.

A subsequent memory-lifetime change releases current decoded arrays before
the solve. All 13 affected restoration checks pass again in 48.29 seconds;
the guard takes 64.906 seconds, peaks at 153,255,936 bytes and replays all
66 resource observations. The CPU memory policy is unchanged.

At commit `a0f81f5`,
[focused restoration run 38900532752](https://github.com/DocMorphic/strep/actions/runs/38900532752)
passes all 13 cases on Ubuntu (7.97 seconds) and Windows (50.88 seconds).
The accompanying
[fit run 38900536662](https://github.com/DocMorphic/strep/actions/runs/38900536662)
passes all 16 cases on Ubuntu (7.33 seconds) and Windows (68.45 seconds),
including the regression for input changes between validation and loading.

The preceding high-five diagnostic measures the failed candidate both before
and after Float32 storage. Both representations retain the same 49 native
failures for A and 44 for B. The quantized preview and exported vectors agree
within 4.80e-11 per component. Continuous normalized excess reaches 0.0325214
for A and 0.0458966 for B. Storage is not the main source of these failures;
the next restoration must address nonlinear motion while preserving the
original bounds. The diagnostic completes in 76.047 seconds at a
286,441,472-byte peak, with 77 independently replayed resource observations.

The first current-point high-five restoration retains all 660,002 original
native rows, three authored contacts and 4,034 floor-protection rows. It uses
the same 672 original-source controls, a 0.02 trust box, a 0.001 difference
step and 0.001 dimensionless search headroom. Its fresh 31,201 surface guides
produce 695,243 total rows and 2,988,967 nonzeros. Original canonical vertices
agree within 6.66e-16 m; current smooth versus decoded material gaps differ
by at most 4.63e-8 m.

Clarabel reports `Solved` after 48 iterations. The optional minimum-norm phase
reports `NumericalError`, so the checked primary direction is retained. All
664,039 hard affine rows pass the existing 1e-8 normalized postcheck, with
1.10e-9 maximum excess. Actual exported contacts pass their authored bounds.
This is a proposal result pending separate actual native/floor/mesh validation.
The guard completes in 648.391 seconds at an 811,671,552-byte process-tree
peak, with all 641 resource observations independently replayed. It preserves
the original selection and grants no quality or release approval.

Independent actual-export validation rejects this candidate. Each actor retains
all 330,001 original native conditions; failures fall from 49/44 to one each.
Row identity matters: 92 previous failures resolve, B retains one, and A gains
one new failure. Both are positional accelerations at the source 2.025-second
interval start:

| Actor / joint | Actual (m/s²) | Original cap (m/s²) | Normalized excess | Identity |
| --- | ---: | ---: | ---: | --- |
| A / RightHandMiddle2 | 27.886508713 | 27.872578035 | 0.000499799 | newly failed row 238963 |
| B / RightHandThumbEnd | 31.143904529 | 31.142564795 | 0.0000430194 | retained row 238956 |

All 2,017 source floor protections pass for each actor; all 2,017 physical floor
failures per actor remain. The coupled validator independently replays all
660,002 saved native vectors/caps/scales and all retained canonical meshes,
then performs fresh contacts and the unchanged direct geometry query. Exported
contact distances are 29.109847, 12.541951 and 29.506907 mm, within the authored
30-mm bounds.

Compared with the original source at the five declared times, 20 mesh measures
improve, five regress and ten are unchanged. Intersections increase from
567 to 700, 594 to 770, 644 to 701 and 455 to 628 at the last four times.
A's vertices deeper than tolerance inside B increase from 18 to 30 at
2.033333302 seconds. The largest depth is 15.212721 mm, still above the 5-mm
screen. Several intersection counts are also worse than the preceding failed
fit, despite its larger maximum depth. Fewer failed rows or lower peak depth
therefore do not establish better animation quality.

The actor guards complete in 148.375 / 139.859 seconds, peaking at
272,142,336 / 274,845,696 bytes with 148 / 140 observations replayed. The coupled
guard takes 86.281 seconds, peaks at 350,162,944 bytes and replays 87 observations.
An inherited auxiliary table in B's worker accidentally pairs the preceding
A result with current B. That table is excluded. A separate passive replay of
both current actors verifies every native residual, failed-row identity and
geometry change; its 17.187-second guard peaks at 56,995,840 bytes and replays
19 observations. The coupled acceptance result uses the correct two current
actors and is unaffected by that auxiliary-table defect.

The original remains selected. This run establishes a bounded current-point
repair mechanism, not a usable high-five. Next, investigate the two actual
acceleration failures and increased crossings together. A stricter search
margin may be tested against the frozen same-point matrix after exact input,
implementation and original-cap replay; it must not substitute for decoded
acceptance or a method that handles newly introduced crossings. Grounding,
complete-clock geometry, engine fidelity, semantic review, broad held-out
actions/rigs/objects, editing/style and developer/independent cleanup evidence
remain required. No model training or release approval is admitted.

## Aggregate surface objectives and frozen retries

`native_scene_conic_sum.direction` minimizes the sum of positive normalized
soft-row excesses with one nonnegative slack per responsive soft row. A fixed
worst row therefore cannot flatten the objective for every other row. Full
hard vector norms retain their second-order cones and original supplied caps.
Scalar soft norms use both signs of their absolute value as linear bounds;
general three-dimensional soft norms retain complete cones. Fixed and whole-
trust-box passing rows are accounted for separately. A complete-row budget
rejects an oversized problem rather than returning a subset.

This objective is a search alternative. Its aggregate loss is not an animation
rating, a triangle-count guarantee or a collision certificate. Actual decoded
native motion, contacts, floor and mesh conditions still decide acceptance.

`scripts/native_interval_pair_retry_job.py` accepts schema
`strep-native-interval-pair-retry-v1`, a pinned `parent` request, explicit
`rate_headroom` and objective `minimax` or `sum-positive-excess`. The parent must
be a completed original-source current-point restoration with a complete saved
matrix. If its resource-guard records exist, their completed independent replay
is required. Every archived producer file must still match the current source;
additional retry implementation files are recorded separately in the new
implementation snapshot. Original inputs, control order, source-reference copy,
native observations/caps/scales and original search reserve are checked before
using the complete matrix. Search headroom may only increase within 0.01.

The retry preserves the original current point, trust box, all frozen contact
and floor rows, and every original acceptance cap. It does not recompute the
matrix or independently resample its parent source reference. A passing affine
proposal is exported from original source models, with full decoded acceptance
left to separate validators. Both unsuccessful proposals and exports remain
unselected; no quality or release approval is granted. This permits an objective
comparison with the same matrix and margin without repeating finite differences.

Run through an owned resource-guarded worker in the pinned CPU environment:

```text
python scripts/native_interval_pair_retry_job.py retry.json fresh-output
```

The `parent.path` resolves to the existing restoration's `request.json`; its
complete original input files and implementation archive must remain available.
The command is a backend component, with Studio integration still pending.

Twelve aggregate-solver tests verify full hard vector norms, signed scalar
absolute norms, general soft cones, original boxes, normalization units, fixed
conflicts and complete-population rejection. Nineteen retry tests cover frozen
source caps/vectors/scales, producer archives, actor/control order, stricter-only
reserves, first-pin retention across a mid-validation change, unsuccessful
directions, rejection of an unsafe `Solved` iterate and untouched existing
outputs. All 31 cases pass across the completed local runs. The initial combined
27-case run passes in 168.75 seconds (185.578 guarded seconds, 150,155,264-byte
peak, 185 replayed resource observations). After hardening, 18 retry cases pass
and one test reverses a single-node list without actually changing it. Correcting
that test to change the node passes the targeted rerun in 63.67 seconds
(81.125 guarded seconds, 148,312,064-byte peak, 82 replayed observations).
The earlier integer-NaN and single-node test-fixture failures remain retained
and audited; they are not counted as passes. These source checks provide no
animation, engine, held-out or full-inventory approval. Declared inventories
now contain 531 Python modules and 45 Node suites; the contact/rig subset has
95 Python modules and five Node suites.

At commit `f6dd3b7`,
[aggregate run 38906203916](https://github.com/DocMorphic/strep/actions/runs/38906203916)
passes all 12 tests on Ubuntu (0.28 seconds) and Windows (0.85 seconds).
[Retry run 38906210837](https://github.com/DocMorphic/strep/actions/runs/38906210837)
passes all 19 tests on Ubuntu (7.36 seconds) and Windows (247.18 seconds).

The first paired comparison reuses the same 695,243-row matrix, original
control point, 0.02 trust box and 0.002 search headroom for both objectives.
The minimax control reports `Solved` after 48 iterations and passes the full
664,039-row hard postcheck, at 4.55e-11 maximum normalized excess. It exports
and independently passes all 660,002 actual native conditions: the preceding
two acceleration failures are resolved without changing original caps.
Fresh coupled contacts are 29.161454, 12.693444 and 29.506691 mm, within the
authored 30-mm limits.

This control still fails geometry. Twenty selected measures improve, five
regress and ten are unchanged. Crossings increase from 567/594/644/455 to
715/774/713/627 at the last four selected times; the deep-vertex count again
increases from 18 to 30 at 2.033333302 seconds. Peak depth is 15.216414 mm.
Floor arrays remain exactly equal to the source at all 2,017 times per actor;
all fail the physical screen, with maximum depths 10.436307 mm for A and
8.331530 mm for B. The candidate remains rejected and unselected.

The aggregate solver reports `Solved` after 31 iterations but fails five native
hard affine rows above the unchanged 1e-8 postcheck tolerance. Maximum excess
is 1.6296216e-7. Its proposal is retained and **not exported**. Saved affine
positive soft excess sums are 7,683.425513 for minimax and 5,163.747810 for
aggregate; worst soft excess instead increases from 3.141435 to 3.422485.
These are surrogate tradeoffs. With no aggregate animation, this experiment
cannot establish a decoded objective-quality improvement.

| Guarded stage | Seconds | Peak process-tree bytes | Independently replayed observations |
| --- | ---: | ---: | ---: |
| Minimax proposal/export | 124.875 | 535,465,984 | 125 |
| Aggregate rejected proposal | 43.594 | 611,127,296 | 45 |
| Actual actor A | 143.343 | 275,427,328 | 143 |
| Actual actor B | 134.125 | 275,476,480 | 134 |
| Coupled scene | 85.375 | 332,333,056 | 86 |
| Complete saved affine/report replay | 30.359 | 171,278,336 | 32 |

The passive replay reproduces every saved affine residual for both proposals,
including all five rejected rows. Next, improve aggregate numerical precision
under the same objective, boxes, caps and postcheck, then measure any actual
export independently. No tolerance relaxation or animation-quality inference
from aggregate loss is justified. Broader motion/rig/object, grounding,
complete-clock geometry, engine, semantic/held-out and human cleanup evidence
remain required; the single entire-project goal stays active.

### Selective aggregate precision retry

The aggregate solver now measures the complete clipped proposal before
returning it. A finite, in-box `Solved`/`AlmostSolved` point that fails the
unchanged 1e-8 hard-row postcheck triggers one cold retry with gap/feasibility
tolerances tightened from 1e-9 to 1e-11. Each attempt retains the same matrix,
objective, caps, boxes, 100-iteration limit and 30-second solver time limit.
Already feasible proposals do not trigger another solve.

Finite in-box attempts, including failed solver statuses, retain normalized controls, clipped deltas, settings and
full-row measured failure summaries. If the retry also fails, the last finite
failed direction is returned explicitly for diagnostics and remains ineligible
for export. A failed-status or invalid retry cannot adopt the preceding failed
point. Actual decoded acceptance is still separate.

All 17 aggregate source tests pass locally in 2.04 seconds, including the real
solver cases and injected retry outcomes. New regressions verify identical
conic matrices/objectives across attempts, unchanged caps and postcheck,
retained rejected controls, rejection after two failures or an invalid/status
failure, and no extra solve for an already feasible point. The 512-MiB guard
completes in 19.218 seconds, peaks at 111,730,688 process-tree bytes and
independently replays 21 resource observations. This is source validation,
not proof that the retained large aggregate problem is repaired.

The first large precision run reproduces the same five failures in its initial
31-iteration solve. The tighter solve stops with `NumericalError` at iteration
33. No clip is exported, and the initial failed direction remains diagnostic.
The guard completes in 57.703 seconds, peaks at 613,462,016 bytes and replays
59 observations. Failed-status finite points are now captured and measured
without adopting them; a separate regression verifies that a failed status
cannot return a point even when its measured hard rows pass.

`scripts/native_affine_sum_segment.py` provides a separate deterministic
restoration method. Given a hard-feasible anchor and a proposed point inside
the original delta box, it bisects their affine segment and checks the complete
hard prefix at every probe using the existing 1e-8 comparison. Caps and scales
are unchanged. It returns a changed point only when its complete positive soft
excess sum improves beyond an explicit arithmetic reserve. It does not claim a
global or segment-loss optimum, decoded feasibility or mesh clearance.

All 29 affected checks pass locally in 2.61 seconds: 18 aggregate tests and 11
segment tests. The segment cases cover full three-dimensional norms, multiple
hard rows, invalid anchors, original boxes, incomplete/oversized matrices and
refusal to label a worse feasible target as progress. The guard completes in
19.250 seconds at a 101,957,632-byte peak; all 21 observations replay. Inventories
now declare 532 Python/45 Node suites and a contact/rig subset of 96/five.
These checks do not confer animation or release approval.

At `19012ce`, [aggregate source run 38910367992](https://github.com/DocMorphic/strep/actions/runs/38910367992)
passes all 18 tests on Ubuntu/Windows (0.61/0.93 seconds), and
[segment run 38910372784](https://github.com/DocMorphic/strep/actions/runs/38910372784)
passes all 11 cases (0.48/0.68 seconds).

The complete precision replay retains both finite failed proposals. The first
has five failed hard rows at 1.6296216e-7 normalized excess; the tighter
`NumericalError` point has three at 6.4993650e-8. Neither is exported directly.
The new run takes 55.797 guarded seconds at 614,199,296 bytes, with 57 resource
observations replayed. This captures the failed-status point missing from the
first retained precision run, without interpreting its status as success.

The separate deterministic segment study uses the already measured feasible
minimax control as anchor, the lower-aggregate failed point as proposal, and
the exact same original matrix, point, 0.02 trust and 0.002 search headroom.
It records the proposal's `NumericalError` status explicitly. All 34 full-row
probes replay exactly. A fraction of 0.9998908720444888 passes all 664,039 hard
affine rows under the unchanged 1e-8 comparison; maximum excess is
9.9999825e-9. Positive soft sum falls from 7,683.425513 to 5,163.755522.
This is a new deterministic restoration result, not a relabelled solver result.

Actual exported validation passes every one of the 660,002 original native
conditions. Caps, scales and times match the previous control exactly.
Fresh contact distances are 29.499724/10.781735/29.498655 mm, within 30 mm.
Floor arrays remain source-exact: all 2,017 times per actor still fail the
physical screen, at 10.436307/8.331530-mm maximum depths.

Direct geometry shows a tradeoff, not a qualifying improvement. Against the
original source, 19 selected measures improve, five regress and 11 are unchanged.
Against the minimax control, 12 improve, 13 regress and ten are unchanged.
Crossing counts decrease at all five times, but eight directional depth peaks
and five deep-vertex counts worsen. Largest depth rises from the control's
15.216414 to 16.083803 mm, still above the 5-mm screen.

| Time (s) | Original crossings | Minimax control | Aggregate segment |
| --- | ---: | ---: | ---: |
| 1.933333278 | 640 | 631 | 611 |
| 1.966666698 | 567 | 715 | 612 |
| 2.000000000 | 594 | 774 | 652 |
| 2.033333302 | 644 | 713 | 669 |
| 2.066666603 | 455 | 627 | 589 |

Existing native and geometry implementation hashes match between these decoded
studies; only the aggregate proposal module changes and the segment module is
added. Historical producer snapshots are verified separately, rather than
declaring their complete source maps equal to the current checkout.

| Guarded stage | Seconds | Peak process-tree bytes | Replayed observations |
| --- | ---: | ---: | ---: |
| Segment and original-source exports | 110.718 | 248,594,432 | 111 |
| Actual actor A | 151.234 | 280,289,280 | 151 |
| Actual actor B | 149.219 | 274,505,728 | 149 |
| Coupled direct geometry | 88.266 | 335,163,392 | 89 |
| Full saved probe/native/report replay | 32.438 | 232,615,936 | 34 |

The candidate remains rejected and the original stays selected. Aggregate loss
or crossing count alone cannot protect depth. Next, investigate depth-aware
contact/surface guidance at a feasible pose, with the original motion bounds,
explicit contact geometry and independent full decoded acceptance retained.
Do not continue aggregate-weight tuning as if this loss were an animation
rating. Grounding and the broader release requirements remain unresolved.

### Current-state assembly with explicit depth limits

`scripts/native_depth_guarded_recourse.py` assembles current observed native,
contact, floor and material rows while checking native/contact caps and scales
against explicit original reference arrays. The current anchor must already
pass those original conditions. It keeps duplicate contact objectives, and
position search reserves never affect relative-speed rows. Native search
reserves are limited by the declared normalized headroom, one percent of the
original cap and half the current original slack; fixed rows keep their caps.
Position reserves likewise consume at most half the current authored slack.

Original acceptance caps are not reset to the current pose. Scalar floor and
surface lifts receive new positivity certificates over the current original
control/trust box. Explicit depth-row indices and metre limits add local hard
material bounds; the caller must supply limits that contain the anchor. Every
surface row remains in the soft objective, including protected witnesses.
The complete matrix is rejected if oversized, without dropping conditions.

This separates current observations from derivative refresh: cached native,
contact and floor derivatives remain approximations, while material witnesses
and analytic surface derivatives can be rebuilt at the actual current pose.
Fixed material limits do not certify the nearest surface or newly penetrating
vertices. Separate full decoded native/contact/floor/mesh acceptance is required.

All 42 affected checks pass locally in 3.01 seconds, including 13 new assembly
cases plus the 29 aggregate/segment cases. Tests verify reference-bound rejection,
feasible limited reserves, contact units, complete hard depth rows, nullable
contacts/empty floors, invalid anchors and complete-budget rejection. An actual
small conic comparison changes only the local depth guard and confirms that
it bounds the direction that the unguarded aggregate objective would deepen.
The 512-MiB guard completes in 20.219 seconds at 112,513,024 bytes; all 22
resource observations replay. Inventories now declare 533 Python/45 Node suites
and a contact/rig subset of 97/five. These are source checks, not clip approval.

At `2bf86d9`, [focused run 38915248406](https://github.com/DocMorphic/strep/actions/runs/38915248406)
passes all 13 new cases on Ubuntu (0.52 seconds) and Windows (0.59 seconds).

The first matched current-state study starts at the independently measured
feasible minimax export. It exactly replays both complete saved native
populations against original reference caps/scales, replays all five cached
meshes against their actual GLBs, and freshly measures coupled contacts.
Native/contact/floor derivatives are reused from the earlier point; their
constant vectors and scalar-lift certificates are rebuilt around the current
pose without changing source epoch or acceptance limits.

Fresh actual-pose surface queries retain 34,389 rows and 1,399,023 analytic
derivative entries, with the original source canonical vertices matching to
6.66e-16 m. Both variants use these same data, 672 original controls, 0.02
trust, adaptive headroom up to 0.002, position reserves up to 0.5 mm and 0.5-mm
surface search clearance. The guarded variant adds 3,249 local material bounds:
currently shallow contained witnesses stay within the 5-mm policy tolerance;
currently deep witnesses stay within the current directional material peak.
These are proposal guards, not permission to accept existing physical failures.

| Variant | Hard rows | Total norm rows | Sparse entries |
| --- | ---: | ---: | ---: |
| Free aggregate control | 664,039 | 698,431 | 3,089,605 |
| Local depth guards | 667,288 | 701,680 | 3,226,432 |

Both branches produce a lower-loss direction through the separately checked
bounded-segment method and meet all affine hard rows. Both actual exports meet
the authored contact limits. Raw solver statuses remain `AlmostSolved` and
`NumericalError`; the latter is not relabelled as solved. The shared guarded
study completes in 256.094 seconds at an 841,142,272-byte process-tree peak,
with all 253 resource observations independently replayed.

All six actual validation stages now complete, followed by independent replay
of the complete affine proposals, original native caps/scales, floor arrays,
contacts, geometry comparisons and material witnesses. Neither candidate
qualifies. The original remains selected.

| Decoded measurement | Free aggregate | Scalar depth guards |
| --- | ---: | ---: |
| Native failures / 660,002 rows | 6 (A: 5, B: 1) | 0 |
| Contact distances, mm (30-mm limits) | 29.412465 / 14.497135 / 29.760901 | 29.160359 / 12.713532 / 29.511312 |
| Largest sampled partner depth, mm | 15.581546 | 15.216402 |
| Mesh measurements improved / regressed / unchanged versus anchor | 17 / 8 / 10 | 8 / 5 / 22 |
| Physical floor failures per actor / 2,017 times | 2,017 | 2,017 |

The free proposal fails one position-acceleration and five world-angular-
acceleration conditions. Cached native derivatives did not certify decoded
acceptance. The guarded proposal passes every original native condition, but
its worst depth decreases only about 11 nanometres from the anchor's
15.216414 mm. That is not meaningful physical progress. Crossings at the last
sample increase from 627 to 631; both variants retain five mesh regressions
against the original source. Floor arrays are source-exact, preserving the
original physical failures rather than fixing grounding. These are five-time
partner geometry measurements, not full-clock or continuous clearance.

The guarded direction retains only 0.0191148198 of the proposed step after
34 bounded-segment probes. Its raw `NumericalError` status stays visible;
the segment's complete affine check is separate. All six validation resource
traces replay. Per-stage elapsed times and sampled process-tree peaks are
free A 161.500 s / 274,452,480 bytes, free B 148.156 s / 272,723,968 bytes,
free scene 87.656 s / 365,936,640 bytes, guarded A 174.485 s / 276,340,736 bytes,
guarded B 146.984 s / 274,227,200 bytes and guarded scene 93.016 s /
319,565,824 bytes. The passive summary completes in 23.359 s at 340,774,912
bytes, with all 25 observations replayed. Raw results remain under
`reports/high-five-current-depth-{free,depth}-actor-{A,B}-v1`, the corresponding
scene folders and `reports/high-five-current-depth-summary-v1`.

### Full-vector material guards

The passive replay checks all 3,249 penetrating-vertex witnesses against
canonical target triangles and convex weights. At the anchor, material vector
norms and negative projected gaps agree within 4.568e-16 m. After the free
proposal, 46 projected scalar bounds fail while 51 material-distance bounds
fail: five projected passes miss a full-distance failure. A distance-bound
failure alone does not prove penetration; the full mesh evaluator remains
authoritative. In the guarded clip both checks fail four witnesses, with
maximum material deficit about 31 nanometres, comparable to the approximately
24-nanometre smooth/decoded gap difference. No substantial quality improvement
is established by those differences.

`scripts/native_partner_material_vectors.py` now provides relative 3D material
vectors and their exact-key sparse Jacobians. It validates the complete
declared source-vertex/target-face population, canonical face order, distinct
actors and convex weights. Accepted roundoff in weight sums is normalized on
a copy. Three Cartesian evaluations reuse the unchanged scalar derivative
implementation, retaining original-source vertex agreement checks, current
absolute controls, both actor placements and all three vector components.

`insert_guards` adds full vector-norm conditions after the original hard
prefix, keeping every original vector, cap, scale and soft objective in order.
It requires a feasible anchor and rejects an oversized complete matrix without
truncation. In exact arithmetic the distance to a convex target-face material
point bounds the source vertex's nearest-surface distance from above. A fixed
normal projection lacks that guarantee. The bound covers only declared
vertices; nonlinear motion, serialization, floating-point error, newly
penetrating vertices, triangle intersections and complete mesh acceptance still
require independent evaluation. Distance is unsigned, so this conservative
local bound can also restrict harmless separation after a vertex leaves the
partner. Refreshing containment and material witnesses remains necessary.
This helper is not evidence that a production candidate passes.

All 16 new source cases pass in 14.20 seconds. The final guarded run takes
31.422 seconds at 132,448,256 sampled process-tree bytes; all 33 observations
replay. Before the weight-normalization refinement, all 18 existing scalar
derivative checks also pass. Inventories declare 534 Python/45 Node suites
and a contact/rig subset of 98/five; these counts are not full-suite approval.

At `187bc66`, [focused run 38921219126](https://github.com/DocMorphic/strep/actions/runs/38921219126)
passes all 16 new cases on Ubuntu (3.05 seconds) and Windows (10.63 seconds).

The matched full-vector trial retains the previous free branch's complete
base vectors, caps, scales and sparse matrix exactly before inserting all
3,249 full-vector guards. Canonical material rows are reused from that pinned
current-pose query; vector derivatives are freshly evaluated at the same
absolute original-source controls. Actual decoded anchor vectors define the
guard constants, and the smooth/decoded difference remains recorded.
All other controls, trust, native/contact reserves and physical acceptance
limits stay as declared above. The resulting system has 667,288 hard rows,
701,680 total norm rows and 3,500,086 sparse entries.

The solver reports `AlmostSolved`; separate complete affine postchecking
passes the entire proposed step. Aggregate soft excess falls from 5542.073479
to 5343.440306. Both exported actors meet the authored contacts, while original
source epoch, controls and bounds remain preserved. The producer completes
in 125.062 seconds at 868,278,272 process-tree bytes, with all 125 resource
observations replayed.

All three actual stages and the separate saved-row summary now complete.
The candidate is rejected: all eight failed native conditions are original
world-angular-acceleration rows (A: five, B: three), despite passing their
affine search bounds. Authored contact distances are 29.007674, 13.757977 and
29.762859 mm. Floor arrays remain source-exact, including all 2,017 physical
failures per actor. The original source remains selected.

At the five selected geometry times, 23 measurements improve against the
feasible anchor, one regresses and eleven are unchanged. All five crossing
counts decrease, to 614 / 661 / 740 / 707 / 613. Peak partner depth is
15.130781 mm, about 0.085633 mm below the anchor but still above the 5-mm
physical screen. A-inside-B depth at 2 seconds instead increases from
9.124863 to 9.126193 mm. Compared with the original source, twenty measurements
improve, five regress and ten stay unchanged. These are measured geometry
tradeoffs on a rejected clip, not animation-quality approval.

The independent summary replays all complete affine rows and probes, verifies
all inserted vector rows/caps/scales and sparse entries, and independently
reconstructs normalized target-face material points from decoded meshes.
Fourteen material distances exceed the added search limits after nonlinear
export, at a maximum deficit of 0.011888 mm. Four projected scalar bounds fail;
ten scalar passes miss a distance-bound failure. This reinforces the need for
decoded checking even when the full-vector affine model passes. Unsigned
material-distance failure still does not itself prove physical penetration.

The original eight failed native rows have strictly passing affine predictions;
their actual-versus-predicted vector differences are about 0.303–0.933 rad/s².
Those residuals alone do not separate derivative staleness, finite-difference
error, nonlinear curvature and serialization. The directional-fidelity study below
compares current-pose central differences at two step sizes with the cached
direction and continuous-versus-decoded vectors, preserving original caps.

The three stage guards complete in 150.719 s / 274,067,456 bytes, 145.469 s /
273,514,496 bytes and 89.453 s / 301,273,088 bytes; all 150 / 145 / 90 resource
observations replay. The passive summary takes 20.329 s at 331,628,544 bytes,
with all 22 observations replayed. Results are retained under
`reports/high-five-material-vector-{actor-A,actor-B,scene,summary}-v1` and
`reports/high-five-material-vector-guards-v1`. No inference, training or engine
run is involved; full-clock geometry, grounding and broader release work remain.

### Current-direction error decomposition

The separate `reports/high-five-material-direction-fidelity-v1` study now
completes. It reconstructs each actor from the original zero-control source,
replays all 660,002 original native vectors/caps/scales and clocks, then compares
the same proposed direction at the actual feasible anchor. Central directional
differences use relative step fractions 0.01 and 0.001; they do not rebuild a
complete current-point Jacobian or produce a new candidate.

Across the eight failed angular-acceleration rows, the two central estimates
agree within 4.974e-7 rad/s². Their difference from the cached predicted
direction is 0.263682–1.068921 rad/s². The full-step continuous nonlinear
remainder is 0.176080–0.897765 rad/s². By comparison, continuous-to-decoded
full-step vector differences are only 0.000282–0.000365 rad/s²; anchor storage
differences are 0.000162–0.000631 rad/s². Two-step agreement is a numerical
observation, not a derivative-error certificate, and component norms are not
additive error shares.

A prediction using the fresh current-direction derivative flags one failed
row for actor A and two for B. The actual export fails five and three,
respectively. Thus refreshing derivatives alone would still miss five of
the eight actual violations at this step size. Serialization is not the
dominant discrepancy in these rows. The next proposal should refresh native
derivatives at the feasible current point, use smaller/adaptive trust and
require complete nonlinear decoded acceptance before retention. Original
source caps must remain unchanged, and geometry/grounding still need separate
correction and full-clock checking.

The directional study completes in 81.171 seconds at 320,024,576 process-tree
bytes, and all 82 resource observations independently replay. Its outputs are
diagnostic only; no animation is selected and no quality or release gate changes.

### Staged current native derivative refresh

`scripts/native_actor_derivatives.py` differentiates every native rotation,
displacement and rate row for one actor at current absolute source controls.
It requires a zero original seed and independently rebuilds the complete
original reference caps/scales before checking the caller's reference arrays.
Current observed vectors anchor the proposal; differences use continuous
quaternion evaluation, while original caps/scales stay unchanged. Caller-
supplied worlds are checked for complete shape/finite values; their provenance
and correspondence to the controls remain the caller's responsibility.

Every control column is evaluated with central differences at the declared
step (default 0.0001). Near a box boundary, two inward samples produce a
second-order one-sided derivative without stepping outside original controls.
All exactly nonzero entries are retained, including tiny coefficients. The
complete three-component matrix must fit the explicit 3-million-entry actor
budget; exhaustion rejects rather than returning a truncated population.
Coupled contacts, floor minima, surface witnesses, nonlinear export and actual
acceptance are separate; the metadata never grants quality or release approval.

The first source test attempt finds two failures when its independent pair
reference uses a 2e-6 control step. A guarded five-step diagnostic retains that
failure and measures a maximum 1.478714e-5 derivative difference at that tiny
step. An independent 2e-4 reference gives 5.300677e-7 maximum difference with
zero violations of the original test tolerance. The tests use this stable
reference without widening their tolerance, and additionally compare the
stencils with closed-form trigonometric/polynomial derivatives at both box
boundaries. This diagnostic does not certify the production step for every rig.

All 14 new cases and 14 existing actor-validation cases pass locally in
25.11 seconds. The guard completes in 41.656 seconds at 142,356,480 sampled
process-tree bytes; all 43 observations independently replay. The separate
step diagnostic takes 29.484 seconds at 112,295,936 bytes, with all 31
observations replayed. Tests
cover independent pair-row comparison at nonzero and boundary controls,
explicit observed anchors, source epoch/cap/scale rejection, malformed inputs,
complete budgets and preservation of tiny nonzeros. Inventories declare
535 Python/45 Node suites and a contact/rig subset of 99/five; these counts
are not full-inventory approval. The real current-point evaluation below uses
separate guarded actor stages before the coupled smaller-step fit.

At `ad25217`, [focused run 38924013825](https://github.com/DocMorphic/strep/actions/runs/38924013825)
passes all 14 new cases on Ubuntu (4.14 seconds) and Windows (12.41 seconds).
The first real stage stops before differentiation because the old anchor's
whole producer map includes an older `native_scene_conic_sum.py`. Its immutable
failure and all 31 resource observations are retained and replayed. The revised
stage reconstructs original assets using the newer independently validated
current-pose receipt, checks its controls against the same anchor export, and
verifies every old producer archive file against its saved hash. It builds new
derivatives; it does not reuse or rebind the old optimizer matrix.

Both revised real stages complete and independently replay. Each retains
330,001 native rows and 336 controls at the same feasible anchor. Actor A's
matrix has 844,800 nonzeros; its guard takes 269.344 seconds at 337,731,584
bytes, with all 267 observations replayed. Actor B has 845,010 nonzeros and
takes 268.531 seconds at 335,286,272 bytes, with all 266 observations replayed.
Their full original source vectors/caps/scales and clocks match the bound
references; current observed native vectors match the separately decoded
anchor. No sparse entries or native rows are discarded. The matrices and
receipts are under `reports/high-five-current-native-derivative-{A,B}-v2`.

The matched proposal uses their complete block diagonal native matrix,
fresh analytic derivatives for all three authored position contacts, and a
0.005 trust radius instead of 0.02. Surface and full-vector material witnesses
remain pinned to the same anchor; floor derivatives are explicitly cached.
Search reserves and original acceptance caps remain as before. Changing both
derivatives and trust is not an isolated ablation. Complete decoded native,
contact, floor and mesh validation remains required before any retention.

The complete refreshed matrices also replay the previous rejected clip's
independent directional probes at this anchor. Maximum vector differences
are 1.795060e-8 and 1.799344e-8 across each actor's complete native rows.
Maximum differences normalized by original row scales are 1.287490e-9 for A
and 5.924157e-10 for B, versus 0.008789510 and 0.005428227 for the cached
direction. This validates the assembled current-point projection for that
direction, not arbitrary steps or nonlinear feasibility.

The fresh smaller-step model retains 667,288 hard rows, 701,680 total norms
and 3,499,962 sparse entries. Its raw status is `AlmostSolved`; independent
full-row affine checking passes the full proposed step with maximum normalized
hard excess 5.991284e-9, below the unchanged 1e-8 search comparison. Soft excess
decreases from 5542.073479 to 5458.721593. Actual authored hand contacts pass
on both exports. The producer completes in 114.766 seconds at 820,752,384
process-tree bytes, and all 115 resource observations replay.

Full actual validation and the independent saved-row summary now complete.
Both exports pass every original native condition: zero failures among all
660,002 rows, versus eight in the preceding full-step trial. The authored
contact distances are 29.578526 / 13.420479 / 29.608919 mm, all within their
unchanged 30-mm limits. Floor arrays remain source-exact, including all 2,017
physical failures per actor. Changing derivatives and trust together does not
isolate either change's effect.

Against the feasible anchor, 24 of the 35 selected geometry measurements
improve, none regress and eleven are unchanged. Crossing counts are
617 / 700 / 754 / 701 / 627. Largest partner depth is 15.179006 mm, about
0.037408 mm below that anchor but still above the 5-mm physical screen.
Against the original source, twenty measurements improve, five regress and
ten are unchanged. The original-source geometry qualification therefore fails;
the candidate remains unselected, with all quality/release flags false. This
is a native-feasible measured correction, not a production-quality high-five.

All projected scalar material bounds pass, but seven full material distances
exceed the added search bounds after nonlinear export, by at most 0.001152 mm.
The summary reconstructs normalized canonical target-face points and replays
every inserted vector row and sparse entry. These tiny failures are retained;
they are not rounded into a pass. A local full-vector affine pass still does
not certify nonlinear material bounds or full mesh clearance. Further work
must retain original native/contact bounds while correcting these nonlinear
material violations and the remaining physical intersections. Grounding and
full-clock geometry remain separate required work.

The actual stage guards complete in 162.344 s / 276,103,168 bytes,
148.265 s / 275,247,104 bytes and 82.187 s / 340,938,752 bytes; all
162 / 148 / 83 resource observations independently replay. The summary takes
20.234 seconds at 242,860,032 bytes with all 22 observations replayed. Raw
results remain under `reports/high-five-fresh-small-{actor-A,actor-B,scene,summary}-v1`
and `reports/high-five-fresh-native-small-step-v1`. No inference, training,
engine playback, held-out action coverage, animator rating or cleanup-time
approval is inferred from this single selected-time scene comparison.

### Restoration from a material-infeasible export

`scripts/native_material_bound_restore.py` adds an explicit restoration path
for the seven nonlinear material-bound violations. Existing feasible-anchor
insertion behavior is unchanged. The new assembly requires a passing original
base prefix but allows material vectors outside their original limits. It
retains every base vector/cap/scale and all material rows. Only material search
caps tighten by the declared inward reserve (default 0.5 micrometre); original
reference limits remain unchanged and complete matrices reject on budget
exhaustion.

The restoration solver minimizes the normalized control-step norm under the
complete hard prefix. Soft rows remain saved and measured, but their animation
guidance objective is not optimized during this correction. Every active
three-vector norm remains a cone; fixed failed rows reject. A row can be
omitted from the solver only with the complete affine-box bound and arithmetic
reserve, and the returned point is checked against every hard row afterward.
Both an accepted solver status and the full affine postcheck are required.
Nonfinite residuals cannot be serialized as a passing result. No source caps
are enlarged, and no nonlinear/export/mesh acceptance is inferred.

All 16 new checks pass in 1.97 seconds, including actual infeasible-start and
curved-contact solves, source/soft-row retention, budget rejection, fixed
conflicts, status/postcheck disagreement and nonfinite norm rejection. The
final guard takes 19.266 seconds at 122,085,376 bytes; all 21 observations
replay. Before the nonfinite-result refinement, all 16 existing material-vector
checks also pass. Inventories now declare 536 Python/45 Node suites and a
contact/rig subset of 100/five, not full-inventory approval.

The real restoration will keep the previous material faces and reference
limits, refresh material/contact derivatives at the current decoded candidate,
and explicitly reuse native/floor derivatives as approximations. Its declared
trust is 0.0005 with a 0.5-micrometre inward material search reserve. Original
native/contact/floor acceptance and the actual full-vector reference limits
must still pass after export.

At `5fc4b29`, [focused run 38928435610](https://github.com/DocMorphic/strep/actions/runs/38928435610)
passes all 16 new cases on Ubuntu (0.81 seconds) and Windows (1.07 seconds).
The first real worker stops before solving because its inferred producer-guard
path assumes the older folder layout. Its 27 resource observations replay;
the corrected worker pins explicit producer guard/audit paths.

The corrected real model completes with 397 active cones, but reports
`NumericalError` after 21 iterations. Its finite diagnostic point passes the
complete affine hard postcheck (maximum normalized excess 8.558588e-10).
The status gate still rejects it: no candidate is exported and the failure is
not relabelled as solved. All 83 observations replay over 82.297 seconds at
554,586,112 bytes. This is numerical termination, not proof that the original
constraints are infeasible.

Restoration now accepts an explicit solver convergence setting: `strict`
(default 1e-11, reduced 1e-10) or `standard` (1e-9, reduced 1e-8). This changes
solver termination only; the complete 1e-8 affine postcheck, original physical
caps, statuses and separate decoded acceptance stay unchanged. All 19 source
cases pass in 5.19 seconds, exercising both settings on actual small solves.
The final guard takes 23.500 seconds at 120,107,008 bytes, with all 25
observations replayed. A matched real study rebuilds from original inputs
and must verify identical vectors/caps/scales/Jacobian against the failed
model before testing `standard` convergence.

At `c7d513e`, [focused run 38929459863](https://github.com/DocMorphic/strep/actions/runs/38929459863)
passes all 19 cases on Ubuntu (0.68 seconds) and Windows (1.05 seconds).
The rebuilt real model matches every saved vector/cap/scale, sparse entry and
hard-row count from the strict attempt. Its recipe differs only in convergence
and the comparison-report reference. Standard convergence reports `Solved`
after twenty iterations; all 667,288 affine hard rows independently pass at
maximum normalized excess 8.512191e-10. Actual exported authored contacts also
pass. This shows a termination difference for the same numerical problem;
it does not relax or prove nonlinear acceptance.

The producer completes in 123.750 seconds at 612,347,904 process-tree bytes,
with all 124 resource observations replayed. Full independent actual native,
floor, material and selected-mesh validation and two saved-row summaries now
complete. The original clip remains selected; this candidate is not approved.

Both restored exports pass every original native row (660,002 total) and all
three original hand contacts at 29.578263 / 13.420551 / 29.608442 mm. The strict
material audit verifies every normalized canonical target-face point: all
3,249 original distance limits pass with no comparison tolerance needed and
at least 0.485394 micrometre of margin. This clears the previous seven failed
reference bounds. Three tightened internal search caps miss by at most
0.014606 micrometre after export, while the original limits retain their margin. Search
targets and original acceptance limits remain separately reported.

Full mesh checks still reject the clip. Against the pre-restoration candidate,
four measurements improve, eight regress and 23 stay unchanged. Crossings at
the first sampled time increase from 617 to 619; the other counts remain
700 / 754 / 701 / 627. Peak depth increases by about 1.164 micrometres to
15.180169 mm. Against the earlier feasible minimax anchor, 24 measurements
still improve, none regress and eleven remain unchanged. Against the original
source, five regressions remain. Passing the fixed material bounds does not
certify complete mesh clearance or improvement of the current nearest depths.
Both actors also retain all 2,017 physical floor failures.

The actual actor/scene guards complete in 151.140 s / 273,645,568 bytes,
138.093 s / 274,190,336 bytes and 87.141 s / 343,990,272 bytes. All
151 / 138 / 88 resource observations replay. The first summary completes in
19.219 s at 246,489,088 bytes with 21 observations replayed. The expanded strict
reference-versus-search audit completes in 19.218 s at 252,461,056 bytes with
21 observations replayed. Raw results are retained under
`reports/high-five-material-restored-{actor-A,actor-B,scene}-v1` and
`reports/high-five-material-restored-summary-{v1,v2}`.

### Complete-floor placement diagnosis

A read-only diagnosis checks all 2,017 saved floor samples per actor and exact
point-contact translation algebra with every original target fixed. Floor
arrays remain source-exact. Physical peak depth is 10.436307 mm for A and
8.331530 mm for B; floor-gap ranges across time are 3.195332 and 2.970733 mm. These data
motivate a placement hypothesis; they do not prove an import-origin defect.

Separate minimum actor lifts to the existing 5-mm screen are 5.436307 and
3.331530 mm. Those unequal shifts would move the hand-to-hand distance to
30.187724 mm, outside its 30-mm limit. Separate lifts to zero penetration
also fail that contact, and actor A's world-point contact. No such lift is
applied.

A shared upward scene offset of 5.936307 mm (the larger screen offset plus
0.5 mm reserve) predicts passing all saved floor-screen samples while keeping
original point-contact distances at 29.773872 / 10.320870 / 29.608442 mm,
all below 30 mm. Predicted remaining physical floor depths are 4.500000 mm
for A and 2.395223 mm for B. This is within the declared screen; it is not
zero penetration or proof of planted feet. A shared 10.936307-mm lift would
clear the plane, but breaks actor A's world contact at 30.837374 mm.

The shared-screen hypothesis is a candidate for an explicitly authored scene
placement variant. It has not changed the current root/placement contract,
assets, targets, geometry policy or source bounds. A future variant must
declare its world-placement permission and independently validate exported
transforms, original motion data, contacts and complete floor/mesh geometry.
A common translation preserves partner-relative geometry in exact arithmetic,
so it cannot solve the approximately 15-mm partner intersections. No general
automatic grounding rule for other actions is inferred.

The two profile guards complete in 16.172 and 16.187 seconds, with all eighteen
resource observations replayed for each. The short workers' true peak RSS is
not resolved by the sampling interval. Results remain under
`reports/grounding-offset-profile-{v1,v2}`. All quality/release flags remain false;
full-clock partner geometry, broad actions/rigs/objects, engine and human cleanup
validation remain required under the same project-wide goal.

Run through an owned resource-guarded worker in the pinned CPU environment:

```text
python scripts/native_interval_pair_fit_job.py recipe.json fresh-output
```

The recipe uses schema `strep-native-interval-pair-fit-v1` and contains:

- `contacts` and `geometry`: each a relative or absolute `path` and exact
  lowercase `sha256` for an original source declaration.
- `actors`: exactly the two original actor IDs. Each has pinned `request` and
  zero `controls` files, plus a contiguous list of existing `active_keys`.
- `surface_samples`: sorted unique indices in the original geometry clock.
  Surface derivatives must use exact existing quaternion keys.
- `surface_seed`: an explicit integer seed for source mesh queries. The job
  saves the before/after query states and restores the caller's generator state.
- `trust`, `difference_step`, `contact_reserve_m` and `maximum_nonzeros`:
  explicit bounded proposal settings. The complete combined sparse model must
  fit its budget; no rows or columns are truncated.

Source hashes, actor IDs and zero seeds are validated before fitting. Output
must be fresh and separate from immutable input results. Actor IDs cannot
escape the output directory. Source rigs, poses, original rate caps, root and
boundary contracts remain bound through the existing interval model. New edit
permissions must be declared in the actor requests; they are not inferred from
an action name.

All original native and floor-protection rows remain hard. The contact reserve
tightens only authored **position** norms; relative-speed norms retain their
own units and caps. Fixed surface guides are proposal objectives. If no source
surface witnesses exist, the job runs a contact-only proposal and does not
infer geometry clearance.

The job saves its source arrays, layouts, original caps/scales, complete affine
system/Jacobian, surface rows, query states, solver output and implementation
snapshot. A returned solver direction is saved **before** the full hard-row
postcheck, so a rejected iterate remains diagnosable. Only a passing affine
proposal is exported. Actual coupled contacts are then measured on the export;
full decoded native/floor/mesh validation remains a separate required stage.
Every output keeps `original_selected=true` and quality/release approval false.

Fifteen source tests exercise hash and zero-epoch rejection, actor-path safety,
bounded settings, contact row units, complete original native-cap retention,
unchanged source files, query-generator restoration, rejection of a forced
infeasible iterate even with a `Solved` label, and a forced feasible export
remaining unselected pending independent validation. Solver injection in the
last two cases tests the caller's gate, not numerical solver capability; the
separate full job case uses the actual solver.

All 15 pass locally in 73.06 seconds. The guarded run completes in 89.375
seconds including admission, peaks at 155,557,888 process-tree bytes, and
independently replays all 90 recorded resource observations. The guard stays at
512 MiB for these small fixtures, plus the unchanged 600-MiB free-memory floor.
Larger paired matrix studies retain the 1-GiB profile. These source tests do not
establish animation quality, engine playback, held-out coverage or human review.

The next development case adds explicitly selected finger controls to the
existing high-five source. The source inspection finds all 24 finger joints per
actor have compatible LINEAR tracks on the original wrist clock. Complete world
rate caps and scales replay exactly against the original saved baseline at the
same uniform clock and bins. Local finger motion and world-joint motion are
measured separately; local near-static tracks do not imply zero world-rate
headroom. No source bounds or model weights are changed by this inspection.

At commit `d966978`, [hosted focused run 38893122451](https://github.com/DocMorphic/strep/actions/runs/38893122451)
passes all 15 cases on Ubuntu (10.73 seconds) and Windows (74.24 seconds).
Inventories now list 528 Python modules and 45 Node suites, with 92 Python
modules and five Node suites in the contact/rig subset. This remains focused
source verification, not full-inventory or animation-quality approval.

The source-only finger inspection independently replays the complete original
rate caps/scales for both actors. It uses 477 samples at 120 Hz and the identical
four source bins. All 24 finger joints per actor have existing compatible
LINEAR channels on the 120-key wrist clock. Maximum observed local finger speed
is 33.210447 degrees/s for A and 66.596863 for B; maximum world-joint speed is
563.217710 and 820.943799 degrees/s respectively. These are source observations,
not anatomical limits. The inspection guard completes in 34.406 seconds at
125,771,776 bytes, with all 36 resource observations replayed.

The expanded development fit declares shoulder, upper arm, forearm, wrist and
the first two joints of each right-hand finger: nodes 40–45, 48–49, 53–54,
58–59 and 63–64 for this supplied SOMA rig. These IDs are not a universal rig
mapping. Every declared rotation permission is 10 degrees; the original 50-mm
joint displacement bound, world-rate bounds, source epoch, roots and frozen
endpoints remain in force. Eight active native keys (56–63) per actor give
672 controls under the existing 768-control budget. Five contact-near geometry
times remain the initial selected comparison population.

Compared with the earlier arm-only fit, this changes the edit permissions,
window and local trust radius (0.2 versus 0.1). It is explicitly not an isolated
finger ablation. No old native matrix is reused. The new source surface model
retains all 29,378 rows and has 1,246,068 analytic nonzeros; every canonical
source vertex still agrees with the native decoder to 6.661338e-16 metres.
The rebuilt system contains 693,420 norm rows and 2,941,970 nonzeros, with
660,002 native rows, three coupled contacts and 4,034 floor-protection rows in
its 664,039-row hard prefix. Clarabel reports `Solved` after 53 iterations and
the full affine postcheck passes. The guarded job completes in 660.781 seconds
at a 955,412,480-byte peak, with all 650 resource observations replayed.

The exported candidate meets all three authored 30-mm contacts at 29.530898,
11.275910 and 29.764394 mm. The 29.5-mm search reserve is an affine target;
actual authored acceptance stays 30 mm. Independent actor A validation finds
49 native failures, so the candidate is rejected despite the solver's success.
All 309,831 original source native vectors/caps/scales replay exactly; 20,170
new finger edit rows are separately declared. Actor A preserves its original
floor bounds at all 2,017 times but retains all physical floor failures. Its
guard completes in 152.672 seconds at 274,800,640 bytes with 152 observations
replayed. Actor B has 44 native failures and preserves all original floor
bounds while retaining the physical floor failures. Its guard completes in
140.156 seconds at 272,584,704 bytes, with 140 observations replayed. Rebuilt
source references match all 619,662 original native vectors/caps/scales; the
40,340 additional rotation-edit rows correspond to the declared finger
permissions. Every decoded rotation-edit and joint-displacement row passes.

| Actor | Position speed | Position acceleration | World angular speed | World angular acceleration |
| --- | ---: | ---: | ---: | ---: |
| A | 2 | 14 | 5 | 28 |
| B | 2 | 12 | 7 | 23 |

All 93 native failures are original speed/acceleration limits. The counts above
come from complete saved residual replay and structural row attribution, not
from a selected witness subset. They are source-reference limits, not calibrated
anatomical thresholds.

The separate scene stage replays all 660,002 saved native rows and every cached
mesh vertex against the actual exports, freshly rechecks coupled contacts, and
calls the unchanged direct geometry evaluator. Geometry is explicitly measured
**diagnostically despite native failure**. The qualification condition still
requires zero native failures, so these measurements cannot approve the clip.
This guard completes in 89.328 seconds at 307,367,936 bytes; all 90 resource
observations replay.

The five-time geometry comparison improves 19 measurements, regresses six and
leaves ten unchanged. The largest directional depth decreases from 20.590680 to
15.727350 mm, still above the 5-mm screen. Four intersection counts increase;
at 2.033333302 seconds A-inside-B peak depth increases from 7.778888 to
7.948739 mm and the count of A vertices deeper than 5 mm increases from 18 to 32.
Both actors also retain all 2,017 physical floor failures. The candidate remains
rejected and the original remains selected. This study does not establish a
quality benefit from finger articulation alone.

Next, distinguish continuous-preview errors from stored-export effects and
attempt bounded nonlinear rate restoration using the measured current motion
while retaining the original reference caps, layouts and source assets. A
recentered proposal must not treat the failed candidate as a new source. Surface
objectives also need to account for the remaining intersection regressions;
neither a successful solver status nor better maximum depth proves acceptance.
