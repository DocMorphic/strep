# Coordinated finite scene playback

2026-09-28. Development evidence; motion/contact quality remains unapproved.

`godot_scene_clock.gd` gives every actor and baked object in a scene one playback owner. All participants sample the same cursor before any event callback. It supports automatic physics-tick playback, variable speed, pause, finite endpoint hold, silent scrubbing, forward/reverse traversal, restart and unloading. Reverse signals do not execute forward actions. Reentrant clock mutations are rejected during callbacks.

`scene_runtime.py` creates a portable manifest with asset hashes, actor placements, object-node identities and explicit `baked_track` ownership. It retains authored event payloads and their ordering. The loader checks paths, hashes, participant references and finite animation lengths, stages the imports, then exposes the complete scene. Invalid imports leave no partial actors behind. Root placement applies once; an outer scene parent can place the whole group in the level.

New Studio scene-release exports automatically include `scene-runtime.json`, `godot_scene_clock.gd` and `GODOT-SCENES.md` in their existing ZIP. The standalone packager also packages existing native SOMA scene studies, including paired actors. Previous packages are unchanged. See [integration instructions](../integrations/godot/SCENES.md).

## Actual engine evaluation

`reports/scene-runtime-v2` loads three existing scenes using pinned Godot 4.7.2:

| Scene | Actors | Baked objects | Authored events | Maximum actor matrix error | Maximum object matrix error |
|---|---:|---:|---:|---:|---:|
| Corrected paired interaction | 2 | 0 | 2 | 8.141e-7 | — |
| Existing crate release | 1 | 1 | 3 | 8.153e-7 | 7.317e-7 |
| Existing moving-platform release | 1 | 2 | 1 | 8.153e-7 | 7.255e-7 |

All pass. The reference independently samples the packaged GLBs in Python and composes actor placement plus a nonidentity outer scene transform. Every actor has 77 bones. Checks include all bones and every object on half-frame forward steps, coarse reverse steps, event callbacks, silent seeks, automatic forward playback, automatic double-speed reverse playback and terminal holds: 1,160 pose observations including callbacks. Limits were fixed before the run: actor matrix 1e-4, object matrix 1e-5.

All authored forward/reverse event orders match. No terminal event repeats, pause retains the cursor, reverse can remain silent, invalid time/rate commands leave the clock unchanged, callback mutations return `ERR_BUSY`, and unloading removes owned instances. Three deliberately invalid packages reject a changed actor hash, conflicting live-physics ownership and a missing object node. The last fails after staging imports; every control leaves the scene unbound with zero visible children.

`scene-runtime-v1` is a retained failed harness preflight: three dynamically inferred GDScript variables needed explicit types. No engine comparison ran. V2 uses explicit types and unchanged numerical limits.

## Real worker and export path

Nine tests pass (22.85 s), covering malformed paths, source hashes, clock/reference errors, terminal contact-window events, stable simultaneous ordering, and actual Studio release workers with two actors/two objects in static and moving-collider modes. Their resulting ZIPs contain the new manifest, loader and instructions, with all embedded bytes checked.

The retained `reports/scene-release-jobs/scene-runtime-worker-v1` additionally runs the real release worker and then loads its exported package through the engine. This is an explicitly authored integration fixture: an existing actor is duplicated at another placement, with a crate and prescribed moving shelf. It is not a newly generated two-person interaction. All 413 pose observations pass; maximum actor matrix error is 6.596e-7 and object matrix error 6.731e-7. Five authored events and ten callback-mutation rejections pass. Production simulation, audit, packaging and playback run without mocks.

The first retained-worker attempt under `reports/scene-runtime-worker-v1` was rejected by Studio's allowed-file roots before job preparation. Retrying inside `scene-release-jobs` uses the supported source path. Both attempts remain; no allowed-root rule was weakened.

Source scenes, actor motion, contact/evaluation failures, runtime implementations and hashes are retained. Existing source scenes/packages were not edited. Downloadable tested packages are under each scene in `reports/scene-runtime-v2`, and the real worker export is `reports/scene-release-jobs/scene-runtime-worker-v1/job/scene-animation.zip`.

## Ownership and remaining work

These objects already contain baked trajectories, sometimes produced by an earlier physics simulation. The runtime intentionally keeps one animation owner; a release notification does not start a competing live physics body. This solves synchronized playback and ownership declaration, not a shared live-physics attachment controller. Live handoffs between actors/props, two-hand constraints, crossfades and rollback still need integration.

This is a headless transform/event/lifecycle study, not a GPU appearance or naturalness study. The paired scene retains its overlap/floor problems; the release scenes retain their contact/orientation/body-intersection diagnostics. Passing engine checks does not clear those failures. All release gates and independent animator/cleanup-time requirements remain open.

Reproduce the scene study with `.venv/Scripts/python.exe scripts/study_scene_runtime.py <new-output-folder>`. The retained-worker script uses a fixed output name; select a new output explicitly for a new run. Preserve completed evidence.
