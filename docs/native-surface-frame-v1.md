# Material surface frames in native pose constraints

The high-five's scalar contact landmark is dominated by `RightHandIndex1`.
Matching that point does not constrain palm facing, twist or finger geometry;
the completed anchor study still has extensive finger crossings. Existing
canonical hand-region and posture tools remain available. The new
`scripts/native_surface_frame.py` connects actual skinned material geometry and
its native affine pose derivatives to explicit norm constraints.

## Geometry and authored intent

`measure(points, derivatives, faces, selection)` uses every vertex of an
explicit selection of original triangles. The selection declares triangle IDs,
fixed convex material weights for the contact origin, and two convex material
points defining a proximal-to-distal tangent. Weight order is the sorted unique
vertex order of those triangles. Complete finite derivatives have shape
`[source vertex count, 3, control count]`; at most 96 control columns and a
128-MiB derivative array are accepted. No influences or vertices are discarded
to satisfy this bound.

The normal is the normalized sum of actual posed triangle winding vectors.
The material tangent is projected into that normal's tangent plane and
normalized. All Jacobians differentiate the actual deformed triangles and
material points; no matrix is projected to a rigid pose, and no wrist axis or
dominant joint label substitutes for the surface normal. Explicit minimum
triangle area, normal coherence and tangent length reject collapsed,
cancelling or ambiguous frames. The input geometry is unchanged.

`constraints(frame, target, limits)` supplies three vector-norm rows: origin
position, signed normal direction and signed tangent direction. The target
directions must be unit and orthogonal. A direction's norm-error cap is
`2 sin(angle_limit / 2)`, exactly the unit-vector chord for the declared angular
tolerance. Opposite facing is therefore a failure, even when the two surfaces
share a plane. The material normal's anatomical meaning still requires an
explicitly chosen and reviewed patch.

These rows can join native affine pose derivatives without changing native
curve clocks. Fitting them is not collision, motion-rate, anatomical,
full-clip, engine or quality acceptance. Separate finger authoring and
whole-hand/full-body geometry remain necessary.

## Validation and actual pilot

The first 25 source checks pass in an isolated CPU environment (1.98 s),
including independently differenced deformation derivatives and signed-angle
failures. The guard completes in 18.312 s at 76,316,672 sampled bytes, with 20
observations independently replayed. A subsequent source check composes the
frame derivative with the actual native affine skinner and independently
differences fresh pose evaluations. That added integration check is reported
separately once run; no full-inventory pass is claimed.

The actual pose pilot is a separate experiment at 2 s on the best failed
anchor proposal. It retains the source clips and tests palm origin/facing/twist,
original point contacts, right-hand separation halfspaces, 60-mm joint-world
displacement bounds, and explicit local edit balls: 15/20/30 degrees for
arm/forearm/hand and 10 degrees for twelve finger joints. Reference penalties
prefer the source finger pose, without claiming an inferred anatomical open
hand. Those are new, explicit pose permissions, not inherited approval under
the original material-reference/rate contract.

The first attempt stops before fitting: it compares GLB float32 positions
directly with higher-precision canonical vertices. The separate retry instead
requires exact equality to their float32 encoding, preserves original payloads,
and derives the heuristic patch from the actual stored GLB coordinates. All
triangle indices and mapped joint names must match. The failed intake is
retained. The geometry-derived palm candidate remains anatomically unreviewed.
No animation is exported until native-key timing and full decoded acceptance
are addressed separately.
