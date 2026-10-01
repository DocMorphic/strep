# Coupled contact-pose repair from refreshed triangle witnesses

The matched joint-ball study reduced penetration depth while increasing the
number of triangle crossings. This experiment replaces the fixed hand-plane
objective with witnesses from the actual intersecting surfaces of both actors.
It retains the authored contact target and all original joint-angle budgets.

## Proposal and independent replay

Both actors are optimized together: 132 normalized controls across the two arm
chains and nineteen finger joints per hand. Controls retain the original
native-key envelope and original-reference angle limits. The source is the
completed joint-ball candidate, reconstructed in the same original basis; the
reference and remaining angle budgets are not rebased to that candidate.

At each of at most two outer rounds, audit all partner triangle candidates at
the meeting pose. Select proper crossings and coplanar overlaps, choose a
separating direction per triangle pair from the current geometry, and construct
nine vertex-pair projected gaps per pair. All triangle vertices move with their
actual skinned joints, including the partner. Directions and witness population
stay fixed during a 40-iteration SLSQP proposal and are rebuilt for the next
round after a retained pose change. Gap deficits use a 1e-8 m proposal clearance
and 1 mm residual scale. These projected deficits are not penetration depth.

Marker position, marker gap, normal orientation and joint-angle limits are hard
constraints. Contact constraints use the unchanged authored thresholds: 0.5 mm
per anchor, 2 mm pair gap and 20 degrees normal error. Smooth evaluations guide
the optimizer; serialized native-key replay decides feasibility and proposal
cost. Inward joint projection and bounded backtracking cannot enlarge limits.
If no replayed feasible improvement exists, retain the original controls.

## Geometry and motion decision

After the proposal, independently query the complete partner meshes and both
full vertex-depth directions. Try the full proposal and, if needed, fractions
1/2, 1/4 and 1/8. Internal search retains a pose only when contact still passes,
neither directional maximum depth increases beyond the existing 1e-8 m numerical
allowance, crossing count does not increase, no new uncertain/degenerate
outcomes appear, and at least one depth/count metric strictly improves.

This internal search criterion does not grant mesh-regression or animation
approval. The existing stricter mesh guard still reports every new proper
triangle pair against the source, even if total crossings fall. Its threshold
is unchanged. Every tested full-mesh result and rejected trial is preserved.

Decode the final GLBs independently, repeat contact and complete contact-pose
geometry queries, verify original per-joint angle budgets and unchanged channels,
clocks and outside-window poses, then recompute original motion caps. The full
approach/departure geometry and self-collision are not certified by this pose
experiment. No candidate is automatically selected for Studio.

## Triangle-only result and depth-witness follow-up

The first 40-iteration proposal lowers its serialized projected-gap cost from
237.780499 to 217.000909 while preserving the hard contact screen and joint
budgets. Full geometry rejects it: crossings remain at 220 and directional
maximum depths increase. Full, half, quarter and eighth steps reach overall
maximum depths of 10.335854, 10.315764, 10.274771 and 10.246417 mm, respectively,
versus 10.212648 mm at the source. No internal step is retained; the two output
GLBs remain byte-identical to the source. The unchanged output passes the
regression guard trivially and still fails contact-pose collision and motion
quality. Solver convergence is not claimed.

This evidence motivates adding witnesses for vertices already inside the
partner. Both complete source vertex populations are queried with the same
closed-mesh signed-distance calculation used for validation. The initial pose
contains 123 selected interior vertices per direction, above a 1e-8 m extraction
tolerance. For each, store the nearest partner triangle, convex barycentric
coordinates and a unit direction from the interior point toward that surface.
Both the source point and partner triangle move during fitting. Each 1 mm-scaled
residual penalizes a negative projected exit gap alongside the triangle rows.
These exit gaps are local proposals, not fresh signed distances after movement;
full geometry validation and witness refresh remain required.

