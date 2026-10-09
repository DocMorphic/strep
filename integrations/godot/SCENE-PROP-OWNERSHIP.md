# Shared native scene prop ownership

`scripts/godot_scene_prop_owner.gd` is an opt-in source SDK for a finite
`godot_native_scene_player.gd`: one scene clock drives every actor, and multiple
`godot_scene_prop_body.gd` bodies integrate their own physics. Explicit grip sets
support two-hand holds, partial release, simultaneous changes, handoffs between
characters, and independent release of several props. Events authorize intent;
they do not certify a successful grasp or believable animation.

This SDK requires explicit bindings. The [source-bound package exporter](../../docs/scene-prop-runtime-v1.md)
can install bodies and providers from authored source joint/offset choices;
Studio does not yet create those bindings. The existing
[single-prop consumer](OBJECT-EVENTS.md) and [baked scene clock](SCENES.md) retain
their separate contracts. Do not attach them as additional drivers of this scene.

## Compile explicit intent

Start with the exact native `events.json` used to bind the native scene player.
Write an ownership request; use actual event IDs and actor IDs from that file:

```json
{
  "schema": "strep-scene-prop-ownership-request-v1",
  "objects": ["P"],
  "grips": {"AL": {"actor": "A"}, "AR": {"actor": "A"}, "BL": {"actor": "B"}},
  "commands": [
    {"event_id": "grab", "object": "P", "grip": "AL", "action": "acquire"},
    {"event_id": "grab", "object": "P", "grip": "AR", "action": "acquire"},
    {"event_id": "partial", "object": "P", "grip": "AL", "action": "release"},
    {"event_id": "giver", "object": "P", "grip": "AR", "action": "release"},
    {"event_id": "receiver", "object": "P", "grip": "BL", "action": "acquire"},
    {"event_id": "drop", "object": "P", "grip": "BL", "action": "release"}
  ],
  "position_tolerance_m": 0.001,
  "rotation_tolerance_rad": 0.001
}
```

For an atomic handoff, `giver` and `receiver` must have the same source sample
index. The compiler uses the unchanged binary Float64 clock and sample indices,
not rounded descriptive JSON times. Command order cannot create a transient
release. A grip can own only one prop at a time; it can switch props within one
transaction. Only timing-confirmed, dispatch-enabled gameplay events can command
ownership. Contact intent cannot. Actor IDs must match the commanded grips.

```powershell
python scripts/scene_prop_ownership.py --events events.json --request ownership-request.json --output ownership.json
```

The output is created exclusively; existing files are not overwritten. Source
event and request file hashes are recorded. The compiler checks ownership and
clock consistency without editing either input. It accepts 1–32 props, 1–64
explicit grip bindings and at most 1,024 commands/source events. Pose bounds must
be positive and no larger than 0.01 m/rad. Quality and release flags remain false.

## Bind actual actors, bodies and providers

Copy the owner/body scripts and their native scene dependencies together, keeping
their relative filenames: `godot_native_scene_player.gd`,
`godot_native_root_adapter.gd`, `godot_native_object_player.gd`,
`godot_scene_game_events.gd`, `native_engine_clock.gd` and
`native_godot_preview.gd`. Bind the native scene's actual actor AnimationPlayers,
Skeleton3Ds, root bones and extraction modes first, as in
[native scene playback](../../docs/native-scene-runtime-v1.md). All clips must
share the source duration. Actor-only binding is supported:

