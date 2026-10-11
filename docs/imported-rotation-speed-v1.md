# Imported native-key rotation speeds

The separate `native_engine_rotation_speed.py` audit measures selected local
joint rotations after Godot imports a supplied GLB. It uses the same source-bound
`strep-native-rotation-speed-policy-v1` author limits as the correction workflow.
The audit accepts 1–64 explicit actor/joint limits, including zero, and requires
2–20,000 original LINEAR rotation keys per selected track. It retains the rig
reader's existing rigid-transform and near-unit-scale restrictions.

Every selected native key is kept exactly, including closely spaced fractional
float32 times. An explicit float64 byte clock crosses the engine boundary. Each
joint and its immediate source parent is observed separately, including a
non-joint helper. Imported bones are resolved through the importer's
[GLTF skeleton resource](https://docs.godotengine.org/en/4.7/classes/class_gltfskeleton.html),
using its generated bone names; ordinary helpers use the
[glTF node path](https://docs.godotengine.org/en/4.7/classes/class_gltfnode.html#class-gltfnode-method-get-scene-node-path).
The original source indices/names/parents and generated paths are recorded.
Missing mappings or aliases reject the audit; source poses never replace them.

Local matrices come from inverse(parent world) × joint world. The audit rejects
singular transforms, reflections and shear. Column normalization and the proper
rotation projection are reported and checked against a 2e-6 basis transport
tolerance. This tolerance adds **zero** allowance to an authored speed limit.
The principal quaternion displacement divided by each native interval is checked
strictly. A separate unchanged 1e-4 world-matrix comparison exposes source/import
differences; a pose passing that comparison can still fail a tight speed limit.

This is a check of interval-average principal rotation speeds at native keys.
It does not certify instantaneous speed between keys, Euler winding, contacts,
skinning, collisions, physical realism, real-time playback or human quality.
Strict zero can reject tiny observed numerical motion; it is never silently
replaced with a positive allowance. Untargeted joints are outside its scope.

Use a fresh ignored output folder and an explicitly acquired engine:

```powershell
python scripts/native_engine_rotation_speed.py contacts.json speed-policy.json reports/speed-import --engine <godot-console>
python scripts/native_engine_rotation_speed.py contacts.json speed-policy.json reports/speed-native --engine <godot-console> --playback-mode native-authoring
python scripts/native_engine_rotation_speed.py contacts.json speed-policy.json reports/speed-native --verify
```

Run local numerical jobs through the project's existing RAM admission supervisor.
Native authoring uses the separately saved/reloaded native Animation resource and
authoring seeks; import mode retains its declared 30/60/120/240 FPS bake. Neither
mode starts a renderer or a Studio server. Replay recomputes from raw engine
matrices and checks original/snapshotted inputs, executed/archived methods, engine,
native resources, raw receipts and every stored numerical array. The separate
v1 contact/skin producer and its historical receipt contract remain distinct.

Validation is in progress. The first hosted run at `fbff40f` completes 19 checks
and fails two on each OS: native authoring passes, while 30 FPS import reports a
0.0161602341 maximum source-world element error and fails the original pose
comparison. A scene-root bone also exposes a path-resolution failure. The
mapping now uses the actual imported skeleton resource for that case; tests
retain the import discrepancy as a measured rejection. Limits and pose
tolerances are unchanged. Subsequent actual-engine results will be recorded
after completion; this preparation is not release approval.
