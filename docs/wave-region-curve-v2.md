# Wrist search and temporal collision limits

Increasing the wrist's local search radius clears the wave's original target
frame, but three neighboring sampled times still contain proper crossings.
Independent export and replay confirm this improvement and its remaining
failures. This is a rejected development candidate, not an accepted animation.

## Protocol

Continue [the coupled region study](wave-region-curve-v1.md) with the same
immutable input and original reference, right-arm nodes 14–16, native keys
51–60, 46 geometry times and 439 dense motion times. Increase only the wrist's
residual proposal radius from five to ten degrees. The other two proposal
radii remain five degrees. Original-relative 25-degree total allowances,
40-degree/second correction speed and 5 mm floor depth remain unchanged.

Rescale the previous proposal's coordinates to preserve its actual rotations.
The warm start matches its previous target pose and skin exactly, including
six target crossings. It does not become the reference for total edit limits.
Keep every vertex in both moving regions and all 137,475 projection pairs per
geometry time. Retain the first optimizer iteration and every tenth iteration
as local checkpoints. The desired plane clearance remains 3 mm.

## Observed result

| Observation | Previous coupled fit | Expanded wrist search |
| --- | ---: | ---: |
| Target proper-crossing pairs | 6 | 0 |
| Failed geometry times out of 46 | 5 | 3 |
| Proper-pair observations across those times | 65 | 44 |
| Newly introduced pair observations relative to input | 65 | 44 |
| Peak sampled correction speed, degrees/s | 39.996082 | 39.996025 |

The remaining failures occur at approximately 1.833333, 1.841667 and 1.850000
seconds, with 18, 18 and eight proper-crossing pairs respectively. All 44 pair
observations differ from the input's corresponding pairs. They remain failures;
clearing the original target frame does not clear the window.

Peak sampled floor depth is 4.643784 mm. Maximum original-relative right-arm
rotations are approximately 24.998217, 24.997500 and 10.119359 degrees. Predicted
and exported skin positions agree to 9.40e-16 m. The target's minimum projected
gap becomes positive at 2.058959 mm, below the desired 3 mm guidance clearance.

SLSQP stops after 139 iterations and 325 objective evaluations with a positive
directional derivative for line search; optimizer convergence is not claimed.
The guarded worker completes in approximately 992 seconds including admission,
with sampled peak process-tree memory of 146,427,904 bytes. Its 969 resource
observations replay successfully.

## Independent validation

The separate replay verifies the bound input/proposal/checkpoint files,
re-exports the proposal, checks unchanged unpermitted channels and keys,
recomputes all 439 scalar motion observations, and repeats complete before/after
surface audits at all 46 geometry times. The exported GLB is byte-identical:
`c6fab9ef496842d7cebcb64a91b1fa7dd946caa71df099af6bcf7ad2f6b34248`.
All sampled motion bounds and all three geometry failures are reproduced.
The replay's 147 resource observations also verify, for 1,116 observations
across the producer and this replay. No geometric tolerance or flag exemption
changes. These sampled results do not certify continuous-time collision freedom.

Reports remain in the ignored development checkout as `wave-region-curve-v2`
and `wave-region-curve-replay-v4`. Existing raw results remain immutable.

## Next experiment

The averaged separation objective can improve while leaving collisions at
individual times. The next bounded experiment adds a smooth conservative
region-separation inequality at every one of the 46 geometry times, retaining
the 3 mm guidance clearance, complete vertex sets and both regions' derivatives.
It checks directional derivatives before fitting and retains the same edit,
speed, floor and resource limits. Complete exported mesh audits still decide
whether collisions remain; a failed finite search does not prove infeasibility.

The constraint implementation passes three directional derivative probes across
all temporal floor/separation rows: maximum scaled discrepancy 1.833e-8 against
a 1e-5 check limit. The warm start has six deficient separation rows and a
minimum smooth gap of -9.094478 mm. This stronger guidance is distinct from
the three times with measured mesh crossings.

Two guarded attempts stop when available system memory falls below the existing
600 MiB floor, including one retry with 30 seconds of stable admission. Both
resource traces replay (74 and 80 observations). Initial optimizer checkpoints
remain local. Neither attempt produces a completed fit or supports an
infeasibility claim. Resume in a fresh report folder when memory is available;
preserve these interrupted attempts and repeat independent exported checks.

Full-clip validation, action/style preservation, engine checks, human review
and broader action/rig/object/partner evaluation remain outstanding. No release
capability is approved by this study.