```gdscript
const NativeScene = preload("res://godot_native_scene_player.gd")
const PropBody = preload("res://godot_scene_prop_body.gd")
const PropOwner = preload("res://godot_scene_prop_owner.gd")
var native_scene = NativeScene.new()
var owner = PropOwner.new() # Retain this instance for the scene's lifetime.

# actor_entries contain id, player, skeleton, actor, clip, root_bone and extract.
assert(native_scene.bind(actor_entries, null, &"", {}, source_events) == OK)
# Every body uses PropBody, a centered collision shape and authored rigid pose.
# Configure mass/inertia, material, collision layers/masks and damping first.
# Add each body to the world before binding. No body may also be a baked prop.
assert(owner.bind(native_scene, ownership_document, prop_bodies, grip_providers,
                 Engine.physics_ticks_per_second, 1800) == OK)
owner.faulted.connect(func(reason): push_error(reason))
owner.actions_applied.connect(func(actions): print(actions))
owner.transaction_committed.connect(func(receipt): print(receipt.commit_id, receipt.record.members))
owner.sampled.connect(func(record): print(record.physics_root_deltas))
```

Each provider is a read-only `Callable(object_id)` returning a finite, rigid
**world transform of that prop's center of mass**. Author the mapped bone and
grip-to-prop-center offset explicitly, including a different offset per prop:

```gdscript
var left_provider = func(object_id: String) -> Transform3D:
    var helper = native_scene.actors["A"]
    var bone = helper.skeleton.find_bone(mapped_left_hand_bone)
    return helper.skeleton.global_transform * \
        helper.skeleton.get_bone_global_pose(bone) * grip_offsets[object_id]
```

All active hands must request compatible prop poses within the configured bounds.
The lexicographically first grip supplies the target after every grip is checked;
poses are never averaged and no conflicting hand is dropped. Acquisitions and
handoffs also check continuity against the incoming prop pose; an out-of-bounds
snap faults rather than applying an implicit correction. Alignment/catches and
anatomical grip authoring remain application responsibilities.

The first body callback advances all actors once per common physics boundary.
Marker substeps visit exact source times; `physics_root_deltas` reports the root
movement across the **whole** step, rather than just the final marker substep.
Other callbacks apply the same transaction to their bodies. Missing/repeated
callbacks, provider clock changes, outside scene drivers and a changed physics
step fault. Bind rejects a second owner before mutating the bodies. Use a fresh
native scene to replace a binding; this version has no unbind/rebind API.

## Physical and transport limits

Set `physics/common/physics_ticks_per_second` to 60, 120 or 240 **before engine
startup**. Pass the matching rate at bind. Runtime rate changes and time scaling
are unsupported. All three rates have development evidence; none has exact
fractional physics timing approval. Source markers remain exact, but body
transitions apply at the next physics boundary. Inspect each action's
`source_time_s`, `physics_application_time_s` and `application_delay_s`. The
1.305 s fixture applies 11.667 ms late at 60 Hz and 3.333 ms late at 120/240 Hz.
There is no fractional contact response or compensation for this delay.

Only loss of the last grip releases a prop. Inherited linear/angular velocity
uses the causal previous held pose and exact release pose; it is a sampled
estimate. Released bodies receive the engine's gravity/damping and collision
response. Bodies are unsleeping, use a custom integrator and have their center of
mass fixed at the origin. Keep collision geometry centered and provide matching
inertia. The study validates a cylinder and sphere; broader shapes need their own
integration checks.

Parked, held, paused and previewing props have collision layers/masks zero. They
do not enforce obstacle clearance or physically constrained grips. Characters
remain prescribed animation and do not respond to prop collisions. Released
props restore their original masks; faulted props stop at the last complete
recorded poses. The 60 Hz test reached **63.229 mm** floor penetration, exceeding
the unchanged 10 mm sampled screen. Higher-rate results do not imply general
collision safety or motion quality.

`pause_playback()`, `resume_playback()`, `restart_playback()` and
`preview_tick(tick)` queue one command for the next common callback. Handle
returned errors. Preview silently shows a retained whole-scene record and
disables prop collisions. Resume returns to the saved live cursor, membership,
poses and velocities; it does not branch physics from the previewed past.
Restart clears history and starts a new traversal/session. History is bounded
to 2–3,600 records; expired previews reject without changing state. Actor pose
holds at the finite endpoint while released prop physics continues.

