# Corrected wave: ordinary import and explicit terminal hold

This study checks the completed CesiumMan wave from the real Studio correction
job, separately from the pending get-up developer review. The animation has 120
native keys and 3,273 skinned vertices. Its GLB SHA-256 is
`7678f1bafd355cf3f368c0d2d263e033f1a65ecb657553fa5517871f48d748f0`.
No animation, floor limit or imported-weight normalization is changed here.

## Method

Godot 4.7.2 imports the unchanged GLB at the default 30 FPS bake. Each mode
evaluates the complete 4,737-time population: original Float32 keys promoted to
Float64, seven interior eighths per interval, and the 960 Hz grid. Queries use
the existing exact Float64 wire encoding. Twelve bounded batches per mode retain
raw clocks, bone transforms, complete imported skin, mesh transforms and input
hashes. Every batch also includes the exact source start and end.

The ordinary mode uses the normal imported AnimationPlayer. The explicitly
acknowledged terminal-hold mode calls the existing
`godot_clip_adapter.gd::hold_terminal_frame` with 30 FPS. It changes only the
in-memory Animation length to `max(imported_length, last_key + 1/30)`. It does
not install native-authoring tracks or modify the GLB. Before/after fingerprints
bind each track's type, path, interpolation, enabled state, key times, values
and transitions. They must match both within and across the two modes.

Both modes retain the same 1 ns seek-clock, 0.0001 matrix-element, 0.1 mm skin
and 5 mm floor thresholds on the original motion domain. The adapted length
has its own explicit contract; its captured header still fails the ordinary
duration gate. Eight additional samples at eighths of the terminal hold compare
against the original final pose. These are discrete samples, not a proof over
every instant or a replacement for runtime advancement tests.

## Ordinary import result

All 4,737 pose, skin and floor comparisons pass. The maximum matrix-element
error is 9.802945e-7, maximum skin error is 0.056550 mm, and maximum imported
floor penetration is 4.821438 mm. One strict clock comparison fails: a requested
3.966666666666667 seconds is reported as 3.9666666984558105 seconds, a difference
of 31.789144 ns. Ordinary import therefore remains unapproved under this gate.
This small timing discrepancy is not evidence of a visible animation defect.

The same endpoint policy was observed on the get-up clip. Godot's
[version-pinned AnimationPlayer implementation](https://github.com/godotengine/godot/blob/4.7.2-stable/scene/animation/animation_player.cpp)
snaps approximately equal non-looping endpoints to the animation end. Adding
a hold moves the moving clip's endpoint into the playback interval; it does
not remove that engine policy at the new endpoint.

## Evidence boundaries

The terminal-hold mode passes all 4,737 original-domain samples with zero
reported clock error. Its pose, skin and floor maxima are identical to ordinary
import; all eight additional hold samples pass. The imported duration is
3.9666666984558105 seconds and the explicit adapted duration is
4.000000031789144 seconds. The original and adapted track fingerprints agree
across all 24 captures. This is sampled seek validation of this opt-in duration
contract, not a general claim that Godot endpoint timing has been fixed.

The finalizer completed, freshly reproduced every saved numerical diagnostic,
and passed an independent standard-library check of source clock bytes, all
9,526 raw observations (including repeated batch endpoints), input/output hashes
and unchanged pass thresholds. Both resource traces replay: 126 observations
for the initial failed summary and 121 for the successful finalizer. Peak
observed process-tree memory was 251,936,768 bytes. The generated reports remain
local; no character payloads or bulky captures are published.

The initial study saved all 24 engine captures and all per-batch numerical
diagnostics, then failed while serializing a NumPy boolean in the terminal-hold
summary. Its failed guard receipt, raw observations and partial publication
remain immutable in `reports/studio-surface-wave-engine-v1/` in the development
checkout. A separate `reports/studio-surface-wave-engine-v2/` finalizer binds
those files and re-evaluates every original-domain numerical diagnostic plus
the terminal-hold samples, using JSON-safe booleans. It does not recapture or
change the original evidence.

This study does not approve foot planting (no contact targets were supplied),
object/partner interaction, dynamic balance, transitions, renderer/GPU skinning,
physics, runtime advancement, arbitrary holds or rigs, or perceived quality.
The original remains selected in Studio. No quality or release gate is changed.

The subsequent [forward-playback study](studio-surface-wave-playback-v1.md)
passes five uninterrupted update schedules, completion and restart under the
explicitly adapted duration. Connection poses and transitions remain separate.
Preserve the ordinary import failure, and broaden correction studies across
the existing action/rig screen with explicit contact targets instead of
inferring foot planting from a floor-only pass.