Use `--with-vertices` for the combined follow-up. It starts from the same source,
with the same hard contact constraints, joint budgets, proposal iteration limits
and independent selection checks. Five additional model-free tests cover actual
closed-mesh containment, moving source and partner geometry, rigid placement,
empty witness populations and invalid/open meshes. No vertex-only screen can
approve triangle-edge intersections or the full animation.

## Combined result and remaining geometry regressions

Adding penetrating-vertex witnesses produces two retained internal steps.
Round one uses 220 crossing pairs and 123 interior vertices per direction. The
full proposal reduces crossing count to 216 and directional maximum depths to
9.039264 and 9.109123 mm. The refreshed round uses 216 crossing pairs and 110
interior vertices per direction. Its full proposal is rejected because crossings
return to 220, despite lower depth. The half-step retains 216 crossings and
reduces directional maximum depths to 8.988270 and 9.070073 mm.

Independent decoding and a fresh complete contact-pose audit confirm the final
measurements. Anchor errors are 0.491453 and 0.493924 mm, pair gap is 1.982558 mm,
and target-normal errors are 12.027657 and 13.400552 degrees. The marker screen
passes, but nearly all of its anchor-distance allowance is used. All original
per-joint budgets, native clocks, unedited channels and outside-window poses
are preserved. Both optimizations exhaust 40 iterations; no convergence is claimed.

The fixed-source mesh regression guard still fails: **130 proper triangle pairs
are newly intersecting**, even though total crossings fall from 220 to 216 and
both directional maximum depths fall by about 1.143 mm. No new uncertain pairs
appear. This is an internal search result, not a pass of that unchanged guard
or approval of the remaining intersections.

Original motion caps also fail: 308 position-speed, 153 position-acceleration,
493 angular-speed and 155 angular-acceleration rows. Maximum excesses are
0.102890 m/s, 5.310667 m/s^2, 0.639942 rad/s and 139.972039 rad/s^2. No candidate
is selected for Studio, and no full-interval geometry pass is claimed.

## Next decision and provenance

Keep the hard contact and original joint bounds. Add preventive constraints for
the newly intersecting triangle pairs, using their separated source geometry,
while continuing the coupled vertex-exit and crossing repair. Retain accumulated
collision constraints across rounds instead of only replacing witnesses at each
new pose. Fresh full-mesh checks must still detect additional unmodeled pairs.
A lower maximum depth or total crossing count must not replace the stricter
mesh-regression check; do not proceed to trajectory fitting as though the
contact pose were valid.

All 1,016 model-free source tests pass. The triangle-only study binds 3,325
inputs, 77 archived methods and fourteen outputs; the combined study binds the
same input count, 78 archived methods and fifteen outputs. All archived inputs,
methods and outputs were rehashed; current combined methods also match.

- Triangle-only result SHA-256: `5c76e867226004beeab4096665d2d7c04e040eb1e18b35d59ac479c48d504efb`.
- Combined result SHA-256: `9a1fac0a17fb4de881c7a9fe8d9c753692ebfd3055fdc5301429f69e6272ad69`.
- Combined decoded evidence SHA-256: `b70b331a58033a838cb932eff7049b3a7e5bf74c016f52e9aa5d202cb8a15fe0`.

No training, held-out use, engine import or browser validation occurred. Both
studies remain diagnostic and all fourteen release capabilities are unapproved.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_contact_triangle_pose.py reports/contact-plane-ball-v1 reports/<fresh-output>
.venv/Scripts/python.exe scripts/study_contact_triangle_pose.py reports/contact-plane-ball-v1 reports/<fresh-combined-output> --with-vertices
```

Prior rigs and studies are hash-bound local inputs, excluded from Git. Six new
model-free tests compare hard-contact margins with the independent contact
screen, fit both actors under hard constraints, reject candidates that fail
serialized contact despite passing smooth contact, retain the source when no
serialized improvement exists, and reject invalid or changing input populations.
