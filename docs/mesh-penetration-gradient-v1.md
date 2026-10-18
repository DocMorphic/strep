# Mesh penetration gradients for both characters

Development component, 2026-10-18. This adds a collision observation and its
first derivative; it does not approve an animation or change the selected
reference. The previous paired study showed that improved fixed-point contact
can increase actual body overlap.

`scripts/mesh_penetration_gradient.py` accepts source point tensors, target
vertex tensors and the complete target triangle topology. Its output is a
depth for every supplied source vertex. Convex hulls only reject points outside
the target's hull; retained points query the original triangle mesh. Both
source and target positions receive gradients. Evaluating both directions
therefore permits both characters to participate in a correction, rather than
treating a generated partner as an immovable point target.

The forward measurement uses the same
[Trimesh signed-distance convention](https://trimesh.org/trimesh.proximity.html#trimesh.proximity.signed_distance)
as the existing bounded partner auditor. Inside distances are positive;
Trimesh also treats points within its own near-surface tolerance as positive.
That inherited tolerance is recorded, not removed or presented as exact
arithmetic. No additional physical epsilon or changed acceptance threshold is
introduced. Self-intersecting posed bodies can make inside/outside ambiguous.

At a positive-depth point, the source derivative follows the returned closest
surface point. The opposite derivative is distributed to that triangle's
three vertices using its barycentric coordinates. Each new forward call
rebuilds the target geometry and nearest features. This is a local first
derivative: nearest-feature and inside/outside switches are nonsmooth.
Proposed edits must be remeasured, rather than accepted from a linearization.

The [custom autograd function](https://docs.pytorch.org/docs/2.10/notes/extending.html#extending-torch-autograd)
saves input versions so an in-place edit before backward rejects stale
derivatives. Second derivatives are explicitly unsupported. There is no new
gradient of triangle topology, checkpoint weights or training data.

Calls accept coordinates within ±10,000 m, 1–32,768 source vertices, 4–32,768 target vertices and
4–65,536 target faces. Target meshes must be closed, consistently wound,
outward oriented and nondegenerate; malformed geometry is rejected without
repair or a convex replacement. Queries contain at most 32 points at once.
This bounds simultaneous proximity work, not total runtime.

Owned topology and complete observation receipts retain source/target/topology
hashes, full populations, broad-phase counts, query batches, depth statistics,
barycentric reconstruction error and library conventions. Receipt capacity is
explicit and bounded; exhaustion rejects rather than dropping observations.
The operator has no rig-name or action-name whitelist and works on caller
supplied world-space geometry. It neither authors a valid skeletal pose nor
chooses which frames or body controls may change.

Twenty-four new source cases plus the existing 87 pass locally: **111 cases, zero
failures or skips**. They include finite-difference checks for both complete
input Jacobians, coupled descent followed by fresh geometry measurement,
translation balance, rigid-transform invariance, chunk equivalence, a nonconvex
mesh hole, stale-input detection, owned topology/receipts, invalid geometry and
explicit unsupported second derivatives. The original scene, skin, conditioning
hook, retention and motion-envelope regressions remain included.

Local evidence: `reports/mesh-penetration-gradient-tests-v1` and
`reports/mesh-penetration-gradient-tests-v2`. A collapsed-mesh
rejection triggers a Trimesh zero-volume warning; the previous tensor-scalar
test warning also remains. Neither is a passing motion-quality claim.

## Distinguishing the optimization distance from the auditor

The first real full-skin root-direction probe fails its predeclared 0.1%
derivative check: the discrepancy is 0.821%. It completes without creating a
motion proposal and remains preserved in
`reports/mesh-penetration-gradient-probe-v1`.

Inspection of the pinned
[Trimesh 5.1.0 proximity implementation](https://github.com/mikedh/trimesh/blob/5.1.0/trimesh/proximity.py)
shows that its nearest query can choose between the two best candidates using
normal alignment when their squared distances fall within its tie tolerance.
That returned distance is useful as the existing auditor's observation but
cannot be assumed to form a smooth minimum-distance optimization field.

The default `distance_mode="auditor"` remains unchanged. A separately explicit
`distance_mode="minimum"` now reduces the complete spatial candidate lists to
their minimum Euclidean triangle distances in chunks of at most 4,096 triangles
per point. It uses the original auditor's sign classification; it does not
replace the physical auditor or fix self-intersection ambiguity. Closest
features still switch nonsmoothly, so derivative checks and fresh measurements
remain mandatory. Full auditor depth arrays remain available separately as
owned `last_auditor_depths`; receipts hash both observation arrays and identify
the selected policy. No automatic policy fallback is introduced.

Additional tests check the explicit minimum field against a complete small-mesh
brute-force query, its two-body Jacobians, preserved auditor observations and
policy rejection. The new real-body probe keeps the same finite-difference
step and 0.1% technical check. Earlier failed trials and every physical/motion
requirement remain unchanged.

## Real native-skin derivative and motion proposal

The explicit minimum field passes the same real-body directional derivative
check: relative error **8.9831e-12**, with the original 1e-6 m finite-difference
step and 0.1% technical limit unchanged. Both bodies retain all 18,056 vertices,
36,108 triangles and eight skin influences. The derivative reaches both root
controls through actual native skinning; this is not a loose-vertex deformation.

One fixed 0.5 mm combined translation step, under a declared 1 mm diagnostic
bound, creates two complete 120-frame clip proposals. Local/global rotations,
predicted contact channels and clocks remain unchanged. The original raw files
remain intact. Average squared overlap decreases from 4.152683e-7 to
4.102477e-7 m², about 1.21%, but that objective does not minimize deepest overlap.

Independent raw observation at frame 60 finds:

| Measurement | Original | Proposal |
|---|---:|---:|
| Actual palm gap | 33.282 mm | 33.633 mm |
| Deepest partner overlap | 13.483350 mm | 13.485253 mm |
| Vertices beyond existing 5 mm diagnostic | 180 | 179 |

The proposal still fails the original 30 mm contact tolerance and increases the
deepest tested overlap. Fewer deep vertices or lower average loss does not make
it acceptable. **No output is adopted.** The optimization's ideal Float64
geometry, actual Float32 raw motion and decoded saved-file observations stay
separate; no physical epsilon is added to reconcile them.

The current 111 source cases pass on both hosted operating systems at
`adb4f94e9fba91432f12ff2646d3681ce9209fdb`
([focused run 39126258910](https://github.com/DocMorphic/strep/actions/runs/39126258910)).
Local evidence includes `reports/mesh-penetration-gradient-probe-v2` and
`reports/mesh-penetration-gradient-replay-v2`. The probe completes in
113.563 seconds with a 767,631,360-byte peak under a 2 GiB cap and the unchanged
600 MiB free-memory reserve. The original rejected derivative probe is preserved
with its original source archive and public method revision.

Independent replay covers all four original/proposed exports across
**8,666,880 vertex/frame pairs**, preserving complete raw/saved physical
observations and the original native motion ceilings. Maximum saved skin
component error is 5.756e-7 m. Both candidates fail physical nonregression;
raw and saved paired observations agree that the palm gap and deepest tested
overlap worsen. The replay excludes the new gradient, Torch and sparse-skin
modules. It completes in 175.782 seconds with a 257,814,528-byte peak under a
512 MiB cap. **Partner collision is checked only at frame 60; the other 119
partner frames remain unchecked.** Full pose/floor replay is separate from
complete partner collision coverage.

These tensor tests and the real-body derivative probe run on CPU. CUDA
integration and a complete articulated/time-dependent correction remain
unqualified. The default auditor-field derivative failed this real-body probe;
only the explicitly separate minimum optimization field passes it.

Next constrain worst-case collisions and contacts using permitted articulated
controls, rather than optimizing aggregate overlap alone. A qualified derivative
is only one component of that correction path, not a collision-safe animation
system. Every original output and release requirement remains in force.

Vertex tests at selected discrete frames do not cover edge-only triangle
intersections, continuous-time motion, self collision, forces, semantic quality,
engine behavior or human cleanup. The whole-project goal and every original
release requirement remain active.

The checkpoint `reports/mesh-penetration-gradient-progress-v1` verifies 6,242
current source, archive, asset, data and resource bindings, plus the prior
whole-goal receipt. Three superseded source bindings are checked against their
immutable archives and public `bd5add8` revision, rather than presented as
matches to revised source. Its streaming audit completes in 39.843 seconds
with a 58,003,456-byte peak under 512 MiB. Only goal line 3 and the two permitted
release-matrix progress fields change; all 14 capabilities remain unapproved.
