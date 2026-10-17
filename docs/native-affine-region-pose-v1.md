# Native affine region pose constraints

The [moving contact study](native-coupled-curve-v1.md) finds real high-five
intersections during approach and follow-through, despite a passing contact
pose. The next authoring step needs original-bound surface constraints at
other native keys, with the contact key and source references preserved.

## Reusable constraint rows

`scripts/native_affine_region_pose.py` provides `RegionPoseRows` around the
qualified `PartitionedAffineKeyPose` evaluator. A caller supplies a source
pose/time, complete original-relative controls, an explicit subset of editable
native joints, one displacement band per skin joint, and explicit surface
regions with world halfspaces. It retains native affine transforms and every
skin influence; it does not project the rig to rigid matrices.

Each evaluation retains all rotation-ball rows, including fixed controls,
all skin-joint displacement rows, and every requested region vertex. Active
nodes may occur anywhere in the original control order. The helper copies
the original reference, local matrices, degree caps and placement, and rejects
changes to those bound inputs instead of silently recentering a later iterate.

A region declares a unit normal, scalar plane offset, sign and minimum gap:
`sign * (point_world · normal_world - offset_m) >= minimum_gap_m`.
The default 1-cm normalization affects numerical conditioning only. It does
not change the physical gap. Neither anatomical regions nor a separating
plane are inferred by the helper.

Inputs retain 1–32 declared regions and complete positive joint bands from
1 micrometre to 1 metre. The output is bounded by at most 100,000 rows and
64 MiB for its dense Jacobian. A caller may choose smaller budgets. Requests
that exceed either bound reject completely, before pose evaluation; no rows,
vertices or small derivatives are discarded. The underlying pose evaluator's
separate complete-skin workspace budgets still apply. Measured process guards
remain necessary.

This module constructs rows and derivatives; it does not choose a solver,
edit a source asset, approve an animation, or validate a motion interval.

## Focused validation

The affected local selection passes 77 tests in 101.49 s, including 42 new
cases and the existing partitioned/affine pose suites. New cases cover
nonprefix active controls, fixed original controls, complete region rows,
world placement, affine scale, homogeneous skin coordinates, finite-difference
derivatives, constructor input copies, unchanged source references and actual
Float32 native save/reload. Invalid and over-budget inputs reject before the
pose evaluator runs.

The successful test guard takes 119.390 s at 127,619,072 peak sampled bytes;
all 119 resource observations replay. The first test attempt retains four
failures: one test incorrectly assumed two times in a static fixture must
have different poses, and three existing integration cases encounter the
launcher's outer worker lock when taking their own fixture locks. The fresh
launcher preserves the actual project worker lock and memory guard while
giving tests isolated fixture lock directories. It also tests an explicitly
changed source reference rather than the invalid static-time assumption.
The failed attempt remains separately archived: 35.547 s, 117,829,632 bytes,
37 replayed observations, 73 passed/four failed. No guard is disabled.

Inventories now declare 555 Python/45 Node suites, with 121/five in the
contact subset. Counts do not establish a full-inventory pass.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/38994386967)
at source `35f6605` passes all 42 new cases on each OS: Ubuntu in 2.93 s
and Windows in 13.64 s. This is separate from the 77-case local selection.

