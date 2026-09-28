# Switching between cycles in Godot

`godot_cycle_blend.gd` crossfades two independently bound cycle adapters into a third, visible skeleton. Both clips must use the same bone order, names, hierarchy, rest transforms and mapped pelvis. Retarget different characters before attempting a blend. The controller checks this compatibility; it does not retarget at runtime.

Import three scenes: hidden donor A, hidden donor B, and a visible output instance of the same character. Bind the donors with `godot_cycle_adapter.gd` as described in `GODOT-CYCLES.md`, with extraction **disabled** on both donors. Stop the output AnimationPlayer and set its callback mode to manual. The output skeleton must have no other animation driver, AnimationTree or SkeletonModifier. Keep both donors alive and let only the blend controller advance them.

```gdscript
const BlendController = preload("res://godot_cycle_blend.gd")
var blend = BlendController.new()
output_actor.add_child(blend)
assert(donor_a.seek_preview(0.4) == OK) # Choose initial phase silently.
assert(blend.bind_output(donor_a, output_skeleton, output_actor, "run", true) == OK)
blend.marker.connect(func(event): print(event.source_clip, event.name))
var placement = output_actor.transform

# Later: crossfade to B over 0.3 seconds, beginning B at 0.1 seconds.
# Event policy is an explicit argument; there is no implicit dual dispatch.
assert(blend.start_blend(donor_b, 0.3, 0.1, "sprint", "dominant") == OK)

# Each update:
assert(blend.advance(delta) == OK)
output_actor.transform = placement * blend.root_motion_transform
```

The example names identify clips; they do not generate or classify them. The controller blends local bone translation, shortest-arc rotation and scale. It aligns the incoming pelvis to the outgoing pelvis at blend start, then blends their full trajectories. With extraction enabled, apply the returned transform once to the output actor, as above. Alternatively compose `root_motion_delta` on the right of the actor transform. With extraction disabled, keep the output actor at its scene placement; its skeleton carries the motion. Do not apply both methods. The initial output anchor is the pelvis at `bind_output` time, so its initial returned motion is identity.

Event policies apply at each marker's crossing time, even if an update jumps across the whole blend:

- `dominant`: outgoing markers before 50%; incoming markers at and after 50%. The exact tie belongs to the incoming clip.
- `incoming`: incoming markers throughout the blend.
- `silent`: neither donor dispatches markers through the blend's inclusive end.

After the blend ends, the incoming clip becomes current and its later markers dispatch normally. Each forwarded marker keeps its source timestamp, cycle and authored payload, with `source_clip` and `source_weight` added. Simultaneous markers retain authored order. Source timestamps are clip times, not a new shared gameplay clock. Changing policy does not undo effects from previously emitted events. Semantic actions such as grasp/release need an appropriate caller-selected policy and game state handling; interpolation alone cannot decide ownership.

`start_blend` is silent, preserves the displayed pose, and rejects invalid times, duration, policy, incompatible rigs, the current donor or an already active blend. Source IDs must be nonempty and distinguish the two clips. Wait for `incoming == null` before starting another blend, reusing a compatible hidden donor if desired. Reentrant calls from a marker callback are rejected; queue those changes until `advance` returns. Forward updates are limited by each donor's cycle step/clock limits. A zero update produces an identity delta without repeated events.

The latest transition is retained after completion. `rewind(seconds)` silently traverses it backward, including from subsequent target playback back into the blend. `rewind(seconds, true)` sends reverse crossings on `marker_reversed`; it never invokes forward marker listeners. Ownership is evaluated at each crossing with the same policy and incoming midpoint tie. Reverse crossings include the destination and exclude the origin, with simultaneous events delivered in the inverse of forward order. Both donors follow one compensated transition clock.

For frame-accurate authoring, use `advance_frames(frames)` and `rewind_frames(frames, notify_crossings=false)` after starting a transition. They accept fractional frames and avoid conversion of exact frame intervals to rounded seconds. An integer or half-frame destination can differ by floating-point roundoff when reached through the seconds API; event comparisons do not use an early-crossing tolerance or snap the clock. Use the frame API when landing exactly on a marker matters.

Both donors must remain alive and exclusively owned by the controller. Reverse playback stops at the latest transition's start; a larger request is rejected without mutation. Use `rewind_frames(elapsed_frames)` to reach that boundary exactly. Before any transition, the seconds rewind API can reach the donor's time zero. A successfully started new transition replaces the retained history; earlier transitions are not traversable. Rewinding to the start leaves that transition available for forward replay. The same root transform/delta application rules apply in both directions. Reverse notifications do not undo gameplay effects.

Interrupted multi-way blending, older transition history, root collision response and pose/contact correction remain unsupported. Use baked authoring transitions when you need an editable fixed result. Crossfading can introduce foot sliding, collision or implausible poses even when the source clips look good. Runtime transform agreement is not animation-quality approval.

Implementation references: [Skeleton3D local/global poses](https://docs.godotengine.org/en/4.7/classes/class_skeleton3d.html), [Transform3D interpolation](https://docs.godotengine.org/en/4.7/classes/class_transform3d.html#class-transform3d-method-interpolate-with).
