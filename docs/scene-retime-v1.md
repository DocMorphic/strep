# Shared scene retiming

`scripts/retime_scene.py SOURCE OUTPUT --frames N` changes the duration of a portable native-SOMA scene. All actors, props and events use the same mapping. At 30 fps the pose span changes from `(source_frames-1)/30` to `(N-1)/30`; the final runtime hold remains one output frame. This operates on arbitrary recorded actions, without requiring positive forward travel or a running clip.

Exported animation key times are scaled, preserving meshes, materials, rigs, placement and pose keys. Cubic tangent derivatives receive the corresponding inverse time scale. Native motion arrays are sampled from the preserved export at 30 fps. Predicted foot-contact channels use previous-sample hold; optional smoothed roots use linear interpolation and heading uses unwrapped angle interpolation. These channels remain predictions, not new contact detections. Unknown native channels are rejected rather than guessed.

Events retain precise fractional frame/time positions, stable ties and participant references. Inclusive contact intervals are recorded exactly in `retime-contact-windows.json`; integer native solver windows conservatively enclose them, with the timing expansion reported. A contact shorter than a frame is retained. Existing source quality reports are not copied as approval.

Each package includes source hashes, implementation identities, decoded curve/rate comparisons, native motion, original-rig GLBs, exact events, a shared runtime and a hash-checked ZIP. Outputs use a fresh reports directory; source inputs remain unchanged. Current scope is native SOMA packages with 3–901 frames, up to 30 seconds of poses. The export helper covers LINEAR, STEP and CUBICSPLINE; nonuniform LINEAR/STEP clocks now use hash-bound authored curves in runtime v3. [Studio timing controls and retimed trims](studio-scene-timing-v1.md) are implemented. Generic imported rigs, CUBICSPLINE trimming and variable tempo remain open.

## Engine import and callback corrections

The initial real test preserved the glTF curves but failed Godot fidelity: a fixed 30 fps import resampled the retimed key grid. Its largest actor/object matrix component discrepancies were about 0.0150/0.0228. That failed test, exports and implementation remain in `reports/scene-retime-v1`.

Runtime manifests now derive each participant's import sampling rate from its actual uniform key clock. Godot's `generate_scene` accepts a bake-rate override. [Official API documentation](https://docs.godotengine.org/en/stable/classes/class_gltfdocument.html#class-gltfdocument-method-generate-scene). Using the exported rate corrected the measured mismatch without changing any retimed motion or GLB.

Schema v2 records fractional markers or non-30-fps import grids; integer-marker packages on a 30-fps export grid remain v1. The supplied runtime accepts both. During coarse forward/reverse advancement, all participants are sampled at each marker's exact time before its callback, then at the requested final time for one `sampled` notification. Reverse traversal now includes a terminal marker when leaving the final hold. Baked props keep sole transform ownership; callbacks cannot mutate the active clock.

## Retained results

| Scene | Native frames before → after | Speed multiplier | Fractional markers | Engine pose observations |
| --- | --- | ---: | ---: | ---: |
| Two-person high-five | 150 → 223 | 0.671171 | 2 | 496 |
| Box release | 180 → 121 | 1.491667 | 3 | 288 |
| Moving platform / crate | 180 → 240 | 0.748954 | 1 | 530 |
| Legacy integer-clock control | 150 → 150 | 1 | 0 | 349 |

The corrected import study reuses byte-verified retimed assets from the failed study and repackages the revised runtime. All **1,663 pose observations**, ten authored events, twenty-one callback mutation rejections, automatic transport, reverse ordering and unload checks pass. Maximum actor matrix component error is below 1.265e-6 and object error below 1.039e-6. Fractional markers declared as v1, descending fractional order, boolean frame values and zero import rates are rejected without exposing imported participants.

Six actor/object export comparisons cover **4,062 source-clock samples at 120 Hz**, with maximum matrix component discrepancy below 1.200e-6. The later schema guard produces byte-identical manifests for all four engine-tested cases; that check is retained separately. Fifty Python tests cover clocks, fractional events, terminal holds, conservative contact windows, interpolation/tangent scaling, import rates, runtime validation and existing trim workers.

Evidence is retained under `reports/scene-retime-import-v1`, including the current-runtime check. No browser interaction or animator assessment was performed. This initial study covered the CLI/backend. The subsequent [Studio timing integration](studio-scene-timing-v1.md) adds retiming and trims of retimed exports.

Uniform retiming changes physics: speed scales by the multiplier and acceleration by its square. The faster release has an acceleration multiplier of **2.225069**. Node-origin finite-difference rates are reported, but gravity, force, balance and support are not re-simulated or approved. Preserving a collision-prone path retains its defects. All fourteen release capabilities remain unapproved.
