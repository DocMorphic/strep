# Getting up contact boundary feasibility

All 11 selected static poses can satisfy the original numerical floor, contact
and edit limits without changing the proposed contact targets. Coupling adjacent
poses fixes the correction jumps at four hand-contact boundaries, but all four
initial windows fail between-key floor checks. A small common pelvis lift repairs
two sampled windows. The other two require changes beyond that single degree of
freedom. The complete getting-up animation remains unapproved.

## Growing floor constraints

`surface_pose_working_floor.py` replaces the sharp smooth-floor approximation
with a growing set of explicit floor rows for each optimizer call. It starts
with the lowest 32 vertices and adds previously unselected violating vertices
after each call. Rows are never removed, and the set stays fixed during a call.
Every vertex still contributes to full-geometry assessment and candidate ranking;
an omitted floor row cannot make a penetrating candidate pass acceptance.

The static study checks keys 0, 41, 42, 67, 68, 91, 107, 108, 124, 125 and 179.
These cover the start/end, both sides of every proposed hand-contact change, and
the previous candidate's worst floor key. Contacts, material points, targets and
original limits come unchanged from the
[complete sequence experiment](kaykit-getup-sequence-v1.md). Fixed-neighbor
constraints are intentionally absent here to isolate static feasibility.
This is development evidence on the same adapted clip, not held-out evaluation.

The retained dense first-pose checkpoint passes again. Across all 11 poses,
eight initially pass strict decoded acceptance; three satisfy floor/contact
limits but miss hard edit bounds through tiny numerical overshoot. A separate
proposal moves parameters inward by at most 1.000006 micrometres in root
translation and 9.990e-7 radians in a rotation block. All 11 then pass the
unchanged original limits on decoded GLBs, including every mesh vertex.
The maximum resulting floor penetration is 4.000358 mm. Static mesh roundtrip
error is at most 5.088e-16 m. These are static matrix-node assets, not animations.

## Simultaneous neighboring poses

`surface_pose_window.py` places all pose constraints and adjacent correction
differences in one optimizer problem. Both sides of each pair have derivatives;
moving one key cannot silently invalidate an earlier fixed-neighbor check.
It supports two to eight poses with matching parameter layouts. These limits
control correction steps, not total animation velocity or anatomical motion.

The study solves the pairs 41–42, 67–68, 107–108 and 124–125. Each pair preserves
the original 25 mm root-step and 5 degree rotation-vector-step acceptance limits,
using small interior reserves during fitting. All four pass the two native-key
constraints and the decoded step limits. However, interpolated poses exceed the
5 mm floor threshold: initial window peaks range from 5.213371 to 11.183870 mm.
For example, pair 41–42 reduces a 131.911 mm root correction jump and a
25.848 degree rotation correction jump to 24.990 mm and 4.999428 degrees, while
still failing between-key geometry. Key-only checks would miss this failure.

Each diagnostic GLB changes only its declared pair of keys in the full original
clip. All other channel values and clocks are retained. The adjoining external
boundaries and the rest of each clip are not accepted by this local study.

## Common lift and actual engine checks

The existing `root_plane_contact_bounds.py` computes the interval of common
vertical pelvis translations allowed by every sampled vertex and active point
contact. This uses raw homogeneous skin responses and checks that the root
parent basis is constant. The intersection also retains the original total
vertical edit budget and caps additional lift at 10 mm. Floor and contact fitting
reserves are 10 micrometres; acceptance remains 5 mm and 20 mm respectively.

The audit combines the previous sample times with 960 Hz samples within each
one-frame interval. There are 160 distinct window observations in total.

| Keys | Required lift lower bound | Allowed lift upper bound | Saved sampled result |
|---|---:|---:|---|
| 41–42 | 0.250202 mm | 0.990229 mm | Pass after minimum lift |
| 67–68 | 2.920124 mm | 0.995392 mm | Reject; empty intersection |
| 107–108 | 0.742316 mm | 0.999752 mm | Pass after minimum lift |
| 124–125 | 6.232641 mm | 1.056532 mm | Reject; empty intersection |

The empty intersections apply to this fixed pose interpolation, fixed contacts
and common upward root shift. They do not prove that other joint edits or a
different motion cannot satisfy the request. The arithmetic uses Float64, not
certified interval arithmetic. Dense sampling is not continuous collision proof.

Independent replay reproduces the decoded floor/contact values. Actual Godot
4.7.2 native-authoring capture observes all four clips at the union clock plus
zero and the exact endpoint: 162 times and 648 actor observations. All pose and
skin comparisons pass; maximum skin disagreement is 0.027997 mm. Godot confirms
the same two passing and two failing window geometries. These are four separate
diagnostic clips, not an interaction scene. Ordinary playback, physics and GPU
skinning are not established by this authoring-resource capture.

## Evidence and next work

Eighteen new focused tests pass: nine for growing floor rows and nine for coupled
windows. They cover full versus selected derivatives, hidden omitted-vertex
failures, both sides of adjacent constraints and invalid
parameter populations/layouts. Both CI inventories include the tests; the full
repository suite was not rerun.

Local evidence is under `reports/kaykit-getup-phase-feasibility-v1`,
`kaykit-getup-phase-boundary-v1`, `kaykit-getup-coupled-boundaries-v1`,
`kaykit-getup-boundary-lift-v1` and `kaykit-getup-boundary-engine-v1`.
The lift run completes its native proposals but fails before launching Godot
because its union clock omits the required zero sample. That failure remains
preserved. The final engine run reuses the saved proposals and adds the required
clock envelope, without refitting. All five resource traces replay, totaling
390 observations; maximum observed worker-tree memory is 366,292,992 bytes.

The static boundary result SHA-256 is
`ecb85cf05f267b764425e64003b7854ca788bd9ade3218777e11c23a3c1ba004`.
The final engine result SHA-256 is
`df29f16d59b5d38f67af674558eb6a01a69e881a9180af301b41e64bb8818e16`.

Next, include actual interpolated geometry in the coupled optimization for the
two unresolved windows. Verify derivatives against independent perturbations
and validate serialized samples before extending to the entire clip. Preserve
the failed target set and all raw attempts. Continuous checks, self-collision,
anatomical support, action correctness, human review and cleanup time remain
separate requirements. The project-wide release goal remains active across all
action families, rigs, objects, partners, editing and style controls.
