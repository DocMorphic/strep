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

The loader checks asset hashes, relative paths, actor placements, participant references, a common finite duration and explicit baked object ownership. It stages imports before adding them to the parent, then samples every participant at zero. It imports with constant scale tracks retained to preserve object quaternion rotations. Object mesh compression is disabled to preserve exported primitive vertex positions. Actor placement is applied once; objects already use scene coordinates. Moving/rotating `scene_parent` places the complete scene in your level. Root extraction is not applied here.

`play(rate)` advances automatically on physics updates, with nonzero rates from -4 through 4. `pause()` holds all tracks. `seek_preview(seconds)` pauses and silently samples the complete scene. `restart(true)` returns to zero and optionally notifies initial authored markers; call `play()` to resume. Manual `advance(seconds)` and `rewind(seconds, notifications)` clamp at their finite endpoints. Do not combine automatic and manual advancement or drive the contained AnimationPlayers elsewhere. The final sample holds for one interval; `finished` is emitted only when forward playback reaches the duration. Reverse playback stops at zero.

All actor/object poses update before `sampled`, marker or completion notifications. Commands that change the clock during its callbacks return `ERR_BUSY`; pause is allowed. Reverse notifications use `marker_reversed` only, descending time and reverse metadata order for simultaneous events. Silent seeking never dispatches authored actions. Coarse updates visit every crossed marker in order and sample all participants at its exact `time_s` before the marker callback (`observed_at_s` equals that time), then restore the requested final time and emit one `sampled` notification. Reverse playback includes a terminal marker when leaving the final hold. This samples baked curves; it does not resimulate the interval. `unload()` removes owned scene instances. Freeing the clock also queues its owned scene for removal.

Events describe authored intent/contact windows or a recorded simulation boundary. They do not certify successful contact, move objects between parents, start physics, play sounds or reverse external gameplay effects. Preserve the source events and evaluation files. This runtime resolves playback ownership only; hand/body intersections, implausible reactions and other retained motion defects still need correction and review.

Scope: 1–4 actors, 0–8 baked primitive objects (boxes or spheres), 3–1,800 samples at 30 fps; each asset must contain exactly one finite non-RESET animation on the shared sample span. Spheres use a versioned geometry descriptor; their exported triangle approximation records an inset bound. Offline release supports matching box/sphere collision shapes and bakes the resulting trajectory before packaging; playback itself does not simulate physics. Binding failures leave no imported participants in the scene. Different per-actor clocks, crossfades, live attachment handoffs, collision response and networking are separate integrations. The current packager is for the project's native SOMA study scenes and includes their license; it is not a license generator for arbitrary third-party assets.

Runtime schema v2 permits finite fractional marker frames so uniform retiming does not round event timing to 30 fps. Integer-only event packages with a 30 fps export grid remain v1; non-30-fps import grids also require v2. The supplied runtime accepts v1, v2 and v3. Pose arrays remain 30 fps. Each actor/object export records its own `bake_fps`, derived from the actual common uniform animation key clock; Godot imports at that rate while every participant still plays on the shared scene clock. Old packages without this field default to 30. Mixed or nonuniform LINEAR/STEP clocks use schema v3 and hash-bound authored TRS sidecars. After import, the runtime restores exact keys on uniquely matched tracks before exposing participants. Invalid bindings, duplicate tracks and keys collapsed by engine precision are rejected. CUBICSPLINE sidecar import is unsupported.

Uniform retiming preserves the recorded path and changes velocity and acceleration. A retimed fall or release is not a new physical simulation under the original gravity. Review dynamics and naturalness again. The CLI scene retimer supports native SOMA packages through 30 seconds of poses; Studio offers shared-scene speed changes and trims of retimed LINEAR/STEP exports. Precise contact windows survive repeated timing edits.

The finite scene clock snaps rounding residue within 1e-12 seconds of zero or the terminal duration to that endpoint. This prevents an extra physics update at the end of very short clips. Three-frame and 901-frame native timing packages are exercised by the endpoint study; physics-release source limits remain separate.
