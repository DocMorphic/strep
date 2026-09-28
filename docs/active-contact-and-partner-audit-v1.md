# Active contact constraints and partner surface audit

2026-09-26. This is development evidence under the single full-project goal.
All candidates remain unapproved; no new inference, training or held-out run.

## What changed

Solver v7 separates two different meanings of sliding. Inferred ground supports
retain their existing world-motion penalty. Authored moving contacts instead
penalize motion relative to the requested target track, only between consecutive
active frames on the same skin vertex. Following a moving grip is therefore not
penalized as world-space sliding.

The earlier explicit contact loss also averaged Gaussian fade frames into a
one-frame high-five request. V7 uses active-frame inequality constraints for
point distance (5 mm internal target) and surface-normal direction (10° internal
target). A small separate fade term supports approach/release smoothness. Three
bounded L-BFGS subproblems update nonnegative multipliers and increase penalties.
The method follows the slack-free PHR formulation described in the official
[PETSc/TAO documentation](https://petsc.org/release/manualpages/Tao/TAOALMM/), but
this implementation uses existing PyTorch L-BFGS, not PETSc. It offers no global
convergence or feasibility guarantee on these nonconvex poses.

The implementation and parameters were frozen before running in
`benchmarks/oriented-contact-v7-freeze.json`. The scenes, 3 cm point screen,
15° normal diagnostic, object trajectories, root/rotation budgets and original
source motion are unchanged from v6. Both hands of a box share the same actor
optimization and fixed object track. This does not yet implement a free rigid
object jointly optimized with both hands, nor physical attachment.

## Results on the retained fixtures

| Source | Peak requested point error | Normal error | Box skin-vertex depth |
|---|---:|---:|---:|
| High-five seed 11 | Each world point 4.74 mm; actual palms 7.94 mm apart | World targets 9.29° each; opposing palms 14.62° | Not applicable |
| Box seed 11 | Left 2.40 cm; right 2.97 cm | Left 15.33°; right 14.68° | 1.84 cm |
| Box seed 22 | Left 3.76 cm; right 3.47 cm | Left 12.85°; right 16.19° | 2.42 cm |

High-five point/orientation screens now pass, but pose displacement remains
flagged. Both box trials still fail: increased contact pressure trades against
the fixed-weight collision penalty, and support/pose regressions remain. The
geometry audits are retained independently; no threshold was relaxed to accept
these outputs. Legacy inferred hand-support slide/gap metrics still require
interpretation for deliberately moving grips.

## Actual partner skin penetration

`audit_partner_surface.py` checks every SOMA skin vertex against the other
actor's triangle surface in both directions. SOMA's mesh topology is closed and
consistently wound. It uses the documented positive-inside convention of
[Trimesh signed distance](https://trimesh.org/trimesh.proximity.html), with an AABB
broad phase. `requirements-scene-audit.txt` pins Trimesh 5.1.0 and Rtree 1.4.1;
the small official PyPI Rtree Windows wheel was installed in the project venv.

The high-five was checked on all 120 discrete frames, with all 18,056 vertices
eligible in each direction. Fourteen frames exceed the provisional 5 mm depth
diagnostic. At requested contact frame 60, fingers penetrate 15.23 mm. The peak
is **21.13 mm at frame 62**, near the right thumb. The result is an additional
rejection even though the point and palm-normal screens pass. Browser close-up
also shows that normal alignment alone does not ensure the hands' finger axes
are oriented appropriately.

This audit is not a triangle-intersection or continuous collision proof. Edges
can cross without vertices inside; posed self-intersections can make signed
inside/outside ambiguous. Self-collision and physics remain unimplemented.
The two actors reuse the same native generated take, so this is one paired
fixture, not two independent samples.

Studio displays the partner depth, number of frames and audit scope. **Show
partner overlap** jumps to frame 62. Placement edits invalidate the saved
measurements and hide that jump control. A passing palm gap is no longer the
only visible interaction diagnostic.

## Two-hand rigidity diagnostic

`two_hand_rigidity.py` checks a necessary geometric condition before assuming a
rigid object can follow two existing palms. If grip separation is d and palm
separation is s, the minimum equal point tolerance under any freely translated
and rotated object is |s-d|/2. A point-optimal pose is also computed, with the
smallest axis correction to the authored object orientation. Two points leave
twist unconstrained; those diagnostic object poses are not applied.

On v7 box seed 11, all 61 requested frames satisfy the 3 cm per-hand separation
condition, with a maximum lower bound of 2.62 cm. Seed 22 has two impossible
frames for its *current fixed hands*, with a 3.31 cm maximum lower bound. This
does not prove a corrected body pose is unreachable.

The previous one-hand-attached seed-22 clip has a lower bound of only 1.37 mm
despite its observed secondary-hand gap reaching 58 cm. That separates an
object-orientation/attachment error from a hand-spacing impossibility; attaching
to one wrist alone is not a coordinated two-hand solution.

## Verification and next work

156 Python tests pass, with four upstream Torch deprecation warnings. Added
tests cover inequality gradients, motion relative to a moving grip, rigid fit
geometry and antipodal axes, signed-distance sign conventions and rejection of
open target surfaces. All eight v7 GLBs validate without errors or warnings.
Four actor exports preserve raw hashes, root XZ, root/finger rotations, rigid
bone lengths and correction budgets; decoded GLB contact points independently
agree with the measurements. Studio's new partner jump and hand close-up render
without browser errors or warnings.

Outputs: `reports/scene-fitting-v7`, including `quality-audit.json`, individual
normal audits, `partner-surface-audit.json` for the high-five, and the two box
`two-hand-rigidity.json` files. The v6 and earlier attachment comparisons remain
available. No candidate is promoted to the default editor.

Next work must constrain full hand orientation and partner surface clearance
during fitting, rather than merely detect penetration afterward. Box fitting
needs contact and clearance feasibility together, including a coordinated rigid
object trajectory where the author permits it. Preserve the strict authored
tracks when no trajectory freedom is specified. Then continue feasible model
conditioning, rig transfer, broader editing/action coverage and the remaining
full release requirements; do not equate this small study with completion.

Reproduce in a fresh output folder:

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-scene-audit.txt
.venv\Scripts\python.exe scripts/run_scene_fit.py reports/scene-fit-fixtures-v3/high-five.json reports/scene-fit-fixtures-v3/box-seed-11.json reports/scene-fit-fixtures-v3/box-seed-22.json --solver-version 7 --output reports/active-contact-repeat
.venv\Scripts\python.exe scripts/verify_scene_fit.py reports/active-contact-repeat
node scripts/validate_scene_exports.mjs reports/active-contact-repeat
.venv\Scripts\python.exe scripts/audit_partner_surface.py reports/active-contact-repeat/oriented-high-five-seed-11/candidate.json --output reports/active-contact-repeat/oriented-high-five-seed-11/partner-surface-audit.json
```