The [contact/rig regression run](https://github.com/DocMorphic/strep/actions/runs/38994579949)
at the same source passes all eight jobs across Ubuntu and Windows, including
both contact shards, lineage and game-package source checks. The broader
source inventory run is still in progress when these results are recorded.
Source regression success does not validate the generated clips or constitute
an actual engine import or human review.

## Follow-through pose feasibility pilot

At existing native key 63 (2.0999999046325684 s), both actors retain the
original angular caps, original 60-mm wrist/other-joint and 150-mm finger
bands, original roots, fixed finger controls from the moving v4 initializer,
and a source-derived shared plane. All positively hand-influenced incident
triangles participate: 2,960 vertices in 5,892 triangles per actor. A has
nine active body coordinates and B twelve. The guide asks each hand region
to stay at least 1 mm on its own side of the plane.

The elastic proposal uses temporary slack only during search, a 1e-6
normalized hard-row reserve and a separate 20-micrometre plane reserve.
No physical threshold or original source reference changes. Search converges
in six optimizer iterations and 14 evaluated poses, taking 11.797 s.
All 6,119 original angular/world/region rows pass without temporary slack.

The saved Float32 clips also pass the selected pose's angular/world/plane
rows. Fresh complete partner/floor geometry finds zero partner surface
records and zero legacy signed vertex depth. Hand self scans find zero
records for both actors. The original binary prefixes, rig declarations,
original animations, every other key/track, the 2-s contact worlds and both
endpoint worlds remain unchanged. Maximum raw-to-decoded vertex differences
are 1.644889e-8 m / 1.443148e-8 m. Floor depths are 2.169752 mm / zero at
this one time.

The complete pilot guard takes 63.813 s at 215,703,552 peak sampled bytes;
all 65 resource observations replay. Records are local under
`reports/high-five-followthrough-pose-repair-v1`. This intentionally edits
only one key to establish pose feasibility. Neighboring motion, rates,
complete partner/self clocks, full-body self, engine playback and human
quality remain unvalidated. It is not a corrected motion release. The
original remains selected and all quality/release flags remain false.

## Independent row replay and guide scope

The reusable helper independently reconstructs the pilot's 6,119 conditions
with maximum difference 1.776357e-15. All raw world matrices, vertices and
full controls reconstruct exactly; all decoded vertices and expected
Float32 channels also match exactly. Four additional actual-asset directional
derivative checks pass. Original source contents, original reference epoch,
contact worlds and endpoints remain intact. Collision predicates are not
rerun: their existing evidence is bound through identical decoded vertices,
topology and policy. The replay guard takes 47.687 s at 205,930,496 bytes;
all 49 resource observations replay under
`reports/high-five-followthrough-region-replay-v1`.

The unchanged v4 curve is also screened against the same fixed guide at all
120 native keys. Forty-one keys fail: 32–43, 49–59 and 61–78. The fixed
contact key 60 and both endpoints pass. These are guide failures, not 41
proven mesh collisions. For example, key 75 at 2.5 s has an approximately
49.786-mm fixed-plane deficit for B, while its prior complete partner/floor
sample passes. A single fixed plane overconstrains part of the gesture.

Four additional complete v4 partner/floor checks establish that actual
collisions extend beyond the original dense packet:

| Native time, s | Surface records | Maximum legacy vertex depth, mm |
| --- | ---: | ---: |
| 2.166666746 | 344 | 20.189035 |
| 2.200000048 | 303 | 18.638227 |
| 2.299999952 | 158 | 12.114485 |
| 2.400000095 | 366 | 10.205848 |

Each has an exact represented-triangle strict crossing witness. All of the
listed crossing triangles belong to the complete hand regions on both
actors. This still does not establish that all body collisions at other
times are covered by those regions. V4 coverage becomes 143/2,017 distinct
times with 54 failures and 1,874 unchecked; this is a different curve from
the one-key repair pilot. The boundary guard takes 149.422 s at
232,521,728 bytes, with all 149 resource observations replayed, under
`reports/high-five-v4-followthrough-boundary-geometry-v1`.

## Candidate-derived axis screening

A separate proposal screen uses complete 2,960-vertex hand regions at native
keys 57–75. It tests both signs of the original contact normal, every face
normal from both full-region convex hulls, and the centroid-difference axis
when defined. Every original region vertex is projected on every tested
axis; hull vertices do not replace the surface population. Projection chunks
contain at most 64 axes, with a complete-family limit of 10,000 axes per
key. No edge-cross family, optimal separating direction or collision
certificate is claimed.

The selected direction maximizes `min(B · axis) - max(A · axis)` within that
explicit finite family. Its plane offset is the midpoint of the two support
extremes. At key 66, the selected support gap is -54.0462 mm, compared with
-158.2618 mm along the original contact axis. The selected axis differs
by 81.307 degrees. Negative best gap does not prove inseparability along
untested directions or physical mesh overlap.

These axes are guides measured on the explicit v4 candidate at each time.
They never become a new zero for angular or joint-displacement bounds.
Physical scene acceptance stays unchanged. At later times even this
finite-family convex-region guide can be unnecessarily restrictive; the
actual mesh checks remain authoritative.

Records are under `reports/high-five-moving-hand-axis-screen-v1`. The
guard completes 19 native-key screens in 40.610 s at 128,385,024 sampled
bytes; all 42 resource observations replay. These are proposed directions,
not fitted motions or animation approval.

## Moving-guide follow-through pilot

A second pose pilot uses existing key 66 (2.200000047683716 s), with the
screen's candidate-derived axis and support midpoint. A separate guide
coordinate permits at most 60 mm of shared plane-offset movement; it does
not move either character root or redefine any original joint permission.
There are 21 body coordinates and one guide coordinate. Finger controls
remain fixed to their original-relative v4 values at this time.

The normalized hard search reserve is explicitly 0.001, compared with
1e-6 in the first pilot; physical angular/world bounds stay unchanged.
The plane search reserve remains 20 micrometres inside the same 1-mm
half-gap. The selected shared plane shift is 0.732691 mm. Its axis differs
81.307 degrees from the contact guide, which is a change to a geometric
proposal direction, not an 81-degree joint edit.

Search takes 14.329 s, eight optimizer iterations and 15 evaluated poses.
All 6,119 original physical/region rows pass before and after Float32
encoding. Fresh complete partner/floor geometry has zero partner records
and zero legacy vertex depth; localized hand self scans have zero records
for both actors. The contact and endpoint worlds, other keys/tracks and
original asset contents remain unchanged. This still establishes only the
selected pose, not its neighboring animation.

The pilot guard completes in 79.406 s at 211,906,560 sampled bytes with
all 80 observations replayed. A fresh independent replay reconstructs
worlds, vertices, controls, expected Float32 tracks and source contents;
all 6,119 rows agree within 1.776357e-15. Four body derivative directions
and all 5,920 shared-plane derivative rows are checked. Collision predicates
are not rerun in this replay. Its guard completes in 42.531 s at
222,887,936 bytes with all 44 resource observations replayed.
These are `reports/high-five-followthrough-pose-repair-v2` and
`reports/high-five-followthrough-region-replay-v2` respectively.

The next sequence proposal uses these constraints at neighboring native
keys, preserving the contact key and original reference at every time.
Previous corrected coefficients may influence a declared smoothing target;
they never become the zero for source-relative bounds. A complete decoded
curve still needs interpolation, rate, full partner/self, engine and human
validation before any promotion.

## Pre-contact self-collision and finger posture

The first sequential proposal stops at key 59. Its decoded angular/world/
plane and partner/floor checks pass, but B retains 20 localized hand
self-intersection records. The controller does not promote the sequence.
A same-time comparison distinguishes this from a body-repair regression:

| Actor | Original hand records | V4 initializer | Body-corrected proposal | Projected finger-reference raw pose |
| --- | ---: | ---: | ---: | ---: |
| A | 92 | 0 | 0 | 0 |
| B | 214 | 20 | 20 | 0 |

The body proposal introduces no same-kind pairs relative to v4. B's 20
pairs differ from the original source's pairs; fewer records are not by
themselves an acceptance score. The source diagnosis is recorded under
`reports/high-five-precontact-hand-self-origin-v1`, completing in 111.359 s
at 206,467,072 bytes with all 111 resource observations replayed.

The new reference takes the actual local finger rotations from the verified
2-s contact pose. At the current time it computes each target relative to
the unchanged original quaternion, then projects the rotation vector inside
0.999 of that joint's existing edit ball. It is a distinct posture initializer,
not the earlier fixed tapered-offset condition or a new source zero. One B
finger's exact target would require 1.005623 of its existing 30-degree cap;
that target is clipped, rather than receiving a larger cap.

At key 59, this changes vertices by at most 5.231726 mm for A and 8.028244 mm
for B. The raw continuous reference has zero hand-self records for both actors,
zero partner records, a passing floor condition and no failed joint bands.
Those raw results alone do not establish saved-file success. A fresh sequence
study subsequently saves/reloads key 59 and passes its angular/world/plane,
full partner/floor and localized hand-self checks with zero records for both
hands. It still does not establish interpolation or complete motion quality.

The first launch of the new condition fails before fitting because its
private study driver omitted the rotation dependency import; its failed guard
and trace remain preserved. The fresh driver corrects that import and retains
the same numerical condition. The sequence adds a declared previous-key
coefficient target and feasible coefficient refinement. These are smoothing
proposals, not calibrated physical-rate bounds or a joint temporal optimum.

## Saved poses versus their combined motion

The corrected sequential studies `high-five-native-contact-sequence-fit-v3`
and `-v4` save and reload 15 separate poses: key 59 and keys 61–74. Each
passes all 6,119 declared rows, the complete partner/floor check and localized
hand-self checks for both actors. Their guards and archived source bindings
are independently replayed. This establishes those poses only.

`high-five-native-contact-sequence-assembly-v1` combines the 15 changes into
actual editable 120-key clips. Original animations, source geometry, untouched
tracks and keys, root movement, endpoints and the 2-s contact remain exact.
The combined files reproduce every corrected pose's worlds and complete
vertices exactly; only those 15 native-time observations are inherited.

The combined curve exposes failures that separate poses miss:

| Check | Combined result |
| --- | --- |
| Original angular limits, 2,017 times | Both actors pass |
| Complete floor, 2,017 times | Both pass; source floor minima unchanged |
| Original joint displacement limits | A fails 8 rows; B passes |
| Source-relative rate budgets, speed/acceleration/angular speed/angular acceleration | A: 552 / 372 / 2,076 / 271; B: 907 / 395 / 396 / 248 failed rows |
| New partner/floor checks between native keys | 3 failures among 21 selected times |

The three partner failures occur at 2.15, 2.45 and 2.483333333 s, with
191, 271 and 42 surface records and legacy depth estimates of 17.628455,
7.377448 and 1.096134 mm. Surface intersections independently fail the
condition even when the reported vertex depth is below the 5-mm limit.
These 21 checks are not full-clock partner coverage. Rate budgets are
conservative source-relative edit limits, not calibrated anatomical realism
thresholds; the release declarations remain unset.

The assembly's guard completes in 322.453 s, with a peak process-tree RSS
of 371,163,136 bytes and all 319 resource observations replayed. Original
source world/floor arrays are reused only through their exact prior
independent replay bindings, with six additional world spot checks per actor;
the candidate's complete sampled arrays are freshly evaluated.

`high-five-native-contact-sequence-interval-diagnosis-v1` reproduces all eight
world-limit failures from the saved arrays. They affect A's right wrist
between keys 65 and 66, peaking at 60.177899 mm against its unchanged 60-mm
limit. The region guide also changes direction by 100.389 degrees between
keys 64 and 65 and 123.823 degrees between 73 and 74. These are guide-axis
changes, not measured joint rotations. The diagnosis completes in 18.250 s
at 172,789,760 bytes with all 20 resource observations replayed.

A fresh condition therefore tests coherent neighboring guide axes, a symmetric
neighbor coefficient target and a 0.313921-mm inner world search reserve.
That reserve does not expand the original 60/150-mm physical limits or make
the original motion reference a corrected clip. Its results must be evaluated
as a new combined curve, retaining the failed assembly above.

## Coherent neighboring-guide trial

`high-five-native-contact-sequence-coherent-fit-v1` changes only keys 64,
65, 66 and 74 of the first assembly. At 64 and 74 the guide uses the
normalized sum of neighboring oriented normals; plane offsets come from
the actual initializer's complete hand supports. The body-coefficient
objective targets 0.25 previous + 0.5 current + 0.25 next. Fingers retain
the explicitly projected local-posture prior described above.

The search retains a 0.001 normalized angular reserve and derives every
world-row reserve from the same 0.313920596-mm physical inner margin and
that row's unchanged original band. A verified body-only ray supplies a
feasible hard-row initializer. These are search conditions; the original
60/150-mm acceptance bands and source poses do not change.

All four separately saved/reloaded poses pass all 6,119 declared rows,
complete partner/floor checks and both localized hand-self checks with
zero records. Each terminal trace replays with matching archived bindings:

| Native key | Worker execution (s) | Peak process-tree RSS (bytes) | Resource observations |
| --- | ---: | ---: | ---: |
| 64 | 65.266 | 211,419,136 | 82 |
| 65 | 102.859 | 216,301,568 | 119 |
| 66 | 73.250 | 220,803,072 | 90 |
| 74 | 56.984 | 211,955,712 | 74 |

Execution excludes the separate 15-s stable-memory admission. These pose
results do not establish that the revised assembled motion passes between
keys, satisfies source-relative dynamics, or has acceptable anatomy.

## Revised combined motion

`high-five-native-contact-sequence-assembly-v2` applies those four explicit
overrides to the same 15-key assembly. It freshly evaluates the complete
2,017-time candidate joint/floor populations. Both actors now pass all
original joint displacement and angular limits; floor minima remain exactly
the original minima. The previously observed 0.177899-mm wrist excess is
absent in this sampled candidate. Root movement, endpoints, contact at 2 s,
all 120 native timestamps, source prefix and original animations remain exact.

The 21 selected between-key partner/floor checks still contain three failures:

| Time (s) | Surface records | Legacy depth (mm) |
| --- | ---: | ---: |
| 2.116666667 | 22 | 0.561473 |
| 2.118750000 | 48 | 2.793270 |
| 2.483333333 | 155 | 3.704693 |

The former 2.15-s and 2.45-s failures pass, but the changed trajectory
introduces two earlier failures and retains the 2.483333-s failure. All
three fail the surface-intersection condition despite depths below 5 mm.
This is not a collision-free motion, and fewer records or lower depths
do not establish an overall quality improvement.

Source-relative rate failures remain A: 544 / 384 / 2,204 / 280 and B:
814 / 377 / 396 / 237, in the same metric order as above. There is no
complete partner/self-clock, continuous collision, anatomical, engine or
human approval. The guard completes in 235.187 s at 370,106,368 peak
sampled bytes; all 234 resource observations replay with matching bindings.

The next numerical condition must account for actual quaternion interpolation
between existing keys. Independently optimizing each native pose against its
own guide can move a failure to a neighboring interval even when every
selected saved pose and sampled original displacement band passes.

## Native-key interpolation map diagnostic

`high-five-native-interval-control-map-pilot-v1` tests the next mathematical
component before fitting another candidate. It maps selected existing native
body-key controls through the actual LINEAR quaternion interpolation into
the original-relative local controls expected by the affine pose evaluator.
Unedited endpoint quaternions come from the actual saved initializer; active
endpoints use the unchanged original quaternions and degree caps. Fingers,
translations, scales and the original source pose at each subkey time remain
fixed. No interpolated or corrected pose becomes the source reference.

Ten actor/time cases cover both actors at 2.116666667, 2.11875 and
2.483333333 s and native keys 64 and 74. The early cases include two
independently editable neighboring keys, 63 and 64; the late cases use 74.
Reproducing the current Float32 endpoints gives a maximum world-matrix
difference of 9.992008e-16 and a maximum complete placed-vertex difference
of 9.164595e-16 m against the actual native sampler. Every declared hand
region retains all 2,960 vertices, and every original angular/joint row
remains present.

The diagnostic composes a central-difference control map (step 1e-6) with
the existing complete analytic affine row Jacobian. All 30 independent
directional checks pass against direct differences at step 2e-6, with
maximum absolute normalized-row error 1.569589e-8. This is measured
agreement at these samples, not an analytic derivative of interpolation or
a bound over all possible inputs. The guard completes in 81.328 s at
241,643,520 peak sampled bytes; all 82 resource observations and archived
bindings replay.

This diagnostic performs no fit, new clip export or collision predicates.
It does not change the failed assembled candidate or confer interval,
dynamics, engine or human acceptance. Its private study implementation is
archived with the report; it is not yet a public general-purpose solver API.

## Joint constraints at subkey times

`high-five-native-subkey-constraint-fit-v1` fits the 21 body coordinates at
existing key 64 jointly against four actual interpolated times. Study `-v2`
does the same at key 74. Each fit has four separately bounded guide-plane
offset coordinates, giving 25 variables. Both retain the current saved
fingers, all other native keys/tracks, original timestamps, root movement,
2-s contact, endpoints, original animation prefix and unchanged physical caps.
The original source pose is sampled independently at each constraint time.

| Study | Constraint times (s) | Optimizer iterations | Search (s) |
| --- | --- | ---: | ---: |
| Key 64 | 2.116666667, 2.11875, 2.133333445, 2.15 | 5 | 52.031 |
| Key 74 | 2.45, 2.466666698, 2.475, 2.483333333 | 4 | 47.375 |

For each fit, all 24,476 complete angular/world/hand-region rows pass before
and after Float32 export. This includes 796 original angular/joint rows
and every region vertex at all four times. The shared plane offsets remain
separate guide coordinates, each bounded to 60 mm; this does not expand any
skeleton edit limit. Search requests a 1e-6 normalized hard reserve and a
20-micrometre region reserve. Retention and decoded acceptance use the
unchanged original inequalities with zero temporary slack; the selected raw
minimum original hard rows are 9.999855e-7 and 9.021998e-7 respectively.

The guide normal varies by normalized interpolation of neighboring oriented
native guides, and offsets start at the actual initializer's support midpoint.
The tested control-map Jacobian composes with the complete pose Jacobian.
Two independent full-row directional checks run for each actual fit before
search. The solver minimizes temporary feasibility slack with a small
coefficient-change penalty. It does not optimize a physical dynamics model
or claim a global solution.

Fresh complete partner/floor checks pass at all eight selected times with
zero surface records. Both localized hand-self scans have zero records at
each time: 16 scans total. Neither fit alone establishes interpolation between
those times, full sampled source-relative dynamics, whole-body self geometry,
anatomical quality or engine/human acceptance.

The key-64 guard completes in 166.781 s at 268,472,320 peak sampled bytes
with 166 replayed observations. Key 74 completes in 150.375 s at
255,590,400 bytes with 150 replayed observations. Both terminal traces and
archived bindings replay. The failed assembly-v2 remains unchanged; these
are separate candidate files until independently combined and checked.

## Combined subkey-constrained candidate

`high-five-native-contact-sequence-assembly-v3` combines the body-only
key-64 and key-74 updates with assembly-v2. There are 15 additional repaired
keys relative to the already edited tapered-v4 initializer; this revision changes only two body
keys relative to its assembled initializer. All 120 timestamps, fingers,
other tracks, root movement, endpoints, contact at 2 s, original binary
prefix and original animations remain exact.

Fresh complete joint/angular/floor evaluation at all 2,017 declared times
passes for both actors. The previous candidate is also freshly decoded to
verify exact world identity outside the two changed key intervals. Original
source world/floor arrays retain the independently replayed file bindings
described above. The candidate's floor minima remain exactly the original
minima, including A's 4.5-mm maximum depth.

All 23 fresh selected partner/floor checks pass with zero surface records:
the previous 21 selected subkeys plus the two changed native poses. This
includes the three assembly-v2 failures. No native-pose geometry observations
are inherited in this run. Passing these selected samples is not full-clock
partner coverage or a continuous-time separation proof.

Source-relative rate failures remain, and several counts increase:

| Actor | Linear speed | Linear acceleration | Angular speed | Angular acceleration |
| --- | ---: | ---: | ---: | ---: |
| A | 632 | 388 | 2,188 | 280 |
| B | 862 | 400 | 500 | 249 |

These are the same unchanged original edit budgets. Neither improved selected
collision results nor passing displacement bands establish overall motion
quality. The candidate has no whole-clock self, anatomical, engine, animator
or release approval, and the original remains selected.

The combined guard completes in 250.766 s at 367,927,296 peak sampled bytes,
with all 248 resource observations and archived bindings replayed. A separate
fresh survey, `high-five-native-subkey-dense-partner-v1`, is launched to check
all 70 declared geometry-clock samples inside native intervals 63–65 and 73–75.
Its results are pending; it does not cover the rest of the clip or unsampled
time, and this section does not count planned work as passed coverage.

## Complete sampled check of the two repaired intervals

The dense survey completes all 70 declared geometry-clock samples in native
intervals 63–65 and 73–75. It freshly skins both complete meshes at every
time; no interpolation result or geometry observation is inherited. The
first interval passes throughout its sampled clock. Five failures remain
near the end of the second interval:

| Time (s) | Surface records | Legacy depth (mm) |
| --- | ---: | ---: |
| 2.489583333 | 83 | 3.018054 |
| 2.491666667 | 91 | 6.012435 |
| 2.493750000 | 158 | 4.401407 |
| 2.495833333 | 97 | 6.851848 |
| 2.497916667 | 87 | 4.919284 |

All five fail the surface condition; two also exceed the unchanged 5-mm
legacy penetration limit. The passing 23 selected checks therefore do not
establish an acceptable sampled path. The survey completes in 261.547 s
at 188,465,152 peak sampled bytes, with 258 resource observations and the
archived bindings independently replayed. All failed samples retain their
full posed vertices and geometry observations.

The next condition explicitly adds neighboring body key 75 to editable key
74 and jointly constrains 11 times, including every newly observed failure,
both native keys and two samples after 75. Key 75 is an interior clip key;
the unchanged original taper experiment spans native keys 0–119. This is
a different authoring condition from editing only key 74. Fingers, original
physical caps, root motion, the 2-s contact and actual clip endpoints remain
fixed. Extending the editable pair also extends its affected interpolation
window to native interval 73–76, which needs separate validation.

The first two-key attempt (`high-five-native-subkey-constraint-fit-v3`)
stops before optimization at its requested 1e-6 inner search reserve. The failed guard
completes in 52.078 s at 247,689,216 bytes with all 53 observations replayed.
The original physical inequality still uses zero; its threshold is not
increased or relaxed. Fresh study `-v4` records every initial row and verifies
a body-only warm ray. Multiplying just the two editable body-key controls by
0.99999 yields a minimum hard row of 1.877527e-5 with the original source,
fixed fingers and physical limits unchanged. The fresh reconstruction records
the original initializer's minimum hard row as 9.021998e-7. This is an
initializer, not a new source zero or an accepted animation.

The two-key fit then converges in three optimizer iterations and 12 evaluated
controls, taking 145.937 s for search. All 67,309 original angular/world/
region rows pass before and after Float32 export at the 11 declared times.
This includes 2,189 complete angular/joint rows. Fresh complete partner/floor
checks pass with zero surface records at every time, and all 22 localized
hand-self scans have zero records. The selected raw minimum original hard
row is 9.915691e-7 and the minimum region row is 0.002738149. Physical
thresholds remain unchanged; temporary search slack is not accepted.

The guard completes in 403.734 s at 415,297,536 peak sampled bytes, with
399 observations and all archived bindings replayed. These are selected-time
results of the explicitly different two-key condition. Complete sampled
displacement/floor/dynamics and partner coverage over the expanded 73–76
interval remain unproven until separately evaluated.

## Reusable native-key map

[`KeyPoseMap`](../scripts/native_key_pose_map.py) makes the tested interpolation
construction available to the authoring layer. It accepts a qualified
`PartitionedAffineKeyPose`, the unchanged original source time, a complete
original-relative native control seed, and explicit `(key, node)` pairs.
The pairs may use arbitrary permitted joints and nonprefix control order.
It does not select permissions, infer anatomical targets or edit an asset.

`controls(value, quantized=True)` reproduces Float32 endpoint encoding for
comparison with saved native clips. `evaluate(value)` returns continuous
sample-time original-relative controls and a central-difference map Jacobian.
Only the actual one or two interpolation endpoints contribute pose derivatives;
other selected keys retain exact zero columns. Their native rotation-ball
rows remain present regardless of whether they influence this sample time.

`region_rows(problem, value)` composes the map with all declared affine
angular/world/region rows and appends every selected native rotation ball.
The region problem must use the identical original model/time and all local
controls in source order. No source pose, control zero, physical degree cap,
skin influence or requested region row is replaced or truncated. Fixed seed
rotation balls are verified at construction; selected native balls are
observable inequalities even for a key outside the sampled interval.

The bounded component supports at most 4,096 native keys, 768 selected scalar
coordinates, 100,000 complete composed rows and 64 MiB per returned Jacobian.
Smaller caller budgets reject completely when insufficient. Finite-difference
steps are bounded from 1e-8 through 1e-4. Proposal components outside [-2,2]
reject as a numerical-domain guard; the physical normalized rotation-ball
limit remains one. File/rig provenance, editing permissions, decoded motion,
complete geometry, dynamics, engine import and human quality remain caller
responsibilities.

The locally guarded affected selection passes 103 tests in 30.65 s: 46 new
map cases, 42 existing region cases and 15 partitioned-pose cases. New tests
use an actual changing affine source with alternating quaternion signs,
Float32 native export/reload at boundaries, native and between-key times,
placed/homogeneous skin derivatives, complete native ball rows outside the
sample interval, input copies, source mutation rejection and complete budget
rejection before pose evaluation. The guard completes in 74.219 s at
131,969,024 bytes, with all 75 observations and archived bindings replayed.
The public source and tests are byte-identical to this tested candidate.

Inventories now declare 556 Python/45 Node suites and a contact subset of
122/five. These are registration counts; the newly changed complete inventory
and hosted map checks have not yet established a pass at this point.

The subsequent [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/39002002360)
at source `2f75132` passes the 46 new cases on both Ubuntu and Windows.
This does not establish a pass for the newly changed full inventory.

`native-key-pose-map-actual-replay-v1` independently exercises the public API
against the prior diagnostic map and actual saved character clips. Sixteen
actor/time cases include original native and subkey times, both actors and
two independently selected neighboring keys. Original-relative local
controls and their map Jacobians match the prior implementation exactly.
All composed pose rows and appended native balls agree. The largest saved
world-matrix difference is 1.332268e-15 and the largest complete placed-vertex
difference is 9.139343e-16 m. All 32 independent directional checks pass,
with maximum absolute normalized-row error 1.487347e-8.

The replay completes in 99.844 s at 241,225,728 peak sampled bytes; all
100 resource observations and archived bindings replay. It performs no new
fit/export or collision predicates, and the floating agreement is not used
as bitwise collision inheritance or animation-quality approval.

## Edit-scope accounting correction

Earlier 15-key totals describe additional repairs to the already edited
tapered-v4 initializer, not every modification to the original raw source.
The immutable assembly-v3 field `cumulative_original_source_edited_keys`
is mislabeled and must not be used as a raw-source edit count. Those
historical reports and candidate files remain unchanged.

The new assembly-v4 encoding audit computes both scopes directly. For each
actor, 118 of 120 keys have nonzero original-relative controls and actually
changed encoded quaternion values compared with the raw source. Sixteen
keys differ from the tapered-v4 controls: 59 and 61–75. Assembly-v4 itself
changes body keys 74/75 relative to assembly-v3. The clip endpoints remain
unchanged, while the authored 2-s contact is preserved from the tapered
initializer rather than being described as an unchanged raw-source pose.

These counts are recorded separately in `assembly-v4/edit-scope.json`,
including the complete key lists and their comparison references. They are
encoding/provenance measurements; the new combined candidate still needs
its complete sampled motion and expanded-interval geometry checks.

## Combined two-key repair and expanded dense check

Assembly-v4 subsequently completes the full sampled motion checks. Both
actors pass original joint displacement and angular limits at all 2,017
times, and complete floor checks pass with the original floor minima intact.
Actual world transforms are freshly compared with assembly-v3 outside native
interval 73–76; those worlds remain exact. True clip endpoints and root
movement remain raw-source exact, and the authored 2-s contact pose remains
unchanged from the tapered initializer.

All 32 fresh selected partner/floor checks pass with zero surface records.
They include the preceding selected points, the five dense failures, key 75
and post-75 samples. The full guard completes in 272.875 s at 369,061,888
peak sampled bytes, with 271 observations and archived bindings replayed.

`high-five-native-subkey-dense-partner-v2` then freshly evaluates every
declared geometry-clock sample inside native intervals 63–65 and 73–76.
All 86 samples pass complete partner/floor checks with zero surface records.
This includes the additional interpolation interval introduced by editing
key 75; checking only the previous interval would be insufficient. The guard
completes in 271.594 s at 192,000,000 peak sampled bytes, with all 269
observations and archived bindings replayed.

The two runs' sample-index union contains 102 distinct times for the same
candidate out of the 2,017-time geometry clock. Thus 1,915 times have not
received partner geometry checks from these runs. Complete sampled coverage
of two intervals is not a whole-clip or continuous-time collision certificate.
Localized hand-self scans remain the 22 selected-time observations from the
fit; whole-clip self geometry is not established.

Unchanged source-relative rate budgets still fail: A has 632 / 388 / 2,188 /
280 failed rows; B has 886 / 425 / 500 / 249. B's linear-speed and
linear-acceleration counts increase relative to assembly-v3. These are the
same diagnostic edit budgets, not newly calibrated realism thresholds.
The original remains selected and no anatomical, engine, developer/animator
or release approval is granted. Next steps are complete clip coverage and
integration of the tested key-map component into the scene authoring path.

## Whole-clock continuation exposes earlier intersections

The later journal `high-five-subkey-full-geometry-journal-v1` uses assembly-v4
and the complete 2,017-time clock with partner query batches of one. Its first
64 and then 320 committed samples pass. Continuing the same pinned journal
finds the first failure at index 586, time 1.1541666666666666 s. At the saved
611-sample prefix, 25 samples fail (indices 586–610). This contradicts any
whole-clip interpretation of the preceding 86-sample interval result; that
interval result remains valid within its original scope.

The continuation was intentionally stopped after those failures were saved,
to avoid spending the remaining query time on a known failing candidate.
The owned worker processes were identified before stopping; the supervisor
recorded a failed terminal result. This was neither a RAM stop nor a complete
population run. The stopped guard records 700.984 s, 220,811,264 peak sampled
bytes and 692 observations, with archived bindings and resource replay intact.
The final committed checkpoint and the abandoned next-frame attempt remain
available. The suffix of 1,406 clock samples is not counted as verified.

`high-five-subkey-full-geometry-diagnosis-v1` independently revalidates the
611-frame checkpoint chain and reconstructs the first failure using the public
geometry path. All 85 first-frame surface records receive independently
verified exact rational crossing witnesses for the represented Float64
triangles. This certifies those represented triangle crossings; it does not
certify unrounded skinning, penetration depth or continuous collision. The
public and affine skin providers differ by less than 1e-15 m at this frame,
so provider rounding cannot explain these millimetre-scale intersections.

Across the 25 failed frames, 4,781 records involve A triangles outside the
declared right-hand influence region against B's right-hand region; another
2,897 involve both right-hand regions. These are influence-region labels,
not anatomical classifications. Further correction must inspect the complete
approach and interacting body regions rather than only the late palm contact.
The independent diagnosis guard completes in 47.672 s at 130,899,968 sampled
bytes, with all 49 observations replayed. Assembly-v4 remains unapproved.

`high-five-early-crossing-origin-v1` next compares exactly those same 85 pairs
at the first failed time across three immutable epochs. All 85 pairs have
strict rational separating-axis proofs in the raw source; all 85 have exact
crossing witnesses in both tapered-v4 and assembly-v4. Complete vertices for
both actors are bitwise identical between taper and assembly at this time.
Thus these specific intersections were introduced by the broad taper, not by
the later key repairs. This is a failure-conditioned 85-pair comparison, not
an assertion that the raw scene has no other collisions. The guard completes
in 30.485 s / 176,984,064 sampled bytes / 32 replayed observations. The next
repair must reconsider the approach correction and validate its complete
affected time range, while preserving the authored contact and original bounds.

## Complete fixed poses with bounded derivative columns

The generic native pose evaluator now separates the full edited pose from
the coordinates being differentiated. `evaluate_columns(value, columns)`
applies every supplied control and returns derivatives in the explicitly
requested column order. `transforms` evaluates the complete hierarchy and
skin-joint position derivatives without allocating skinned vertex derivatives.
The existing `evaluate(value)` remains a complete-column request.

`PartitionedAffineKeyPose` permits 1–96 declared joints with an optional
`maximum_derivative_controls` bound. Its 16-node constructor blocks, 30-degree
maximum caps, 128-MiB derivative limit and 256-MiB estimated workspace limit
remain unchanged. Allocation estimates now use the declared derivative width.
Requests exceeding that width fail; no fixed control, vertex or skin influence
is removed. A real two-hand pose can retain more than 32 joint controls while
differentiating only the explicitly editable arm coordinates. This is a
working-set bound, not a promise of process RSS; guarded execution still applies.

`RegionPoseRows` retains every declared rotation, joint and region row while
requesting only its active derivative coordinates. `KeyPoseMap.region_rows`
accepts that partial helper only if it covers every topologically dependent
coordinate and its fixed values exactly match the complete original-relative
seed at the sampled time. All selected native-key ball rows remain, including
keys outside that time's interpolation bracket. There is no source rebase.

The affected local selection passes 145 cases in 106.72 s: 22 new selected-column
cases and 123 existing key-map, region, partitioned and affine cases. The new
tests cover a 64-controlled-joint hierarchy, empty/nonprefix/reversed columns,
full-pose and finite-difference agreement, Float32 save/reload, fixed-control
row retention, interpolation dependencies and invalid/changed budgets. The
512-MiB guard completes in 137.344 s at 128,335,872 peak sampled bytes; all 137
observations and archived bindings replay. Inventories declare 557 Python/45
Node suites and 123/five in the contact subset; these are inventory counts,
not full-inventory test results. This math change does not grant motion quality
or release approval and is not yet an end-to-end scene editing workflow.

### Actual two-hand rig probe

`native-affine-selected-columns-actual-v2` probes both actual SOMA rigs at
four times each. It retains 44/46 controlled joints (132/138 coordinates),
all 77 skin-joint rows, both complete 2,960-vertex incident hand regions and
every one of the eight skin influences. Only 9/12 arm coordinates are
differentiated. Requesting full derivatives still rejects at the unchanged
workspace budget. The other hand has an explicitly synthetic nonzero seed,
with exact zero at the true clip endpoints; it is not a generated or reviewed
animation. Zeroing it changes vertices by 3.536–11.510 mm, confirming that
the fixed hand's pose is actually retained rather than silently ignored.

Eight actor/time checks, 16 directional vertex checks and eight composed-row
checks pass. The maximum vertex derivative error is 3.149e-10; the maximum
normalized composed-row directional error is 3.267e-8. Native Float32 exports
preserve the original binary prefix and original animations. Quantized pose
worlds agree with native reload within 1.333e-15, and all complete skinned
vertices within 1.342e-15 m. The unrounded proposal differs from the encoded
clip by up to 2.507e-8 m, measured separately from encoded replay agreement.

The first probe is preserved as a validation-script failure: it incorrectly
required unrounded active proposals to match Float32 exports within 3e-12.
The fresh probe keeps that strict tolerance for quantized reload, measures
proposal rounding separately, and passes. The failed guard replays 24
observations (22.329 s / 121,610,240 bytes); the successful guard replays 36
(34.422 s / 146,448,384 bytes). No physical cap, workspace cap or collision
tolerance changes. These are math/encoding probes, not a fit or a fresh
collision check; the synthetic other-hand seed is not selected for the scene.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/39006110672)
at source `be13bc0` passes the 22 new selected-column cases on Ubuntu and
Windows. This is the focused suite; the complete repository inventory is not
claimed as a passing run.

