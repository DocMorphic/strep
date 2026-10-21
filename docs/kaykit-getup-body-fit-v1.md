# Full-body get-up transfer: source check and bounded pose trial

The source get-up motion already intersects the floor before transfer. The
stylized target introduces much larger clearance failures. A new bounded
full-body pose trial repairs one severe target pose under explicit geometric
constraints, but it is not yet a corrected animation or an approved motion.

## Separate source and target defects

`reports/kaykit-getup-body-v2/` checks all 180 original source frames with the
bundled SOMA standard preview body: 18,056 vertices and all eight raw skin
influences. Source floor depth reaches 146.983074 mm, and every native frame
exceeds 5 mm. A separate cached inverse-bind, per-influence matrix/sum replay
agrees on all 180 depths within 1.943e-16 m. This validates the raw source
surface calculation; it does not independently certify source forward
kinematics, anatomy, or a continuous-time collision population.

The target has 4,858 vertices. At native frame 40 (1.3333333730697632 seconds in
the stored Float32 clock), its deepest penetration is 633.661003 mm. Scaling
root motion by the mean leg-length ratio of 0.43996074173593835 cannot preserve
whole-body surface clearance for these proportions. As one descriptive
measurement, the maximum reference-space distance from the head joint to a
vertex with at least 65% head weight is 0.924662 m on the target, versus
0.072200 m on the leg-scaled source. These use different reference pivots and
are not equivalent anatomical skull-radius measurements.

The earlier [auxiliary-root study](kaykit-auxiliary-root-v1.md) already rules
out fixing the maximum depth by changing only the extra root's skin
contribution while holding the other node worlds fixed. Both source-body
defects and target contact placement therefore remain in scope.

## Pose model and explicit development proposal

`scripts/surface_pose_model.py` provides whole-mesh positions and derivatives
for a world-space root displacement and right-multiplied local rotation edits
at the root or its descendants. It composes derivative matrices through the
actual hierarchy and evaluates every original skin influence. It retains raw
weights and homogeneous inverse-bind coordinates, including tolerated affine
drift, rather than assuming normalized weights or perfectly rigid parents.
Chunking bounds intermediate allocation without dropping vertices.

The frame-40 experiment permits all 18 mapped rotations, each within 45 degrees
except the head at 60 degrees. Root displacement has a 150-mm horizontal norm
cap and a nonnegative vertical allowance up to 750 mm. These are deliberately
declared bounds for a new major-retargeting proposal, not relaxed acceptance
limits for an older cleanup candidate. The chosen solution uses much less
than the vertical allowance.

For each hand and foot, the proposal selects the baseline lowest vertex among
vertices with at least 65% weight on that mapped role, then projects its
position onto the floor while retaining X/Z. These are geometry-derived point
targets, not artist-authored palm/sole patches or confirmed source contacts.
No contact normal, friction, body balance or self-collision condition is
inferred from them.

SLSQP minimizes squared root and rotation edits, scaled by 0.3 m and 0.35 rad,
subject to every mesh vertex's floor inequality, four contact-distance bounds,
rotation-vector norm bounds and the root bounds. Floor acceptance remains
5 mm and point-target acceptance remains 20 mm. A 10-micrometre floor reserve
is used during fitting. The second trial also reserves 10 micrometres for
point distance and horizontal root displacement; it retains the original
acceptance thresholds.

## Preserved outcomes

| Measurement | Original frame | Refined static proposal |
|---|---:|---:|
| Maximum floor penetration | 633.661003 mm | 4.990000 mm |
| Maximum proposed point-target error | Targets defined from original pose | 19.990829 mm |
| Pelvis vertical displacement | 0 | 285.616860 mm |
| Pelvis horizontal displacement | 0 | 149.990000 mm |
| Largest local rotation edit | 0 | 34.228689 degrees, pelvis |

The first trial finishes 80 iterations and is rejected: three point distances
exceed 20 mm by tiny amounts, and the optimizer reaches its iteration limit.
The second uses that saved seed and the tighter fitting reserves. It finishes
67 iterations with a line-search failure. Nevertheless, its saved static pose
independently satisfies all original declared numerical constraints. This is a
feasible witness for those constraints, not optimizer convergence or optimality.
Both outcomes remain recorded.

Independent verification reads the exported GLB, checks all 4,858 vertices,
reconstructs the target selection, checks each rotation and root limit, and
compares local transforms with the source pose. Unedited local matrices agree
within 2.221e-16; non-root local translations agree within 1.111e-16 m. The
original mesh, skin and embedded binary are unchanged. The derived files are
explicitly static poses with no animation tracks; the original animation is
untouched.

Eleven focused tests pass, including complete finite-difference derivative
checks at zero, tiny and larger rotations, raw weights, nonunit homogeneous
responses, affine drift, world-space root translation, fixed unskinned geometry
and invalid edit selections. Eight actual-character directional checks cover
all 4,858 vertices and agree within 4.367e-10. Both CI source inventories include
the tests; this is not a current full-suite CI claim.

## Evidence and remaining work

Local reports are `kaykit-getup-body-v1/v2`, `kaykit-getup-pose-fit-v1/v2`, and
`kaykit-getup-pose-replay-v1` under `reports/`. The first body attempt fails
before measurement because this motion archive has no embedded joint-name
array. The next version uses the existing validated SOMA metadata path and
binds its definition file. That failure is preserved. All five resource traces
independently replay, totaling 172 observations; the largest measured worker
tree is 140,759,040 bytes. The existing free-memory guard remains 600 MiB.

The refined static GLB SHA-256 is
`da6cefcfbab5eace12bc9e9ae4ff6f047e5ccf7b62c4f8ab03865e46a898e81f`.
The independent replay result SHA-256 is
`0124db1b9a0752ba513dd81c6e214a285edd52b90d8261f7b46b27c5bba6c6e5`.
Local point-cloud comparison figures show the source/target mismatch and the
static proposal; they are diagnostic plots, not rendered animation reviews.

Next, extend this explicitly bounded pose work into a temporally coupled
get-up correction with contact release/arrival phases, retained source evidence,
native-key and between-key validation, self-collision checks and actual engine
verification. Reusing the same four contacts throughout standing would be
incorrect. Human review and cleanup timing are still required, as are the
broader action, rig, object/partner, style, editing and release checks. No
animation-quality or release approval follows from this single pose. The one
project-wide goal stays active.
