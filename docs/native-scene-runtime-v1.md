# Finite native scene playback

`scripts/native_scene_runtime.py` turns an existing native game asset ZIP into a
portable Godot scene with a shared finite clock for all actors, saved object
motion, root extraction and explicitly confirmed gameplay intent. It supports
supplied actions through their native resources; no action-name whitelist or new
motion generation is involved.

The original character GLBs, selected animations, saved resources, contact intent,
root references and gameplay request remain byte-identical. The original game
manifest is retained as `source-game-package.json` in a new `runtime-assets.zip`.
Runtime components/settings live under `runtime-v1/`, leaving the original
package's helper files untouched. Old reports and failed attempts are preserved.

## Use

Create a JSON modes file with an explicit choice for every actor:

```json
{"A": "extracted", "B": "embedded"}
```

Then run:

```powershell
python scripts/native_scene_runtime.py GAME_ASSETS.zip FRESH_OUTPUT_DIRECTORY --modes MODES.json --engine GODOT_EXECUTABLE
```

The model-free Python dependencies and Godot executable must already be available.
The public repository does not bundle third-party character payloads or engine
binaries. Existing asset/model licenses continue to apply to the exported files.

The worker snapshots the entire input ZIP, checks its exact member population,
hashes every original member and rejects duplicate/case-colliding, absolute or
traversing paths. The complete ZIP has an explicit 1 GiB budget; exceeding it
rejects before extraction rather than dropping files. Source selection, root
choices, contact intent, complete clock and marker timing/confirmation are checked
against the source request. Roots must contain the whole skeleton, including
unweighted gameplay bones; arbitrary reference joints are not extraction roots.

The resulting ZIP includes `project.godot` and a Node3D scene that can be embedded
in a game. The bootstrap uses an absolute monotonic clock and forwards a
`gameplay(event)` signal. It starts event dispatch on the first process tick, so
the parent scene can connect its listener in `_ready()` after the child becomes
ready. It provides character/object nodes and movement; the
game supplies its camera, environment and gameplay consumers. No rendered preview
or frame-rate certification is inferred from the headless checks.

## Runtime components

- `godot_native_scene_loader.gd` checks configured file hashes, imports the exact
  selected GLB animation and loads the previously saved native Animation resource.
  It does not recreate native keys. Failed loading frees only its newly created
  container; an already loaded scene remains intact.
- `godot_native_root_adapter.gd` retains embedded root motion or moves it onto
  the actor once, preserving full root rotation and vertical motion. Its existing
  whole-skeleton, rigid-transform and LINEAR bone-track limits remain in force.
- `godot_native_object_player.gd` evaluates saved rigid object tracks directly.
  It accepts a single object used as the AnimationPlayer root as well as objects
  below a common parent. Method/audio tracks, duplicate targets, non-unit scale
  keys, missing objects and unsupported interpolation reject.
- `godot_native_scene_player.gd` owns all participant poses and their finite
  playback clock. It preflights every participant before any advance, preview or
  restart, so a broken last actor cannot partially advance earlier actors or props.
- `godot_scene_game_events.gd` retains the existing binary Float64 clock and
  integer marker indices. Only explicitly timing-confirmed gameplay intent can
  dispatch. Sampled contact success never confirms gameplay or attachment.

All resources are duplicated in memory before evaluation. Character/object
files stay unchanged. Concurrent animation trees, pose modifiers, extra actor
skeletons/players, unskinned accessories, physical simulation and competing
built-in root-motion extraction remain unsupported ownership conflicts.

## Callbacks at the right pose

Advancing directly from zero to a clip's end must not call a grasp listener while
showing the end pose. The controller splits that request at each crossed confirmed
marker time, samples **all actors and objects** there, then dispatches the markers
in their original stable order. Simultaneous partner markers see the same pose
and clock. It samples the requested destination after processing earlier markers.

Callbacks therefore see the scene at the event's exact authoritative clock time,
including when frames are skipped. Contact boundaries and unconfirmed gameplay
intent remain non-dispatchable. No generated event name is treated as an action
being performed correctly.

`root_deltas` covers the entire external advance for each actor, including its
intermediate event samples. The actor transform is already applied in extracted
mode. Applying that transform a second time doubles motion. Repeated playback
times produce exact identity deltas and do not repeat markers.

Callbacks cannot reenter advance, preview or restart: those requests reject
without changing the scene. Consumers must not change the owned pose graph or
reparent the authored objects while this controller is active. The events are
notifications for game integration, not a verified grasp/physics consumer.

## Preview and restart

The controller deliberately keeps `pose_time_s` separate from `playback_time_s`.
`seek_preview(time)` changes the visible poses silently; it does not rewind the
playback/event cursor, replay effects, or replace the last playback root deltas.
The next valid advance restores the requested playback pose before dispatch.

