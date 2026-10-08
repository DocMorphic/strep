# Synchronized dense scene import audit

`scripts/run_scene_playback.py` checks every placed actor and separately exported
object GLB together in actual headless Godot. It accepts the existing scene
preview/fit manifests, with an explicit selection of scene IDs. It provides a
reusable simultaneous import stage alongside the private, one-contact-specific
playback studies; contact and collision measurements remain separate.

```powershell
python scripts/run_scene_playback.py reports/scene-preview-v1 reports/my-scene-playback --rate-hz 120 --scene-id lift-box-seed-11 --scene-id high-five-seed-11
```

Use a fresh output directory. Existing model-free NumPy/SciPy/threadpoolctl
dependencies suffice; the engine executable must already be installed locally.
`--engine` overrides the default local Godot 4.7.2 path. This command downloads
nothing, runs no model, and changes no input motion or character asset.

## Protocol

- Bind the scene manifest, chosen scene records, original motion and actor GLB
  bytes. Both existing asset-manifest formats require one exact file binding.
- Require a shared nominal 30 fps clip, 2–1800 source frames, one exported
  animation per actor, and complete uniquely named imported joints. Sampling
  rates are integer multiples of 30 between 30 and 240 Hz.
- Preserve the complete uniform clock and every actual stored actor/object key.
  Deduplicate exact equal times only. Nearby float32 keys and nominal times
  remain distinct, including terminal keys.
- Instantiate all actors and the object GLB in one scene. Seek every player on
  the same absolute clock. Record requested and actual player timestamps as
  little-endian Float64 bytes because Godot's decimal JSON output rounds them.
- Compare every placed joint and object transform against independent source
  GLB local-track sampling and hierarchy composition. Actor position/basis
  element screens remain `1e-4`; object screens remain `1e-5`. Invalid clocks,
  nonfinite matrices, incomplete populations, changed bones, looping clips and
  altered source bindings reject the audit.
- Godot snaps a nominal terminal seek to the stored animation endpoint. Only
  that exact declared terminal sample may report its exact source endpoint
  instead. Each adjustment is recorded, with source duration and delta. This
  is not a general clock tolerance or permission to shift other samples.
- Save requests, protocol, method snapshots, engine output/log, measured results
  and terminal status. Failed attempts remain separate. Recheck all input and
  method hashes after measurement.

The existing native-frame scene-import runner retains its default 30 fps clock.

## Observed results

The selected longer fixtures use their unchanged original motions, not outputs
from the memory-stopped V16/V17 lift fits.

| Scene | Clock | Samples per actor | Actor poses | Object poses | Result |
|---|---|---:|---:|---:|---|
| Original box lift, seed 11 | 120 Hz + stored keys | 885 | 885 | 885 | Pose screens pass |
| Original high-five, seed 11, actors A/B | 120 Hz + stored keys | 589 | 1178 | 0 | Pose screens pass |
| V16 reference candidate, seed 7103, authored placement | 240 Hz + stored keys | 261 | 261 | 261 | Pose screens pass |
| V16 reference candidate, seed 7104, authored placement | 240 Hz + stored keys | 261 | 261 | 261 | Pose screens pass |

Across these four scenes, 2585 actor poses (all 77 bones each) and 1407 object
poses were compared. Maximum actor position-element error was
`5.908e-7 m`, basis-element error `1.229e-6`; maximum object position-element
error was `1.197e-7 m`. Each actor/object player recorded one terminal adjustment:
about +31.8 ns in the longer clips and -27.8 ns in the reference clips.

The first engine attempt rejected rounded decimal clock echoes. The second,
with exact binary echoes, exposed the terminal snaps. Both failed attempts and
their diagnoses remain unchanged; the final run explicitly accounts for those
observed endpoints. No pose screen was loosened.

The unchanged native-frame runner also passed for four reference source/candidate
clips, 120 actor poses total. Local integration checks passed 108 tests, including
the actual object-rotation regression; 90 overlapping model-free tests passed
without Torch. The model-free CI inventory now contains 395 Python modules
split `[99,99,99,98]`, plus 37 Node scripts per operating system.

## Limits and next work

These are in-sample development fixtures and finite manual-seek observations.
Passing establishes sampled import/placement/clock fidelity only. It does not
verify imported skin identity, hand/partner contact, penetration, attachment,
GPU rendering, continuous collision, runtime physics/events, anatomy, action
correctness, animator ratings or cleanup time. The box trajectory remains
authored; the high-five motions retain their existing quality failures.

Use these synchronized observations with the existing source-bound imported
skin and scene-contact/geometry evaluators. The longer lift still needs stable
system memory and a completed constrained candidate. All fourteen release
capabilities remain unapproved; the whole-project goal stays active.
