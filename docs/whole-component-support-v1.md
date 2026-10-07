# The remaining collision is in the motion path

The [storage-corrected event half](grouped-storage-correction-v1.md) passes original motion/contact/reference checks and positive-separation guards, but its full scene still has 29,642 proper crossing records. A complete component diagnostic now distinguishes the hand-contact instant from the surrounding path.

At the authored contact time, approximately 0.500000015 seconds, the complete hand components have a positive signed support gap of 9.679618 micrometres and zero recorded proper crossings. The worst signed component gap is instead -26.987298766 mm at approximately 0.892708376 seconds, during recovery. That time is absent from the preceding nine guide frames. Across all 1,673 original samples, the negative-gap mask exactly matches the recorded crossing mask: 1,575 negative/crossing samples and 98 positive/non-crossing samples. All recorded crossings remain on the same complete source-index components; no actor triangle is removed from the original gate.

This signed support gap is a different quantity from maximum partner vertex-containment depth, which remains 4.680554928 mm. A vertex-depth measure can be small while component interiors intersect through faces and edges. The new number is a projection-based component guide, not a replacement penetration tolerance, an independently certified collision predicate, or an exact continuous-motion distance.

## Complete support directions and rows

`scripts/native_convex_component_support.py` accepts two complete, closed, consistently wound, connected convex triangle components under explicit Float64 diagnostic checks. Every input vertex must be referenced; incomplete surfaces, nonconvex components, degenerate triangles and exhausted budgets are rejected. Either consistent winding direction is supported. Callers must authenticate full source-index membership; matching coordinates alone cannot establish it.

Candidate separating directions come from both components' triangle normals and every pair of topological edges, with both signs. The method follows the face-normal/edge-cross-product separating-axis construction described by [Geometric Tools](https://www.geometrictools.com/Documentation/DynamicCollisionDetection.pdf). Triangulation diagonals add candidate directions without deleting actual edges. Near-parallel directions are explicitly recorded. This implementation retains the whole declared candidate population rather than searching a chosen face subset.

For the measured fixture, each component has eight vertices, twelve triangles and eighteen topological edges. Each sample therefore declares 348 raw directions and a 696 signed-direction budget. For every tested unit direction `n`, the gap is:

```text
min(left vertices dot n) - max(right vertices dot n)
```

The largest gap selects a direction. All 64 left/right vertex-pair rows are retained along that direction; their minimum represents the same support condition. The difference between pairwise and interval arithmetic is recorded, without using it as a motion or collision acceptance allowance. Convexity checks, near-parallel thresholds and Float64 rounding prevent treating this helper as an exact collision certificate. The original complete-mesh gate remains decisive.

The fixture's components are identified from complete source-index connectivity, with all eight vertices rigidly bound by unit skin weight to source node 8. The source name `test_LeftHand` is a label, not a verified anatomical palm. Complete source meshes remain present in every recorded scene comparison. General imported character surfaces may not have this convex rigid structure; the helper rejects unsupported component shapes rather than substituting bounding boxes or claiming general character coverage.

## Contact normals do not explain an infeasible event

The existing area-weighted winding-normal calculation at the authored corner vertex gives approximately 18.896857835 degrees opposition error in the current pose and 16.790967184 degrees in the original reference. Three permitted rotation tracks per actor each have a five-degree reference limit. Their combined ideal rigid-rotation triangle-inequality budget is 30 degrees, yielding a zero lower bound on the achievable opposition error. This bound therefore does not establish orientation infeasibility. Mean corner normals are also not inferred palm normals. No new normal condition or anatomical judgment is added to the contact contract.

## Validation and next correction

The diagnostic reconstructs complete skin points from authenticated saved worlds at all 1,673 original scene samples. It samples two reference contact poses for the normal comparison, but generates no new edited curve, derivative stencil, or full-scene collision audit. The separate original-context reader reconstructs component membership, unit-weight binding, every face/edge candidate, all 64 pair rows, axis selection, arithmetic discrepancies, all crossing-mask identities and the corner-normal/rotation-budget diagnosis without calling either diagnostic producer API. Shared skin and Float64 arithmetic remain in use; there is no exact or global pose-feasibility claim.

All 22 focused tests pass. They cover volume overlap, touching, diagonal separation despite overlapping axis-aligned bounds, an edge-cross-only separating case missed by every face-normal direction, reversed winding, rigid transforms/reindexing, complete topology/resource rejection and input preservation. The tests are registered once in the source workflow. Hosted CI success is unverified.

Next explicitly branch from the verified motion-passing storage-corrected pose and capture fresh native/material/full-skin/guard models. Retain prior guide times and add the newly identified worst component-gap time; evaluate complete component support deficits alongside original hard motion, contact, depth and separation conditions. A desired component clearance must respect the existing 20-micrometre point-contact tolerance at the contact event. This turn proposes no new motion and promotes no internal anchor. No derivative at the previous pose is reused as though it belonged to the corrected pose.

Raw observations and readers stay in ignored `reports/`. Original assets remain selected, all fourteen release evidence arrays remain empty, and the full-project goal stays active. No arbitrary-action semantics, production anatomy, engine import/playback, animator review, cleanup-time or release approval follows from these fixture diagnostics.
