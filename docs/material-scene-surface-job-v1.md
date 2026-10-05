# Material scene jobs with explicit facing constraints

`scripts/material_scene_surface_job.py` connects a verified [material scene package](material-scene-package-v1.md) to its explicit [surface-contact policy](native-imported-surface-contacts-v1.md). The combined sampled decision requires both the native authoring job's point/geometry conditions and source-native/imported native-authoring surface conditions. A matching grip position cannot override a failed facing or side condition.

```powershell
python scripts/material_scene_surface_job.py plan PACKAGE SURFACE_POLICY.json PATH_TO_GODOT_CONSOLE_EXE FRESH_RECIPE.json
python scripts/material_scene_surface_job.py run RECIPE.json FRESH_EXECUTION_FOLDER
```

The policy must bind the package's exact `contacts.json` and cover every contact. Supply explicit world/object target normals in the declared target coordinates; partner normals use the selected partner surface. Keep the desired opposition angle, backface allowance, normal reliability thresholds and complete pose-query budget explicit. Winding does not identify an anatomical palm, and these commands do not choose or label one automatically.

Planning checks the complete package, input hashes, policy and current methods. Execution requires an idle production worker and fresh outputs. It runs the existing material authoring engine job, imports the complete surface observations and then replays every saved surface decision. Each stage runs serially, and an execution failure leaves its partial output and failure record.

The original policy bytes are copied untouched. The effective policy changes only its contact-file hash to bind this execution's active contact scene. An optional bounded object edit may change only the named object's keyframes and actor file references pointing to identical bytes. All actors, placements, geometry, contact references, correspondence, timing, limits and other objects remain protected. Actual object rotations transform object-space normals during the audit.

The result keeps separate point/geometry and facing decisions, complete per-mode surface counts, bound engine/surface/replay receipts and the combined decision. Default object-import comparisons remain visible; the combined decision concerns native-resource authoring. A completed diagnostic job can fail its sampled conditions and still retain the original Studio selection. Quality, training-admission and release flags remain false.

This workflow supports supplied world, object and partner contacts without an action whitelist. It does not generate or correct motion automatically. Anatomical review, force/dynamics validation, root/events, real-time playback, GPU appearance, physics, continuous/self collision and human cleanup review remain separate release requirements.

## Source validation

An isolated public-source copy passes **45 checks**: **14 new job cases and 31 unchanged imported-surface regressions**, in 432.84 seconds. Original/copied source hashes match; no models, downloaded characters or vendor code are copied. Actual tiny GLB, contact, geometry, import-correspondence and surface-replay APIs run with only the engine subprocess mocked. Correct facing passes; wrong facing fails even when point/geometry conditions pass. Receipt mutation during replay leaves a failed partial job. The first focused fixture exposed its own unrelated quantized-skin and undeclared-geometry failures; its output is retained, and the corrected synthetic fixture isolates the facing gate without changing production thresholds or methods. Source receipt SHA256: `2135539974d053055ba1163231e7304292b34518cd2ce6e2eeab8552712357cc`.
