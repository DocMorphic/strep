# Palm contact regions and native rig fitting

The fixed center marker failed all 48 animated/rest rigid-hand screens. This
experiment authors a different contact condition: a declared area of the palm
can supply the contact point. It does not change or reinterpret the old
fixed-marker benchmark.

## Declared region and geometric selection

Use the animated skin from `reports/contact-pair-prevention-v1`. The region is
within 40 mm of original vertex 14712 along mesh edges, with an outward vertex
normal no more than 60 degrees from that seed's normal. Edge-path distance is a
discrete surface-distance definition, not an exact continuous geodesic. Nearby
disconnected surfaces cannot enter through Euclidean shortcuts. Region membership
is frozen from the declared source pose; anatomy remains pending human review.

Compute supporting planes of the convex hull of the complete selected hand
surface. A candidate must be inside the declared region and its actual surface
normal within the unchanged 20-degree authored normal tolerance of the support
normal. All hand vertices must lie behind its support plane within 1e-8 m.
Rank distinct candidate vertices by edge-path distance, then normal error, then
vertex ID. This selects vertex 14683 on both hands, 27.230123 and 27.278322 mm
along the surface from the original marker. Both regions have 186 vertices;
there are 15 and 14 eligible supporting vertices respectively.

Place the chosen points at the existing target positions, 1 mm apart, and align
the support normals to the existing desired directions. This is an explicit new
surface-point condition. Actual surface normal errors are about 1.003 and 0.415
degrees and are checked independently. Every selected hand triangle lies in the
corresponding half-space for these rigid proposals; full crossing and vertex
containment queries remain mandatory.

All 24 actor-B twist samples pass the selected-hand geometry screen. This is
an initializer result, not a rig or animation result.

## Actual arm-chain reach

The next stage searches each actor independently over 24 wrist twists and 25
elbow swivels, preserving rigid bone lengths, local translations and finger
transforms. It tests all 22 original arm/finger pose-angle budgets against the
same original reference. Of 600 candidates per actor, 25 and 22 pass those pose
limits. Ranking feasible poses by summed squared original arm angles selects
zero extra twist and zero swivel for both actors.

The actual skinned full-body pair at this instant has no detected inter-actor
triangle intersections or contained vertices. Contact gap is 1.000012 mm, anchor
errors below 0.000007 mm, and normals remain within tolerance. The arm angles
are 8.670/15.132/16.111 degrees for actor A and 9.022/16.252/16.382 for actor B,
all below the original 45-degree limits. Finger pose limits also pass.

This is one pose: no native-key, approach/departure, rate, floor, self-collision
or human-quality approval follows from it. The orthographic inspection in
`reports/palm-region-rig-inspection-v1/hands.png` was visually inspected; it shows
the newly selected palm-heel points on the actual mesh and does not substitute
for anatomical review.

## Native-key motion protocol

Fit only the three arm rotation channels to that validated pose using the
existing triangular native edit envelope. Use per-joint correction balls equal
to each joint's remaining original-reference 45-degree allowance over all native
keys. This explicit allowance belongs to the new condition; the earlier donor
experiment's additional 15-degree search cap is not silently reused as a release
criterion. Original final arm/finger edit budgets remain unchanged.

