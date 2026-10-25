# Coupled region separation and sampled correction limits

Fitting across the affected time window removes the previous sampled correction
speed failure, but the wave still intersects itself. At the original target time,
proper-crossing pairs fall from 35 to six. Five of 46 assessed geometry times
still fail. The candidate remains a rejected development result.

## Protocol

Start from the same rejected temporal input and immutable floor-corrected
reference used in [the preceding plane study](wave-hand-head-plane-v1.md).
Only right-arm nodes 14–16 at native keys 51–60 may change. Keep five-degree
residual proposal balls, original-relative total allowances of 25 degrees,
40-degree/second correction speed, and the 5 mm floor allowance. The earlier
failed plane proposal is an initial search point, not a new reference.

At every one of the 46 affected geometry times, include every vertex of the
complete dominant-node hand/head face groups: 65 hand vertices and 2,115 head
vertices. Each time gets its own initially selected separating direction and
3 mm desired clearance. Both regions move with the skin. Average the complete
pair objectives over time and include a complete-body minimum-height row at
each time. The objective retains all 137,475 vertex pairs per time; chaining
vertex gradients through local pose controls avoids a large pair/control
derivative allocation.

The [qualified correction-curve calculation](native-correction-curve-v1.md)
adds original-relative angular and neighboring correction-speed rows at all
439 retained dense times. Native-key limits remain as additional checks.
The fitting reserve is not an acceptance tolerance; saved outputs retain the
original allowances. These are sampled checks, not continuous-time guarantees.

## Observed result

The solver stops after 56 iterations and 85 objective evaluations with a
positive-directional-derivative failure. A better diagnostic candidate passes
the sampled motion bounds, but optimizer success is not claimed.

| Observation | Rejected input | Earlier one-time plane fit | Coupled fit |
| --- | ---: | ---: | ---: |
| Target proper-crossing pairs | 35 | 8 | 6 |
| Failed geometry times out of 46 | 13 | 6 | 5 |
| Proper-pair observations over those times | 437 | 77 | 65 |
| Newly introduced pair observations | — | 77 | 65 |
| Peak sampled correction speed, degrees/s | 24.2563 | 40.135596 | 39.996082 |

All 65 remaining pair observations differ from the corresponding input pairs
and remain failures. The target's six pairs still belong to the dominant
hand/head grouping. No surface flags are exempted.

Peak floor depth remains 4.643784 mm. The largest original-relative right-arm
edits are approximately 24.998275, 24.997500 and 10.119359 degrees. Predicted and
exported skin positions agree to 9.19e-16 m. The minimum target plane gap is
still negative, approximately -1.338 mm, rather than the desired positive 3 mm.
The worker completes in about 471 seconds including admission, with sampled
peak process-tree RSS of 147,705,856 bytes. Its 461 resource observations replay.

## Independent replay

Independent export produces an identical GLB. The first replay stops because
it demands exact equality of overlap lengths computed from model-predicted
and decoded vertices. Their pose/skin agreement is already within 1e-12 m,
and the diagnostic comparison preserves all classifications while lengths
differ at rounding scale. A second replay stops on unset overlap lengths in
ambiguous records. Both failures and resource traces remain archived.

The revised replay keeps every record and requires identical classification,
pair identity and non-length fields, with equal unset values. Numeric overlap
lengths must agree within 1e-12 m, consistent with the existing pose/skin
comparison. The geometric classification tolerance remains 1e-8 m. It then
recomputes all 439 scalar motion observations and every complete before/after
surface audit at the 46 geometry times. The third replay completes and verifies
all sampled motion bounds, unchanged unpermitted channels/keys, all five geometry
failures and all 65 new pair observations. The exported GLB is identical; the
maximum target overlap-length discrepancy is 6.592e-16 m with every classification
unchanged. All 189 successful-replay resource observations verify. Across the
producer and all three replay attempts, 861 resource observations are retained
and replayed. Two verifier failures remain explicit; they are not motion passes.

## Next bounded search

The five-degree residual balls are active for all three edited joints at
keys 54–56. This is a local proposal limit; the wrist still has substantial
room under its original-relative 25-degree allowance. A prepared follow-up
increases only the wrist residual proposal radius to ten degrees, rescales
the warm-start coordinates to preserve their actual rotations, and retains
the original total caps, motion limits, complete time sets and source assets.
It also retains periodic optimizer checkpoints. This is a new finite search,
not proof that a feasible repair exists or permission to relax acceptance.

Reports remain under the ignored development checkout: `wave-region-curve-v1`,
`wave-region-curve-replay-v1` through `v3`, and prepared `wave-region-curve-v2`.
Other clip failures, action/resting-pose preservation, engine checks, developer
and animator review, and broader action/rig/object/partner evaluation remain
part of the full project goal. No release capability is completed here.