## Continuing an edited clip without resetting its source

`scripts/native_seeded_region_fit.py` now exposes `SeededRegionProblem` and
`fit`. This is a reusable multi-time proposal/export path, with no action-name
whitelist. The caller supplies the original actor, complete original native
clock, declared joint order and degree caps, a complete original-relative seed,
explicit editable key/joint pairs, frozen native keys, original world bands,
and timed surface halfspaces. It can start from an already edited clip without
turning that clip into a new zero or losing its fixed finger/other-hand edits.

Frozen keys must include both true clip endpoints; edits cannot name a frozen
key. Frozen values and every unselected key/joint retain the supplied seed
exactly. That is preservation of the supplied seed, not an assertion that its
endpoints equal the raw source. All measurements still use the unchanged raw
source epoch. Callers explicitly freeze authored contact keys as needed.

Every observation retains complete pose rotation balls, all joint/world bands,
every supplied region vertex and every selected native-key ball, including
keys outside that observation's interpolation bracket. A global limit of
128 observations, 100,000 rows and 64 MiB of dense Jacobian storage rejects
the complete request if exceeded. It never returns a reduced observation set.
The existing per-pose workspace guards still apply. Run in a supervised worker.

The SLSQP objective minimizes normalized displacement from the seed. Solver
success is reported separately from actual condition acceptance. Final raw
rows and Float32 endpoint rows are independently evaluated against `>= 0`,
with no acceptance tolerance. Quantization has no claimed analytic derivative.
Each distinct evaluated proposal and its failed-row count remain in the fit
report. Infeasible frozen observations are retained and reported as failures.

