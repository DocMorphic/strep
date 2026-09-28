# Hand-frame controls and reference-surface clearance

2026-09-26. Development under the existing full-project goal. These are
in-sample deterministic edits of the same high-five source, not new generation,
training, independent paired samples or release validation.

## Hand orientation now includes a second axis

`tangent_target` adds an authored wrist-to-knuckle direction alongside the palm
normal. Its measured direction is the mean position of the four non-thumb
knuckles relative to the wrist, projected into the actual skinned palm tangent
plane. Desired normal and tangent must be unit length and orthogonal. Targets
may be in world or object coordinates and are transformed into actor-native
coordinates before fitting. Degenerate directions fail explicitly.

Solver v8 adds tangent inequalities using the same active-frame multiplier
method as v7. Existing frame, root, bone, finger and 40° correction limits remain.
Fingers are still not articulated by this editor. Older solvers reject requests
containing tangents or partner cuts rather than silently ignoring them. The
independent orientation audit now measures normal and tangent errors separately.

`reports/scene-fit-fixtures-v4/high-five.json` adds explicit world-up tangents to
the two meeting contacts. Point targets and timing are unchanged. The initial
implementation/configuration was frozen before the ablation in `freeze.json`;
the report source snapshot preserves the actual code used.

## Comparison

| Variant | Palm-to-palm gap at frame 60 | Opposing normal error | World-up tangent error | Peak partner vertex penetration | Frames over 5 mm |
|---|---:|---:|---:|---:|---:|
| Previous v7 | 7.94 mm | 14.62° | Unconstrained | 21.13 mm | 14/120 |
| Hand-frame targets only | 4.15 mm | 8.42° | 10.02° per hand | 20.10 mm | 13/120 |
| Hand-frame targets + frozen clearance planes | 14.21 mm | 9.21° | 7.98° per hand | 19.91 mm | 5/120 |

Both new candidates pass the provisional requested point/orientation screens,
but **both remain rejected** for partner overlap and excessive pose displacement.
Hand orientation alone does not resolve an earlier unwanted encounter or all
finger contacts. Each complete paired surface was checked on all 120 discrete
frames in both directions, using the existing vertex-inside-closed-mesh audit.
This still excludes edge-only/continuous/self-collision certification.

Reports are `hand-frame-fit-v1` and `partner-clearance-fit-v1`. The original v7
and raw source outputs remain untouched.

## What the clearance pass does, and why it remains insufficient

`partner_surface_cuts.py` builds local outward clearance planes from the
hand-frame reference's actual intersections. It selects up to 64 penetrating
skin vertices per actor/frame, yielding 785 constraints per actor. Each plane
passes through the closest partner-surface point and uses the outward direction
from the penetrating point. Geometry, actor placements, source hashes and the
cut file hash are recorded. A changed placement, clock or hash rejects the
frozen context.

V8 fits a 2 mm clearance inequality against those planes, while retaining hand
targets and the existing edit bounds. Both actors fit against the same frozen
reference; this is not a jointly evolving collision solve. The pair must be
audited again after both actors move.

The final worst overlap is at frame 61. In each direction, its deepest vertex
was **not among the 64 selected cuts** for that frame. Of those 64 original
planes, ten still classify their source vertex as inside while the updated
partner surface classifies it outside. The recorded
`cut-validity-diagnostic.json` therefore demonstrates both missed newly relevant
vertices and stale local-plane penalties. Increasing the same fixed weights
cannot establish collision-free motion. The solve also leaves some original
plane inequalities violated; edit bounds alone are not a feasibility guarantee.

The next geometric method must refresh the active surface constraints as the
pair changes, or use a suitable continuously queryable collision representation,
with independent mesh validation afterward. Full hand shape/finger editing and
initial-pose feasibility must also be considered. Preserve failed candidates;
do not promote v8 to default contact editing from this single fixture.

## Downloadable editable actor candidates

Each new candidate has separate **Actor A/B · animation ZIP** links in Studio.
`package_scene_actors.py` includes GLB, BVH, NPZ, root track, predicted foot
contacts, contact specification, recipe, evaluation and provenance. Actor scene
placement is recorded separately because individual assets retain native
coordinates. Each ZIP includes the supplied SOMA license and explicit unreviewed
status. The pack does not contain the other actor or a complete game scene.

All four ZIPs were checked internally and their HTTP-served bytes match local
hashes. Studio shows both comparisons, includes tangent failures in the hand
orientation count, jumps to the latest worst overlap at frame 61, and exposes
both actor downloads. Terminal-frame scrubbing reaches 3.97 s; jumping back to
contact returns frame 60. No browser console errors or warnings were observed.

## Verification

160 Python tests pass with four upstream Torch deprecation warnings. New tests
cover tangent projection and rigid-transform equivariance, orthogonal target
validation, outward cut direction and cut-context hash/placement binding. Both
reports independently verify all four actor exports and their edit invariants.
All eight raw/candidate GLBs validate with zero errors and warnings. These checks
establish artifact integrity, not realistic or acceptable interaction.

To reproduce, use fresh output paths:

```powershell
.venv\Scripts\python.exe scripts/run_scene_fit.py reports/scene-fit-fixtures-v4/high-five.json --solver-version 8 --output reports/hand-frame-repeat
.venv\Scripts\python.exe scripts/audit_partner_surface.py reports/hand-frame-repeat/hand-frame-high-five-seed-11/candidate.json --output reports/hand-frame-repeat/hand-frame-high-five-seed-11/partner-surface-audit.json
.venv\Scripts\python.exe scripts/partner_surface_cuts.py reports/hand-frame-repeat/hand-frame-high-five-seed-11/candidate.json reports/hand-frame-repeat/hand-frame-high-five-seed-11/partner-surface-audit.json --output reports/hand-frame-repeat/partner-cuts.json
```

To repeat the recorded frozen-cut fit exactly, use
`reports/scene-fit-fixtures-v4/high-five-with-cuts.json` with solver v8 and a fresh
output folder. For a newly rebuilt cut file, explicitly update the input scene's
`partner_cut_file` and `partner_cut_sha256` before fitting. Do not substitute a
different reference silently. Re-run mesh audits and `verify_scene_fit.py` on
each new candidate; use `package_scene_actors.py <report>` and then
`register_scene_artifacts.py <report>` for new downloads.

## Broader generation path inspected

The pinned Kimodo code exposes `EndEffectorConstraintSet`; Strep's current
`generate_actions.py` still passes an empty constraint list. Vendor docs and
`kimodo/constraints.py` confirm that end-effector constraints also constrain
root path, hip height and heading, and that SOMA77 is reduced to SOMA30 for model
conditioning. Wrist position/rotation and hand-end positions can be supplied
from a valid reference pose. This is not an arbitrary scene-object or partner
collision interface.

The next generation integration should pass explicit feasible pose constraints
with their root implications and preserve an unchanged baseline, rather than
assuming a text prompt gives scene awareness. This remains alongside renewed
collision fitting, target-rig transfer, broad clip editing/action evaluation and
the remaining full release contract. No fine-tuning or new licensed data has
been introduced here.
