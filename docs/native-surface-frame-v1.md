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
differences fresh pose evaluations. All 26 checks pass on Ubuntu (0.66 s) and
Windows (1.40 s) in [hosted run 38968193740](https://github.com/DocMorphic/strep/actions/runs/38968193740).
No full-inventory pass is claimed.

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

The failed intake completes in 18.265 s at 120,356,864 sampled bytes with 20
observations independently replayed. The corrected intake verifies exact
float32 encoding (maximum difference from the higher-precision source is
5.722046e-8 m), topology and joint mapping, then uses actual stored vertices for
the candidate patch. Original files remain unchanged. Its complete local Python
method population is archived and hashed before fitting.

## Completed pose pilot: mixed result, retained failure

At the initial pose, the proposed material normals differ from their desired
directions by 66.464921 degrees for A and 42.975495 degrees for B. The fitted
pose reduces those errors but does not meet all declared constraints. SLSQP
reaches its 60-iteration limit after 120 observations; 29 inequality rows still
fail. No solver-success or animation-quality claim follows.

| Frame condition | A candidate | B candidate | Declared limit |
| --- | ---: | ---: | ---: |
| Material-origin position error, mm | 21.661144 | 10.410453 | 5 |
| Signed normal error, degrees | 9.075535 | 6.724029 | 5 |
| Signed tangent error, degrees | 15.914853 | 15.006644 | 15 |

Separate matched native CPU geometry queries at 2 s find 834 surface records
and 13.303821-mm maximum vertex depth in the starting pose, versus zero records
and zero depth in the candidate. The candidate passes the declared geometry at
that single time. It nevertheless remains a failed pose because geometry and
contact/edit constraints are separate requirements. No curve, other time,
original world-reference budget, motion rate, export or engine playback is
validated by that result.

The complete pilot takes 185.296 s at 251,097,088 sampled process-tree bytes;
183 resource observations independently replay. Fitting itself takes 111.813 s.
Original clips stay selected and unchanged; all quality/release flags remain
false. Further work must identify the conflicting bounds and find a feasible
contact pose before extending the correction across native keys.

The separate native replay reconstructs both actors from the original source
and saved controls. Every stored world matrix, skinned vertex and inequality
matches exactly. It classifies the 29 failures as six material-frame rows,
thirteen local edit balls, and ten whole-hand halfspace rows. All three original
point contacts pass, and maximum joint displacements are 47.474118/55.355145 mm,
below the explicit 60-mm limit. Thus the result does not justify changing the
original point thresholds or claiming incompatible landmark definitions.

Three independently differenced frame-derivative directions per actor have
maximum absolute error 1.007536e-9 at step 1e-5. These are directional checks,
not a complete Jacobian certificate or collision rerun. The replay completes in
30.593 s at 188,911,616 sampled bytes, with 32 resource observations replayed.
Pose result SHA-256:
`102dcd43e9920ebd0988e7a4bb861ce9813334a02a5e94cb3c6a3df786a34a21`.

A separately recorded feasibility-first follow-up keeps all physical and edit
limits unchanged. It initializes from the failed pose projected into each
original local edit ball, retains the zero source-reference epoch, minimizes
complete constraint violations with group scaling, then refines inside a
normalized 0.001 search reserve. The reserve tightens search; original limits
remain the acceptance authority. Its artifacts are kept under
`reports/high-five-surface-frame-pose-v3/`, separately from the initial intake,
SLSQP pilot and replay.

## Protected feasibility and expanded finger condition

The first feasibility-first run reduces its worst violation to 0.789987,
but the following norm-refinement step regresses while still infeasible.
It completes in 188.203 s at 257,179,648 sampled bytes (186 observations
replayed). This is retained as evidence to gate quality refinement on actual
feasibility rather than solver termination alone.

The next experiment protects local edit balls, joint displacement and original
point contacts, while temporarily allowing slack on material targets and hand
halfspaces. Acceptance still requires zero violations in every original row;
temporary slack never approves a pose. It retains a protected-feasible candidate,
but palm/halfspace conditions fail. Its geometry has 294 surface records and
5.574071-mm maximum depth. The run takes 146.157 s at 252,588,032 sampled bytes
with 146 observations replayed. Independent source/array/inequality replay
takes 29.453 s at 189,857,792 bytes (31 observations); directional derivative
error is at most 1.544075e-9. The worst halfspace vertices are dominated by
`RightHandThumb1` for A and `RightHandPinky4` for B. The thumb was not editable.

A separately labelled expanded condition adds `RightHandThumb1` and permits
20-degree edits for twelve finger joints plus a 30-degree thumb-base edit.
Arm/forearm/hand caps remain 15/20/30 degrees and joint displacement remains
60 mm. All target, gap-halfspace and geometry conditions are unchanged. Warm
controls are remapped by joint labels and rescaled to preserve physical rotation
vectors; the original zero source-reference epoch remains unchanged. It is not
a pass under the earlier 10-degree/no-thumb permissions.

That 96-control pose passes all of its declared inequalities strictly, with
minimum normalized margin 0.001. It also has zero surface records and zero
vertex depth at the one queried time. The run takes 76.344 s at 260,513,792
sampled bytes with 77 observations replayed; fitting takes 23.859 s. Independent
replay exactly reproduces all stored worlds, vertices and inequalities, with
six directional frame-derivative checks below 1.319772e-9. That replay takes
31.594 s at 203,165,696 bytes with 33 observations replayed.

Nevertheless its two material origins are 13.993424 mm apart. Individual 5-mm
world-target tolerances around distinct target points do not establish a
5-mm pair gap. This pose is not approved as a finished high-five.

## Direct material-frame pair constraints

`scripts/native_surface_frame_pair.py` adds a direct origin-gap norm and signed
normal/tangent relationship norms. The default is opposing normals with aligned
tangents. Explicit shared control ownership sums both derivatives in one basis;
independent actors concatenate their columns. Unit-vector chord caps retain
the declared angular tolerances. The API rejects invalid ownership, signs,
frame directions, derivative populations and incompatible shared widths.

Twelve isolated source tests pass in 1.73 s, including independent geometry
differences on both actors and cancellation under shared translation. The guard
completes in 18.234 s at 80,318,464 sampled bytes with 20 observations replayed.
A stronger pose experiment adds a 5-mm direct material-origin gap, 5-degree
normal opposition and 15-degree tangent agreement. It preserves the expanded
condition's edit bounds and all original contact/geometry limits. Its results
are separate from the individually targeted pose above.

The 12 pair checks also pass on Ubuntu (0.36 s) and Windows (0.72 s) in
[hosted run 38970899597](https://github.com/DocMorphic/strep/actions/runs/38970899597).
Current inventories contain 547 Python/45 Node suites, contact subset 111/five;
these are inventory counts, not full-inventory passes.

## Stricter pair conditions remain unresolved

The direct-pair fixed-facing condition still fails: 507 surface records and
4.068930-mm maximum depth at 2 s. It completes in 145.594 s at 258,252,800
sampled bytes; 145 resource observations replay. A sub-5-mm vertex depth does
not waive the separate zero-crossing condition.

A new authoring condition derives a common plane normal from the difference
of the two original posed material normals, and a common tangent by projecting
their summed tangents into that plane. It does not assert a fixed world Z/Y
orientation, which the user's high-five prompt did not specify. The same gap,
angular, contact, edit and geometry thresholds remain in force. This condition
also fails: 280 surface records and 3.898044-mm depth. The run completes in
144.187 s at 259,919,872 sampled bytes, with 144 observations replayed.

Source reconstruction and all stored inequalities replay exactly in 32.547 s
at 204,472,320 bytes (34 observations). Six directional derivative checks stay
below 1.052289e-9. The candidate's material-origin gap is 5.758464 mm, opposing
normal error 5.759106 degrees, and tangent agreement error 7.061906 degrees;
the first two miss their 5-mm/5-degree caps. Local edit balls, 60-mm joint
displacement and the three legacy point contacts pass, but 824 other rows fail.
No global infeasibility is proven by this local search.

Finally, a separately authored landmark condition replaces the legacy index
vertex with the geometry-derived candidate palm vertex in all three contact
rows. It retains the world meeting points, timing, tolerances, placements,
source clips and geometry policy; the old landmark condition is measured
separately and never relabelled as passing. The new point contacts are restored
as goals rather than assumed feasible at the original pose. Anatomical review
of this candidate patch remains pending.

This condition still fails: 177 surface records and 3.885398-mm maximum depth.
Its direct palm-origin gap is 5.712439 mm, opposing-normal error 5.712972 degrees
and tangent agreement error 17.152402 degrees, all above the respective
5-mm/5-degree/15-degree caps. The original landmark diagnostic also fails,
including a 41.238888-mm inter-landmark error against its unchanged 30-mm cap.
Changing contact intent is explicit authoring, not a pass of the old benchmark.

That run completes in 138.547 s at 281,247,744 sampled bytes (138 observations),
with replay in 32.594 s at 203,907,072 bytes (34 observations). All stored worlds,
vertices and inequalities reproduce exactly; six directional derivative checks
stay below 7.347316e-10. The worst hand-halfspace vertex in each actor is
dominated by `RightHandRing4`, which is absent from the 16-joint edit set.
This is a reason to test fuller hand articulation, not proof that it alone
will solve the interaction.

The original clips remain selected. No animation, native motion-rate result,
engine playback or human cleanup evidence is produced by these pose pilots.
The next implementation should expose all relevant weighted finger joints
within measured memory bounds, retain the original affine evaluator and source
epoch, and evaluate complete decoded curves before any asset promotion.