`controls` reconstructs the complete original-relative key array and rejects
native rotations outside their original balls. `export` appends a separate
unselected animation, retains original binary/animations, and refuses to
overwrite an existing file. Export does not mean the observation rows passed.
File hashes, scene/permission provenance and immutable output retention remain
the job caller's responsibility; the source-bound interpolation helper rejects
changed in-memory source curves, pose caps and placements.

The local affected selection passes 84 tests in 23.05 s: 16 new seeded-fit
cases, 46 key-map cases and 22 selected-column cases. Tests exercise multi-time
derivatives, out-of-bracket pose rows, nonzero fixed seeds, frozen keys,
correction of a surface target, infeasible fixed observations, solver limits,
global budgets and actual Float32 native save/reload. The guard completes in
55.859 s at 125,042,688 sampled bytes, with all 57 observations and archived
bindings replayed. Inventories now declare 558 Python/45 Node suites and
124/five in the contact subset; these counts are not a complete-inventory pass.

This API is not yet wired into the Studio correction form. Its explicit
observations are proposal constraints, not a complete contact, collision,
dynamics, engine, anatomical or human acceptance procedure. The existing
source-zero scene fit remains a distinct workflow until integration is tested.

### Encoded native limits and the first real-scene attempt

The initial 84-case selection is followed by a stronger encoded native-angle
check. Final Float32 rows now measure the actual encoded angle of every
selected key relative to its original quaternion, including keys outside the
observation bracket. Checking the unrounded unit vector alone can hide a small
encoded angle overshoot. The added regression exports seven boundary directions
and compares every native-ball row with an independent saved-file reader;
at least one direction exposes that overshoot without changing a physical cap.

