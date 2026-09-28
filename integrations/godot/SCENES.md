# Shared finite scene playback

This package plays all actor and object GLBs on one owned clock. It retains authored placement and existing contact/quality failures. All object tracks are **baked animation**, including any previously simulated release. They have no live physics body and must not also receive a second transform or physics driver.

Copy the package into your Godot project. Add a Node3D for the scene's placement in your level, then bind:

```gdscript
var clock = preload("res://your_package/godot_scene_clock.gd").new()
add_child(clock)
assert(clock.bind_package("res://your_package", scene_parent) == OK, clock.last_error)
clock.marker.connect(func(event): print(event.payload, event.time_s))
assert(clock.play() == OK)
```

The loader checks asset hashes, relative paths, actor placements, participant references, a common finite duration and explicit baked object ownership. It stages imports before adding them to the parent, then samples every participant at zero. It imports with constant scale tracks retained to preserve object quaternion rotations. Actor placement is applied once; objects already use scene coordinates. Moving/rotating `scene_parent` places the complete scene in your level. Root extraction is not applied here.

`play(rate)` advances automatically on physics updates, with nonzero rates from -4 through 4. `pause()` holds all tracks. `seek_preview(seconds)` pauses and silently samples the complete scene. `restart(true)` returns to zero and optionally notifies initial authored markers; call `play()` to resume. Manual `advance(seconds)` and `rewind(seconds, notifications)` clamp at their finite endpoints. Do not combine automatic and manual advancement or drive the contained AnimationPlayers elsewhere. The final sample holds for one interval; `finished` is emitted only when forward playback reaches the duration. Reverse playback stops at zero.

All actor/object poses update before `sampled`, marker or completion notifications. Commands that change the clock during its callbacks return `ERR_BUSY`; pause is allowed. Reverse notifications use `marker_reversed` only, descending time and reverse metadata order for simultaneous events. Silent seeking never dispatches authored actions. Coarse updates report every crossing with its authored `time_s` and the current `observed_at_s`; they do not resimulate the interval. `unload()` removes owned scene instances. Freeing the clock also queues its owned scene for removal.

Events describe authored intent/contact windows or a recorded simulation boundary. They do not certify successful contact, move objects between parents, start physics, play sounds or reverse external gameplay effects. Preserve the source events and evaluation files. This runtime resolves playback ownership only; hand/body intersections, implausible reactions and other retained motion defects still need correction and review.

Scope: 1–4 actors, 0–8 baked box objects, 3–1,800 samples at 30 fps; each asset must contain exactly one finite non-RESET animation on the shared sample span. Binding failures leave no imported participants in the scene. Different per-actor clocks, crossfades, live attachment handoffs, collision response and networking are separate integrations. The current packager is for the project's native SOMA study scenes and includes their license; it is not a license generator for arbitrary third-party assets.
