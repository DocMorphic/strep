# Saved-scene object release in Studio

Studio → Scenes → **Simulate object release** now accepts an explicit saved scene, box, release frame, mass, friction and bounce. It freezes the source assets, simulates the selected released box locally and creates a reviewable input/candidate pair with downloadable animation assets. This is a reusable authoring operation, not a new action whitelist or a trained scene-aware model.

The current tool supports one to four native 77-joint actors and one to eight boxes over 4–900 frames at 30 fps. It preserves actor motion/placement, every other box and saved contacts. Release must follow all saved contact windows for that object and leave an output tail. Draft values persist per source revision; an active request resumes observation after reload. A shared worker lock prevents concurrent heavy operations. Invalid origins, stale assets, altered snapshots and overlapping contact windows are rejected.

Only the floor is simulated as a collider. Actors and other objects do not yet produce collision response. Mass and material values are explicit authoring assumptions. Existing contact/body/orientation failures remain visible. Current native-rig and box restrictions apply to this operation; the broader product still targets arbitrary action descriptions, imported humanoid rigs, environments and partners.

## Real request and retained failure

The actual Studio request `scene-release-jobs/20260927-052950-518417bb` used the existing seed-22 authored box scene, release frame 121, 3 kg, friction 0.4 and restitution 0.2. Frame 120 was rejected in the UI because it overlapped the contact window. The accepted job completed; it was not rerun for export corrections.

Independent verification checks frozen input hashes, exact authored prefix through frame 121, unchanged actors and contact definitions, existing events plus the explicit `dynamic_release_start` marker, 240 Hz simulation samples and their 30 fps bake, frame/half-frame decoded object transforms, ZIP bytes, portable paths and HTTP-served bytes. The simulation's maximum floor depth was **9.14 mm**, final floor distance **0.11 mm**, final speed **0.0000619 m/s**, and first floor contact at source frame **130.5**. The decoded frame/half-frame maximum floor depth was **0.886 mm**. This difference is why the higher-rate physics record is retained.

One of two requested contacts remains missed; peak sampled body/box penetration is about **10.1 cm**, and both hand-orientation checks remain outside their provisional tolerance. No whole-interaction or human approval follows from the floor screens.

## Portable scene and engine correction

The ZIP contains separate actor GLBs/NPZs, an animated `objects.glb`, object/scene data, events, source snapshots and simulation records. Apply actor placements from `portable-scene.json`; play actor and object clips on the same clock. Object transforms are already in world metres. Runtime physics is unnecessary for playback.

The initial actual Godot import of the relocated ZIP preserved all 77 actor bones across 180 frames, but the box failed the existing **1e-5 matrix-element** precision screen (maximum **0.0002813023**). Diagnostics established that imported keys and direct quaternion interpolation were accurate while the animated node transform differed.

[Godot 4.7.2 AnimationMixer](https://github.com/godotengine/godot/blob/4.7.2-stable/scene/animation/animation_mixer.cpp#L1833-L1844) applies full transforms when translation, rotation and scale tracks are all used; its other rigid-node path converts through Euler angles. Our translation/rotation-only object export triggered that path near a rotation singularity. Adding constant unit-scale animation avoids it without changing the motion. **Keep constant tracks when importing** (`remove_immutable_tracks=false` for the tested `GLTFDocument.generate_scene` path).

The corrected export is versioned under `exports/trs-v1`; the original failed package remains linked. All 359 whole/half-frame decoded matrices for each input/candidate object GLB are exactly unchanged. Actual Godot object rotation error becomes **2.607e-7**, below the unchanged screen; actor position error is **2.980e-7 m** and actor rotation error **6.855e-7**. Both original and revised sets of three GLBs have zero validator errors/warnings. A regression fixture reproduces the near-singular failure without scale tracks and passes with complete TRS tracks. The combined actor/box exporter receives the same forward fix; its historical packages remain unchanged.

## Evidence and reproduction

- Frozen request protocol, independent verification, engine diagnostics, export comparison and decision: `reports/scene-release-authoring-v1/`.
- Original engine import: `reports/godot-scene-release-authoring-v1/`.
- Revised engine import: `reports/godot-scene-release-trs-v1/`.
- Actual Studio job, original package and corrected export: `reports/scene-release-jobs/20260927-052950-518417bb/`.
- Worker/API tests cover multiple actors and objects, portable paths/events, stale requests, concurrency, origin checks and snapshot races. Full-suite logs are retained separately from focused tests.

From the project root:

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_scene_release_job.py tests/test_scene_object_export.py
.venv/Scripts/python.exe scripts/verify_scene_release_job.py reports/scene-release-jobs/20260927-052950-518417bb reports/scene-release-authoring-v1/verification.json
```

To repeat an engine audit, call `scripts/run_portable_scene_import.py SOURCE NEW_OUTPUT_DIRECTORY`; it extracts a fresh ZIP and imports separate actors/objects together. Do not reuse an existing output directory or rerun the completed physics job merely to observe it.

The project-wide goal remains active. Actor/environment collision response, interaction reliability, held-out motion/rig coverage, offline installation and independent animator/cleanup evidence remain release work. No model training or raw dataset acquisition occurred in this change.