The new affected selection passes 85 cases in 23.27 s (17 seeded-fit cases
plus the previous 68 map/selected-column cases). The guard completes in
54.000 s at 122,269,696 sampled bytes, with all 55 observations and archived
bindings replayed. This is the source version used by subsequent proposals.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/39006835337)
at source `0ee6f65` passes all 17 seeded-fit cases on Ubuntu and Windows.
The full repository inventory remains outside this focused result.

The first actual approach proposal, `high-five-seeded-approach-region-fit-v1`,
tries to separate A's complete forearm/hand incident region and B's complete
right-hand region using one source-derived plane per time, before invoking
the seeded solver. The first plane preflight fails and no motion fit/export
runs. Its guard is retained and replayed: 22.281 s / 144,236,544 sampled bytes /
24 observations. It is a failed proposed constraint setup, not a memory stop
or evidence that the native fitter succeeded.

Fresh `high-five-seeded-approach-plane-diagnosis-v1` records the complete
preflight at all six declared times. Every bounded floating LP reports success
with zero margin, so this search finds no positive-gap plane. All matrices,
solutions and conventions are retained. This is not an exact proof of convex
nonseparability, and it does not contradict the earlier 85 individual triangle
separation proofs. Whole curved regions can impose a stronger condition than
local surface separation. The diagnosis guard completes in 30.484 s /
150,867,968 sampled bytes / 32 replayed observations.

