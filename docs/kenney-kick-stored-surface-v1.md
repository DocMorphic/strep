# Surface correction from a stored-feasible start

The explicit stored-key continuation now supports an actual surface proposal
without changing the original source motion or its limits. One development
kick accepts a small exported step, but still fails floor geometry. The largest
continuous-feasible proposal remains under a separate storage-repair study;
none of these assets is approved for release or selected over the original.

## Original reference and complete checks

The start is the separately replayed [native storage correction](kenney-kick-position-storage-v1.md).
The [continuation state](native-storage-continuation-v1.md) retains its 72 controls
and eight absolute Float32-neighbor corrections. Four existing left-leg tracks,
30-degree track bounds, a 0.22-m displacement bound, preserved endpoints and
frozen root remain. The 120-Hz source-rate clock and all four cap arrays exactly
match the original source; the 1e-5 rate tolerance is unchanged.

One surface-vector iteration uses trust 0.02, difference step 0.001,
minimum-envelope plane guidance and no restoration. Every export receives
strict authoring/payload checks, all 107,527 original native conditions and the
complete floor population: 2,017 times, 1,029 referenced vertices and 1,604 faces,
with the same 5-mm allowance. The solver reports `AlmostSolved`; actual decoded
checks, rather than that solver label, determine acceptance.

## Surface proposals and fresh storage screen

The optimizer retains eleven export records: start, nine proposed fractions
and final. The accepted fraction is 1/256 (`1-8`). The peak changes from
49.500702 mm to **49.486447 mm**, a reduction of only **0.014255 mm**. Geometry
still fails at 233 of 2,017 times. This is a reproducible accepted step, not a
meaningful floor repair or usable animation.

A separate guarded screen freshly decodes every saved GLB, reproduces its
recorded worlds/residuals exactly and checks the corresponding unrounded
intended curves against all original native rows.

| Export | Fraction | Stored native failures | Unrounded native failures | Peak floor penetration (mm) |
| --- | ---: | ---: | ---: | ---: |
| Start | 0 | 0 | 0 | 49.500702 |
| `1-0` | 1 | 12 | 2 | 45.551435 |
| `1-1` | 1/2 | 9 | 0 | 47.600935 |
| `1-2` | 1/4 | 6 | 0 | 48.569589 |
| `1-3` | 1/8 | 5 | 0 | 49.039846 |
| `1-4` | 1/16 | 8 | 0 | 49.271452 |
| `1-5` | 1/32 | 1 | 0 | 49.386376 |
| `1-6` | 1/64 | 4 | 0 | 49.443608 |
| `1-7` | 1/128 | 1 | 0 | 49.472180 |
| `1-8` and final | 1/256 | 0 | 0 | 49.486447 |

Seven rejected proposals pass before Float32 storage and fail afterward. The
full fraction also fails two unrounded rows, so its rejection cannot be
attributed entirely to storage. The screen independently checks native motion;
its geometry values are retained producer receipts, not a new geometry query.

## Largest continuous-feasible proposal

Proposal `1-1` improves the starting peak by about 1.900 mm and fails floor
geometry at 232 times. Its nine stored native failures motivate a bounded
one-neighbor search with fixed continuous controls. Eight stages with up to
eight probes per stage export 25 records including the start: 24 actual neighbor
exports. All eight stages select a merit improvement, ending with 16 corrected
components and **three remaining native failures**. The normalized positive
residual maximum ends at 3.7414701e-7. Every export retains the same
47.600935-mm floor peak; root error is zero throughout. Exhausting this finite
budget does not prove no allowed storage solution exists.

The surface trial, fresh storage screen and first larger-step search complete
within the unchanged resource policy. Their final execution observations are
324.609 s, 92.625 s and 389.016 s; all **337, 109 and 401** recorded resource
observations replay with matching bindings. Raw outputs remain under
`reports/kenney-kick-stored-surface-v1`,
`reports/kenney-kick-stored-surface-screen-v1` and
`reports/kenney-kick-larger-stored-step-v1`.

The seeded continuation under `reports/kenney-kick-larger-stored-step-v2`
finishes after two of its four allowed stages, testing four neighbor exports
plus its start. Eighteen corrected components now pass all 107,527 original
native conditions. Across both searches there are 30 export records, including
the repeated continuation start, not 30 distinct motions. Continuous controls,
source caps, root and endpoints remain unchanged. Geometry still fails at
232 times with the same 47.600935-mm peak.

A separate worker reconstructs all 18 corrections directly with scalar
Float32 `nextafter`. Fresh decoding reproduces every recorded world matrix and
native residual, every cap array and the rate clock. Root error remains zero
at all 2,017 times. An appended unapproved animation at index 1 retains every
original animation and the binary prefix, with identical complete sampled
poses. A new complete geometry query reproduces the still-failed floor samples.
This uses the shared sampler/cap/geometry methods; it is not independent engine
or human quality validation. The continuation and reconstruction finish at
95.437 s and 37.719 s execution; all **112 and 55** resource observations replay.

Two further surface iterations from this independently replayed larger state
are running under `reports/kenney-kick-stored-surface-v2`, retaining the same
original reference and fixed 18 corrections. Record their terminal outcome
before drawing a conclusion. No checkpoint, training data, generation, engine
import, human rating, cleanup-time result or release gate is changed by these
development studies.
