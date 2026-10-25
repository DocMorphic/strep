# Shoulder direction and constant-edit study

The worst-pose shoulder search found a pose with zero proper crossings, but
applying those fixed local rotation edits throughout the wave failed at 12 of
17 declared geometry times. This is not an accepted clip repair. Lower total
crossing counts conceal many new collisions, so neither aggregate improvement
nor smooth corrections are sufficient acceptance criteria.

## Pose experiment

Starting from the first bounded 25-degree reference-guided proposal in
[the preceding study](wave-self-repair-pose-v1.md), freeze every control except
node 17's local shoulder rotation. At 2.2312500178813934 seconds, evaluate the
parent, zero shoulder edit, and all 26 normalized nonzero vectors in
`{-1, 0, 1}^3` at each of 12.5, 25 and 35 degrees: 80 trials total. Use the
previously declared 1e-5 relative fitting reserve and retain every full-surface
audit, including ambiguous records. No upper-arm exclusions are permitted.

Rank by proper-crossing count, introduced pair count, maximum crossing segment
length, then trial index. Segment length is not penetration depth.

| Selection | Trial | Shoulder edit | Proper pairs | New pairs |
| --- | --- | --- | --- | --- |
| Best within original 25-degree cap | 28 | 24.99975 degrees, direction (-1,-1,-1) | 9 | 3 |
| Best with explicitly expanded 35-degree cap | 58 | 34.99965 degrees, direction (-1,0,0) | 0 | 0 |

The latter still has 4,750 ambiguous surface flags. It exceeds the original
cap and is a separate diagnostic experiment, not a retroactive passing result.
Its floor depth is 2.69896 mm. Zero proper pairs at one pose establishes neither
anatomical quality nor feasibility throughout the clip.

## Constant local edits over the clip

Apply trial 58's fixed local rotation offsets to nodes 14–18 at all 120 keys.
Node 19's offset is zero and is omitted. Root translation values remain exactly
unchanged. Both endpoints are explicitly editable and require later transition
review. Serialize and reload the GLB before evaluation. The source is the
previous floor-corrected wave, SHA-256
`7678f1bafd355cf3f368c0d2d263e033f1a65ecb657553fa5517871f48d748f0`.

The new experiment declares a 35-degree shoulder cap and 25-degree caps for
the other edited nodes. Native keys, eighth-interval samples and the 960 Hz
clock yield 4,737 unique observations:

- Floor depth: maximum 4.821543 mm, passing the declared 5 mm limit.
- Rotation edits: all within the new declared caps after serialization.
- Intended versus decoded skin: maximum error 0.000068287 mm.
- Consecutive local correction change: maximum 0.000000251169 degrees,
  below the declared 0.001-degree limit.

Full triangle geometry is checked separately at 17 evenly spaced times, not
all 4,737 observations. Proper-crossing counts in time order are:
`68, 23, 0, 0, 7, 0, 56, 4, 9, 0, 52, 0, 4, 26, 18, 60, 61`.
Five sampled poses have zero proper pairs; twelve fail. Across these times,
proper pair observations fall from 588 to 388, but 313 of the new observations
are pairs absent from the source at the corresponding time. These are summed
observations, not unique pairs or a perceptual quality score.

No engine replay, action-preservation review, dense self-surface certification,
or release approval is claimed. The original remains selected. No model was
trained, and no candidate was promoted by this experiment.

## Verification and retained evidence

Ignored development-checkout reports retain the following evidence:

- `reports/wave-shoulder-directions-v1/`: request, guarded worker, all 80 pose
  arrays and complete surface audits, and selected-pose location tables.
- `reports/wave-constant-arm-clip-v1/`: independent reconstruction of all 80
  parameter/pose populations, full geometry replay of both selected poses,
  export receipt, candidate, dense observations and 17 complete surface audits.
- `record-verification.json` in the latter folder: verification of 1,807 bound
  inputs, candidate/observation/surface hashes, recorded maxima and decisions,
  and pair-set comparison with the previously audited source at identical times.
  This last step replays stored evidence; it does not recompute geometry.

Both guarded workers completed. The clip worker peaked at 132,161,536 bytes
across 102 resource observations. Production code is unchanged; this follow-up
does not claim a new test-suite or hosted CI run.

## Next experiment

Use temporal windows with distinct arm/shoulder proposals at the failed times,
then enforce correction-change bounds across adjoining windows. Reject new
proper pairs at each comparison time, preserve floor and authored contacts,
and validate serialized interpolation between keys. Keep the original motion
and rejected candidates. A smooth schedule cannot be accepted from the five
clear poses alone: newly crossing pairs, endpoints and action preservation
must all be checked. Wider action/rig/object/partner validation remains required
by the whole-project goal. Related research and its limitations are recorded
in the [source ledger](source-ledger.md).
