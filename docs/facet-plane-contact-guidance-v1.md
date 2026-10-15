# Facet-normal guidance for complete surface regions

`surface_separation_planes.face_planes` adds a finite candidate family to the
existing explicit-axis helper. It uses world XYZ plus every facet normal
returned by each complete supplied population's convex hull. The normal/offset
representation follows [SciPy 1.15.3 ConvexHull](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.spatial.ConvexHull.html).
Hulls choose directions only; every original supplied vertex participates in
every projected interval. No hull replaces the original mesh in acceptance.

For each direction, the lower mean projection determines the left population;
the first population wins exact mean ties. The first largest gap wins, using
XYZ then each hull's returned facet order. The output records every axis, gap,
population order and the chosen extremal witnesses/halfspaces. The direction
is explicitly marked geometry-derived, with no anatomical-normal inference.

Inputs require 4–32,768 finite points per nondegenerate 3D population. The
explicit candidate and projection-workspace budgets reject an incomplete job;
they never truncate points or axes. Projection columns are tiled, with both
temporary projection matrices released after each tile. No Qhull joggling is
requested. Edge-cross directions are not included: this is neither a complete
separating-axis test nor a minimum-translation solver. Failed projection
separation does not establish a collision. Positive gaps remain ordinary
Float64 diagnostics, not certified arithmetic or motion approval.

All **44** affected tests pass in **5.27 seconds**: 31 projection/facet checks
and 13 existing pose-region checks. Thirteen new cases cover oblique boxes
whose world-axis intervals overlap despite actual separation, rigid coordinate
changes, retained outliers, one-column projections, overlapping regions,
degenerate/oversized populations and incomplete budgets. The 512 MiB CPU guard
completes in **22.266 seconds**, peak **126,070,784 bytes**; all **24** resource
observations replay. No new module is added to the existing 518-Python/45-Node
inventory; contact/rig remains 82 Python modules / five Node suites.

## Actual forearm/hand pose trial

The source is the unchanged native motion of the weight-conditioned SOMA
high-five export. At **1.1395833333333334 s**, each region includes every
incident triangle of vertices carrying at least 0.5 total skin weight from the
named RightForeArm subtree, including every vertex of those triangles. This
is weighted source metadata, not reviewed anatomical segmentation.

The finite family contains **1,199** candidate directions. The selected world
axis is approximately `[-0.051592, -0.597219, 0.800418]`. Each actor fits in nine
iterations. The proposal uses a 45 mm joint-displacement radius inside the
unchanged 50 mm original bound; the original four-joint 10-degree rotation
limits and fixed roots remain. The fitted regions have a **2 mm** projected gap.

The subsequent query uses both complete original actor meshes. It reports
**zero surface outcomes and zero maximum inside depth in either direction**;
the original sampled pair conditions pass. The maximum joint displacement is
45.000000000011 mm for A (within solver inequality tolerance) and 36.859051 mm
for B, both safely within the original 50 mm bound. Roots remain exact. The
ground screen still fails at 7.285620 / 6.336010 mm depth, so the complete scene
pose does not pass. No animation or engine approval follows from this pose.

The original cached native baseline is reused with exact source-input,
geometry-method and measurement bindings. It had 301 crossings at this time;
the earlier hand-only world-axis proposal retained 92. This new trial changes
region, direction family and proposal reserve together, so it is not an
isolated ablation of the axis family. The source/failed attempts remain intact.
The pose guard completes in **43.625 seconds**, peak **187,703,296 bytes**; all
**45** resource observations replay. Local records remain under ignored
`reports/high-five-forearm-facet-pose-v1`.

## Single predefined native curve

The retained pose controls are applied with one compact quintic falloff, half
width 0.5 s around the pose time, at existing native keys only. Both actors are
edited. This trial changes the early approach only; it adds no meeting-pose
seed. The original 2 s contact observations remain exactly unchanged and fail.

The decoded native curves have **zero rotation/joint-bound failures** on the
complete original interval clock. Maximum joint displacement is **45.133477 mm
for A / 41.255106 mm for B**, within the original 50 mm bound. Root and endpoint
matrices remain exact. Original caps/scales and each original rate-cap array
are preserved. Every candidate floor time is requeried; both 2,017-time arrays
are exactly unchanged from the bound cached source baseline and fail throughout.

| Selected native time (s) | Pair conditions | Surface outcomes | A inside B maximum | B inside A maximum |
| --- | --- | ---: | ---: | ---: |
| 1.1395833333333334 | Pass | 0 | 0 mm | 0 mm |
| 1.1666666269302368 | Fail | 266 | 7.438055 mm | 21.483742 mm |
| 1.2000000476837158 | Fail | 310 | 17.754146 mm | 30.784762 mm |

The original motion-rate checks still fail **60 rows for A / 114 for B**.
The three selected geometry times are a diagnostic slice, not a complete-clock
audit. No full clip is adopted. This trial isolates the approach and does not
reuse the earlier contact-only meeting edit, so its rate counts are not a
controlled comparison with that differently edited clip.

The curve guard completes in **180.891 seconds**, peak **343,089,152 bytes**;
all **180** resource observations replay under the unchanged 512 MiB CPU profile.
Records remain under ignored `reports/high-five-forearm-facet-curve-v1`.
The result calls for changing geometry targets over time and restoring original
motion-rate bounds, alongside separate ground/support and meeting-contact
corrections. One successful pose is insufficient. No new model inference,
training, engine run, human-quality or release approval is claimed.
