# Exact native-track authoring seek

A separate Godot authoring seek helper passes the existing pose and clock audit
for both native contact clips, including the sample immediately before the clip
endpoint. Ordinary AnimationPlayer seeking still has its documented endpoint
snap; runtime playback and gameplay/event dispatch are separate work.

## Behavior and scope

`native_godot_preview.gd` validates all track targets before changing any pose.
It accepts only non-looping LINEAR bone position, rotation and scale tracks on
the selected skeleton. Non-finite/out-of-range times, missing bones, unsupported
track types, empty tracks and alternate target paths are rejected. It sets the
player's seek position without updating playback, then evaluates the saved
Animation tracks directly with Godot's interpolation methods.

This is scrubbing support for the experimental native-track adapter. It does not
advance playback, dispatch events, change clip length, or retime original keys.
Godot's ordinary playback processing deliberately snaps approximately equal
endpoint times to the endpoint. The separate authoring path avoids invoking that
processing; it does not patch the engine's runtime behavior.
[Godot AnimationPlayer implementation](https://github.com/godotengine/godot/blob/4.7-stable/scene/animation/animation_player.cpp).

## Matched results

`reports/checkpoint-native-authoring-seek-v1` binds the same immutable candidate
GLBs as the previous native-engine audit. It saves and reloads binary Animation
resources, verifies every original key time and compares all 77 world joints at
642 distinct full-clip, native-key, midpoint and authored constraint times per
actor. Pose tolerance remains 1e-4; clock comparisons still allow only two double
floating-point steps. Neither tolerance has been widened.

| Measurement | Actor A | Actor B |
| --- | --- | --- |
| Maximum joint-position component error | 0.518193 micrometres | 0.534013 micrometres |
| Maximum basis-element error | 5.291976e-7 | 6.209748e-7 |
| Maximum requested/actual seek difference | 4.440892e-16 s | 4.440892e-16 s |
| Event position error | 0.143122 micrometres | 0.312706 micrometres |
| Duration error | 0 | 0 |
| Strict pose and seek-clock audit | PASS | PASS |

Both actual event positions report exactly 2.0917225950783 seconds. Non-looping
clips and one skinned surface per actor are preserved. All 4,650 bound input
files and 22 output files rehash without mismatch. Result SHA-256:
`a4c75f39c560de3ab7d1e0c612fa7dddd124721c0a6933703959f4d41f580763`.
The binary resources differ from the previous study's resources; this study's
key verification and pose observations are the relevant evidence.

```powershell
.venv/Scripts/python.exe scripts/run_native_contact_engine.py reports/checkpoint-guard-contact-v1 reports/native-authoring-seek-new --native-tracks --authoring-seek
```

Use a fresh immediate folder under `reports/`. The runner archives its methods
and binds the engine binary, input evidence and output observations. Authoring
seek without `--native-tracks` is rejected.

## Remaining limits

This check establishes headless engine authoring poses and clocks. It does not
establish GPU rendering for this new seek route, collision/contact correctness,
Studio integration, runtime event semantics or human quality. Earlier imported
skin/GPU studies remain separate evidence. Original motion-rate failures,
sampled floor penetration and continuous collision uncertainty remain visible.
No training or held-out evaluation was used and no release gate was approved.