`restart()` explicitly starts a new traversal, samples zero silently, resets root
deltas and clears the event cursor. Initial markers dispatch on the next advance.
It does not undo gameplay effects from a previous traversal.

Playback advances are finite, forward and within the shared duration. Backwards,
negative, nonfinite or out-of-range requests reject without modifying participant
poses, root deltas or event cursors. The bootstrap holds the terminal pose by
requesting the exact duration; the game's simulation clock remains separate.
There is no transition blend, loop wrap or reverse gameplay protocol here.

## Verification and limits

The worker checks embedded, extracted and mixed modes with every source clock
sample. Headless Godot records complete bone worlds, actor/root transforms,
object worlds, saved native keys, raw imported skin bindings/weights/triangles,
complete skeleton/mesh-node world transforms,
repeated/reversed previews, and scene snapshots inside actual event callbacks.
It tests full, whole-clip, skipped and repeated event traversals, seven malformed
scene configurations, invalid clock changes, reentrant callbacks and a hierarchy
change in the last participant. The actual exported bootstrap also runs for four
headless process frames; an enclosing scene connects its listener after child
readiness and must receive all initial markers at the zero pose. This is a startup
check, not a frame-rate benchmark.

Existing pose/skin/object limits remain unchanged. CPU skin comparisons retain
all vertices and raw imported weights; no normalization or smaller population
can hide a failure. Every original saved object key is compared with its GLB
counterpart, in addition to full-clock object poses. Complete Float64 observation
arrays retain dtype, shape and bytes through NPZ readback. Original assets and
executed/archived method bytes are checked again before ZIP packaging and readback.

The additional `native_runtime_affine_skin.py` check reconstructs skin in
skeleton space, then applies the actual mesh-node world transform. Godot's
quantized raw weights can sum slightly below one. Multiplying world bones by
those weights scales the outer translation; the local-skin/mesh-transform order
applies that translation once. Identical bone worlds therefore do not imply
identical mesh positions after root extraction. The earlier weighted-world-bone
diagnostic remains recorded, with this separate affine check governing the full
scene result under the unchanged 0.1 mm skin limit. Every imported surface vertex,
including duplicated equivalent skin functions, participates. No weights are
modified. This CPU reconstruction follows the pinned engine's shader algebra;
actual GPU arithmetic and rendered appearance remain unverified.

Numerical failures keep a complete unapproved result and package with
`finite_scene_controller_verified: false`. Engine failures preserve their logs,
snapshots and failed pipeline record. Neither output can be overwritten by retry;
each attempt requires a fresh directory. A successful scene/controller check is
separate from physical contact, motion realism and release acceptance.

The local final record is `reports/native-scene-runtime-validation-v3/checks.json`.
Its procedural case uses two articulated cube characters and a saved prop resource.
The humanoid case explicitly duplicates a recorded humanoid clip/resource into
two placed actors for concurrency testing; it does not claim a newly generated
partner interaction or a formal held-out action. Extra-partner collision geometry
is unverified, and no scene geometry or motion model is rerun for these checks.

| Fixture | Complete times per mode | Actors | Imported vertices per actor | Largest affine skin difference |
| --- | ---: | ---: | ---: | ---: |
| Procedural | 1,101 | 2 | 8 | 0 mm |
| Recorded humanoid copies | 2,201 | 2 | 18,056 | 0.049916 mm |

All three root modes pass. Each mode delivers the five confirmed markers in four
traversal scenarios with zero callback pose difference. The unconfirmed marker
never dispatches. Source-byte, executed-method, complete array and ZIP receipts
verify; physical/quality/release approval remains false.

Model-free Python tests use explicit engine doubles to cover package corruption,
whole-scene populations, native key changes, late callbacks, pose/object/preview
errors, intent/confirmation changes, source snapshots, failed-result retention and
ZIP readback. Actual Godot results are separate from those test doubles.
The related model-free suite passes 129 checks, including negative controls where
bone worlds match but the raw-weight affine skin error must fail.

The full project goal remains active. Rendered appearance, timing under real frame
load, transition/loop integration, physical attachment/collision, broad held-out
action/rig coverage and developer/animator review remain open. Studio's original
game packages are still separate immutable inputs; this CLI provides the next
engine integration step without restarting the live Studio server.

Primary API references: Godot [Animation tracks](https://docs.godotengine.org/en/stable/classes/class_animation.html),
[GLTFDocument import](https://docs.godotengine.org/en/stable/classes/class_gltfdocument.html)
and [signal callbacks](https://docs.godotengine.org/en/stable/classes/class_signal.html).
The version-pinned skin algebra is in Godot's
[local skeleton shader](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/drivers/gles3/shaders/skeleton.glsl),
[subsequent scene vertex transform](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/drivers/gles3/shaders/scene.glsl)
and [bone/bind upload](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/3d/skeleton_3d.cpp).
