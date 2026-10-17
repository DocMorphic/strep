# Native-key coupled motion development

The [coupled contact study](native-self-separation-cuts-v1.md) finds a strict
single-pose candidate at 2 s. The next work is a native animation curve,
decoded validation and complete motion evidence. A passing isolated pose
does not establish an animation or transfer its approval to an exported file.

## Native-key save/reload probe

A diagnostic appends one animation per original actor GLB and edits only the
existing 2-s key (key 60 of 120). A has 22 controlled rotation tracks and B
23. It retains original translations/scales, mesh/skin/node declarations,
original animation objects, every native timestamp, the entire original
binary prefix and all other key values exactly. Source animation index 1
remains intact; the diagnostic uses appended index 2. This deliberately
abrupt neighboring motion is a codec probe, not a motion proposal.

Directly decoded worlds and all eight skin influences are checked against
the source pose. Maximum world-matrix element differences are 3.639636e-8
for A and 5.321447e-8 for B; maximum vertex differences are 5.655724e-9 m
and 1.986715e-8 m. Both root worlds remain exactly unchanged. All 6,131
contact/edit/support pose rows pass after decoding. One of the 171 search
guide rows fails, with minimum normalized value -1.048254e-7. This remains
recorded: the exported file does not pass the original all-row condition.

The decoded contact-frame gap/opposition/tangent errors are 4.997487 mm /
2.950925 degrees / 14.750262 degrees against unchanged 5-mm / 5-degree /
15-degree limits. Actual partner geometry and localized hand checks pass.
Complete 36,108-triangle-per-actor self scans retain A 131 / B 70 original
pairs, remove A 101 / B 65 and introduce zero. Inherited source defects
remain. Only one of the planned 2,017 geometry times is checked; rates,
complete-clock geometry, engine and human quality are unapproved.

The guarded diagnostic completes in 154.281 s at 182,845,440 sampled bytes;
all 152 resource observations replay independently. The saved raw source,
single-key outputs, numerical guide failure and guard traces remain separate.

## Native-clock control taper

`scripts/native_key_control_taper.py` weights explicit original-relative
rotation-vector controls on a supplied unchanged native clock. Its start,
peak and end must be existing keys. A quintic envelope uses seconds,
including nonuniform clocks, with exact zero controls outside/boundaries
and exact anchor controls at the peak. Weights stay between zero and one,
so normalized angular edit balls remain bounded at the supplied keys.

Input bounds are 3–4,096 increasing finite native times and 1–32 complete
finite three-component control vectors in their unit balls. The maximum
returned control array is 3,145,728 bytes. The helper preserves its inputs;
it does not recenter a reference or infer an anatomical range.

The underlying scalar envelope is C2. Encoded glTF uses its native
interpolation, so quaternion/world smoothness, subkey angular bounds,
displacement, motion rates, contacts and collisions still need separate
decoded checks. A tapered initializer is a proposal, not a physical result.

Twenty-four local tests cover exact peak/outside controls, readonly inputs,
nonuniform-time analytical values, clock subdivision, quaternion edit angles,
boundary behavior, the complete allocation bound and invalid inputs. The
guard completes in 18.281 s at 96,088,064 bytes; all 20 observations replay.
Inventories now contain 553 Python/45 Node suites, with 117/five in the
contact subset. These counts are not full-inventory passes.

Every moving proposal must retain original root tracks, endpoint keys and
timestamps, record full source-relative angular/displacement/rate results,
and include known geometry failure times before claiming broader success.
Original assets remain selected; this work changes no release criterion.

