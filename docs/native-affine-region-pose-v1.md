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

## Explicit observation admission and the proximal-finger comparison

The seeded API now accepts `maximum_observations` explicitly: the default stays
128, while callers may request 1–512. The chosen bound is reported. Invalid
bounds reject before pose construction, and the 100,000-row / 64-MiB Jacobian
limits remain hard even with larger observation admission. No regions, vertices
or earlier witnesses are discarded to meet those limits. Resource guards remain
necessary; admitting 512 groups is not a process-memory or runtime guarantee.

The affected selection passes 148 cases in 42.59 s, including eight new cases
covering default rejection, explicit 129/512-group retention, single-time reuse,
invalid bounds and unchanged global budgets. The guard completes in 74.328 s /
123,101,184 sampled bytes / 75 replayed observations.

`high-five-seeded-approach-region-fit-v5` retains all 5,476 accumulated pairs
as 174 observations per actor over the same six times. It permits the arm and
five proximal finger joints at keys 34–37; all other tracks/keys and frozen
0/60/119 poses retain proposal-v4's complete original-relative seed. Original
degree/world caps remain. A has 96 optimizer coordinates, 39,222 rows and a
30,122,496-byte Jacobian; B has 108 coordinates, 40,092 rows and 34,639,488 bytes.
Search adds 1 micrometre to surface rows and 1e-5 normalized reserve to other
rows; original strict physical acceptance is unchanged.

A's SLSQP call stops with status 8 after five iterations and only its initial
distinct evaluation. It retains 3,463 raw and encoded failed rows; minimum
raw row is -1.510531. This candidate is already rejected independently of the
unfinished B search. B's subsequent completed probes remain archived, but its
fit and any paired export/geometry result are not counted as completed.

The owned worker tree is intentionally stopped to diagnose the guidance before
further optimization or geometry scans. The supervisor remains running and
records a failed terminal guard: 383.860 s / 423,272,448 sampled bytes / 380
replayed observations, with the stop reason/verified process identities saved.
This is not a RAM stop, completed motion comparison or proof that finger
articulation cannot solve the actual interaction. All 40 retained probe archives
subsequently pass ZIP CRC checks; no paired candidate is selected.

## Exact diagnosis of conflicting generated planes

`high-five-feedback-halfspace-proof-v1` groups the generated inequalities by
actor, time and vertex. After 248 of 4,413 groups, it finds a four-row exact
contradiction for A vertex 11118 at 1.1625 s. All four are original declared
10-micrometre gap constraints; the extra search reserve is not used. With
nonnegative rational weights summing to one, their combined normal is exactly
zero and their combined bound is approximately -0.130870 mm. Thus the represented
linear proxy requirements imply `0 <= -0.130870 mm`, even for a freely positioned
vertex. These proxy planes cannot all be met by adding more rig freedom.

The certificate concerns the generated fixed-plane setup, not true mesh
separation, another guidance choice or feasibility of a different motion.
The diagnosis guard completes in 28.453 s / 119,177,216 sampled bytes / 30
replayed observations. This changes the next action: address the guidance
representation before interpreting optimizer failure as a model/rig limitation.

`scripts/native_halfspace_certificate.py` is a portable read-only verifier.
It binds a certificate to the complete region request hash, requires a common
declared vertex and up to four distinct region indices, reconstructs exact
rational coefficients from represented normals/offsets/gaps, and checks the
weighted contradiction independently. Input bounds and canonical rational
weights are validated. It does not run a model, optimizer or geometry query,
and a verified proxy contradiction never approves or rejects a different motion.

```powershell
python scripts/native_halfspace_certificate.py regions.json certificate.json
```

Its final 27 cases pass in 1.32 s, covering opposing and tetrahedral constraints,
request/support tampering, feasible/touching cases, invalid/nonfinite/large
numeric inputs and the actual JSON CLI. The guard completes in 31.469 s /
81,162,240 bytes / 33 replayed observations. A preceding combined 173-case
selection also passes; its guard replays 75.297 s / 126,619,648 bytes / 76
observations. The final numeric-bound validation is independently rechecked
in the 27-case suite; do not treat those as two separate sets of 173 new cases.
Inventories now contain 559 Python/45 Node suites and 125/five in the contact
subset; counts are not full-inventory pass results.

`high-five-feedback-halfspace-proof-replay-v1` binds all 920 region records
for the actual actor/time and supplies the four weights to the public checker.
Both the checker and its separate CLI reconstruct the same exact negative
fraction. The replay completes in 23.281 s / 47,869,952 bytes / 25 replayed
observations. The portable request/certificate/verification JSON remains under
that ignored report folder; it needs no character/model payload to audit.

The next proposal should keep the collision-pair population while allowing
the two actors to share separation movement. For a chosen pair normal, the
relative condition `min(n·B) - max(n·A) >= 2*gap` retains every triangle vertex
and is equivalent to allowing a separating plane offset to move, instead of
fixing each actor's vertices to an arbitrary original midpoint. This formulation
still needs implementation, numerical validation and fresh complete geometry,
interval, self, dynamics, engine and human checks. No candidate is approved.