The next explicit condition uses all recorded crossing triangle pairs at
the six selected times, rather than a single convex-region plane. It retains
every pair within that declared selection, with bounded groups of at most
32 region constraints. It permits body keys 34–37 while freezing the authored
contact key and true clip endpoints and holding all other keys/fingers fixed.
This is a new proposal condition, not a relaxed geometry acceptance rule.
Until it completes, it is not counted as a successful repair, and even a
selected-time pass would require complete affected-interval validation.

### The captured pairs clear, but new collisions appear

`high-five-seeded-approach-region-fit-v2` completes that proposal. It uses all
1,748 previously recorded triangle pairs across six times, grouped into 58
observations per actor. A has 36 editable native-key coordinates and 11,682
complete constraint rows; B has 48 coordinates and 11,972 rows. Existing caps,
source epoch, frozen 0/60/119 keys, all fingers and all other keys are retained.
Both SLSQP calls report success in six iterations, but this is not acceptance:
A has zero raw/three quantized failed rows, and B has four raw/six quantized.

All failures are surface halfspace rows. B's four raw negatives are about
-1.565e-14 normalized. Quantized minima are -4.422e-7 for A and -6.804e-7
for B: roughly 4.422/6.804 nm short of the declared 10-micrometre plane gap.
They remain recorded failures under the unchanged zero comparison. Rotation,
world-joint and selected-native ball rows have no negative entries in this
study. The new encoded native-angle regression remains separately necessary;
it is not the source of these particular failures.

