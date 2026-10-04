# Object fitting with original-relative movement limits

An experimental CPU authoring command now fits explicit object-surface
correspondences inside translation and rotation limits relative to the
**original object path**. Character files remain unchanged. This addresses the
[unconstrained multiple-point trial](native-object-correspondence-fit-v1.md),
which passed point contacts but exceeded its object edit budget.

The fitting objective uses every selected correspondence with equal weight.
Translation is restricted to a ball around the original position; the rotation
vector of the original-relative proper rotation is restricted to an angle ball.
A declared internal reserve makes those domains slightly tighter than the
public limits. Normalized variables and analytic derivatives feed
[SciPy 1.15.3 SLSQP](https://docs.scipy.org/doc/scipy-1.15.3/reference/optimize.minimize-slsqp.html).
The solver's objective stopping precision is separate from the physical contact
and movement limits, which are rechecked on the saved motion.

## Request

```json
{
  "schema": "strep-native-object-bounded-fit-v1",
  "contacts_sha256": "<SHA-256 of source contact JSON>",
  "object": "item",
  "contact_ids": ["left-palm", "right-palm", "left-side"],
  "edit_window_s": [1.5, 4.5],
  "maximum_translation_m": 0.002,
  "maximum_rotation_degrees": 2.0,
  "maximum_keys": 3601,
  "maximum_correspondences": 16,
  "initial_scene": null,
  "solver": {
    "schema": "strep-object-pose-solver-v1",
    "maximum_iterations": 100,
    "ftol": 1e-10,
    "bound_reserve_fraction": 1e-3
  }
}
```

```text
python scripts/native_object_bounded_fit.py contacts.json request.json geometry-policy.json fresh-output
```

`initial_scene` may instead bind an explicit `{ "path": "initial.json",
"sha256": "<SHA-256>" }`, relative to the source contact JSON's directory.
That scene must retain the original actors, animation identity, placement,
duration, complete contact intent, object geometry and every unedited object
path. Only the selected object's path may differ. It supplies initial solver
poses and is archived separately; it cannot reset the source-relative budgets.
With `null`, the original object path initializes the fit.

The [multiple-point protocol](native-object-correspondence-fit-v1.md) still
defines the complete population: 3–256 distinct, noncollinear supplied
correspondences, all native hold keys and all twelve rate/phase clocks. Centroids
contribute one correspondence. No anatomical patch, hand shape or contact
target is guessed. Whole-population resource overflow and unobservable input
geometry reject instead of dropping points or frames.

A proper unconstrained fit is used directly only when it already lies inside
the reserved domains. Otherwise SLSQP fits the bounded six-dimensional pose.
Component bounds implied by the balls stabilize axis-aligned boundary steps;
they do not remove feasible rotations or translations. The analytic rotational
derivative is checked against independent central differences, including the
small-angle case and rotated original frames.

The final solver parameters are projected onto the reserved balls if numerical
iterates drift outside. That projection is recorded. A projected solution whose
objective is worse than its projected initial pose retains that initial pose,
also explicitly recorded. Nonconvergence stays visible; a finite bounded pose
does not turn an iteration-limit or line-search failure into solver success.
This is a pointwise local optimization, not a global optimum or minimax proof.

## Saved-motion acceptance

Quintic ingress and egress return corrections to zero outside the edit window.
Original exterior keys keep their exact JSON values. The actual saved JSON is
reopened before evaluation. Its original-relative budgets, **all** source scene
contacts, held slip and complete sampled actor/object/partner/plane geometry
remain separate conditions. Convergence of every fitted time is an additional
protocol requirement; objective precision cannot override a physical failure.

Every run binds source/request/policy/initial inputs, unchanged actor snapshots,
implementations, unconstrained comparisons, normalized parameters, solver
records, contact observations and complete per-triangle geometry arrays. The
initial path's contacts and source-relative budgets are measured separately;
its geometry is not automatically rerun or approved. Failed proposals and
computation errors remain inspectable. The original remains selected, and
training, quality and release approval remain false.

## Development study

The retained humanoid sphere case uses the same ten authored correspondences,
previously corrected but unapproved actor bytes and complete original contact
intent as the preceding study. The explicit initialization is the earlier
two-point object path, rechecked against the added point conditions. Original
limits remain 5 mm point error, 5 mm/s slip, 2 mm movement and 2 degrees rotation.
There is one humanoid and two declared spheres; no partner or world plane is
declared. No model sampling or training is performed.

The first request uses 100 iterations, objective precision `1e-12` and an
internal reserve fraction `1e-6`. Its 1,033 fitted times stay bounded and pass all
four contact/slip conditions, but 87 hit the iteration limit. A fixed probe of
the first, middle-index and last failed rows checks two stopping settings:
raising the budget to 500 iterations at `1e-12` leaves two of three unconverged;
using `1e-10` at 100 iterations terminates all three in 21 iterations. This is
only a numerical stopping diagnosis, not complete-motion validation or a
change to any contact or release limit. The original run remains retained.

The first full geometry audit also passes, but the aggregate proposal remains
rejected because of nonconvergence. A separate object-only Godot probe exposes
another failure: the nearly saturated 1.999998 mm author correction becomes
2.000038 mm in Float32 storage and up to 2.000055 mm after import, exceeding
the original 2 mm limit. Those failed results remain retained.

A matched follow-up uses 100 iterations, `ftol=1e-10` and an internal reserve
fraction `1e-3`, leaving 2 micrometres below the translation cap. It changes
neither the original pose budget nor any physical contact, slip or geometry
limit. All 1,033 fitted times converge. The saved path passes at 1.998000 mm
translation and 0.810377 degrees rotation, with maximum point error 4.688173 mm
and held slip 3.168697 mm/s. Every one of the 36,108 actor triangles is queried
against both objects at all 1,266 times, producing 2,532 actor/object records;
all sampled geometry conditions pass.

An independent replay reconstructs every normalized pose, objective and ramp,
uses SciPy alignment for the unconstrained comparator, reproduces contact
arrays exactly and checks all saved geometry-array reductions. Geometry queries
are not rerun. Shared native skin decoding and the original containment query
remain explicit dependencies. A finite-difference stationarity diagnostic has
maximum residual `4.891e-6`; it is not a global optimality or quality certificate.

## Object export

```text
python scripts/native_object_bounded_handoff.py passing-fit fresh-output --engine path/to/godot
```

This experimental command requires a complete passing bounded fit with bound
inputs, implementations and saved observations. It independently exports the
**original author path** and proposed path, then measures Float32 assets,
default Godot import and native Godot resource authoring on one complete clock.
Physical movement budgets always compare against the original Float64 author
poses. The initialization and imported reference cannot reset that epoch.

Protected original export keys and actual exterior observations must match the
independently exported original exactly. Unedited object tracks are protected
everywhere. Float64 author values need not be bit-identical after Float32 export;
that representation error is recorded separately. Exact native knots now use
their declared/stored poses, preventing Slerp endpoint recomposition from
introducing tiny rotations at unchanged keys. Truly rounded or merged Float32
times still resample the source interpolation, with all collisions recorded.

Both Godot modes and their failures are saved separately. Native authoring
acceptance does not imply default import acceptance. The handoff checks rigid
object tracks only: it does not import actor skins, repeat full imported scene
geometry, render, certify real-time playback or approve the animation.

The actual follow-up handoff has 2,201 times, including all original audit
times, fitted/geometry times and actual stored Float32 object keys. Float32
assets and native Godot authoring pass the original-relative movement,
protected-pose and object-contact conditions. Native authoring peaks at
1.998049 mm movement and 0.810380 degrees rotation. All 91 protected sphere
poses match the independently exported original exactly, as do all 2,201
observations of the unedited prop. Default import retains a 0.048200 mm
position difference and `0.000484756` basis-component error versus the
proposed author path, exceeding the exporter fidelity limits; it stays
rejected. These are transform-seek checks, not playback or full-scene approval.

## Scope

Hard object edit domains are not contact, grasp, balance, anatomy or realism
certificates. Pointwise fitting may introduce slip or interpolation defects,
and the post-fit checks must catch those rather than relaxing limits. Supplied
actors are untouched; this operation does not articulate fingers or repair
body motion. Complete sampled geometry does not certify self/object-object
collision, continuous motion, forces, engine playback or human action quality.

All 197 related CPU checks pass, covering solver derivatives and hard bounds,
source/initializer preservation, failed-contact retention, Float32 knot and
collision handling, protected export epochs, producer binding and scene replay.
Actual humanoid evidence remains separate from procedural fixtures, solver
tests and source checks. Local reports and character payloads remain excluded from
the public repository. The full project goal and all release requirements
remain active.