Other scene objects, solver contact caches, native gameplay listeners and their
side effects are not rolled back. Use `transaction_committed` for an immutable
whole-boundary receipt after every owned body supplies its assigned state.
The existing `actions_applied` callback still receives the action list. Source
`gameplay` callbacks observe actor poses before the physical transaction completes.
Neither callback grants grasp, realism or release approval. Faults require application
recovery with a fresh binding; they do not undo already emitted gameplay effects.

## Consume a committed ownership receipt

`transaction_committed(receipt)` emits once per successful live physics boundary
that contains ownership changes. Simultaneous prop changes share one receipt.
Failed preparation or a missing participant cannot dispatch a receipt for that
boundary. Pause, retained preview and resume do not replay notifications; restart
creates a new session and allows the authored changes again.

All dictionaries and arrays in the receipt are recursively read-only, detached
from the owner. Its `record` includes every prop's membership, mode, tracking pose,
assigned direct-state pose/velocity/spin, contacts and physics properties. Actor
root motion and extraction modes accompany that same source clock. `source_events`
contains the original contracts used by these actions, in source order, once per
event even when that event commands several hands or props.

The `commit_id` combines the live `owner_instance_id`, session and physics tick.
Keep the instance ID as a string: Godot RefCounted IDs may be negative and exceed
JSON's exact floating-point integer range. This identifies a live binding, not a
durable character or network identity. Bind your game's entity identity separately.

Each action retains `source_time_s`, `physics_application_time_s` and
`application_delay_s`. `action_clock` also stores those three values, in that order
for every action, as little-endian Float64 bytes. Default decimal JSON output can
round them; preserve the binary field or use full-precision serialization when
recording receipts. `source_clock` remains the unchanged authored binary clock.

`props_state_phase` is `assigned_before_force_integration`. The snapshots describe
the states assigned during the body callbacks, before the owner invokes force
integration. They are not settled post-collision results or a grasp certificate.
The fixed-boundary application delay, disabled held-prop collisions and documented
timing/depth failures remain. Listeners may queue transport commands for the next
boundary; other gameplay side effects cannot be undone by this SDK.

[Receipt validation and engine evidence](../../docs/scene-commit-receipts-v1.md)
includes complete-state callbacks, detached-copy isolation, atomic handoff and
partial release, restart/preview behavior and retained physical failures.

[Development evidence](../../docs/scene-prop-ownership-v1.md) covers procedural
fixtures and headless Jolt physics. No production character rendering, animator
review, crossfade ownership, arbitrary moving-world replay or Studio integration
has been validated here. Integration follows Godot's
[RigidBody3D contract](https://docs.godotengine.org/en/stable/classes/class_rigidbody3d.html#class-rigidbody3d-private-method-integrate-forces)
and [direct body state API](https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate3d.html).

## Explicit CCD comparison

The original 60 Hz sampled floor-depth failure has a measured development remedy
for the existing cylinder/sphere fixture. With both bodies' `continuous_cd`
already enabled, an explicit project setting activates CCD at smaller motion:

```ini
[physics]
jolt_physics_3d/simulation/continuous_cd_movement_threshold=0.05
```

The matched pinned-engine comparison reduces maximum sampled floor penetration
from 63.229 mm to 1.008 mm in both body orders, without changing the physics rate,
ownership clock, authored poses, release velocities, geometry or 10 mm depth
screen. The native study CLI exposes this as `--collision-profile ccd-threshold`;
its default remains `engine-default`. This setting is opt-in for an integrating
project and is not applied globally by the ownership SDK or Studio. Other shapes,
speeds, scales and production scenes need their own validation; CPU cost is not
established by the single short fixture. Tighter CCD penetration fraction adds
no measured benefit here. Exact physical event timing still fails by 11.6667 ms
at 60 Hz, and held-prop collisions remain disabled.

[Matched settings, retained raw failures and reproduction](../../docs/scene-collision-profiles-v1.md).