More seriously, every fresh full-mesh partner/floor sample fails. Surface
record counts at indices 586, 590, 595, 600, 605 and 610 are respectively
212, 246, 448, 248, 252 and 226. The proposal guard completes in 424.578 s
at 316,424,192 sampled bytes, with all 420 observations/bindings replayed.
No complete affected-interval, self, dynamics, engine or human pass follows.

`high-five-seeded-approach-pair-replay-v1` then accounts for all six saved
reports and every negative row. None of the original 1,748 pairs remain in
the new surface records, but 1,632 different pairs are now reported as proper
crossings. These are per-time pair counts, not distinct mesh pairs across the
entire clip. The comparison replays retained floating predicate reports; it
does not run independent exact crossing proofs. Its guard completes in
24.343 s / 55,681,024 sampled bytes / 26 replayed observations.

The immutable proposal summary's `region_vertices` fields retain the earlier
whole-region preflight sizes (3,300/2,960). They are not the vertex populations
used by this triangle-pair fit. The actual population is in `condition.json`:
1,748 three-vertex region records, or 5,244 vertex rows per actor, with repeated
vertices retained. The summary's `complete_controls` means the 36/48 selected
optimizer coordinates, not the complete nonzero native seed. Those metadata
labels must not be used to claim all native controls were optimization variables.

This result demonstrates why satisfying a captured witness set cannot approve
a full scene: a local repair can create different intersections. Next add
feedback from fresh complete geometry while retaining earlier constraints,
with explicit inner search margins for saved-file rounding. Reuse evaluations
at identical times to keep larger feedback sets practical on this laptop.
Preserve original acceptance limits and require complete affected-interval,
whole-clip/self, dynamics, engine and human checks before selecting any clip.

## Reusing poses while retaining complete feedback constraints