The [focused observation-budget run](https://github.com/DocMorphic/strep/actions/runs/39009765717)
and [certificate run](https://github.com/DocMorphic/strep/actions/runs/39009763561)
at source `0c0c5d1` pass their 38 and 27 respective cases on both Ubuntu and
Windows. Both tested modules are pushed. These focused results do not establish
a full repository pass or validate an animation.

## Coupled relative-gap prototype

`high-five-coupled-relative-gap-fit-v1` implements a new experimental condition
using all 5,476 pair references and all three vertices on each side. It replaces
the contradictory fixed global offsets; those heuristic unary requirements are
not retained as if they were user-authored physical requirements. Original raw
source bounds, 84 body-only native-key coordinates, frozen poses and the complete
original-relative proposal-v4 seeds remain. The original collision acceptance
policy is unchanged. No extra finger motion is included in this comparison.

For each chosen unit pair normal, search uses a conservative smooth support
gap: soft minimum of B's three projections minus soft maximum of A's three
projections. Log-sum-exp temperature is 10 micrometres. This lower-bounds the
exact `min(B) - max(A)` gap rather than sampling a triangle vertex subset.
The required relative gap is 20 micrometres, equivalent to a freely chosen
plane offset with 10 micrometres on each side. Raw and Float32 postchecks use
the exact min/max projections; smooth search feasibility is kept separate.

All original pose rotation and joint/world rows occur at each of six times,
and every selected native-key ball occurs once, including keys outside the
queried interpolation bracket. There are 6,698 rows and 84 controls, requiring
4,501,056 Jacobian bytes. Repeated legacy proxy blocks are replaced explicitly
by this new condition, not omitted from an unchanged claimed test. Source/input
bindings and complete seeds are written before fitting, and every fresh proposal
and full row vector is retained during the solve.

Two initial directional checks pass with maximum normalized errors 7.552e-7
and 7.744e-7. This validates those directions at the initial point, not all
motion or solver behavior. The solve subsequently reaches its 32-iteration
limit (status 9), retaining 532 raw and encoded failed rows. No candidate is
exported, so no new full-mesh samples are counted as checked. The complete guard
replays 514.969 s / 214,904,832 sampled bytes / 509 observations. The failed
solve does not prove the relative-gap condition or actual motion infeasible.

The next explicit comparison, `high-five-coupled-relative-gap-fit-v2`, keeps
the same pairs, controls, limits, seeds, smooth support method and strict
postchecks. It replaces independent triangle directions with the existing
source-derived `meeting_plane.axis_world`, oriented from A's root toward B's
root at the frozen 2-s pose. Thus it tests a shared palm-contact direction
without restoring fixed offsets or pruning collision pairs. Until completed,
it is not counted as a repair or a physical/geometry pass. Whole-interval,
whole-scene/self, dynamics, engine and human validation remain required.

That comparison completes with solver success after six iterations and zero
raw or Float32 failed declared rows. Both initial directional checks pass
(maximum normalized errors 2.500e-7 and 3.218e-7). All six independent full-mesh
checks still fail, reporting 226/264/397/342/282/254 surface records. Comparing
the saved per-time triangle identifiers shows none of the original 5,476 pair
references remains among these records; all 1,765 records are additional pairs.
This is collision migration, not a successful animation repair. No claim is
made that the original clip was otherwise collision-free. The guard independently
replays 214.422 s / 316,698,624 sampled bytes / 213 observations.

`high-five-coupled-relative-gap-fit-v3` explicitly accumulates those 1,765 new
pair references with the previous 5,476, discarding none. It starts from the
complete proposal-v2 original-relative seed, retains the original source epoch,
control caps, frozen poses and shared contact direction, and repeats raw/encoded
and independent full-mesh checks at the same six times. This tests 7,241 pairs;
it does not extend checked temporal coverage. Until the complete result is
recorded, its planned checks are not counted as passed.

Proposal-v3 completes with zero raw/encoded declared failures, but full geometry
again fails at every selected time (102/178/330/510/250/276 surface records).
Its complete guard replays 175.672 s / 320,303,104 sampled bytes / 175 observations.
The iteration therefore remains rejected; clearing a retained witness population
is insufficient evidence for selecting the resulting animation.

The saved identifier comparison finds no retained pair among proposal-v3's
1,646 surface records. A further cumulative trial must therefore carry all
8,887 references (5,476 + 1,765 + 1,646), rather than replace its collision
population with only the latest failures. It still covers just six times.

## Shared support-gap calculation

`scripts/native_support_gap.py` exposes `triangle_support_gaps(left, right,
normals, temperature_m=...)` independently of the rig and optimizer. Each batch
contains complete three-vertex triangles and one explicit unit direction per
pair, oriented from left to right. It returns the floating extrema projection
gap, the smooth lower support bound in metres, and both complete vertex-gradient
arrays. The helper uses a common local origin and shifted exponentials to avoid
exponentiating large world coordinates. It supports up to 16,384 pairs without
pruning and rejects invalid shapes, nonnumeric/nonfinite inputs, nonunit normals
and unbounded coordinates or temperature. Larger workloads must be divided
explicitly without discarding pairs; optimizer row/workspace budgets remain the
caller's responsibility.

The smooth bound differs from the extrema gap by at most
`2 * temperature_m * log(3)` in real arithmetic. This is a search formulation,
not an exact mesh predicate or a proof from floating-point residuals. A negative
projection gap can occur for nonintersecting triangles; direction choice is a
heuristic. Acceptance must independently check encoded motion, complete geometry,
temporal coverage, self contact, task semantics and human quality. Neither this
helper nor its derivative tests approves an animation.

All 27 focused fixtures pass in 1.49 s, including every-coordinate central
differences near support ties, the entropy error bound, rigid transforms,
side reversal, duplicate vertices, every-vertex extrema and malformed inputs.
The test guard independently replays 40.657 s / 81,481,728 bytes / 42 observations.
`native-support-gap-actual-replay-v1` separately reconstructs the saved encoded
v2/v3 character meshes and compares all 5,476/7,241 retained triangle references
with the private prototype. Maximum smooth-gap difference is 6.246e-17 m and
maximum vertex-gradient difference is 5.935e-13. Both retain their declared
20-micrometre projected gaps; their independent mesh failures remain failures.
These are numerical equivalence comparisons, not new collision tolerances.
The replay guard completes in 27.437 s / 155,512,832 bytes / 29 observations.

`high-five-coupled-relative-gap-fit-v4` is prepared to use this public helper
with all 8,887 accumulated pairs and the complete original-relative v3 seed.
It retains the original 84 controls, caps, frozen poses, source epoch and mesh
acceptance policy. Its planned checks are not counted as passed before the
complete numerical and independent geometry results are recorded.

The [focused support-gap run](https://github.com/DocMorphic/strep/actions/runs/39011456159)
at source `1ea7936` passes on both Ubuntu and Windows. It checks the 27-case
standalone helper suite; it does not validate the coupled optimizer or approve
its output. The model-free inventories now contain 560 Python/45 Node suites
and 126/five in the contact subset; these are inventory counts.

Proposal-v4 completes successfully after seven optimizer iterations with zero
raw/encoded declared failures. Its two initial directional errors are 3.366e-7
and 3.480e-7 normalized. The independent full geometry at index 586
(1.1541666667 s) passes; the other five samples still fail with
155/95/493/348/266 proper-crossing records. All 8,887 retained pair references
are absent from those 1,357 new records. This is a limited sampled improvement,
not a clean approach interval or a selected animation. The independently replayed
guard completes in 160.219 s / 362,749,952 sampled bytes / 159 observations.

`high-five-coupled-relative-gap-fit-v5` retains all 10,244 accumulated pairs,
uses the complete original-relative v4 seed and the same public support helper,
source epoch, 84 controls, caps and frozen poses. It repeats all six mesh checks,
including the previously passing time: changing shared native keys may introduce
other pairs there. A prior sampled pass cannot substitute for checking the new
candidate. No planned checks count as completed before the result is recorded.

Proposal-v5 completes with solver success after seven iterations and zero raw
or encoded declared failures. Full geometry passes at indices 586 and 590;
the four remaining samples report 62/367/290/265 proper crossings. The 10,244
retained pair references are absent from the 984 new records. The independently
replayed guard completes in 117.890 s / 361,000,960 sampled bytes / 118 observations.
The original remains selected. A further cumulative trial requires 11,228 pairs
and all six fresh mesh checks; two sampled passes do not establish an interval.

## Pose bounds independent of separation guidance

`scripts/native_affine_pose_bounds.py` provides `PoseBoundsRows` for a native
source pose, complete original-relative controls, explicit editable native
joints and every skin-joint displacement band. It evaluates all rotation-ball
and joint-band rows and their selected-coordinate derivatives, retaining fixed
controls and the constructor-bound original source, native affine transforms,
placement and complete skin surface. It takes no synthetic region or separating
plane. It is a pose constraint evaluator, not a collision or motion validator.

`RegionPoseRows` now extends that common evaluator and appends every explicitly
supplied region vertex. Its public constructor, nonempty region requirement,
row order, original bounds and complete row/Jacobian budgets remain. This avoids
constructing obsolete heuristic plane rows merely to extract the motion limits
for a coupled correction. New standalone bounds tests exercise reordered active
controls, homogeneous skin coordinates, finite differences, tight budgets,
input copies, immutable source bindings and observable violated rotation balls.

The focused 196-case local selection passes in 44.05 s: 21 new pose-bound cases
plus region, seeded-native-curve, key-map, selected-column and support-gap
regressions. Its guard independently replays 75.312 s / 125,427,712 bytes /
76 observations. The existing region module's LF endings are preserved; the
qualified archive differs only by CRLF-to-LF encoding, with identical AST.
Saved real-character row/derivative equivalence is checked separately before
using this evaluator in another coupled proposal. No human or release approval
is inferred from those checks.

`native-pose-bounds-actual-replay-v1` compares the refactor with the frozen
pre-extraction region/seeded implementations, using current unchanged affine
and key-map delegates. On original actor sources and the complete saved v5
seeds, all 35,742 rows / 36 controls for A and 36,612 rows / 48 controls for B,
their full Jacobians, and encoded rows are bitwise identical. The 174 legacy
observations per actor remain complete. A separate fresh bounds-only evaluation
at every one of six times per actor matches the old bound prefix, Jacobian,
native world transforms, posed complete surface and controls bit for bit.
The legacy proxy failures (6,452/5,520) remain failures; they are not requirements
of the newer relative-gap proposal. The independently replayed guard completes
in 56.843 s / 188,502,016 bytes / 58 observations.

`high-five-coupled-relative-gap-fit-v6` carries all 11,228 accumulated collision
references, the complete original-relative v5 seed, 84 controls, and unchanged
source, caps and frozen poses. Each actor/time context now constructs
`KeyPoseMap` and `PoseBoundsRows` directly. It needs no obsolete fixed-plane
region rows to obtain movement limits. The study-local seed/export holder
reuses the existing complete-control reconstruction and separate-clip export;
it is not a newly qualified public coupled fitter. It still needs independent
raw/encoded, six-time full mesh, interval, self, engine and human checks. No
planned check is counted as passed.

The [21-case pose-bounds suite](https://github.com/DocMorphic/strep/actions/runs/39012068529)
and [42-case region suite](https://github.com/DocMorphic/strep/actions/runs/39012070638)
both pass on Ubuntu and Windows at source `4bc8736`. The inventories contain
561 Python/45 Node suites and 127/five in the contact subset; these are counts,
not a complete repository run.

Proposal-v6 completes with solver success after nine iterations, zero raw and
encoded declared failures, and initial directional errors 3.296e-7/3.648e-7.
Its 12,450 rows / 84 controls retain all 11,228 pair references. Full geometry
passes at indices 586/590/595 and fails at 600/605/610 with 124/299/229 proper
crossings. All tracked pairs are absent from those 652 new records. The guard
independently replays 87.203 s / 343,773,184 bytes / 88 observations. This remains
a rejected motion proposal with three sampled passes, not a validated interval.

`high-five-coupled-relative-gap-fit-v7` retains all 11,880 cumulative pair
references and uses the complete original-relative v6 seed, the same direct
pose-bounds setup, controls, caps and frozen poses. Every one of the six sampled
times is checked again after fitting. The original remains selected, and whole
affected-interval, whole-clip, self, task correctness, engine and human checks
remain required regardless of these six outcomes.

Further cumulative feedback trials retain all preceding pair references and
use the same original source, caps, clock, frozen poses and 84 controls:

| Trial | Retained pairs | Iterations | Raw/encoded failed rows | Passing mesh samples | New proper crossings |
| --- | ---: | ---: | ---: | ---: | ---: |
| v7 | 11,880 | 10 | 0 / 0 | 4 / 6 | 353 |
| v8 | 12,233 | 12 | 0 / 0 | 5 / 6 | 126 |
| v9 | 12,359 | 12 | 0 / 0 | 5 / 6 | 46 |

All three optimizers report success; none approves the motion. No retained
pair occurs in the new surface records. Proposal-v7 passes indices 586–600
in this six-time selection, then reports 142/211 crossings at 605/610. Both
v8 and v9 pass the first five selected times and fail at 610. Their independently
replayed guards are respectively 87.485 s / 345,432,064 bytes / 88 observations,
80.187 s / 328,712,192 bytes / 81, and 78.250 s / 325,079,040 bytes / 79.
This is evidence of decreasing collision migration at the sampled times, not
general convergence, anatomical correctness or interval clearance.

Proposal-v10 retains all 12,405 cumulative pairs and the complete v9 seed;
its planned checks are not counted as completed. Before broader acceptance,
an explicit affected-interval audit must include all original policy clock
samples within the interpolation support of edited keys 34–37 (bounded by
native keys 33 and 38), all original pose/joint limits, actual encoded joint
positions and complete native-key rotation checks. A prepared slice harness
keeps per-frame geometry/observation/bound receipts and requires all six anchor
mesh checks to pass before starting. The harness has not yet established any
interval result. The entire 2,017-time clock, self/dynamics, engine and human
validation remain separate requirements.

Proposal-v10 completes with solver success after 12 iterations and zero raw or
encoded declared failures. All six independent anchor geometry checks now pass,
with zero surface records. All 12,405 accumulated pair references remain in its
13,627 rows / 84-control problem. Its independently replayed guard completes in
74.094 s / 330,276,864 bytes / 75 observations. This establishes the six sampled
conditions for this candidate only; the original is still selected and no
animation-quality or release decision changes.

The first affected-interval slice, `high-five-coupled-approach-interval-v1`
case `anchor-v10-first32`, now starts on that exact candidate. It requests the
first 32 full-policy clock samples inside native keys 33–38, retains every
geometry observation and pose-bound result, verifies the saved complete native
quaternion tracks against the original-relative seed, and checks all native-key
rotation balls. At each selected time it also compares modeled encoded affine
transforms with the actual saved clip and checks actual joint displacement
bands independently. The matrix equivalence threshold is diagnostic, not a
relaxed acceptance tolerance. Until its committed receipts and terminal guard
are audited, no interval sample is counted as passed.

## Dense affected-interval measurement

`anchor-v10-first32` completes all requested indices 559–590, with geometry,
raw/encoded pose bounds and independently measured saved-joint bands passing
at each time. All 120 native keys on A's 22 controlled joints and B's 23 joints
also pass their original raw/encoded rotation limits (5,400 unique rows per
representation). The complete interval has 85 original-policy samples,
indices 559–643 within 1.1000000238–1.2666666508 s. The first batch therefore
leaves 53 interval samples and 1,932 other full-clock samples unverified for
this candidate. Its guard independently replays 211.671 s / 183,558,144 bytes /
210 observations. A passing partial batch does not pass the interval.

`partner-query-batch4-actual-v2` compares batch sizes one and four on v10's
passing frame 590 and v9's failing frame 610. Every report field matches except
the explicitly declared `partner_query_batch_size`; their single archived
clock arrays match by logical bytes too. These fixtures contain no archived
per-point signed-distance transcript, so that is not a per-point byte-equality
claim. Observed query times are 1.339/1.215 s and 1.993/1.623 s respectively,
not an end-to-end or general speed guarantee. The guard independently replays
32.422 s / 162,119,680 bytes / 34 observations. The first comparison attempt
is retained as a failed harness check because it incorrectly required the
batch-configuration field itself to remain one; its failed guard also replays.

A separate interval-v2 harness preserves the first batch's source bindings and
uses batch size four for `anchor-v10-rest53`, requesting indices 591–643.
Preliminary committed results expose partner crossings starting at index 611
(1.2020833333 s), immediately after the last passing anchor. Movement limits
pass there. This is new measured failure evidence beyond the six anchor poses;
the interval remains rejected. The job continues measuring its complete requested
population, rather than discarding later failures after finding the first one.

An independent receipt replay is prepared to verify exact 85-sample coverage,
all per-frame file/observation hashes, complete native rows, actual encoded
joint/rotation bands and floor depths. It will preserve failed geometry as failed;
no prepared replay is counted as completed. The next correction prototype will
retain every historical anchor pair and every newly exposed dense-time pair,
while applying the original pose limits at all 85 times. It is not started until
the measurements and receipt replay finish.

The remaining 53-sample batch completes with 20 geometry passes and 33 failures,
at every index 611–643 (1.2020833333–1.2666666508 s). All movement limits pass.
Together the batches cover all 85 selected times: 52 geometry passes, 33 failures,
and 7,913 additional proper-crossing pair references, bringing the prospective
retained anchor-plus-dense population to 20,318. No old anchor constraints are
discarded. The second guard independently replays 510.438 s / 232,058,880 bytes /
503 observations. The six-anchor candidate remains rejected for its interval.

`high-five-coupled-approach-replay-v1` independently verifies exact ordered
85-time coverage without gaps or duplicates, all source/case/frame/observation
bindings and complete native rows. It reconstructs actual saved joint and local
rotation bands and floor depths; the reconstructed rotation rows match exactly
(maximum difference zero), while the physical comparisons remain strictly
nonnegative. Stored raw model rows are retained. Partner geometry queries are
not rerun by this receipt audit. It confirms the 52/33 split and passing motion
bounds throughout. Its guard replays 43.610 s / 165,085,184 bytes / 45 observations.
The other 1,932 full-policy clock points remain outside this interval audit.

## Correct temporal edit support before another solve

`high-five-fixed-endpoint-diagnosis-v1` finds a structural obstacle at index 643:
the exact time is native key 38, while both actors permit edits only at keys
34–37. Both `KeyPoseMap` instances report singleton bracket `[38]` and no
dependent editable pair. Their entire native-to-pose Jacobians are zero, and
raw/encoded arrays remain bitwise identical across distinct bounded probes.
The conclusion comes from the absent bracket dependency, not from observing a
zero derivative at just one nonlinear pose.

That saved endpoint reports 150 proper crossings. An independent exact rational
witness verifies a strict interior crossing for represented triangles A 25612 /
B 26622. It certifies those represented triangle coordinates, not upstream
skinning arithmetic, penetration depth or continuous motion. Under the unchanged
key-34–37-only problem, the endpoint pose cannot change, so that crossing cannot
be corrected by any choice of its 84 variables. This is a limitation of the
current temporal edit permissions; it does not prove the rig, action, model or
another edit representation infeasible. The guard independently replays
26.407 s / 165,167,104 bytes / 28 observations.

The prepared dense-85 proposal is therefore gated off before optimization;
its no-launch decision and source-bound diagnosis remain recorded. Original
rotation/world caps and frozen gameplay poses are not relaxed. The next step
is `high-five-native-clock-scope-v1`: measure the candidate's complete 120-key
native clock, reusing only the six exact already-audited dense geometry receipts
and querying the remaining native times afresh. It also checks actual saved
joint and local rotation limits. This coarse scan will locate the failing edit
region before choosing revised temporal permissions. It is not full coverage
of the 2,017-time policy clock, and its planned results are not counted as passed.

The native-clock scan completes all 120 original keys: 117 geometry passes,
failures only at keys 37/38/39 (238/150/88 crossing records), and passing actual
joint/local-rotation limits everywhere. It performs 114 fresh geometry queries
and reuses six exact dense receipts. Combined geometry coverage is 199 distinct
times of the 2,017-time policy clock, leaving 1,818 unmeasured times. It does not
clear subframes outside the dense interval. The independently replayed guard
completes in 749.094 s / 217,075,712 bytes / 738 observations. The measured next
edit range is keys 34–39, with validation extending to its neighboring keys
33 and 40. This broadens temporal support without changing the original caps
or frozen gameplay poses.

## Solver preflight for fixed sampled pose conditions

The public `native_seeded_region_fit.fit` now checks structural native-clock
support before optimization. If a sampled pose has no editable endpoint in its
interpolation bracket and a physical pose row is negative, SLSQP is not started.
The report retains every original row and the initial evaluation, identifies
the observation, endpoint keys and local/global failing rows, and returns the
unchanged seed with `solver_was_run=false`, `preflight_rejected=true`, zero
iterations and reserved status `-1`. Original raw/encoded conditions remain
failed and the original remains selected. Existing successful proposals retain
their numerical conditions and solver path.

The check excludes native-key ball rows outside the sampled bracket: those
variables can still change at their own times. It also excludes search-reserve
failures and does not infer infeasibility from a zero numerical gradient.
Clock support is recomputed from bound clocks/pairs before evaluation and
rechecked after the initial observer callback; mutated support metadata fails.
This is a single-actor sampled-region preflight, not general coupled or geometric
reachability analysis and not an automatic expansion of edit permissions.

Twelve added cases bring the focused local selection to 208 passes in 45.10 s,
covering 50 seeded-fit cases plus region, pose-bounds, key-map, selected-column
and support-gap regressions. Its guard independently replays 75.110 s /
126,808,064 bytes / 76 observations. The real endpoint replay constructs an
explicit A-side separation requirement against B's fixed triangle at native 38:
all 114 rows, their 36-control Jacobian and encoded rows match the frozen previous
implementation bit for bit. Both failed rows remain failed, the initial complete
observation is retained, the seed/frozen controls remain unchanged and the
optimizer is called zero times. That guard independently replays 27.453 s /
155,877,376 bytes / 29 observations. This does not claim a coupled motion repair.

`high-five-expanded-interval-v1`, case `anchor-v10-extend35`, measures the
remaining 35 policy times through native key 40 on the unchanged v10 candidate.
It extends the baseline interval from 85 to 120 dense samples before fitting
the proposed six-key range. Native-clock count 120 and dense-interval count 120
refer to different time sets. The added sample results remain pending; no
expanded-interval or animation acceptance follows from their preparation.

The [50-case seeded-fit suite](https://github.com/DocMorphic/strep/actions/runs/39015047535)
passes on both Ubuntu and Windows at source `dd03f09`. This verifies the public
preflight and its unchanged evaluator/export regressions; it does not approve
the paired animation or implement a public coupled solver.

The added 35 samples complete with seven geometry passes, 28 failures and passing
motion limits. The guard replays 247.125 s / 201,121,792 bytes / 245 observations.
`high-five-expanded-interval-replay-v1` independently combines all 120 dense
times from indices 559–678: 59 geometry passes, 61 failures at 611–671
(1.2020833333–1.3208333333 s), and passing original motion limits throughout.
Actual reconstructed rotation rows again match exactly. It validates the archived
source snapshots while explicitly allowing only the changed, unused `fit`
function in the broad source inventory: all other AST nodes in that module match,
and the read-only producers do not import it. Other source bindings remain exact.
This does not silently treat old source as current. The replay guard completes
in 51.969 s / 165,498,880 bytes / 53 observations.

`high-five-coupled-expanded-gap-fit-v1` starts a revised proposal from the complete
v10 seed with native keys 34–39 editable on the same body joints, giving 126
controls. Original degree/world bands and frozen keys 0/60/119 remain. It retains
all 12,405 historical anchor pairs plus all 10,645 dense crossing pairs: 23,050
total references, with pose bounds at every one of 120 selected times. Its
46,972 rows require 47,347,776 Jacobian bytes, within the unchanged 100,000-row /
64-MiB budget. Every captured pair time has structural support in the revised
key range, unlike the rejected four-key proposal. No pair, vertex or bound is
discarded. Raw/encoded postchecks and all 120 fresh independent mesh checks
remain required; the running solver is not a measured motion repair yet.

The expanded worker subsequently exceeds its unchanged 1-GiB process-tree limit
while running geometry, and the guard terminates it. Its failed status and
independent resource replay remain intact: 806.390 s / 1,097,506,816 bytes /
793 observations. It had saved a complete numerical proposal, exported tracks
and 44 geometry reports, but no completed study result. Those partial reports
do not establish an interval pass.

`high-five-expanded-solution-replay-v1` recovers the saved numerical work in a
separate process without calling the optimizer. It checks NPZ integrity and
source bindings, verifies the copied calculation function's AST against the
failed worker, and reproduces all 46,972 raw and encoded rows bit for bit, with
zero failures. Complete saved controls, encoded tracks and all native-key
rotation limits also match. Its independent guard replay completes in
106.453 s / 280,477,696 bytes / 107 observations. This recovers a numerical
solution; it does not change the failed study into a successful one or approve
geometry.

`high-five-expanded-geometry-replay-v1` requests fresh geometry at all 120
selected times on that exact recovered candidate. It retains no optimizer
workspace, collects temporary geometry objects after each frame, and reuses
none of the failed worker's 44 partial checks. Saved joint positions, local
rotation limits and floor depths are reconstructed independently of the pose
Jacobian, and complete per-frame reports and observation receipts are retained.
The same 1-GiB limit and physical acceptance thresholds apply. Completion and
coverage verification remain required before reporting the selected sample set
as passing; the full 2,017-time clock, self-collision, dynamics and human review
remain separate requirements.

The geometry-only attempt is deliberately stopped after 75 committed samples
(indices 559–633), once it has established 23 geometry failures and zero motion
bound failures. This is a performance handoff to previously qualified query
batch size four for the unfinished indices, rather than another RAM stop.
The owned worker PID, creation time and descendants are recorded before stopping
only that tree; its supervisor remains to finish the independent resource audit.
The failed attempt retains all receipts and replays 679.735 s / 217,366,528 bytes /
668 observations, exit 15, with no resource-guard reason. The separate
`intentional-stop.json` explains the stop; it must not be described as a completed
120-sample run. Fresh bounded tail slices and an aggregate exact-coverage audit
are required before using the full feedback population. Completed prefixes are
reused only through their immutable receipts, never converted into a successful
guard result.

The two fresh tails complete the remaining 45 samples. The 32-sample guard
replays 227.047 s / 201,314,304 bytes / 224 observations; the 13-sample guard
replays 104.235 s / 175,865,856 bytes / 104 observations. Both remain partial
slices of the selected interval, and neither changes the failed prefix status.

`high-five-expanded-geometry-receipts-v2` independently verifies all three
committed receipt populations, their source bindings and observation transport,
and exact coverage of indices 559–678. It reconstructs all saved actual joint,
rotation and floor checks and the complete native rotation limits. The selected
120 times have 77 geometry passes and 43 failures at indices 611–653, with 6,937
surface records and zero motion-bound failures. The maximum reconstructed pose
row difference is 5.885e-15; comparison tolerance never relaxes physical row
acceptance. The guard replays 53.032 s / 169,676,800 bytes / 54 observations.
The unchanged v10 baseline had 61 failed times in this same sample set. This is
a reduction in sampled defects, not an accepted animation: 1,897 other policy
times, self-collision, dynamics, semantics, engine playback and human review
remain unverified for this candidate, and the original stays selected.

`KeyPoseMap.evaluate` now resamples only the perturbed local quaternion track
for each finite-difference column, starting from a fresh complete sample at the
current evaluation point. It still reconstructs the complete relative-control
vector for each side of the difference and retains every Jacobian row and
column. Multiple editable endpoints on one track are applied together. Full
affine hierarchy and skin derivatives, original references, Float32 export,
native rotation balls and allocation limits remain unchanged; no pose is cached
across evaluations. Local track independence is used before forward kinematics,
not to discard effects through ancestors or skin influences.

Twelve new cases check byte equality against full-control finite differences
at native, interpolated and outside-support times, both endpoint edits on the
same track, pair order, complete columns and fresh evaluation points. An
instrumented case verifies fewer local track samples without dropping tracks
from the complete result. All 220 focused regressions pass in 54.80 s; the guard
replays 97.125 s / 125,349,888 bytes / 97 observations. This qualifies the source
change's regression behavior, not motion quality. A separate supplied-character
comparison against the frozen previous implementation remains required before
using it in another measured correction study.

`native-track-local-map-actual-v1` completes that comparison on both supplied
actors at six native/interpolated/outside-support times, each at the initial
seed and recovered solution: 24 comparisons. Every complete local-control
vector and Jacobian is byte-identical to the frozen previous implementation;
Float32 endpoint controls and complete native-ball values and derivatives also
match. The guard replays 28.531 s / 116,424,704 bytes / 30 observations. Timing
observations are local map measurements, not a whole-optimizer speed guarantee.
This preserves the previously measured motion and its 43 failed geometry times;
it is not a new animation correction or quality approval.

The [58-case interpolation suite](https://github.com/DocMorphic/strep/actions/runs/39018172184)
also passes on Ubuntu and Windows at source `2665422`. The next private trial,
`high-five-coupled-expanded-gap-fit-v2`, starts from the complete recovered seed
and adds all 6,937 newly observed proper-crossing pairs to the previous 23,050.
None of the new crossings is a previously constrained pair. All 29,987 pair
references remain, with original bounds at all 120 selected times, the same
126 controls, source epoch, frozen poses and degree/world limits. Its 53,909 rows
use 54,340,272 Jacobian bytes within the unchanged limits.

This trial saves numerical results and exports before a separate process checks
geometry; it performs no inline mesh queries. It also releases the saved initial
Jacobian before optimization. These changes avoid retaining solver workspace
during geometry without reducing constraints. A running trial or a numerical
pass alone does not establish a repair, and fresh complete selected-clock mesh
checks remain required on any resulting candidate.

The v2 search reaches 21 complete checkpoints (indices 0–20) but stops at its
unchanged 900-second execution guard while refining tiny reserve residuals.
Its failed result independently replays 915.860 s / 617,672,704 bytes / 900
observations, exit 15, reason `execution_time_guard`. This is not a RAM failure,
optimizer completion or measured motion repair.

`high-five-expanded-candidate-recovery-v2` selects the largest committed
checkpoint index with finite complete nonnegative physical search rows: index
20. All checkpoint NPZs through that committed index pass ZIP integrity checks.
The calculation function's AST matches the stopped worker; all 53,909 saved
smooth rows reproduce byte for byte. Independent exact raw and Float32 endpoint
postchecks each have zero failed rows. The new process exports a fresh candidate
without running the optimizer or claiming that its search completed or found
an optimum. The failed search, original assets and every checkpoint remain.
Its guard independently replays 147.844 s / 278,413,312 bytes / 147 observations.

`high-five-expanded-candidate-geometry-v2` now requests fresh slices of
32/32/32/24 samples on that exact recovery output. A serial controller starts
one guarded worker at a time and stops on a deferred or failed worker; it does
not retry or rerun successful slices. Each worker first verifies every native
rotation bound, Float32 track reconstruction, noneditable and frozen controls,
original animations/rig/topology and unchanged noncontrolled channels. It then
reconstructs actual saved joint/local-rotation/floor checks and retains complete
mesh and observation receipts for each declared clock index. Four successful
slices must still pass an independent exact-coverage receipt audit before the
selected 120-time population can be reported as passing. Prepared or partial
results do not approve the candidate, and the original stays selected.

The four fresh slices complete with geometry failure counts 0/11/22/0 and
passing motion bounds throughout. Their guards replay respectively
199.719 s / 183,660,544 bytes / 198 observations,
240.656 s / 198,111,232 bytes / 239 observations,
247.953 s / 212,168,704 bytes / 246 observations, and
158.594 s / 177,684,480 bytes / 158 observations.
`high-five-expanded-candidate-receipts-v2` independently verifies exact coverage
of all 120 indices, source/export/native limits and actual joint/rotation/floor
rows: 87 geometry passes, 33 failures at 612–644 (1.2041666667–1.2666666667 s),
4,031 surface records and zero motion-bound failures. The reconstructed pose
row difference is at most 7.217e-15, separately from physical acceptance. Its
guard replays 54.969 s / 170,291,200 bytes / 56 observations. This improves on
43 failed times but does not pass the selected interval. The other 1,897 policy
times, self/dynamics, semantics, engine and human acceptance remain unverified.

`high-five-region-union-diagnosis-v1` reconstructs all 29,987 previous pair
references and confirms their exact directional gaps still pass on the exported
candidate. Every one of the 4,031 current crossings is a new pair, giving 34,018
retained references. At each of 67 witnessed times, the diagnosis forms complete
vertex unions from every referenced triangle on each actor. No witness vertex
is removed. A common-direction gap between these unions is a stronger condition:
the union's left maximum is at least each triangle's left maximum, and its
right minimum is at most each triangle's right minimum. Therefore a passing
union gap implies each covered pair's directional gap in real arithmetic.

The converse is false. The stronger envelope currently fails at 50 times,
including 17 geometry-clear times, with minimum gap -55.873 mm. It must not be
used to declare the motion, rig or action infeasible. Maximum union populations
are 394/1,293 vertices. The same complete pose/native bounds plus 67 region rows
would allow the already declared arm and five proximal-finger nodes per actor
at the same six keys: 306 scalars, 24,049 rows and 58,871,952 Jacobian bytes,
within the existing 64-MiB limit. This is allocation arithmetic and proxy
diagnosis, not a fitted motion. Its guard replays 40.594 s / 156,782,592 bytes /
42 observations. All 34,018 pair gaps and fresh full geometry remain mandatory
postchecks for any trial using the stronger search condition.

The reusable `native_region_support_gap.region_support_gap` now computes complete
unequal point-set extrema, conservative log-sum-exp gaps and every smooth vertex
gradient. It validates bounded finite populations, unit directions and positive
temperature; no centroid, vertex or skin influence is substituted for the full
declared set. Its real-arithmetic entropy bound is
`temperature * (log(left_count) + log(right_count))`. It shares the stronger
envelope's limitation and grants no mesh or animation approval.

Thirty-four new cases plus the existing 27 triangle-gap cases pass in 2.38 s,
including every-coordinate differences, tied supports, full population limits,
rigid transforms, implication to covered triangles and a counterexample to the
converse. The guard replays 32.516 s / 83,189,760 bytes / 34 observations.
`native-region-support-gap-actual-v1` replays all 67 supplied-character region
values with maximum difference 1.388e-17 m and composes the complete 306-scalar
native map with all 24/27 active pose columns and full affine skin derivatives
at one witnessed time. Two directional comparisons differ by 1.632e-9 m and
7.630e-10 m. Its guard replays 37.703 s / 180,310,016 bytes / 39 observations.
These are numerical comparisons, not motion acceptance tolerances. No new
correction, solver feasibility or human quality is established by this helper.

The [34-case region helper suite](https://github.com/DocMorphic/strep/actions/runs/39020864727)
also passes on Ubuntu and Windows at source `bea82c1`. The private
`high-five-coupled-region-envelope-fit-v1` trial now uses those complete regions
and the already declared arm/proximal-finger nodes, with the same six editable
keys, original limits and frozen poses. All 34,018 original pairs remain exact
raw and encoded postchecks. The stronger envelope is guidance for this trial,
not a new claim that all geometry-clear poses must satisfy one shared plane.

Value-only evaluations use the existing affine API with an empty derivative
coordinate list, preserving the complete hierarchy, pose and eight skin
influences. Before search, all 24,049 rows must reproduce the Jacobian-bearing
path byte for byte and the complete problem must pass two directional checks.
Search can stop at a checkpoint only after independent raw/encoded aggregate
and original-pair postchecks pass; it then records that no optimizer-completion
or optimality claim follows from this stop. Otherwise the actual optimizer
return or guard failure is retained. Solver termination tolerance is separate
from the unchanged strict physical comparisons. Fresh full selected-clock mesh
validation remains mandatory for any exported candidate; a running or prepared
trial cannot pass the motion.

The global-region/finger trial stops at the unchanged 900-second execution
guard without exporting a candidate. All 13 committed checkpoints (0–12) fail
its physical search rows. Its independently replayed failure is 915.937 s /
665,899,008 bytes / 904 observations. The final checkpoint has 83 pose, 29
region and one native-ball violation. This is a failed bounded search, not a
proof that the rig, action or original pair conditions are infeasible. The
global envelope had already been shown to reject 17 geometry-clear times.

`high-five-exact-group-diagnosis-v1` instead expands every retained triangle pair
into its nine scalar vertex comparisons along the common direction. Left
vertices with identical right-side neighborhoods form complete bipartite groups;
the symmetric right partition is also computed, and the smaller partition is
chosen. The group products are disjoint and their union is exactly the original
comparison relation. Consequently group support gaps preserve the original
projected inequalities for a common point-set/time/direction/threshold context.
They introduce none of the global region's cross-pairs.

All 34,018 pairs reduce to 100,533 distinct vertex comparisons and 5,493 groups.
Every edge is covered, none is added, and the minimum group and pair gaps match
within 1.041e-17 m on the decoded character meshes. Failure times are the same
33 as the original pair conditions, rather than the global envelope's 50.
The diagnosis also verifies ZIP integrity and classifies all committed failed
global-trial checkpoints. Its guard replays 31.516 s / 129,761,280 bytes /
33 observations. This changes the representation of existing requirements,
not physical tolerances or the full-mesh validation population.

At 306 scalars the exact grouped Jacobian would require 72,154,800 bytes, so
that allocation is rejected under the existing 64-MiB budget. Keeping all arm
keys 34–39 and the five finger keys 35–39 uses 276 scalars, 29,465 rows and
65,058,720 bytes. The current failed interval uses native keys 36–38; those
finger keys surround it while retaining every original pair and all 120
validation times. This is a declared edit-window choice, not a reduced test
population, relaxed bound or fitted result.

The reusable `native_pair_gap_groups.triangle_gap_groups` validates complete
bounded integer reference triples, binds their count/order with a canonical
digest and returns the exact neighborhood cover. Callers must partition
different actors/point sets, evaluation times, directions or thresholds before
grouping. Twenty-six new cases plus 61 support-gap cases pass in 3.33 s,
including independent edge expansion, gap-equivalence checks, duplicates,
permutations, sparse IDs, full reference budgets and invalid inputs. The guard
replays 34.640 s / 98,586,624 bytes / 36 observations.

`native-pair-gap-groups-actual-v1` independently reproduces all 5,493 group ID
sets, every edge and all 67 supplied-character gap populations. Group minima
and pass flags match the original pairs without added comparisons; maximum
gap difference is again 1.041e-17 m. Its guard replays 34.641 s / 135,864,320
bytes / 36 observations. These transport and numerical checks do not create a
new motion or approve any animation.

The exact pair-group source at `bfb03dc` also passes all 26 focused cases on
Ubuntu and Windows in hosted run `39023085921`; the local run metadata retains
the exact tested source and both successful jobs.

The following arm/finger numerical trial uses that exact grouping, 276 native
scalars and all 29,465 rows. Its value-only calculation matches the complete
Jacobian-path row vector byte for byte. Two initial directional comparisons
have maximum errors 3.677e-7 and 3.735e-7 under the unchanged 2e-5 numerical
criterion; these checks validate derivatives, not motion quality. All 34,018
original raw and Float32-encoded pair gaps remain independent postchecks.
The initial point fails those physical requirements. Checkpoint 7 independently
passes all 29,465 strict physical rows and all 34,018 original pair gaps in
both raw and Float32-encoded curves. The worker exports fresh candidate clips
and stops at that verified feasible point without claiming optimizer
completion or optimality. Its complete guard independently replays 675.453 s /
705,716,224 bytes / 663 observations. No physical acceptance threshold,
source pose, native/world displacement cap or frozen key is relaxed.

Fresh four-slice full-mesh validation runs serially, followed by a
separate receipt/actual-pose audit. These workers require the terminal,
resource-audited numerical parent and every strict motion and original-pair
condition. They retain all 120 selected policy times, unchanged thresholds and
original source poses; no prior candidate's geometry observations can be
reused. Their completed results follow below. Numerical feasibility alone does not
approve new triangle intersections, self contact, dynamics, task semantics,
engine imports, animator ratings or cleanup time. The original stays selected.

The four fresh mesh slices and independent receipt/export/actual-pose audit now
complete the same 120 selected times. There are 104 geometry passes, 16 failures
at indices 616–631 (1.2125–1.241666667 s), 1,326 surface crossing records and
zero motion-bound failures. The preceding candidate had 87 passes, 33 failures
and 4,031 records over that identical population. This measures fewer mesh
failures; visual quality and cleanup time have not been measured. The maximum
independent pose-row difference is 8.882e-15, used only as a numerical comparison;
every physical row is checked separately against its unchanged threshold.

The four complete guards independently replay 200.297 s / 182,902,784 bytes /
199 observations; 202.250 s / 193,802,240 bytes / 201; 198.969 s / 200,417,280
bytes / 198; and 146.109 s / 178,733,056 bytes / 146. The independent receipt
audit replays 52.703 s / 150,949,888 bytes / 54 observations. These fresh reports
and their complete source/clock/transport/receipt populations are retained in
`high-five-exact-group-candidate-geometry-v1` and
`high-five-exact-group-candidate-receipts-v1`.

`high-five-exact-group-transport-diagnosis-v1` samples the actual saved GLBs
and computes scalar triangle projections without the interpolation map,
optimizer or support-gap helper. All 34,018 retained pair gaps independently
pass 20 micrometers. Their maximum difference from the archived encoded gaps
is 8.743e-16 m; that comparison tolerance does not relax physical acceptance.
All 1,326 fresh crossing records are unique, previously unconstrained pairs;
none belongs to the retained input. The complete guard independently replays
35.469 s / 130,084,864 bytes / 37 observations.

Keeping all earlier pairs and all newly observed pairs gives 35,344 references.
The exact neighborhood cover still has 5,493 groups, with different comparison
contents. The 276-scalar / 29,465-row / 65,058,720-byte allocation remains inside
the unchanged 64-MiB Jacobian cap. Allocation arithmetic is not a feasible fit.
The following exact-group trial starts from the last candidate's controls,
with the original source epoch, all 120 times, native/world caps, frozen keys
and body/finger edit permissions unchanged. Its numerical result follows below;
fresh full-mesh results remain pending. The original is still selected; 1,897 other policy
times, self contact, dynamics, semantics, engine imports and human review remain
unverified. No whole-motion or release approval follows from this study.

The 35,344-pair follow-up now exports a numerically feasible checkpoint 9:
all 29,465 physical rows and all retained pair gaps pass in raw and Float32
curves. It stops on the independently postchecked point without an optimizer
completion or optimality claim. Its complete guard independently replays
633.687 s / 705,622,016 bytes / 625 observations. Fresh mesh validation of this
new motion is still required; the previous candidate's 16 failures cannot be
reused as its result.

`native_grouped_pair_gap_rows.GroupedPairGapRows` extracts the grouped row
calculation into an action- and rig-independent numerical component. Each
instance snapshots paired triangle-index triples, complete vertex counts,
unit direction, physical gap, temperature and normalization scale. Callers
must partition distinct actors/objects, times, normals and thresholds and bind
their source files, clocks and edit permissions. The class does not infer
contact intent, choose edit keys, optimize motion or approve an animation.

`evaluate` accepts complete world-space point populations and optional
per-side `vertices × 3 × coordinates` derivative tensors. It returns every
grouped row and separate left/right Jacobians for later native-key composition.
A fixed side can omit derivatives. Exact extrema mode is values-only; smooth
gradients are never mislabeled as derivatives of a nonsmooth exact minimum.
`exact_pairs` separately checks every original reference in its original order,
including duplicates, against the unchanged physical gap. Conservative smooth
guidance is not collision detection or a feasibility proof.

The component retains the existing 16,384-pair context limit, 65,536-vertex
population limits and at most 768 derivative coordinates per side. Input
derivatives are bounded to 128 MiB per side; the complete returned Jacobians
together must fit the caller's limit, capped at 64 MiB. Over-budget requests
raise an error without dropping references, groups, vertices or coordinates.
All supplied positions and derivatives, including unreferenced vertices, must
be finite and have the complete declared shapes.

The isolated prototype passes 139 cases: 52 new integration/finite-difference/
strict-threshold/budget/input-snapshot cases plus 87 existing gap cases. All
5,493 grouped rows and 35,344 pair gaps over 67 real-character times reproduce
the archived failed initial trial point bit for bit in raw smooth, raw exact
and Float32 exact modes. One complete 276-native-scalar chain with 24/27 pose
coordinates passes two directional comparisons (2.067e-7 and 1.624e-7 versus
2e-5). Reproducing a failed input tests truthful transport; it does not repair
or approve that input. The prototype test guard independently replays
44.625 s / 107,200,512 bytes / 46 observations; the actual-character replay
replays 42.547 s / 146,882,560 bytes / 44 observations. Public source is copied
byte for byte from those qualified snapshots; public import-path checks and
hosted diagnostics are tracked separately.

The public import-path run independently passes the same 139 cases in 4.47 s;
its complete guard replays 33.453 s / 94,826,496 bytes / 35 observations.
Both public source and tests are byte-identical to the qualified isolated
snapshots. The source manifests and focused hosted workflow include the new
52-case file. Hosted results must be checked against the actual pushed source;
no broad inventory or motion-quality pass is inferred from registration.

Hosted run `39025753066` at exact source `fbc8029` passes all 52 selected
cases on Ubuntu and Windows. Final run/job metadata and both observed test
counts are retained separately from local qualification. Fresh four-slice
mesh validation and independent receipt/actual-pose replay of the new
35,344-pair candidate are measured separately; their completed results and a
distinct memory-stop recovery follow below. No numerical-component test result
substitutes for that mesh validation.

The same complete 120-time population now has 113 geometry passes, seven
failures at indices 623–629 (1.227083333–1.2375 s), 160 crossing records and
zero motion-bound failures. The previous candidate had 104 passes, 16 failures
and 1,326 records on that identical clock. This measures fewer mesh failures,
not a visual-quality score or a whole-motion pass. The independent pose-row
comparison differs by at most 7.661e-15; physical bounds are separately strict.

The four query guards independently complete at 194.875 s / 185,077,760 bytes /
194 observations; 184.797 s / 177,283,072 bytes / 184; 202.359 s / 194,289,664
bytes / 201; and 160.250 s / 175,640,576 bytes / 159. The original receipt
worker then fails at the unchanged available-RAM guard: 19.344 s /
149,012,480 bytes / 22 observations. Its failed receipt report and stopped
controller remain unchanged. After memory recovers, a fresh, byte-identical
receipt worker in `high-five-exact-group-candidate-receipts-v3` independently
verifies every original current-candidate query/receipt/source/clock/export/
actual-pose observation. It completes at 53.797 s / 168,759,296 bytes /
55 observations. This does not rerun geometry or relabel the failed worker.

`high-five-exact-group-transport-diagnosis-v3` independently samples the actual
saved clips and verifies all 35,344 retained pair gaps against 20 micrometers.
Maximum difference from archived encoded gaps is 9.437e-16 m. The public
GroupedPairGapRows component matches every direct projection with zero
difference and matching grouped extrema. All 160 remaining crossing records
are unique, previously unconstrained pairs. Its complete guard independently
replays 36.563 s / 145,235,968 bytes / 38 observations and binds both the failed
original receipt audit and successful separate recovery audit.

The next retained-pair trial uses the shared component for its actual fit rows,
per-side derivatives and original-pair physical postchecks. All 35,504 references
remain, as 5,508 exact groups / 29,480 rows / 65,091,840 Jacobian bytes with
the same 276 native scalars and unchanged 64-MiB cap. All 120 times, original
source epoch, rotation/world bands, frozen keys and body/finger permissions
remain unchanged. Initial full-Jacobian and value-only rows match bit for bit;
two directional comparisons have maximum errors 3.029e-7 and 3.872e-7 under
the unchanged 2e-5 numerical criterion. Checkpoint 11 subsequently passes every
raw/Float32 physical row and retained pair condition. The worker exports fresh
clips and stops without claiming optimizer completion or optimality. Its guard
independently replays 748.421 s / 751,206,400 bytes / 738 observations. Its
distinct fresh mesh/receipt results follow below.
The original stays selected. The other 1,897 policy times, self/dynamics,
semantics, engine and human review remain unverified.

The complete shared-row candidate interval now passes all 120 original policy
times, with zero reported surface crossing records and zero motion-bound
failures. All native-key raw and encoded bounds independently pass. The four
fresh query guards independently replay 188.890 s / 183,054,336 bytes /
188 observations; 190.469 s / 180,588,544 bytes / 189; 205.656 s /
177,270,784 bytes / 204; and 143.922 s / 177,696,768 bytes / 144. The independent
source/export/clock/receipt/actual-pose audit replays 51.750 s / 155,021,312
bytes / 53 observations. Its maximum pose-row comparison difference is
8.993e-15; every physical bound remains a separate strict check. This clears
the specified interval policy, not whole-motion, self, continuous-collision,
dynamics, task-semantic, engine or human acceptance. The original stays selected.

The direct saved-GLB projection audit independently verifies all 35,504
retained gaps against 20 micrometers; maximum difference from archived encoded
gaps is 7.807e-16 m. The public grouped-row component matches every projection
exactly and reproduces the grouped extrema. There are no new crossing records.
The complete guard replays 40.797 s / 144,060,416 bytes / 42 observations.
These complete current-candidate observations are retained in
`high-five-shared-row-candidate-geometry-v1`, its separate receipt audit and
`high-five-shared-row-transport-diagnosis-v1`.

`native_coupled_key_pair_rows.CoupledKeyPairRows` now exposes the complete
two-rig row evaluator without the study's hardcoded rig names, key indices or
triangle tables. Each left/right specification supplies a loaded original
native actor, nodes, rotation bands, original clock and complete seed (including
any nonzero fixed keys),
explicit editable key/node pairs, frozen keys and per-joint world bands.
Each observation supplies a distinct increasing shared time and complete gap
contexts: paired triangle IDs, unit world direction, physical gap and optional
normalization scale/temperature. Different native clocks and node counts are
allowed across actors; their durations must match exactly. Controlled channels
must retain their original common per-actor LINEAR quaternion clocks. Both
sides currently require nonempty explicit edit pairs; this is a numerical
two-rig component, not a fixed-object adapter or complete scene fitter.

`evaluate` returns every declared pose, pair-guidance and variable-native-key
row and the complete combined Jacobian. `values` supports raw or Float32
sampling; `postcheck` separately retains strict exact raw/Float32 original-pair
conditions. `controls` reconstructs the full seed grid while preserving every
uneditable/frozen key and rejecting out-of-ball native proposals. Constructor
arguments are copied; repeated evaluations reject changed source/pose bindings.
The layout retains structurally fixed time rows instead of dropping them.
The component neither optimizes nor exports, selects motion, infers contacts
or approves a clip; whole-curve/fixed-seed, actual saved-mesh, rates, dynamics,
engine and human validation remain caller responsibilities.

The unchanged complete-request limits are 768 combined native variables,
100,000 rows and 64 MiB for the dense Jacobian. Observations default to at
most 128 and can be explicitly raised to 512; each time accepts at most
32 separately bound gap contexts, each preserving at most 16,384 original
references. Over-budget or invalid requests raise rather than discard data.

Twenty-four new coupled/source-mutation/finite-difference/frozen-key/native-codec
cases plus 123 related cases pass in both isolated and public import-path runs.
The isolated test guard replays 79.172 s / 131,026,944 bytes / 80 observations;
the public run passes 147 cases in 32.61 s with guard 62.875 s / 122,322,944
bytes / 64 observations. Complete real-character 120-time / 276-variable /
29,480-row / 35,504-reference replay matches all archived smooth/raw/Float32
rows and original-pair conditions bit for bit. Row positions and roles are
equivalent with an explicit `gap` to `region` label alias. Both archived analytic
direction products match exactly; new finite differences give 3.029e-7 and
3.872e-7 under the unchanged 2e-5 comparison criterion. The failed initial
point remains failed; this is operator qualification, not a new correction.
The complete real-character guard replays 137.172 s / 362,131,456 bytes /
137 observations. Public source/test bytes equal their qualified snapshots.

Hosted focused run [39030349815](https://github.com/DocMorphic/strep/actions/runs/39030349815)
passes all 24 selected coupled-row cases on Ubuntu and Windows at source
`8a24e427f1b1344b8926a14c2227c555717259c5`.

### Frozen contact-pose self geometry and default-pose calibration

Separate full-surface queries at the exact 2-s native key retain all 18,056
vertices and 36,108 triangles per actor, including crossings between triangles
with shared topology. Current partner/plane geometry and actual saved-clip
joint/local-rotation bands pass at this time. Self-surface checks fail: actor A
has 131 proper-crossing face pairs and B has 70. The original authored reference
has 232 and 135 respectively. Exact face-pair identity confirms that every
current pair was already present in that reference, 101/65 reference pairs are
absent from the candidate, and no new pairs were introduced at this pose.
These counts measure surface intersections, not visible severity or realism.

All positive influences across all eight skin-weight slots and their ancestor
closures are retained in a separate diagnostic. Remaining dominant weighted
labels include head, left shoulder/arm, chest and toes. None of the remaining
faces has a positive influence descended from a currently editable node. Also,
the exact native bracket is the frozen key 60, with no dependent editable pair.
Both spatial ancestry and temporal support therefore exclude these records
from the current approach-edit domain. This is not a proof that the rig or
action cannot be corrected. No permissions, frozen keys, caps or exclusions
were changed. The complete self study replays 217.625 s / 179,511,296 bytes /
216 observations; influence/support diagnosis replays 25.360 s / 147,865,600
bytes / 27 observations.

Full self-surface calibration at the unanimated glTF default node transforms
finds 61 proper-crossing face pairs. Both actors have byte-identical default
geometry and triangle populations, so this complete query is performed once
and its geometry/report hashes explicitly bind both actors. Of the current
contact-pose pairs, A shares 56 with the default pose and has 75 contact-only
pairs; B shares 47 and has 23 contact-only pairs. Five default-pose pairs for A
and 14 for B are absent at contact. The guard independently replays
70.078 s / 132,255,744 bytes / 71 observations. Every record remains visible;
default-pose persistence does not authorize an anatomical exclusion. Default
node transforms are not assumed to equal bind, clean rest or intended anatomy,
and contact-only pairs do not establish causality from the latest correction.

Composite scene/pose sample coverage is now 121 of the 2,017 full-policy times;
the earlier 120-time receipts remain unchanged. The other 1,896 times,
full-clip self contact, motion dynamics, contact anatomy/semantics, held-out
actions/rigs/objects/partners and actual engine/human cleanup requirements
remain open. Next correction work must distinguish persistent asset geometry
from deformation and explicitly version any expanded edit domain. Neither
this diagnostic nor the cleared approach interval approves motion quality.

### Explicit self and reversed-partner pair contexts

`CoupledKeyPairRows` gap contexts now accept optional `actor_sides`: `[0, 0]`
or `[1, 1]` binds both triangle populations to the same supplied actor;
`[1, 0]` reverses the partner order. Omitting it preserves `[0, 1]`.
Triangle IDs are checked against the corresponding actor's full topology.
The unit world normal retains its declared direction: the measured gap is
the second population's minimum projection minus the first's maximum.
No direction, contact intent, anatomical exception or edit permission is
inferred. For example, a context may contain:

```json
{
  "actor_sides": [0, 0],
  "pairs": [[120, 360]],
  "normal_world": [1, 0, 0],
  "minimum_gap_m": 0.00002
}
```

The indices above illustrate the schema; callers must supply actual bound
face references and an appropriate authored separation direction. Directional
separation is a condition to check, not an automatic collision repair. Shared
vertices or incompatible directions can make a positive requested gap
unreachable; no failing pair is silently dropped.

Both geometry derivative chains accumulate into the same native variable
slice for a self context. Fixed-row classification considers only actors
referenced by that context, so an unrelated movable actor does not make a
frozen self condition editable. Raw/Float32 postchecks preserve every original
pair in its declared order. Seeds, complete pose/native-key rows, source
bindings and all existing resource limits remain unchanged.

Seventeen new cases cover all four actor orders, every native derivative
column, actual saved self-pair projections, frozen self support independent
of the other actor, snapshotting and malformed actor indices. All 164 selected
new/existing cases pass; the guard replays 75.016 s / 125,759,488 bytes /
76 observations. Full-character qualification keeps all 367 authored-reference
self pairs in each of three explicit diagnostic directions at 1.2 s and 2 s,
plus reversed partner references: 2,204 original pair checks, 1,446 complete
rows, 276 native scalars and a 3,192,768-byte Jacobian. Both saved clips retain
all 18,056 vertices / 36,108 faces and original mesh, skin, node and binary
prefix data. Independent saved-mesh projections differ by at most 6.662e-14
in normalized row units. Two complete directional comparisons differ by
3.940e-7 and 3.938e-7 under the existing 2e-5 numerical criterion. All six
active self contexts have nonzero derivatives; all six frozen 2-s self contexts
have zero derivatives, as required by their native support. The actual-data
guard replays 28.375 s / 165,228,544 bytes / 30 observations.

A separate complete compatibility replay retains the original 120 times,
29,480 rows, 276 native variables and 35,504 pair references. All archived
smooth/raw/Float32 rows and original-pair postchecks remain bitwise identical;
both archived analytic direction products match exactly. Fresh finite
differences give 3.029e-7 / 3.872e-7 under 2e-5. The failed initial point remains
failed. Its guard replays 134.813 s / 377,913,344 bytes / 135 observations.

Hosted focused run [39032025228](https://github.com/DocMorphic/strep/actions/runs/39032025228)
passes all 41 coupled-row cases on Ubuntu and Windows at source
`0eabd8f90a99d76588004c21c255d334f0179c6d`. This covers the evaluator's source
suite; it does not replace the separately archived real-character checks.

The diagnostic separation conditions remain failed. These results qualify
an evaluator and native export checks, not an optimized self correction,
new collision-free motion, anatomy, whole-clip realism or release approval.

### Full original animation-key sweep

The current saved candidate is now checked at all 120 original native animation
keys across the entire clip. The earlier interval/contact studies covered nine
of those keys. A new query covers every remaining 111 keys, with all 18,056
vertices / 36,108 faces per actor, unchanged partner/plane geometry policy and
direct actual saved-clip joint/local-rotation bands. All 111 new samples pass
scene geometry and pose bounds, with zero reported partner surface crossings.
Every raw/Float32 native rotation bound, frozen/uneditable coefficient,
unmodified track and original mesh/skin/node binding is independently retained.
Native rotation row comparisons differ by at most 1.111e-15; physical rows are
checked separately against zero without a tolerance. The query guard replays
574.172 s / 217,124,864 bytes / 567 observations.

A separate receipt audit independently verifies complete native-clock coverage,
every observation/receipt hash, actual pose rows, floor extrema and current
actor GLB identities against both prior studies. It replays 44.782 s /
151,597,056 bytes / 46 observations. Composite current-candidate scene/pose
coverage is 232 of 2,017 policy times, including all original 120 native keys;
1,785 other in-between policy times remain unchecked. Previous reports remain
unchanged. This is a complete native-key sample pass, not full interpolated
motion, continuous collision, self-intersection, dynamics, semantics, engine,
animator or release acceptance. The previously measured contact-pose self
failures remain open.

### Bounded coupled correction API

`scripts/native_coupled_pair_fit.py` adds `preflight(problem, value=None)` and
`fit(problem, iterations=32, maximum_evaluations=128, search_reserve=None,
on_evaluation=None, starting_value=None)` for a complete `CoupledKeyPairRows`.
This is a development API; Studio's existing contact/rate solver is unchanged.
Callers must retain every original scene/contact/rate condition when composing
an integrated problem, and independently audit actual saved assets afterward.

Preflight reconstructs native endpoint support and complete row/pair layouts.
It rejects exact raw/Float32 physical violations outside that support, retaining
all original pair indices. A negative smooth gap, reserve margin or numerical
zero derivative is not an infeasibility proof. Fixed self conditions consider
only their referenced actor. Source and structural bindings are checked before
cached values are consumed; fresh kernels perform their own complete source
checks. Every potentially feasible point receives a fresh exact postcheck,
including after an evaluation callback.

The solver minimizes distance to the unchanged original problem seed under all
declared pose, native-ball and directional self/partner rows. Search reserves
are complete normalized guidance arrays, not physical acceptance thresholds.
An already feasible starting point is preserved. A new proposal can stop at an
independently postchecked feasible checkpoint without optimizer convergence or
optimality. Solver success alone never accepts motion. Limits remain 1–64
iterations and 1–512 complete evaluations, plus caller-enforced resource guards.
Callbacks receive copies of complete controls and rows for durable checkpoints.

`starting_value` accepts a complete native variable vector in the existing
scalar search box, without automatic clipping. It does not rebase the original
source, objective seed, caps, frozen keys or permissions. Callers must bind the
checkpoint to its complete original recipe and source hashes. A restart resets
SLSQP's internal state; it is not a resumed Hessian or a reclassification of a
failed job. Failed proposals remain unselected.

Thirty-six new fitter cases plus 41 coupled-row cases pass in both isolated
prototype and production-import tests. These include a real small contact
repair with independently sampled saved GLBs, fixed physical failures, stronger
smooth-proxy failures, callback/source invalidation, exact evaluation limits
and preservation of the original objective across a restart. Prototype guard:
69.875 s / 132,284,416 bytes / 71 observations. Production-import guard:
72.063 s / 122,056,704 bytes / 73 observations. Earlier failed prototype records
remain immutable; validation-order and stale cached-postcheck failures are
covered by the passing suite.

The full 120-time / 29,480-row / 276-variable / 35,504-reference prototype run
reproduces all twelve prior research checkpoints with byte-identical complete
control and row arrays. It reaches checkpoint 11 but stops at the unchanged
900-s execution guard before final verification: failed guard 916.063 s /
725,618,688 bytes / 901 observations. That attempt remains failed. A separate
production-API recovery checks the durable point under the original problem;
its outcome is recorded separately and is not inferred from positive search
rows. No new model inference, training, data license, edit permission, motion
selection, complete scene implementation or release approval is implied.