Both hosted platforms also pass the 24 taper tests: Windows in 0.37 s and
Ubuntu in 0.52 s, [run 38987834250](https://github.com/DocMorphic/strep/actions/runs/38987834250),
source `deb20a7`. These are focused helper tests, not animation acceptance.

## Independent codec replay

The native-anchor replay reconstructs every expected Float32 rotation key,
original binary prefix, original animation, clock, world matrix, vertex and
pose inequality exactly. An initial replay omitted the Float32 cast when
constructing expected keys and failed; that failed experiment is preserved.
The successful fresh replay compares the actual accessor representation.
It does not rerun the collision predicates.

The remaining exported guide failure is row 133, involving B triangles
26546/26552, shared vertex 2979 and vertex pair 11116/2979. Its represented
gap is -1.058254e-10 m against the already declared 1e-12-m arithmetic
cushion. This tiny shared-vertex search-guide failure does not invalidate
the separately passing physical pose rows, and is not silently rounded
away or reported as a passing all-row export.

## Moving curves and sampled displacement repair

The first moving proposal applies the taper to every original native key,
retaining the exact contact anchor. It appends animation index 2 to each
actor file; original animations 0/1, mesh/skin/node declarations, original
binary prefix, translations, scales, roots and endpoint worlds remain
unchanged. There are still 120 keys on the original 30-Hz clock. Sampling
uses native affine transforms, including scale; no rigid projection is
used to produce the mesh.

The unchanged geometry/rate union contains 2,017 distinct times, including
477 samples at 120 Hz. At every union time the producer checks all 77
joints against their original source worlds and all 18,056 vertices per
actor with every one of eight skin influences against the declared floor.
Original angular caps and displacement bands remain unchanged: finger
descendants other than the wrist have 150 mm; the wrist and other joints
have 60 mm. These are explicit edit permissions, not anatomical limits.

The sequence preserves each failed condition in its own study:

| Proposal | Native-key world failures | Dense world failures | Observation |
| --- | ---: | ---: | --- |
| Taper v2 | Not separately counted | B 453 | B RightForeArm reaches 67.656376 mm against 60 mm; failures span 1.108333–1.997917 s. |
| Ancestor backoff v3 | 0 | B 324 | Native keys pass, but interpolation reaches 60.209280 mm, worst at 1.216667 s. |
| Interior-margin backoff v4 | 0 | 0 | Both actors pass all 2,017 sampled world and angular checks. |

An earlier moving worker fails during array-shape setup before completing
these audits. It is retained separately. The corrected evaluation uses an
explicit time-by-joint displacement array, with shape assertions.

Backoff changes B's RightShoulder/RightArm controls at 26 existing keys.
These ancestors can move the forearm origin; rotating the forearm itself
cannot. The search uses quantized rotation values in a copy of the actual
native sampler, tests feasibility before retaining a point, and keeps
finger controls and the contact key unchanged. It does not assert a
globally optimal or monotone feasible region.

V3 reserves 1 micrometre inside the unchanged world bands at native keys.
Its measured subkey excess is 209.280397 micrometres. V4 uses a separate,
explicit empirical search reserve of 313.920596 micrometres at nonanchor
keys, keeping the contact key's 1-micrometre reserve. This is a new search
condition; it neither relaxes the physical band nor proves continuous
feasibility. The source worlds and all original rate caps remain fixed.

For v4 both roots and all endpoint worlds remain exactly unchanged. Floor
minima are exactly equal to the source throughout the complete sampled
clock: A's maximum depth is 4.5 mm and B's is zero, within the unchanged
5-mm floor condition. Maximum sampled angular fractions are
0.998999991 / 0.999499851 of the authorized A/B caps.

Fresh independent replays reconstruct all encoded rotations, native
timestamps, original contents, complete saved world arrays, world-band
rows, motion-rate arrays and original rate caps exactly for v2/v3/v4.
The backoff replay additionally matches all 120 native-key worlds and
control scale factors. Independent floor replay covers six explicit
times per actor with zero discrepancy; the producer's 2,017-time floor
scan is not mislabeled as independently recomputed in full.

## Timing and geometry remain separate conditions

V4 still exceeds the original four-bin per-joint rate budgets:

| Actor | Linear speed rows | Linear acceleration rows | Angular speed rows | Angular acceleration rows |
| --- | ---: | ---: | ---: | ---: |
| A | 299 | 66 | 1,875 | 84 |
| B | 481 | 128 | 251 | 62 |

These are unchanged source-relative edit-budget diagnostics. The release
matrix's per-joint dynamics thresholds remain unset pending calibration;
these row counts alone are not an anatomical realism judgment. No timing,
semantic quality or animator acceptance is inferred from the position
and floor results.

Fresh whole-mesh partner/floor checks at the old collision times 1.075 s
and 1.1395833333333334 s find zero triangle records and zero legacy signed
vertex depth. The 2-s peak has exactly the codec probe's quantized keys,
worlds, vertices, topology, placements and geometry policy. Its existing
contact/partner/self evidence is reused through explicit hash and array
identity checks; collision predicates were not rerun there. The codec's
one failed guide row and inherited A 131 / B 70 self-pairs remain visible.

Eight additional coarse samples at 0/0.5/1/1.5/2.5/3/3.5 s and the exact
clip end pass partner/floor checks. This brings coverage to only 11 of
2,017 distinct geometry times; 2,006 remain unchecked at this checkpoint.
This cannot establish complete-clock or continuous collision validity.
Complete self-collision, new-clip engine playback, anatomical contact
review, developer/animator ratings and cleanup-time evidence remain open.

## Reproduction and resources

Generated files stay in ignored local studies. The moving proposals are
`reports/high-five-coupled-native-taper-v2`, `-v3` and `-v4`; their independent
replays are `reports/high-five-coupled-native-taper-replay-v1`, `-v2` and
`-v3` respectively. Each includes its own input bindings, archived
implementation, decoded observations, results and guard traces. The GLBs
contain editable animation data; they are unapproved experimental assets.

| Completed guarded study | Elapsed seconds | Peak sampled process-tree bytes | Replayed resource observations |
| --- | ---: | ---: | ---: |
| Codec replay, corrected expected representation | 44.734 | 159,035,392 | 46 |
| Taper v2 | 170.156 | 345,255,936 | 169 |
| Backoff v3 | 192.094 | 348,971,008 | 191 |
| Subkey residual diagnosis | 17.219 | 68,120,576 | 19 |
| Interior-margin backoff v4 | 181.094 | 349,057,024 | 180 |
| Independent v3 replay | 96.828 | 266,207,232 | 97 |
| Independent v4 replay | 97.860 | 256,843,776 | 98 |
| Eight extra coarse geometry samples | 45.828 | 237,101,056 | 47 |

All terminal resource traces, including failed workers, are independently
replayed. These are sampled RAM/process-policy results, not a guarantee
against future load or motion quality. No checkpoint training, default
model change, release threshold change or asset promotion occurs.

## Contact-window collision and bounded point queries

A denser follow-up selects 128 remaining clock times nearest the 2-s
contact. Its initial 32-point signed-distance queries hit the unchanged
1-GiB process-tree cap after 49 complete samples; six of those samples
fail. The first failure is at 1.9583333333333333 s, with ten triangle
records and 0.150892-mm maximum legacy vertex depth. A saved exact
represented-triangle witness proves a strict interior crossing for
triangles A 28000 / B 27462. The vertex depth being below the 5-mm depth
limit does not override the separately failing surface condition.

The memory guard stops the worker at 1,077,682,176 sampled bytes after
113.141 s; all 114 resource observations independently replay. There is
no completed 128-sample result for that attempt. Its completed reports,
vertices, exact witnesses and partial progress remain intact.

`convex_partner_surface.penetration` now accepts an explicit integer
`query_batch_size` from 1 to 32, defaulting to the previous 32. Scene
evaluation, archive writing and the command-line audit expose and record
the same setting as `partner_query_batch_size`. This changes simultaneous
signed-distance points, not the mesh, convex broad phase, selected vertex
population, tolerance or crossing test. A single dense point can still
require substantial memory; the process guard remains necessary.

Eighty-two local tests pass across the partner query, scene geometry and
observation archive suites. New tests measure actual point batch sizes,
retain the complete hull-candidate population and original global vertex
IDs, compare depths and nonconvex geometry decisions across 1/2/7/32-point
batches, reject invalid settings before work, and check propagation into
an archived scene result. The test guard completes in 26.375 s at
112,799,744 bytes; all 28 observations replay. Inventories now contain
554 Python/45 Node suites and 120/five in the contact subset, as counts
only. A fresh full contact-window attempt uses single-point queries under
the same 1-GiB cap and compares all 49 completed prior results explicitly.

That single-point attempt also stops at the process cap after 50 complete
samples (seven failures): 96.407 s, 1,080,537,088 peak sampled bytes and
98 independently replayed resource observations. All 49 prior geometry
decisions and crossing records reproduce; depth discrepancies stay within
the explicit 1e-12-m comparison bound. Smaller queries alone do not solve
this multi-sample worker's memory growth.

A subsequent fresh attempt loads the two complete decoded world arrays
once instead of repeatedly decompressing them for each sample, and
explicitly collects Python cycles between samples. It records RSS before
and after each collection, retains single-point queries and the same
1-GiB cap, and compares the 50 completed predecessor samples. These are
explicit worker-lifetime changes, not changes to the numerical condition.
They do not, by themselves, establish which allocation caused the growth.

The same source (`0d0486d`) passes each affected suite on both hosted
platforms:

| Suite | Tests | Ubuntu seconds | Windows seconds | Hosted run |
| --- | ---: | ---: | ---: | --- |
| Partner point batches | 14 | 0.74 | 1.10 | [38991915180](https://github.com/DocMorphic/strep/actions/runs/38991915180) |
| Complete scene geometry | 30 | 2.16 | 4.90 | [38991916893](https://github.com/DocMorphic/strep/actions/runs/38991916893) |
| Observation archive | 38 | 0.50 | 1.18 | [38991918865](https://github.com/DocMorphic/strep/actions/runs/38991918865) |

The fresh lifetime-managed contact-window study completes all 128 selected
times from 1.8729166666666666 to 2.127083333333333 s. It reproduces all 50
completed predecessor samples' geometry decisions and records. Fifty new
samples fail, starting at 1.9583333333333333 s; the final sampled time
still fails. All 50 have an explicit exact represented-triangle witness
of a strict interior crossing. The maximum legacy vertex depth is
21.367634 mm at 2.11875 s, with 325 surface records at that time; the
maximum number of records at any selected time is 562. The depth condition
also fails, independently of the surface condition.

Coverage is now 139/2,017 distinct partner/floor times, with 1,878 still
unchecked. This subset does not bound the beginning/end of every collision
interval, and its last failed sample does not establish that follow-through
clears afterward. Previously passing pose, world-band and floor checks
do not transfer to a whole-motion collision pass.

The completed guard takes 886.828 s at 248,791,040 peak sampled bytes;
all 871 resource observations replay. The successful study is
`reports/high-five-coupled-native-taper-contact-window-v3`; the two stopped
attempts remain separately preserved as `-v1` and `-v2`. The point-query
setting, eager world-array loading and explicit cycle collection are all
recorded, without assigning the memory improvement to one isolated cause.

## Original motion versus corrected contact path

A separate guarded diagnosis evaluates unchanged animation index 1 at
four selected failure times, using the same actor placements, topology,
geometry conditions and clock as candidate index 2. Every original world
matrix matches the earlier source arrays exactly. The candidate reports
are reused; their exact witnesses are reconstructed from the saved full
vertices and original face indices. This does not add new candidate times
to the 139-time coverage count.

| Time, s | Original surface records | Candidate surface records | Original maximum legacy depth, mm | Candidate maximum legacy depth, mm |
| --- | ---: | ---: | ---: | ---: |
| 1.958333333 | 715 | 10 | 19.600064 | 0.150892 |
| 2.095833333 | 564 | 562 | 20.215385 | 20.492500 |
| 2.118750000 | 388 | 325 | 20.894609 | 21.367634 |
| 2.127083333 | 298 | 386 | 20.982901 | 20.831136 |

Both versions fail at all four times. No same-kind triangle-pair record
is retained between versions at these times: the correction removes the
listed original records and introduces the listed candidate records.
The first selected time has substantially less measured overlap, while
follow-through still has roughly 20–21 mm depth. Surface-record counts
are descriptive, not a calibrated motion-quality score. An original clip
is not approved merely because it is the reference, and meeting the
authored contact at 2 s does not establish a correct interaction path.

Explicit skin-weight labels for the candidate witness triangles involve
RightHand, RightForeArm and right finger nodes, including pinky nodes.
These are declared rig influences, not an anatomical review of the chosen
contact patch. The source diagnosis is
`reports/high-five-coupled-native-taper-crossing-origin-v1`, completing in
145.921 s at 234,819,584 peak sampled bytes; all 146 resource observations
replay independently.

The next authoring experiment must address approach and follow-through,
retain the original reference epoch and explicit permissions, and check
decoded interpolation, dynamics and complete partner/self coverage.
Neither this candidate nor the original gains engine, developer/animator,
anatomical or release acceptance from this diagnosis.

The subsequent [native affine region study](native-affine-region-pose-v1.md)
adds reusable original-bound surface rows, verifies saved corrections at
15 selected native keys, and measures their combined curve separately.
The first combined curve still fails eight wrist-displacement rows and
three of 21 selected subkey partner checks; passing poses do not establish
a passing interaction path.
