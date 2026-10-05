# Cylinder penetration bounds before physics integration

Native object animation already exports boxes, spheres and cylinders. Physics release still accepts boxes/spheres: enabling a cylinder collision shape alone would leave its independent overlap audit incomplete. `primitive_penetration_bounds.py` adds the required read-only geometry query for every box/sphere/cylinder pair, with an explicit penetration interval and retained uncertainty. `release_geometry.preview_penetration_bounds` exposes it separately from the existing qualified release path. No model, motion, scene target, source cap or physics policy changes.

```python
import numpy as np
from object_geometry import Geometry
from release_geometry import preview_penetration_bounds

result = preview_penetration_bounds(
    Geometry('cylinder', (.2, 1.)), [0., 0., 0.], np.eye(3),
    Geometry('box', (.3, .4, .5)), [.1, 0., 0.], np.eye(3),
    radial_tolerance_m=.001, maximum_segments=128,
)
print(result['penetration_lower_m'], result['penetration_upper_m'])
```

Positions are primitive centres in a shared metre coordinate system. A cylinder's local Y axis is its length axis; its dimensions are radius and full height. Rotations must be proper rigid matrices within the declared numerical check. Persist the supplied poses, settings and implementation identity alongside any study that consumes this query; the returned dictionary is an in-memory diagnostic, not a source-bound study receipt.

## Geometry and interpretation

For each cylinder, regular inscribed and circumscribed prisms bracket its analytic solid. The outer prism has radius `r / cos(pi/N)` and its vertices are shifted by `pi/N`, placing its side planes tangent to the circle at the inner prism's vertex directions. Doubling N nests both sequences: inner prisms grow, outer prisms shrink. Full height and end caps stay unchanged. The result records per-object radial expansion/inset and segment counts. Resolution increases until the outer radial expansion meets the declared tolerance; exceeding the complete segment budget rejects instead of returning a coarser subset.

Each prism/box comparison evaluates every face-normal direction and every nonzero cross-product of edge directions. Near-parallel nonzero edge axes remain included; no angle cutoff, rounded deduplication or outcome-dependent axis selection is used. This finite polyhedron test follows [David Eberly's separating-axis description](https://www.geometrictools.com/Documentation/MethodOfSeparatingAxes.pdf), section 4. The implementation here is independently written. The nested-cylinder depth construction and refinement claims are this project's derivation, rather than an attribution to that reference.

For overlapping convex solids, the minimum translation needed to separate them equals the distance from the origin to the boundary of their Minkowski difference. Inclusion of the inner/analytic/outer solids gives inclusion of those differences, so their penetration depths bracket the analytic cylinder depth. Complete separating-axis projections compute the prism penetration depths. Positive projection gaps are **not Euclidean distances** and need not be ordered across the different inner/outer direction sets. Only the nonnegative penetration depths follow the inclusion order. The API therefore exposes `penetration_lower_m` and `penetration_upper_m`; its two projection-gap fields retain their narrower diagnostic meaning.

Sphere pairs use the analytic signed distance from the sphere's centre to the other solid, offset by the sphere radius. Cylinder side, cap, rim and interior cases participate. This branch needs no prism and does not consume a segment budget. Box/box comparisons use complete box SAT. These branches preserve the same penetration meaning, including containment.

Float64 arithmetic includes a reported numerical pad, based on the caller's base pad and the relative position/primitive radii. This is **not certified interval arithmetic**. Clear separation, positive penetration and uncertain touching stay distinct; a zero lower bound does not establish separation. These are rigid-pose sampled diagnostics, with no swept/continuous collision, articulated self-collision, engine contact, actor response, anatomical intent or motion-quality conclusion. All certification/physics/quality/release flags remain false.

## Validation and next work

A frozen isolated public-source run passes **87 Python checks in 12.88 s**, including 55 new bound cases and existing geometry, mesh and native object-export regressions. Analytic coaxial cylinder depths, all sphere/cylinder regions, all non-cylinder pair types, touching/separated/contained bodies, rigid-transform invariance, preserved near-parallel axes, complete resource rejection and nested refinement are covered. Twelve rotated cylinder/box and cylinder/cylinder cases compare both prism depths against an independent SciPy convex hull of the full Minkowski vertex population. Eight further fixed seeds check refinement at arbitrary relative orientations. Existing actual tiny GLB export tests retain actor bytes and original object clocks. Source and frozen-copy hashes agree; no vendor/models/downloaded characters, production pose/geometry query, engine, renderer or live Studio are used.

An intermediate run retained a separated-body rejection caused by incorrectly requiring the positive projection gaps to be ordered. The guard now applies to penetration depths, matching the derivation; no acceptance limit was relaxed. A later new analytic test hit Float64 endpoint rounding at the pad boundary. It now checks enclosure and interval width directly rather than requiring a rounded endpoint difference to equal the pad exactly. Both observed failures precede the complete final source check. The early same-phase outer construction was also replaced during review so power-of-two refinement nests the outer prisms; the new independent/refinement tests cover that property.

Next, connect the depth upper bounds and their uncertainty to physics-release overlap checks, install and verify actual cylinder collision shapes/inertia, retain all engine failures and test static/prescribed supports and convex actor envelopes. The existing `require_release_geometry` continues to reject cylinder release at this revision. This mathematical component does not qualify the wider interaction capability. Human review/cleanup and all fourteen release evidence arrays remain absent/empty; the full-project goal stays active.

Frozen source-check receipt SHA256: `f13026cfbbe2e06b29cc2ad2d4ca6d13e86a0d2a605ca82e383dad04eef6d325`. Raw fixtures/checks stay local under ignored `reports/cylinder-penetration-source-check-v1/`.
