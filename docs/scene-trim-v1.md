# Synchronized scene trimming

`scripts/trim_scene.py` trims an existing portable native-SOMA scene as one unit. All actors, baked props, authored contacts and event times use the same inclusive native-frame range. It preserves actor placements and absolute root motion. The original GLB meshes, rigs, skinning, materials and embedded image data stay intact; only baked animation tracks are sliced and their time origin shifted. This prevents editing one actor while leaving its partner or prop on the old clock.

The command writes a fresh portable scene, native motions, animated GLBs, event file, runtime manifest and verified ZIP. Contact intervals are intersected with the selected range and shifted. Stable same-time event order is retained. Events outside the range are retained in `trim-context.json`, without replaying them; contacts already active at the new start are listed as authored context. No grasp, release or physical state is inferred. The source package's exclusive terminal event is retained only when its original tail is retained.

Input scene/event/asset hashes, clock, actor placement and baked object ownership are checked. Invalid ranges and inconsistent runtime metadata are rejected. Source files are unchanged, and old whole-clip quality summaries are not copied into a differently timed result. Baked props keep one playback owner; trimming does not rerun physics or initialize a live rigid-body simulation.

```powershell
.venv\Scripts\python.exe scripts/trim_scene.py reports/scene-runtime-v2/paired reports/my-scene-trim --first 20 --last 100
```

## Real scenes and engine checks

| Existing scene | Retained source frames | New frames | Actors / props | Retained events | Godot pose observations |
| --- | --- | ---: | --- | ---: | ---: |
| Paired interaction | 20–100 | 81 | 2 / 0 | 2 | 203 |
| Crate release | 90–150 | 61 | 1 / 1 | 2 | 162 |
| Moving platform | 1–120 | 120 | 1 / 2 | 1 | 283 |

Every native motion array is an exact source slice. All original mesh/rig/material records match. Decoded source-versus-trim matrices were compared at 120 Hz over 321, 241 and 477 scene times respectively; the maximum component discrepancy is below **9.64e-7**. These are matrix-component errors, not one distance unit for both translations and rotations.

All **648 Godot pose observations** pass, including shared scene placement, automatic playback, retained event order, reverse traversal and unloading. Maximum engine/reference actor matrix discrepancy is below 9.54e-7 and object discrepancy below 7.10e-7. Five authored events and eleven callback-mutation rejections are checked by the existing scene-clock audit. This trial supplies no additional invalid-package engine controls.

The crate trim begins after its authored grasp. The grasp remains in prior-event context, both grip windows are identified as active, and the grasp callback is not spuriously replayed at frame zero. Its two release notifications remain synchronized at new frame 31.

Fourteen focused tests pass, covering clipped intervals, initial context, same-time events, exclusive terminal markers, invalid ranges/clocks, real fractional actor/prop export comparison and inconsistent placement/ownership metadata. After adding the final metadata checks, a repeated valid paired trim is byte-identical for both actors, native motions, scene, events, context and runtime manifest. The exact earlier implementation is retained with the three-scene engine evidence.

Evidence and methods are under `reports/scene-trim-v1` and `reports/scene-trim-validation-v1`. This is currently a CLI operation on native-SOMA portable packages with complete baked 30 fps tracks. Speed changes, generic sparse/CUBICSPLINE animations, Studio trim controls, revised quality audits and human animation review remain open. No new motion was generated, no interaction defect was corrected, and no release capability is approved. The separate expanded-window contact study continues unchanged.

The subsequent [Studio integration](studio-scene-trim-v1.md) exposes this trim through scene controls and verified backend jobs. Browser interaction remains unverified.
