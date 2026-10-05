# Strep Godot runtime adapter

Tested with the official Godot 4.7.2 Windows build on Strep's SOMA exports. This
adapter imports authored event data into an AnimationPlayer method track. It
does not infer contact success or implement a game's grasp/release physics.
Current box/high-five clips remain failed motion-quality experiments.

Copy `godot_clip_adapter.gd` into your project. Load the scene GLB with
`GLTFDocument.append_from_file` and `generate_scene`, or use an existing freshly
imported instance. Add the adapter under that model before binding:

```gdscript
const StrepAdapter = preload("res://godot_clip_adapter.gd")

func prepare_clip(model: Node, player: AnimationPlayer, clip: StringName,
        events: Dictionary) -> Node:
    var adapter = StrepAdapter.new()
    adapter.name = "StrepEvents"
    model.add_child(adapter)
    var error = adapter.bind_clip(player, clip, events)
    if error != OK:
        adapter.queue_free()
        push_error("Invalid Strep event document: " + str(error))
        return null
    # Explicitly hold the final sample for one frame. A 180-sample / 30 Hz
    # animation then occupies six seconds, including its terminal hold.
    assert(adapter.hold_terminal_frame(player, clip, 30.0) == OK)
    adapter.marker.connect(func(event: Dictionary):
        print(event.type, " authored at ", event.time_s))
    player.play(clip)
    return adapter
```

Read the sidecar `events.json` as a Dictionary and pass the desired imported
animation name (exclude Godot's `RESET`). Bind once per fresh animation instance;
the adapter modifies that in-memory Animation resource. If your game shares an
Animation resource between instances, duplicate it before binding. Event frames
must be integer, nonnegative, ordered and consistent with `time_s` and `fps`.
Simultaneous markers are allowed. JSON provides payloads, never callable method
names or node paths.

For preview scrubbing use `adapter.seek_preview(player, seconds)`. This uses
`AnimationPlayer.seek(seconds, true, true)` to suppress method/audio tracks.
Calling `seek(seconds, true)` directly can dispatch a marker at the destination.
Scrubbing does not reconstruct game attachment state; games must explicitly
restore that state when seeking during gameplay.

Root extraction is optional, separate from normal scene playback:

```gdscript
assert(adapter.extract_root(player, clip, "Hips") == OK)
# In your chosen animation update loop, read:
var translation_delta = player.get_root_motion_position()
var rotation_delta = player.get_root_motion_rotation()
```

The root bone must match your rig. Extraction cancels its animated transform in
the pose; you must apply the deltas using your game's coordinate conventions.
The included audit checks native SOMA deltas, not CharacterBody movement,
world-space object synchronization, retargeting or blended root motion. Do not
enable extraction on an attached-object scene without handling both actor and
object transforms in your game.

The tested contract is forward, non-looping playback at 30 Hz, coarse 17-frame
advances, restart, boundary markers and silent scrubbing. Coarse updates dispatch
crossed markers on that update; they do not retroactively simulate physics at
the event timestamp. Looping, reverse playback, crossfades and physical release
remain unverified. `hold_terminal_frame` explicitly rejects looping clips.

`verification.json` records actual engine tests. Original GLBs and source motion
are unchanged by this adapter. Asset/model licenses remain those supplied with
the separately downloaded scene pack.

References: [AnimationPlayer seek](https://docs.godotengine.org/en/stable/classes/class_animationplayer.html#class-animationplayer-method-seek),
[AnimationMixer root motion](https://docs.godotengine.org/en/stable/classes/class_animationmixer.html#class-animationmixer-property-root-motion-track),
[runtime glTF loading](https://docs.godotengine.org/en/stable/classes/class_gltfdocument.html).


[Shared scene prop ownership](SCENE-PROP-OWNERSHIP.md) provides an opt-in native SDK for multiple hands, dynamic props and atomic handoffs. It requires explicit providers and retains fixed-step event delays and measured collision failures.