Export GLBs, decode independently, and check original rotation budgets, unchanged
key clocks, unselected channels, outside-window and protected poses. Audit the
same 53 geometry times over the complete edit interval, report floor depth, and
measure all four original-reference speed/acceleration cap groups. Sampling does
not certify continuous collision freedom. Keep failures and withhold Studio
selection unless the whole required workflow qualifies.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_rigid_contact_initialization.py reports/contact-pair-prevention-v1 reports/paired-edit-jobs/relinearized-v2 reports/<fresh-region> --contact palm-to-palm --contact-region-radius-m 0.04
.venv/Scripts/python.exe scripts/study_palm_region_rig_pose.py reports/<completed-region> reports/scene-pair-relinearized-completed-v2 reports/<fresh-pose>
.venv/Scripts/python.exe scripts/study_palm_region_motion.py reports/<completed-pose> reports/<fresh-motion>
```

The older fixed-marker mode remains available without the region option. Its
historical archives and failures remain unchanged. Models, assets and large
raw reports remain excluded from Git. No model training or reserved held-out
prompt use occurs in this experiment.


## Exported-motion result and remaining failures

Both 80-iteration-bounded native fits converge successfully, with final costs
9.58e-11 and 1.03e-10. Independently decoded contact at 2.091722595 s retains
zero detected inter-character crossings/penetration, a 0.999988 mm gap, anchor
errors below 0.000046 mm and normal errors 1.002628/0.414843 degrees. All original
arm/finger native-key angle budgets pass. Native clocks, unselected channels,
outside-window and protected poses are unchanged.

The full sampled interval is **not** clean: 9 of 53 geometry samples fail.
Six are at 1.615660..1.740939 s; three are at 2.041611..2.066667 s, before contact.
There are 3,491 proper crossing pair-times and maximum penetration 22.110409 mm
at 1.665772 s. Two guard times near 2.066667 s differ because one comes from the
native float32 clock; they are retained rather than deduplicated by rounding.
The sampled departure after contact passes these inter-actor screens, but this
is not a continuous or self-collision certificate.

| Original motion cap | Failing rows | Maximum excess |
| --- | ---: | ---: |
| Position speed | 176 | 0.173985 m/s |
| Position acceleration | 147 | 13.819535 m/s^2 |
| Angular speed | 902 | 1.520419 rad/s |
| Angular acceleration | 228 | 239.164658 rad/s^2 |

Floor penetration is unchanged at a maximum 6.003415 mm; unchanged is not a
floor-quality pass. The two GLBs remain local experimental assets under
`reports/palm-region-motion-v1`, and are not selected for Studio or release.
Next extend the supporting-surface constraints across the approach trajectory,
with native timing, original angle limits and rate checks. Preserve this clean
contact pose, the explicit new region condition and the old fixed-marker
benchmark. Do not infer that a larger region or more optimization alone will
make the complete high-five natural.

## Evidence and validation

| Local study | Bound inputs | Archived methods | Outputs |
| --- | ---: | ---: | ---: |
| `palm-region-initialization-v1` | 3,528 | 82 | 27 |
| `palm-region-rig-pose-v1` | 3,638 | 84 | 6 |
| `palm-region-motion-v1` | 3,729 | 85 | 59 |

All recorded input, archived-method and output hashes were rechecked. Result
SHA-256 values respectively:

- `3317f17949308d9305713c17b547b1c70e83a9c641726f5441e60ca508fd30ab`
- `e0c41c3cd82fffd63df2100260c2fd9979ede0605dc5a4772ddd69f9a2023c28`
- `b8ebe29750c47ff74b87dc656ef999c18be99834acc61de7d8d6e26d7dd282e8`

After the experiments, contact rebinding was corrected to discard inherited
cached offsets/normals from the old vertex and to set the authored pair gap
field to the explicit 2 mm maximum. Historical archives retain the original
metadata and are immutable: those runs use actual selected vertex geometry and
the explicit target record for every check, not the inherited cached fields.
Use the archived methods for exact historical reproduction; do not import their
unsanitized `selected_contact` records into a product scene. New runs emit the
cleaned contact descriptors. No expensive geometry run was repeated merely to
rewrite provenance fields.

Eleven added model-free tests cover surface-path membership without shortcuts,
front-facing selection, support planes, rigid invariance, invalid inputs,
unchanged finger transforms and translations under oriented arm reach, and
removal of stale contact metadata. All 1,039 model-free source tests pass. No animations have been judged realistic by a human
as part of this study, and all release capability gates remain unapproved.
