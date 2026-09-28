# Finite clip clock

Use `character.glb`, `runtime-finite.json`, `godot_finite_adapter.gd` and its `godot_cycle_adapter.gd` base together. This clock is distinct from the older method-track `godot_clip_adapter.gd`. Bind one fresh imported rig, one AnimationPlayer and an actor ancestor, with no AnimationTree, root-motion track or second driver.

```gdscript
var clock = preload("res://godot_finite_adapter.gd").new()
actor.add_child(clock)
var data = JSON.parse_string(FileAccess.get_file_as_string("res://runtime-finite.json"))
assert(clock.bind_finite(player, skeleton, actor, clip, data, "res://character.glb", true) == OK)
var placement = actor.global_transform
# In your update, unless a prop consumer owns the clock:
assert(clock.advance(delta) == OK)
actor.global_transform = placement * clock.root_motion_transform
```

With extraction enabled, apply the full relative root transform exactly once. With extraction disabled keep actor placement fixed. Imported animation must be finite, 2–900 samples at 30 fps with its final key at `(frames-1)/30`. Hash and timing are checked. Weighted skin joints must descend from the mapped root; optional metadata export reports unsupported assets rather than removing their animation.

The **pose** clamps at the final sample; the **simulation clock** continues. Markers fire once per forward crossing and do not repeat after the clip. `clip_finished` fires when crossing `frames/30`, after one terminal sample interval, once on each forward crossing of that boundary. A silent seek emits neither markers nor completion. This lets a released prop continue falling after the character action ends.

`restart(false)` silently resets to zero; `restart(true)` additionally emits authored phase-zero markers. `seek_preview(seconds)` is silent. `rewind(delta, true)` emits reverse notifications through `marker_reversed`, in reverse time/order, and never forward actions. Crossed marker intervals match the cycle adapter: `(before,after]` forward and `[after,before)` backward. Reverse notifications do not undo physics. Time limits and compensated clock accumulation follow the base cycle adapter.

For physical attachment/release, follow `GODOT-OBJECT-EVENTS.md`, passing this clock to `bind_prop`. The consumer exclusively owns it at fixed physics steps. Terminal-sample release is permitted; release after the last sample is not an authored event. The prop's recorded transport remains distinct from raw clock seeks. One prop per clock and the other consumer limits still apply. Coarse raw clock advances dispatch intent at the end of the update; they do not retroactively simulate physics.

This finite path does not infer pickup, throw or contact quality, and is not automatically bound from prompts or event names.
