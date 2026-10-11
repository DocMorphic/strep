# Timing layout and native storage on a development kick

Adding timing controls improves the strongest floor correction in this study,
but neither layout produces an accepted export. Both retain the original clip.
This is a development diagnosis of one existing seed-77 Kenney kick, not a
held-out benchmark or a claim about every action.

## Controlled comparison

Both layouts start at zero correction on the same feasible original. Only the
four measured left hip, shin, foot and toe rotation tracks (nodes 50–53) are
editable. The smaller layout has four control times, including the endpoints;
the finer layout has eight. These give 24 and 72 scalar controls respectively.
The finer layout includes all four original times and adds 0.2 s, 0.5 s and the
quarter/three-quarter clip times. Root translation and rotation stay frozen.

Both keep the original 30-degree track bounds, 0.22-m joint displacement limit,
all four source-rate cap arrays, 120-Hz rate clock and 1e-5 rate tolerance.
Each allows one surface-vector primary iteration with a 0.02 trust fraction,
0.001 forward continuous difference step, unit quaternion storage and no
restoration steps. No contacts are invented. All ten changed proposals receive
the same complete sampled floor audit: 2,017 times, 1,029 referenced vertices
and 1,604 faces, with a 5-mm penetration allowance.

The original has 49.727615-mm peak penetration and 234 failing floor times.

| Layout | Controls | Strongest proposal peak | Failing floor times | Accepted changed exports |
| --- | ---: | ---: | ---: | ---: |
| Four control times | 24 | 49.086408 mm | 232 | 0 / 10 |
| Eight control times | 72 | 45.813849 mm | 231 | 0 / 10 |

Every changed export fails at least one native condition. The final unchanged
clip passes native conditions and still fails the floor. Source caps remain
exactly equal and root poses match at all 120 original keys. The earlier
12-track study also used 72 controls; comparing it with this four-track study
does not isolate timing, because the editable joints differ.

The local model protects 107,527 native conditions plus 2,017 separate geometry
guards, with another 2,017 guidance rows: 111,561 norms in total. The smaller
layout's primary solve reports `Solved`; the finer reports `AlmostSolved`.
Both minimum-norm phases report `AlmostSolved`. Solver status and a passing
affine proxy do not establish a passing decoded clip or global feasibility.

The unchanged resource policy admits both jobs. The final execution observations
are 372.000 s and 451.579 s; all 380 and 458 recorded resource observations
independently replay with matching archived bindings. The output, controls,
source-cap arrays, geometry receipts and rejected exports remain locally under
`reports/kenney-kick-temporal-layout-v1`.

## Fresh decoding versus unrounded poses

A separate guarded job compares every retained proposal, plus both unchanged
starts, using freshly decoded GLBs and the same controls evaluated without
Float32 key storage. It runs no optimizer and creates no alternate clips.
It reproduces every producer's native merit, verifies all original cap arrays
and uniform times exactly, and retains both world-pose populations and all
107,527 residuals per comparison. Root poses match at all 2,017 sampled times.

The two unchanged starts pass in both forms. All twenty changed stored exports
fail. **Seventeen changed proposals pass before storage and fail after decoding**:
the smaller layout's fractions 1-2 through 1-9 and the finer layout's 1-1
through 1-9. Their stored failures are positional or angular acceleration rows.
The other three proposals also fail before storage, so serialization is not
the only issue. These are results of this shared sampler and constraint builder,
not independent motion or engine validation.

| Proposal label | Smaller: stored / unrounded failed rows | Finer: stored / unrounded failed rows |
| --- | ---: | ---: |
| 1-0 | 8 / 6 | 12 / 2 |
| 1-1 | 4 / 1 | 7 / 0 |
| 1-2 | 8 / 0 | 6 / 0 |
| 1-3 | 3 / 0 | 4 / 0 |
| 1-4 | 7 / 0 | 1 / 0 |
| 1-5 | 8 / 0 | 6 / 0 |
| 1-6 | 5 / 0 | 1 / 0 |
| 1-7 | 7 / 0 | 4 / 0 |
| 1-8 | 14 / 0 | 1 / 0 |
| 1-9 | 8 / 0 | 3 / 0 |

The diagnostic completes with a final execution observation of 163.546 s;
all 178 resource observations replay with matching bindings. Its raw arrays
and results stay in `storage-diagnostic/` inside the local study folder.
Geometry numbers above belong to the actual stored exports. Unrounded-pose
geometry is unmeasured; a passing unrounded motion does not solve the floor.

The next experiment must address rotation-storage effects while preserving
the original native limits and checking every actual changed export against
the full declared geometry population. Adding more times alone has not solved
this failure, and reducing a proposal fraction does not reliably remove its
stored acceleration violations. The existing storage-cell search handles
translations, so it must not be presented as a rotation-storage solution.

## Limits

These are numerical source/decoded-pose and sampled geometry checks. They do not
establish continuous-time collision safety, engine playback, action correctness,
realism or animator cleanup time. There is no new generation, model training,
changed checkpoint, held-out use or quality approval. The wider project goal
and its acceptance gates remain unchanged.
