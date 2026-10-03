# Native finite root extraction

`scripts/godot_native_root_adapter.gd` evaluates a previously saved native
LINEAR bone Animation in two modes: embedded root motion, or motion moved onto
an outer actor node. It does not resample the clip to 30 fps, change its resource,
project movement onto a horizontal plane, or drop root rotation/height.

This extends the existing sampled finite/cycle adapters. Their 30 fps contracts,
recorded studies and object-event consumers remain unchanged. The new adapter is
an engine integration component; Studio's existing native game package continues
to contain **reference tracks with motion embedded in the character clips**.
The new component is not automatically enabled in those packages.

## Ownership and supported inputs

The caller imports the selected GLB animation, installs the matching saved native
Animation in its AnimationPlayer, and supplies the explicit root bone name.
The player, skeleton and all skinned meshes must belong to an outer Node3D actor.
Resource/character hashes and animation selection remain the caller's binding
responsibility; `audit_native_root_runtime.py` verifies them in its own studies.

The adapter owns that actor's placement, the manual player clock and every bone
pose for the duration of the binding. Do not concurrently move the actor,
animate the skeleton, change its hierarchy or add other pose/physics consumers.
It deliberately accepts a narrower surface than arbitrary engine scenes:

- One skeleton/player; the explicit root contains **every bone**, including
  unweighted gameplay/attachment bones. Selecting a hand or partial subtree fails.
- Every character mesh is skinned to that skeleton, with no morph shapes.
  Static accessories, additional skeletons/players, AnimationTree and skeleton
  modifiers reject rather than losing their movement during extraction.
- Proper rigid actor/skeleton/rest/pose transforms and enabled bones. The
  skeleton uses normal poses and a motion scale of one.
- A finite, non-looping resource with enabled, unique LINEAR position/rotation/
  scale tracks targeting only existing skeleton bones. Scale keys must be unit
  scale. Keys are finite, strictly increasing and within the resource duration.
- No built-in AnimationPlayer root-motion track, method/audio tracks, blending,
  loops, ragdolls or automatic physical attachment.

Eligibility checks precede player/pose/actor mutation. The adapter duplicates the
resource in memory without writing it, preserving original native keys. It
restores every saved base pose before evaluating tracks. Unanimated channels
therefore retain their original values across extracted samples and previews.

## Applying motion once

Let `P` be the actor's initial world placement, `S` the skeleton transform relative
to the actor, and `B(t)` the root's skeleton-space global pose. Define:

```
A = S * B(0)
X(t) = S * B(t) * inverse(A)
```

Embedded mode keeps the actor at `P` and retains the original bone poses.
Extracted mode anchors the root to `inverse(S) * A` and sets the actor to `P * X(t)`.
Because the entire skeleton lies below that root, its world poses remain equal
to embedded mode, subject to measured engine arithmetic error.

`root_motion_transform` is `X(t)`, and `root_motion_delta` is
`inverse(X(previous)) * X(current)` on a forward clock advance. A repeated time
returns an **exact identity delta** without resampling. The adapter applies the
absolute actor transform itself in extracted mode; applying it again doubles
movement.

The earlier reference-package delta `inverse(world(0)) * world(t)` uses a different
multiplication convention. It cannot replace `X(t)` directly. The regression
fixture includes a nonzero initial root rotation and a rotated/translated actor
placement so that exchanging those conventions is detectable.

## Clock and preview

```gdscript
const NativeRoot = preload("godot_native_root_adapter.gd")
var motion = NativeRoot.new()
# After importing the selected character and loading its saved native resource:
var code = motion.bind(player, skeleton, actor, "Native", chosen_root_name, true)
if code != OK:
    return
# Authoritative absolute clip time, rather than repeated frame-time additions:
code = motion.advance_to(authored_time_s)
# Explicit silent preview can seek backwards or repeat a time:
code = motion.seek_preview(preview_time_s)
```

