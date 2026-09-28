# Explicit target-rig transfer: development baseline

2026-09-26. Part of the single full-project goal; **not a completed release capability**.

The old Cesium running study used fixed node numbers, a mesh-node transform to reconstruct its bind reference, four repeated cycles and a shared automatic floor lift. That historical implementation and its outputs are unchanged. The new `scripts/retarget_rig.py` consumes a checksum-bound anatomical profile and a finite SOMA77 clip. It does not select a winning take, repeat the clip or move it above the floor automatically.

## Implemented contract

- Inspect a self-contained rigged GLB and list node indices/names, parents, reference positions, mesh primitive/influence counts and original animation names.
- Map 15 required humanoid roles with optional Spine2, Neck1 and toe bases. Names must be unambiguous; numeric node indices are also accepted. Distinct mappings and chain ancestry are validated. Intermediate helper bones are allowed.
- Use authored default-node transforms as the calibration reference. Preserve inverse bind matrices, meshes, textures, materials and unmapped local transforms. Infer root scale from the mean left/right leg-length ratio; apply only an explicit `world_offset_m`.
- Align primary bone directions and pelvis landmarks; use proper local quaternion rotations to avoid accumulating float32 FK orthogonality drift. Bone-axis twist remains underdetermined without additional authored axes.
- Replace animation channels only in a new derived GLB; original character, existing animations in the source asset and raw SOMA motion remain untouched. Export target transforms, target pelvis/root track, inherited contact intervals, resolved mapping and quantitative diagnostics.
- Verify every exported frame against expected target joint matrices **and skinned mesh vertices**. Validate the derived GLBs with the Khronos validator and check actual target-joint animation in Godot.

`rig_asset.py` validates the supported input subset before transfer: one embedded buffer, one skin in the selected scene, rigid unit-scale nodes, triangle primitives, four/eight weights (including normalized integer weights), interleaved accessors, embedded images. Missing inverse binds use identity. All active mesh primitives are evaluated. Unsupported sparse accessors, morph targets, required extensions, compressed/quantized/instanced geometry, external resources and scaled/reflected/sheared node transforms fail explicitly. FBX and arbitrary glTF extension support are not implemented. This importer is not a replacement for the full Khronos conformance validator.

The [glTF 2.0 skin specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#skins) requires world joint transforms for skinning and ignores the skinned mesh node's transform. Bind-shape transforms may already be baked into inverse binds or vertices; inverse binds alone are not treated as an authored anatomical reference pose.

## Measured cases

Character: existing licensed CesiumMan, SHA256 `b7001eaeea8254bd44773bcd247e78696d94169388fbb2a1800fc69434e777d9`. Profile: `assets/characters/cesium-man/rig-profile-v1.json`. Nineteen mapped bones; scale 0.6332583. CC BY 4.0 and separate logo terms are copied into the report directory. The review applies a grey material override without changing downloaded GLB materials. Studio's default SOMA character is unchanged.

Sources are existing seed-77 wave, kick and get-up clips from `reports/action-jobs/body-holdout-seed77`. Their earlier study name does not make these reused clips held out for this implementation. **No new model inference, training or independently selected character was used.** These three clips are regression cases, not an action whitelist.

| Case | Frames | Peak target mesh floor depth | Frames deeper than 1 cm | Largest per-foot predicted-support speed p95 |
| --- | ---: | ---: | ---: | ---: |
| Wave | 120 | 8.39 cm | 120 | 1.4 cm/s |
| Kick | 120 | 8.24 cm | 120 | 8.4 cm/s |
| Get-up | 180 | 21.73 cm | 180 | 10.8 cm/s |

All three fail the target-floor screen. Low predicted foot speed does not erase this failure. These measurements are sampled vertices against a flat Y=0 floor, not continuous collision, self-collision, object contact, force/balance or independent contact annotation. The finite clip ends at `(frames−1)/30` seconds; sample coverage is `frames/30` seconds.

- CPU GLB matrix roundtrip error below 1.6e-7; skin vertex error below 1e-7 m.
- Three exports: **zero Khronos validation errors, one warning each**. The original character has the same `NODE_SKINNED_MESH_NON_ROOT` warning. Both the spec-compliant CPU evaluator and engine world-bone check account for the existing hierarchy; the hierarchy is preserved.
- Godot 4.7.2: 420 sampled target-rig frames, 19 bones each. Maximum position error 2.10e-7 m; maximum basis-element error 6.36e-7. One skinned surface imported per clip. This is headless import/seek verification, not a GPU-skin, physics, realtime root extraction or gameplay-event test.
- Regression suite: 209 tests passed, including 22 rig import/transfer tests; four upstream Torch deprecation warnings. HTTP downloads match all three recorded GLB hashes.
- Browser: grey target mesh loads, clip selection and frame scrubbing work, get-up holds frame 179, and clicking the preview keeps the character visible. No console errors/warnings observed.

An earlier attempt is retained in `reports/rig-transfer-v1`: 2.24e-5 matrix roundtrip mismatch caused by expected FK accumulating source rotation drift before glTF's quaternion projection. The corrected expected-FK calculation was rerun into `rig-transfer-v2`; the initial failure is not deleted or claimed as a success.

## Reproduce

Run from `C:\wassup\strep` using the existing offline Python environment. Choose new output directories; transfer refuses to overwrite one.

```powershell
.venv\Scripts\python.exe scripts/retarget_rig.py inspect --character assets/characters/cesium-man/CesiumMan.glb --output reports/character-inventory.json
.venv\Scripts\python.exe scripts/retarget_rig.py transfer --character assets/characters/cesium-man/CesiumMan.glb --profile assets/characters/cesium-man/rig-profile-v1.json --source reports/action-jobs/body-holdout-seed77/takes/wave-seed-77/motion.npz --output reports/rig-transfer-reproduction/wave
node scripts/validate_rig_exports.mjs reports/rig-transfer-v2
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/rig-transfer-v2 --output reports/godot-rig-transfer-reproduction
.venv\Scripts\python.exe -m pytest tests/test_rig_transfer.py -q
```

Create the same manifest structure as `reports/rig-transfer-v2/manifest.json` for a different export set before running its validator/engine audit. Input source FPS is explicit; the Godot audit currently accepts only 30fps fixtures. `source-snapshot` stores executed transfer/importer code and the documented post-run invalid-scene-root guard amendment. Original source/model assets stay separate.

## Still required

1. Target-mesh-aware foot/hand/floor contact correction with explicit edit budgets; preserve this failing baseline and compare raw transfer against correction. A single automatic floor lift cannot solve a get-up throughout the clip.
2. Studio character file import, mapping/reference-pose preview and editable anatomical axes. The new path is currently CLI plus a review page.
3. Independent rig assets with different body proportions and reference poses, authored twist axes, finger/helper handling and target-specific contacts. Synthetic tests cover node reordering, 20% leg-length changes, multiple primitives and eight influences; they are not substitute character-quality evidence.
4. Animation import/editing, transitions and the remaining full-project release gates, including blind independent animator review and measured cleanup time.

Evidence: `reports/rig-transfer-v2/{manifest,export-validation,original-character-validation,ui-verification}.json`, per-case `report.json`, `reports/godot-rig-transfer-v1/verification.json`. Review: `http://127.0.0.1:8767/reports/rig-transfer-v2/viewer.html`.
