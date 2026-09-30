# Fixed-axis refinement of swept triangle boxes

Overlapping axis-aligned boxes do not imply that the triangles inside them
intersect. `swept_triangle_separation.py` adds a sufficient projection test for
triangles whose vertices remain inside the movement balls supplied by
`SkinMotionBounds`. It is a standalone diagnostic; the completed adaptive audit
keeps its original implementation and results.

For any fixed unit direction, each vertex projection lies within its center
projection plus or minus its motion radius. A triangle's projection lies
between the minimum and maximum of these expanded vertex projections. If the
two expanded intervals are separated in either order, the two moving triangles
cannot meet during the interval under those input bounds.

Candidate directions include Cartesian axes, the two center-pose triangle
normals, cross products of their edges, and in-plane edge normals. The directions
remain fixed; no assumption is made that the triangles keep their orientation.
Missing a useful direction produces an unresolved result, never a collision
claim. The code accounts for the computed direction norm, uses an explicit
128-machine-epsilon projection reserve scaled to coordinates/radii, and retains
the existing 1e-8 m geometric tolerance. This is floating-point sufficient
separation, not exact predicates or a new quality threshold.

The R-tree counts every swept-box candidate. A declared candidate budget can
leave the entire query unresolved before projection. Otherwise pairs are tested
in bounded batches. The first batch containing an unseparated pair stops the
test with explicit tested and untested counts. Only complete separation of every
candidate permits a surface-separation result. No containment, self-collision,
full-clock or animation-quality approval follows.

Twelve new tests cover diagonally separated triangles with overlapping boxes,
motion-radius expansion, touching/intersecting triangles, actor/winding/rigid
transform invariance, sampled vertex-ball perturbations, large coordinates,
exact complete pair counts, batch early exits and invalid budgets/data. All 829
minimal public Python checks pass.

## Actual unresolved-interval probe

The unchanged full-clock adaptive study reached its original depth limit in
root 37, [1.8411632776, 1.8912750483] seconds. Its complete terminal partition
contains sixteen unresolved intervals after 31 evaluations and 33 inspected
poses. That record is retained at
`reports/adaptive-skin-full-audit-v1/interval-037.json`, SHA-256
`c4003244e7de25a851e80110f63431f8c67699d163221fce4b5373b0ae3a5048`.

A small read-only probe uses one already observed unresolved interval,
[1.86621916294, 1.86935114861] seconds, with the exact same clips, placements and
skin movement bounds. It finds 685 swept-box pairs. The first 256-pair batch
contains unseparated pairs, so the result remains unresolved and 429 pairs are
explicitly untested. This does not replace or modify the full-clock study.

For its sixteen retained unresolved examples, the zero-radius center-pose test
finds separating margins of 2.784591 to 4.457293 mm. Restoring the actual movement
balls gives best margins of -1.717603 to -0.106452 mm. Thus merely testing more
triangle directions does not resolve these examples: the independent movement
balls still overlap. This diagnoses sixteen retained pairs, not the entire
685-pair population. It does not imply an actual between-pose intersection.

Next investigate bounds that retain directional and relative motion information,
rather than inferring that additional pose samples or looser tolerances establish
clearance. Any tighter bound needs analytic fixtures, actual decoded replay and
the original full-clock population. Keep unresolved cases explicit.

Local evidence:

- Probe: `reports/swept-triangle-probe-v1/result.json`, SHA-256 `ca2281b2a8ad1f1c9a1ecf01e887dfd0034113233169c93da0a22a9f491d1083`.
- Intervals: `46c6c64cc5918200a42caad3860d343aadad3510241a812d9bdced59689508bc`.
- Sixteen-pair diagnostic: `reports/swept-triangle-probe-static-diagnostic-v1.json`, SHA-256 `d2f1d23d0eb1bbf3812955017095f46b48913e40f398368bcb5bd3db93c5753a`.

```powershell
.venv/Scripts/python.exe scripts/audit_swept_triangle_separation.py reports/swept-triangle-probe-protocol-v1.json reports/<fresh-output>
```

No animation edit, model training, held-out use, Studio replacement or release
approval is claimed.
