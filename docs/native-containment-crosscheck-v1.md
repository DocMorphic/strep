# Cross-checking native mesh containment

The 30-degree finger-edit high-five pose is rejected. Its legacy partner
evaluator reports a 7.803029-mm maximum signed depth at actor A vertex 17307,
dominated by RightHandIndex2. A fresh query on the exact saved meshes reproduces
that positive signed distance, but ray parity says outside and the complete
signed solid angle gives winding 1.546103e-17, effectively zero. The nearest
target triangle is 29766, between Index2 and Middle2 skin regions.

Exhaustive closest-triangle search returns the same triangle and distance.
The triangle is not numerically collapsed: edge lengths are 3.584, 3.921 and
5.783 mm, and twice-area is 1.380684e-5 square metres. A local overlapping-box
search finds no proper or coplanar-area self-crossing involving that triangle;
this limited query does not exclude self-intersections elsewhere.

The other directional peak, B vertex 17040, has signed distance 0.083357 mm,
ray containment true and winding approximately one. Thus the disagreement
is not a blanket sign-convention reversal. The exact cause of the first
disagreement remains unresolved. Closed topology, consistent winding and
positive total volume do not establish a non-self-intersecting solid.

## Diagnostic and native scene integration

`scripts/native_containment_crosscheck.py` reports unsigned distance, the
unchanged Trimesh signed-distance observation, ray parity and complete
solid-angle winding. It classifies a point as inside or outside only when the
three sign diagnostics agree. Near-surface and disagreeing queries remain
unresolved for acceptance. It never silently changes an archived measurement
or turns agreement into collision certification.

The method accepts 1–32 points, at most 250,000 vertices and 100,000 complete
original triangles. It streams all faces in blocks of 2,048 per point, with
compensated accumulation between blocks. No triangle or point is sampled away.
It requires closed, consistently wound, positive-volume topology but explicitly
leaves self-intersection checks unfulfilled. Resource-guarded execution remains
necessary; input bounds do not guarantee third-party peak memory.

Thirteen tests cover analytically known box queries, rigid transformations,
surface ambiguity, disconnected components and gaps, overlapping outward
shells with winding two, and crossing inward/outward shells with positive total
volume but contradictory local sign and global winding. The last case
reproduces the relevant disagreement without downloaded character data.
Malformed, open and oversized requests reject. The guarded tests pass in
18.172 s at 96,059,392 sampled bytes; all 20 resource observations replay.

This adds a diagnostic API, not a replacement geometry evaluator or a new
release approval. Original source modules, meshes, pose observations and
reported metrics remain unchanged. Complete source-vertex audits, treatment
of ambiguous surfaces, self-collision, motion clocks, engine observations and
human review are still required before promotion.

The thirteen source checks also pass on hosted Ubuntu (0.56 s) and Windows
(0.94 s), run 38976063117 at source b0beef2. The actual saved witnesses are
classified unresolved for A17307 and inside for B17040; the guarded witness
replay completes in 18.250 s at 155,844,608 sampled bytes (20 observations).
Both resource traces replay independently. Inventories contain 550 Python/
45 Node suites, with 114/five in the contact subset, not full-inventory passes.


## Complete source populations at the rejected pose

A separate shadow audit accounts for all 18,056 source vertices in each
direction at 2 s. The unchanged numerical convex-hull screen excludes 17,444
A vertices and 18,032 B vertices; every retained query uses every original
target triangle. This is conservative numerical screening, not exact geometry.

Of A's 612 retained vertices, 607 agree outside, one agrees inside at
0.030812-mm unsigned distance, and four are unresolved: 3067, 12102, 17307 and
17316. Of B's 24 retained vertices, 23 agree outside and one agrees inside at
0.083357 mm; none are unresolved. No retained query is near-surface at the
1e-7-m threshold. Arrays preserve every state, raw sign, ray result and winding;
nonqueried hull-excluded entries have explicit state zero and NaN distances.

The guard completes in 36.531 s at 245,948,416 sampled bytes, with 38 resource
observations independently replayed. Source hashes remain unchanged. This
completes the two source populations at one pose, not a whole-clock geometry
audit. Four unresolved vertices, existing surface records and failed contact
conditions prevent promotion. The next check is complete self-surface and
local topology analysis around the disputed index/middle-finger region before
changing any containment evaluator or repeating curve optimization.

All twelve retained inter-actor surface records are classified as proper
crossings, independently of the disputed signed-depth witness. Resolving that
containment disagreement therefore cannot turn this pose into a passing one.

Complete [self-surface diagnostics](native-self-surface-v1.md) now show
additional self-crossings in the rejected edited mesh. All 1,457 reported
source/edited pairs have exact represented-triangle interior witnesses. This
strengthens the rejection; it does not retroactively alter legacy metrics or
prove the exact cause of the local sign/winding disagreement.

## Native scene consensus method (2026-10-21)

New native scene and imported-mesh scene audits use
`strep-containment-consensus-v1` for point containment. The existing signed
distance, ray parity and complete solid-angle winding diagnostic now supplies
actor/actor, actor/prop and prop/prop vertex queries and primitive-center queries.
Convex-hull rejection remains a conservative broadphase; it does not fill the
hull or replace the target triangles. Each retained batch has at most 32 points.
The original depth limits and query populations are unchanged.

Away from the declared surface tolerance, inside requires positive signed
distance, inside ray parity and winding approximately one. Outside requires
negative signed distance, outside parity and winding approximately zero.
The winding tolerance remains 1e-5. Near-surface points and disagreements are
unresolved. A vertex population with any unresolved query returns
`available=false`, preserves the vertex identity and all diagnostic values,
and omits maximum-depth/count fields. Native scene conditions fail and the
character fitter's local depth guard cannot accept an unavailable comparison.
Primitive-center containment also fails on unresolved results.

This method does not infer union semantics for overlapping shells. Nested
positive shells with winding two remain unresolved. Reversed, open or
numerically degenerate target geometry cannot supply a passing containment
measurement. Agreement at a query point is **not** evidence that the whole
mesh is free of self-intersections. Complete self-geometry eligibility and
nonregression enforcement remain unfinished; fitting the retained humanoid
case remains deferred.

Reports carry the method identifier, and native scene, fitting and journal
producer bindings include the diagnostic implementation. The local depth
comparator rejects mixed legacy/consensus reports. Older reports, their original
allowances and archived implementations stay intact. Both original and candidate
must be evaluated afresh under the same method before a new comparison. Legacy
standalone signed-distance research scripts have not been rewritten and are
not evidence of passing the new native method.

Validation: all 217 checks in the containment, native scene, imported-mesh
scene, local-depth comparison and both geometry-journal suites pass. They
cover complete resumed/direct report equivalence, source pinning, corruption,
surface ambiguity, the measured overlapping-box case, isolated analytic
controls, translations, batching and preservation of the full declared
near-surface tolerance band. The final guarded run and two earlier passing
epochs remain under ignored `reports/containment-consensus-*`; earlier source
snapshots match their recorded hashes and remain distinct from the final fix.

The final run also replays panel vertex zero at 2.1375 s against two saved
humanoid surfaces. The original query is excluded by the expanded convex hull.
For the edited seed, signed distance is -1.715451 mm, ray parity is inside and
winding is approximately one; the new method returns unavailable and no depth.
This checks one point per pose, not the full clip or surface population. No
animation is adopted, no original allowance changes, and no release gate is
approved by these tests.
