# Studio character import and transfer

2026-09-26. Development evidence for the single project-wide goal. No release gate is complete.

## Use it

Open Studio at http://127.0.0.1:8768/studio and choose **Characters** in the dock. Import a local rigged GLB, or use the bundled licensed CesiumMan sample. Review the anatomical mapping, save it, then choose **Preview alignment**. The preview applies a synthetic SOMA neutral pose through the saved mapping; it is not generated motion or a ground-contact quality test.

Each role can follow its bone direction, retain its rest orientation, or use a custom XYZ rotation. Placement offsets are explicit world metres. Changed mappings must be saved before another job can use them. Saved profiles are immutable, hash-bound to the original GLB, and snapshotted into each job.

Choose a clip and motion version in Preview, then **Use character**. Transfer creates target-rig animation while preserving the selected source motion. Optional bounded foot/floor correction runs a feasibility check first. Compare the raw transfer and contact candidate at the same frame, play or scrub the finite clip, and download the GLB, matching root track, predicted contacts, mapping, reports or complete animation package.

The character renderer uses a grey review material. The exported GLB retains source mesh/material data. The main NVIDIA SOMA preview is unchanged.

## Supported input and limitations

- Self-contained GLB up to 32 MiB, one skin, rigid unit-scale hierarchy, at most 512 nodes, 256 skin joints, 64 primitives and 250,000 vertices. Existing importer restrictions apply: no morphs, compressed meshes or external buffers. FBX import is not implemented.
- Fifteen required humanoid roles, with optional spine, neck and toe-base roles. Suggestions are conservative name matches; arbitrary rigs still need mapping and reference-axis review.
- Transfer currently consumes native 30 fps SOMA clips selected from the local Preview library. This is not arbitrary external rough-clip import.
- Automatic foot correction needs suitable foot/toe mappings and flat weighted reference soles. Unsupported automatic drafts retain the valid transfer and record the reason. Other validation failures remain failed jobs with logs preserved.
- Numerical fitting is provisional. Predicted contact intervals are not confirmed gameplay events. Root sidecars describe mapped pelvis world motion; engine root extraction is not applied.
- No self/object/partner collision guarantee, human realism approval, independent rig generalization or complete engine playback certification follows from this feature.

## End-to-end evidence

Browser testing used the real file chooser to import the exact licensed CesiumMan asset, saved the mapping, and started all three jobs through Studio. It also verified duplicate-node rejection, valid mapping restoration, persistence across reload, terminal hold, same-frame variant comparison, and variant-specific root links.

| Studio job | Result |
| --- | --- |
| `20260926-185253-cea72655` | Two-frame neutral alignment; exported and previewed |
| `20260926-185422-40a6c246` | Raw wave seed 77 transferred; floor depth 59.36 mm → 0.52 mm, patch error 0.51 mm after correction; provisional numerical pass |
| `20260926-185621-80fcc546` | Raw get-up seed 77 transferred; 217.31 mm floor penetration. Preflight proves at least 97.31 mm unavoidable under the current editable joints/root cap, so fitting is skipped and transfer retained |

`reports/studio-character-v1/manifest.json` binds these jobs and four GLBs by SHA-256. Khronos validation reports zero errors and one inherited `NODE_SKINNED_MESH_NON_ROOT` warning per file. Actual Godot 4.7.2 import checked all 422 frames across 19 bones; maximum joint-position error was 2.10e-7 m and maximum basis-element error 6.36e-7. See `reports/godot-studio-character-v1/verification.json`. This verifies import/transforms, not GPU skin rendering, physics, contact correctness or animator judgment.

All three packages were fetched from the local server, checked against their recorded hashes, and every archived source/output entry compared byte-for-byte with disk (22/35/24 entries). All four served GLBs matched their hashes. See `package-http-verification.json` in the study folder.

The current full suite has 233 passing tests and four upstream Torch deprecation warnings. New coverage includes invalid uploads, origin and path restrictions, immutable profiles, changed-source rejection, and an actual worker transfer with optional toe mappings removed: the valid GLB/package survives unsupported automatic correction. Source code snapshots inside each job preserve its executed implementation; later UI compatibility fixes do not rewrite old packages.

## Files and next work

`studio_characters.py` owns validated local asset/profile storage; `rig_studio_job.py` supervises snapshotted transfer/correction jobs under the existing worker lock. `character-studio.html`, `.css` and `.js` implement the separate renderer/editor. `action_studio_server.py` exposes only localhost asset/job routes and allowed result files.

Next test independently selected, clearly licensed rigs with different reference axes/proportions. Do not count renamed or modified Cesium copies as independent rigs. Then extend target contacts beyond the lower-body foot heuristic, while continuing the outstanding rough-clip editing, transition/style, scene/partner and release-validation work. The existing full-project goal remains active.
