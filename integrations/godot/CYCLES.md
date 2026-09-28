# Periodic target-rig playback

For explicit authored object attachment and physical release, `GODOT-OBJECT-EVENTS.md` describes the opt-in `godot_event_object_body.gd` consumer. It owns a single cycle clock on fixed physics ticks; use its setup instead of advancing the same clock from this page's example. Bindings are never inferred from motion or event names.

For forward switching between two same-rig cycle clips, the package also includes `godot_cycle_blend.gd` and `GODOT-BLENDS.md`. That controller uses separate hidden cycle donors and explicit event ownership. Follow its setup instead of applying two animation drivers to one skeleton.

Use the one-cycle `character.glb`, `runtime-cycle.json` and `godot_cycle_adapter.gd` together. The final sample is the next cycle's phase zero; do not add a terminal hold or enable Godot's automatic looping. Use a fresh imported scene and the exact original GLB path. The adapter checks its hash and period, then controls the AnimationPlayer manually. Do not combine it with AnimationTree, another animation driver, SkeletonModifiers, or the finite-clip adapter.

Create a Node3D `actor`, import the GLB beneath it, find its AnimationPlayer and Skeleton3D, and select its only non-RESET animation. Add the adapter as another actor child:

```gdscript
const CycleAdapter = preload("res://godot_cycle_adapter.gd")
var adapter = CycleAdapter.new()
actor.add_child(adapter)
var data = JSON.parse_string(FileAccess.get_file_as_string("res://runtime-cycle.json"))
var initial = actor.transform
assert(adapter.bind_cycle(player, skeleton, actor, animation_name, data,
    "res://character.glb", true) == OK)
adapter.marker.connect(func(event): print(event.name, event.cycle, event.time_s))
# Each physics update (the caller owns pause and playback speed):
assert(adapter.advance(delta) == OK)
actor.transform = initial * adapter.root_motion_transform
```

With extraction enabled (`true`), the pelvis stays at its initial clip transform inside the skeleton. `root_motion_transform` is the full relative pelvis transform, including vertical movement, tilt and rotation. Applying it once to `actor` reconstructs the world motion. It is not a horizontal locomotion controller. For incremental game integration use `actor.transform = actor.transform * adapter.root_motion_delta`, after each successful advance. Deltas use right multiplication in actor-local coordinates. Handle collision constraints in your own controller; collision response will change the motion and contact quality. Do not apply both the absolute transform and delta.

With extraction disabled (`false`), the skeleton itself accumulates the cycle transform. Keep the actor at its intended scene placement and do not apply the returned motion again. Weighted vertices must belong to the pelvis subtree for the extraction contract; packaging rejects unsupported weighted ancestors or rigid primitives. Other skeleton ancestors can have different world transforms in extracted mode, while skinned descendant motion agrees.

`seek_preview(seconds)` samples any nonnegative time silently and resets the reported delta. With extraction enabled also set the actor's absolute transform as above. It does not replay events or reconstruct gameplay state. `restart()` silently returns to zero; optional `restart(true)` emits explicitly supplied phase-zero markers whose first_cycle is zero. Generated cycle-boundary markers start at cycle 1. Forward `advance` emits every crossed marker once, including during coarse steps across several cycles; dispatch occurs on that update. Zero advances do not repeat events. Negative arguments to `advance` and steps over 1,024 periods are rejected before mutation. The clock is limited to 1,000,000 periods.

Use `rewind(delta)` to move backward by a nonnegative duration. Root transforms and right-composed deltas work in both directions, including across cycle boundaries. Rewind is silent by default. `rewind(delta, true)` emits crossed markers through the separate `marker_reversed` signal with `direction = -1`; it never emits the forward `marker` signal. These notifications do not undo a sound, spawned object, attachment, release or physics state. The game must explicitly implement any such reversal.

Reverse traversal includes its destination and excludes its starting cursor, traversing events in descending time and reversing metadata order for simultaneous events. A marker can be crossed again after changing direction. Rewinding before time zero, a nonfinite/negative duration or more than 1,024 periods is rejected without changing the cursor, compensation, root transform or last delta. Zero rewind is a no-op with identity delta. Use a silent seek to position the initial cursor before starting reverse playback; no negative-time cycles are supported.

To stop exactly at the beginning, call `rewind(adapter.time_s, notify_crossings)` (within the per-call step limit), or use `rewind(min(delta, adapter.time_s))` in the update loop. Independently summing mixed forward/backward floating-point durations can leave a slightly different remaining cursor; the adapter does not use an epsilon to accept a requested traversal before zero. Consuming the exposed remaining clock sets both the cursor and its compensation to zero exactly.

Current metadata includes authoring cycle boundaries and timing-confirmed authored events. Loop and transition blends preserve source events, but partial-weight markers require explicit timing review in Studio before runtime dispatch. Excluded events and their reasons remain in the metadata; source history stays in the authoring package. Confirmed timing expresses authoring intent, not physical contact verification. Call `restart(true)` after connecting listeners if initial phase-zero authored markers should fire. The adapter never treats predicted contacts as verified grasps or collisions. This runtime does not fix floor penetration, foot sliding, action mismatch or unrealistic motion.

Verification scope and exact implementation hashes are supplied with the separately audited runtime packages. Headless engine tests establish transforms and event dispatch, not GPU appearance or game physics.

References: [AnimationPlayer silent seek](https://docs.godotengine.org/en/stable/classes/class_animationplayer.html#class-animationplayer-method-seek), [Skeleton3D bone poses](https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html#class-skeleton3d-method-set-bone-global-pose).
