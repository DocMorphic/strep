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
key-64 and key-74 updates with assembly-v2. There are still 15 edited native
keys relative to the original source; this revision changes only two body
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
