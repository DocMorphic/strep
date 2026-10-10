# Contact solver conditioning and rejected-point evidence

The verified 0.03 continuation remains the diagnostic motion state described in [the matched search comparison](contact-search-comparison-v2.md). Its second local iteration stops because an `AlmostSolved` conic point fails the unchanged original step-bound check. A solver status does not establish a usable proposal or infeasibility.

Inspection of that archived zero-margin subproblem finds 525 controls, 1,068 scalar rows and 2,265 norm cones. Exactly 727 norm cones duplicate another cone's complete offset, Jacobian and effective radius; 1,538 distinct cones remain. There are no constant norm cones or fixed control bounds. Earlier margin attempts fail step-bound, epigraph or complete affine checks. This identifies a conditioning experiment, not the cause of the failure.

A predeclared local experiment compares the original matrix with elimination of byte-identical norm-cone blocks. Every omitted block must exactly match a retained original block. All original scalar rows, control bounds, vector checks, descent and epigraph checks remain in the final replay. No approximate deduplication, tolerance changes, native pose edits or automatic promotion are permitted. The first two guards defer without starting a child after 600.766 and 600.859 seconds; all 595 observations from each independently replay. Both raw deferrals remain immutable. A third attempt completes under the unchanged 2 GiB estimate plus 600 MiB reserve: 11.609 guard seconds, sampled peak 409,604,096 bytes, thirteen independently replayed resource observations.

Both solves return `AlmostSolved`; both fail the original step-bound check. Independently clipping to the original bounds still fails complete scalar, vector and epigraph checks. Exact duplicate removal reduces residuals but does not produce an admissible start:

| Original-model measurement | Full cones | Exact duplicates removed |
|---|---:|---:|
| Maximum raw step-bound excess | 4.399e-8 | 1.209e-8 |
| Minimum clipped scalar slack | -2.033e-7 | -5.762e-8 |
| Minimum clipped vector slack | -3.296e-7 | -8.988e-8 |
| Predicted worst violation | 1.841481838 | 1.841481992 |
| Proposed epigraph | 1.841481459 | 1.841481888 |

The final independent audit reconstructs every original matrix entry, verifies the exact duplicate map and checks both points against the complete original problem. Its first version fails because one independently summed gradient coefficient differs by 1.137e-13. That failure remains recorded. Version two separately verifies the reconstructed gradient within 1e-12, then uses the archived gradient to bind the actual matrix exactly; motion/solver acceptance tolerances remain unchanged. The successful audit guard completes in 68.110 seconds, including admission, with sampled peak 348,422,144 bytes and 69 independently replayed resource observations. No deduplication API or clipped-point fallback is adopted, and no native pose proposal is retained.

Private receipt digests: study `096b5383eb577bb8e9201de0438d4f79533030937a85872a102f6ff90a195145`; independent numerical audit `b649b87d3020382e4f37c0c19db03dcba29f17f39ae928dfe3eadbfddce77a51`. This exposed development subproblem is not held-out evidence.

`scripts/geometry_conic_start.py` now preserves finite complete solver coordinates from each invoked primary/secondary phase, including rejected points and unavailable statuses. Invalid/nonfinite points retain shape and failure metadata with no numeric payload, so NaN/Infinity cannot enter the immutable archive. These observations never provide a fallback start. The existing checks alone decide whether a proposal is usable; the existing nonlinear, tangent, saved-pose and full-interval checks still decide retention.

Replay validates phase population, status, primary iteration count and point shape/finite values. It binds accepted clipped coordinates and epigraphs back to their observed raw solver points. Failed observations remain diagnostic records rather than acceptance or optimality certificates. Older reports without the new observation schema still replay. Exact archive transport retains readonly numeric arrays, including rejected coordinates.

**220 focused checks pass in 8.15 seconds** across conic starts, conic fitter integration/replay, protected inequality steps, proposal callback derivatives and archive transport. Coverage includes false solver success, rejected secondary points, nonfinite/malformed coordinates, unavailable statuses, altered phase/status/shape/epigraph/points, missing observations, readonly archive round-trip and legacy reports. The test supervisor completes in 12.672 seconds with a sampled peak of 113,455,104 bytes; all 14 resource observations independently replay. This source-only check uses a separate 512 MiB estimate plus the same 600 MiB reserve. It does not reduce the full-study requirement.

No model generation/training, new motion retention, contact pass, dynamics, engine playback or human-quality result follows from the reporting change. Coverage remains 14/21 unique attempted windows, physical/keyed contact passes 0/62, all fourteen release capabilities unapproved and 19 inventory gaps open. The project-wide goal remains active.
