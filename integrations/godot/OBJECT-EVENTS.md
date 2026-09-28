# Authored attachment and physical release

`godot_event_object_body.gd` is an opt-in `RigidBody3D` consumer for one prop and one exclusively owned `godot_cycle_adapter.gd` or `godot_finite_adapter.gd`. It follows an application's world-space grip transform between two authored events, then releases the prop into Godot physics with the grip's linear and angular velocity. No event names are interpreted automatically: the application binds two exact event IDs. Timing confirmation means intent, not a verified grasp.

This consumer supports one attach followed by one release in cycle zero or in a finite clip. Later repetitions do not teleport the released prop back to the hand. An explicit restart begins a new session. It does not consume blended-controller events, a second character or multiple hand constraints yet. One body owns the animation clock; do not attach several consumers to the same clock or advance it elsewhere. For finite clips see `GODOT-FINITE.md`; pose holds at the end while prop physics continues.

## Setup

Import the exact `character.glb`, bind its cycle adapter as described in `GODOT-CYCLES.md`, and leave its cursor at zero. Add a prop using this script and a centered collision shape beneath a world node with identity scale. Set its initial world transform, mass, collision layers/masks, material and damping before binding. The script uses a custom center of mass at the body origin, disables sleeping, and takes over force integration. Do not also freeze the body or add a second integration callback.

Use 60 physics ticks per second for the validated path. The API accepts integer multiples of the 30 fps clip rate from 30 through 240; only 60 has been evaluated in the four-fixture study. Time scaling, a changed physics step and outside clock changes are unsupported and stop playback. Wall-clock rendering speed does not drive this clock.

```gdscript
const EventProp = preload("res://godot_event_object_body.gd")
var prop = EventProp.new()
# Add a CollisionShape3D, set placement/mass/material, then add prop to the world.
# cycle, actor and skeleton are already bound. Keep the initial actor placement.
var placement = actor.global_transform
var hand = skeleton.find_bone("hand_r") # Use your rig's mapped hand bone.
var grip_to_prop_center = Transform3D.IDENTITY # Author this offset for the prop.
var grip = func() -> Transform3D:
    actor.global_transform = placement * cycle.root_motion_transform
    return skeleton.global_transform * skeleton.get_bone_global_pose(hand) * grip_to_prop_center
assert(prop.bind_prop(cycle, grip, "your-grasp-event-id", "your-release-event-id") == OK)
# Do not call cycle.advance(): prop now owns it on physics ticks.
prop.faulted.connect(func(reason): push_error(reason))
```

The provider must return a finite, rigid world transform for the **prop center of mass**, including the authored grip offset. Offset motion and actor root movement therefore contribute to release velocity. An attach snaps to that pose; the author is responsible for a plausible approach and alignment. Both bound markers must be distinct timing-confirmed `authored` entries, with an attach after frame zero and a later release inside the first cycle. JSON cannot select nodes or invoke arbitrary game methods.

Parked, attached, paused and previewing props have collision layer and mask zero. Attached bodies therefore do not push obstacles or prevent interpenetration. On release the original collision layer/mask are restored. Gravity/damping and contact response come from the engine, not a baked falling trajectory. The current pose and previous physics-tick grip pose define inherited velocity; this is a sampled estimate, not a fitted physical throw model. Character collisions require separately authored collision geometry.

## Transport ownership

- `pause_playback()` restores the most recent recorded physics boundary and holds it without advancing the animation. `resume_playback()` restores its pose and velocities and continues.
- `preview_tick(tick)` silently shows an available recorded boundary, including earlier or later recorded states. Calling it with decreasing ticks gives reverse preview. It emits no attach/release actions and disables collisions. Seeking before the retained history returns an error without changing state.
- Resume from preview returns to the **saved live cursor**. It does not branch physics from the previewed past. This avoids pretending that other gameplay objects, sounds or world state have been rolled back.
- `restart_playback()` resets this prop and its owned character clock to their initial states, clears history, and permits the pair of actions in a new session. External gameplay effects are not undone. Do not connect restart to world-wide rollback logic without implementing that separately.
- Commands are queued for the next physics callback. Only one pending command is accepted; callers must handle returned errors. `sampled` reports the applied command and transport state. History defaults to 1,800 ticks; binding accepts 2–3,600. It is bounded and old entries expire.
- Reverse marker notifications are not connected. Arbitrary forward-signal emissions outside the consumer's fixed step are ignored. Other forward marker listeners can still have their own effects; this component does not manage those listeners.

Pause/resume is evaluated with one body and a static floor. Collision solver contact caches, other moving bodies and arbitrary world rollback are not serialized. This is not deterministic save-game or network rollback support. Persist event side effects separately if your game needs them.

## Evidence and limits

Development studies: `reports/godot-event-object-v2/verification.json` and `reports/godot-event-object-small-angle-v1/verification.json`, four existing cycle fixtures/two rig families on pinned Godot 4.7.2 GodotPhysics3D at 60 Hz. The second uses the revised small-angle spin calculation also evaluated on finite terminal release. Checks cover independent GLB-derived grip poses, event timing, inherited velocities, free flight, actual floor contacts, bounded history, silent scrubbing, interruption/resume and replay. The bindings are explicit software fixtures on existing clips; they do not assert convincing pickups or human approval. The missing-velocity negative control is expected to fail clip validation.

Use the packaged source with its provenance. These results do not establish Jolt/other engine behavior, GPU appearance, two-handed manipulation, crossfade attachment ownership, moving-world replay or motion quality.

Implementation follows Godot's [RigidBody3D integration contract](https://docs.godotengine.org/en/stable/classes/class_rigidbody3d.html#class-rigidbody3d-private-method-integrate-forces) and [PhysicsDirectBodyState3D](https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate3d.html). Body state changes happen in the physics callback; released bodies explicitly use the engine's gravity/damping force integration.