`advance_to` accepts only finite, forward absolute times within `[0, duration]`.
Negative, backwards and out-of-duration advances reject without changing the
actor, poses, cursor or root delta. `seek_preview` accepts arbitrary time order
within that same interval and emits no gameplay events. It resets root delta to
identity. A skeleton hierarchy revision invalidates subsequent sampling.

The terminal native key is evaluated directly through the existing native
preview evaluator, avoiding playback-end snapping. Holding the terminal pose
means continuing to request exactly `duration`; times beyond the clip reject.
The caller's simulation clock is separate. There is no automatic `_process`,
event cursor, transition blend, loop-wrap or object controller in this component.

## Reproducible audit

Run `scripts/audit_native_root_runtime.py REQUEST.json FRESH_OUTPUT_DIRECTORY`
with the model-free Python dependencies and a configured Godot executable.
The request contains `glb`, `animation_resource`, `animation_index`, `root_node`,
`times_s`, and optionally `placement` (4×4 row matrix) and `engine`.
Every original native key, zero and the full selected duration must be included
in the strictly increasing clock. There is no smaller sample population.

The audit snapshots both supplied files, archives the complete scene-method
dependency population and new adapter, and hashes the executable and executed
GDScript files. A headless process imports the exact selected GLB and **reloads
the previously saved resource**. It does not regenerate native animations or
requery scene geometry. The complete Float64 clock travels through the existing
binary clock decoder; descriptive JSON clock echoes use its existing check.

It records every bone in both modes, actor/root transforms, root deltas, reversed/
repeated previews and complete raw imported binds, weights, vertices and
triangles. Existing skin-function/topology correspondence handles engine bone,
vertex and winding reorderings. Skin comparisons retain raw engine weights;
they do not normalize away imported quantization. Every source vertex is checked.

All observations are saved as complete Float64 NPZ arrays with dtype, shape and
byte-for-byte readback checks. Numerical failures produce an unapproved complete
result with all samples retained. Engine failures preserve logs/snapshots and a
failed pipeline record. Both cases require a new output directory for any retry.

## Development observations, 2026-10-04

The final local record is `reports/native-root-runtime-validation-v1/checks.json`.
These are development assets from earlier studies, **not formal held-out trials**:

| Saved resource | Complete times | Bones | Vertices | Largest mode skin difference |
| --- | ---: | ---: | ---: | ---: |
| Procedural articulated cube | 1,101 | 6 | 8 | 0.000267 mm |
| Supplied humanoid | 2,201 | 77 | 18,056 | 0.000833 mm |

Both use rotated/translated placements and actual CPU Godot 4.7.2. All sampled
pose, root anchoring, actor application, root delta, native key and skin conditions
pass with the existing pose/skin limits, including the unchanged 0.1 mm skin limit.
Repeated/reversed preview poses match forward samples exactly. Ten ineligible
bindings per asset and invalid clock requests reject without pose/cursor mutation.

An initial humanoid run exposed a repeated-clock residual caused by multiplying
a rotating transform by its inverse. It remains in
`reports/native-root-runtime-humanoid-v1`; the adapter now explicitly returns
identity when time does not change. A successful repair run and the final fully
bound runs have separate directories. No failed or prior evidence was replaced.

The model-free Python suite tests bone reordering, complete skin correspondence,
noncommuting transforms, double root application, wrong multiplication side,
preview leaks, partial skeletons, invalid clocks, changed native keys/durations,
corrupt topology, failure preservation and source snapshots. Its engine outputs
are explicit **test doubles**, separate from the actual headless observations.

This does not certify rendered appearance, frame-rate performance, scene/object
runtime contact, events during animation playback, transitions, loops, physics,
semantic action correctness or animator cleanup time. The full project goal and
formal release gates remain open. Next integrate the component with the complete
multi-actor/object/event clock and broaden actual humanoid/rig/action trials.

Primary API references: Godot's [Skeleton3D global-pose semantics](https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html),
[Animation track API](https://docs.godotengine.org/en/stable/classes/class_animation.html)
and [AnimationPlayer](https://docs.godotengine.org/en/stable/classes/class_animationplayer.html).
