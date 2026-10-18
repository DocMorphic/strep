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

Calls accept 1–32,768 source vertices, 4–32,768 target vertices and
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

Twenty new source tests plus the existing 87 pass locally: **107 cases, zero
failures or skips**. They include finite-difference checks for both complete
input Jacobians, coupled descent followed by fresh geometry measurement,
translation balance, rigid-transform invariance, chunk equivalence, a nonconvex
mesh hole, stale-input detection, owned topology/receipts, invalid geometry and
explicit unsupported second derivatives. The original scene, skin, conditioning
hook, retention and motion-envelope regressions remain included.

Local evidence: `reports/mesh-penetration-gradient-tests-v1`. A collapsed-mesh
rejection triggers a Trimesh zero-volume warning; the previous tensor-scalar
test warning also remains. Neither is a passing motion-quality claim.

Next verify this derivative through native skinning on the recorded high-five
overlap, then connect it to permitted scene controls and full output validation.
Vertex tests at selected discrete frames do not cover edge-only triangle
intersections, continuous-time motion, self collision, forces, semantic quality,
engine behavior or human cleanup. The whole-project goal and every original
release requirement remain active.
