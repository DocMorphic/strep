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

## Separate diagnostic

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
