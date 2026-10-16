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