The seeded problem now groups observations by exact time. Each evaluation
computes one fresh interpolation map and native affine frame per distinct
time, then assembles every observation's rows into their original positions.
Nonconsecutive observations retain their ordering. Only the current group's
frame is held; there is no persistent pose cache across proposals. Repeated
rotation, joint and native-key rows are retained rather than deduplicated.
Every observation still checks its original reference, active dependencies,
fixed seed and model identity. `RegionPoseRows.evaluate` retains its public
signature and arithmetic; internal frame assembly is reused by the seeded path.

`fit` also accepts a complete nonnegative `search_reserve` vector, bounded to
0.1 normalized units per row and copied before solving. The search requires
`row - reserve >= 0`; final raw and encoded acceptance still require the
original `row >= 0`. The default is zero. The full vector and search failures
are reported separately, so an inner optimization margin cannot silently
become a changed physical acceptance tolerance. Reserves use the existing
row scales: a 0.0001 reserve on a 1-cm-normalized surface row is 1 micrometre.

An optional evaluation observer receives copies of the proposal and complete
row array after each fresh evaluation. Jobs can save these immediately, keeping
completed probes if an optimization later stops. Mutating these event copies
cannot change the solver's cached data. Callback failures propagate as job
failures; callbacks do not approve assets or alter the original source epoch.

The affected selection passes 140 cases in 33.88 s: 30 seeded-fit, 46 key-map,
22 selected-column and 42 region cases. New coverage includes interleaved
repeated times, exact row ordering, one frame evaluation per distinct time,
later-observation source/seed checks, strict encoded acceptance with an inner
surface margin, callback copy isolation and invalid reserves/observers.
The 512-MiB guard completes in 62.875 s at 125,157,376 sampled bytes, with
all 64 observations/bindings replayed. Inventory counts remain 558 Python/45
Node suites and 124/five in the contact subset; no full-inventory pass is claimed.

### Actual replay and measured cost

`native-seeded-region-reuse-actual-v1` reconstructs the preceding actual A/B
problems with 58 observations but only six distinct times each. Every raw and
encoded row matches the saved preceding candidate arrays bit-for-bit. Every
Jacobian entry matches the frozen preceding seeded facade running on the
current affine/map delegates. This is not a claim of separately replaying every
historical dependency revision. The unchanged A/B failures (raw 0/4, encoded
3/6) remain; arithmetic equivalence does not clear an animation.

| Operation | A previous / reused (s) | B previous / reused (s) |
| --- | --- | --- |
| Construction | 3.109 / 1.079 | 3.094 / 1.062 |
| Rows and derivatives | 10.093 / 1.485 | 11.031 / 1.407 |
| Encoded rows | 8.390 / 1.391 | 7.218 / 1.078 |

These are single-machine measurements, not latency guarantees. No new fit,
export or geometry query runs in the replay. Its guard completes in 77.250 s
at 174,243,840 sampled bytes, with all 78 observations/bindings replayed.

### A raw-source overlap limits source-separating-plane guidance

`high-five-seeded-approach-region-fit-v3` attempts to retain all 3,380 old and
new pair witnesses. Its first time supplies 297 planes, but the next time
finds no positive source projection gap for A face 26562 / B face 27471 at
1.1625 s; the best tested unit-axis gap is -1.331691 mm. The job stops before
fitting or export, preserving its setup failure. Its failed guard replays
24.375 s / 146,821,120 sampled bytes / 26 observations.

`high-five-feedback-raw-pair-proof-v1` independently reconstructs this one
pair across three epochs. Exact rational witnesses prove represented-triangle
crossings in the original clip and proposal-v2; the assembly-v4 pair has no
strict straddle. This does not certify complete raw-scene absence or contradict
the previous 85 separated original pairs at the earlier time. A new witness
may require moving out of a raw-source collision rather than returning to raw
motion. The proof guard completes in 26.328 s / 124,035,072 sampled bytes /
28 replayed observations, without fitting or changing an asset.

The next explicit proposal retains all 3,380 pairs but permits least-overlap
source axes as guidance when source triangles already overlap. Such an axis
is an optimization proposal, not a separation proof. It keeps the original
movement limits and source epoch, freezes 0/60/119 and all other keys/fingers,
and uses the previous complete original-relative proposal as its seed. Search
adds a 1-micrometre inner surface margin; original 10-micrometre declared gaps
and all strict acceptance comparisons remain. Success is unproven until fresh
saved-candidate checks complete, followed by complete affected-interval and
whole-scene/dynamics/engine/human validation.

### Accumulated body-only feedback: rounding passes, scene still fails

`high-five-seeded-approach-region-fit-v4` completes the revised 3,380-pair
condition. Twelve source-pair axis searches are initially nonseparating or
near-contact by the declared floating gap criterion; only the specifically
diagnosed pair above receives the independent exact witness claim. Each actor
has 109 observations over six times, with 10,140 triangle-vertex rows. Complete
totals are 22,239 rows / 36 optimizer coordinates for A and 22,784 / 48 for B.
Every earlier pair is retained; the complete original-relative proposal-v2
seed and original raw source epoch remain distinct.

A converges in nine iterations and B in eight. Both have zero failed physical
raw rows and zero failed encoded rows under the original strict comparison.
Encoded minima are 9.937343e-5 and 9.962540e-5 normalized. Search-reserve rows
still have four/five tiny negative residuals against the extra inner margin;
those counts remain separate and are not relabeled as a search-condition pass.
Every evaluated proposal/row array is saved by the observer before completion.

Full-mesh checks nevertheless fail at all six selected times. Surface record
counts at indices 586, 590, 595, 600, 605 and 610 are 439, 543, 383, 294, 237
and 200. The complete proposal guard replays 303.407 s / 304,222,208 sampled
bytes / 301 observations. No mesh approval follows from passing pose rows.

`high-five-seeded-approach-pair-replay-v2` independently accounts for the saved
reports and row layouts. All 3,380 accumulated target pairs are absent, but
2,096 different per-time pairs are now reported as proper crossings. Final raw
and encoded negative-row lists are empty. As before, this is report accounting,
not independent exact predicates or a duration/unique-whole-clip count. The
replay guard completes in 23.297 s / 59,228,160 bytes / 25 observations.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/39007883418)
at source `eb16486` also passes all 30 seeded-fit cases on Ubuntu and Windows.
The tested source is pushed; the candidate remains unselected and unapproved.

The next falsifiable comparison is an explicit permission change: allow the
five proximal finger joints as well as the arm controls at keys 34–37, while
retaining all previous/new geometry feedback, original degree/world limits,
other tracks, true endpoints and the authored contact pose. The failure does
not prove that extra finger controls will solve it. It motivates measuring
that condition before assuming that body-only correction or a body-model
fine-tune can supply detailed contact articulation.

The accumulated next pair union has 5,476 per-time pairs, requiring 174 current
32-region observation groups. That exceeds the present 128-observation
admission bound even though the projected total row/Jacobian sizes remain
within their global limits for the proposed proximal-finger permission set.
Do not prune witnesses to fit. A separately qualified explicit admission option
or another complete representation is required before running that comparison.
