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

The [completed hosted run](https://github.com/DocMorphic/strep/actions/runs/38161024358)
at `a239afb` passes **23 checks on each OS**, comprising eighteen source/receipt
cases and five actual Godot 4.7.2 generated-rig cases. Windows takes 6.31 seconds
and Linux 3.53 seconds. Both platforms agree exactly on all five result summaries;
each runner recomputes the result and arrays from its actual imported matrices.
The archived methods match the committed public code. Original inputs, policies,
engine observations, receipts and native resources are retained in the hosted
artifacts and downloaded locally; a separate passive certificate checks 27 source
files and 812 expanded artifact files without claiming a new numerical replay.

The [compatibility run](https://github.com/DocMorphic/strep/actions/runs/38160923780)
at `609d39a` additionally passes all six focused regression jobs: 451 contact/rig,
34 lineage and 32 game-package checks per OS, with editor checks in every job.
All 517 Python checks per platform pass without skips or failures. A separate
certificate verifies 2,391 committed source bindings. This protects the existing
source policy/correction/package behavior; the new acquired-engine checks above
remain distinct from that regression population and from whole-project approval.

| Mode / fixture | Authored maximum (degrees/s) | Observed maximum (degrees/s) | Maximum source-world element error | Combined sampled decision |
| --- | ---: | ---: | ---: | --- |
| 30 FPS import, helper parent | 200 | 79.073821 | 0.0161602341 | Reject: source pose |
| Native authoring, helper parent | 200 | 147.286246 | 5.93068e-8 | Pass selected conditions |
| 30 FPS import, scene-root bone | 200 | 79.073821 | 0.0161602341 | Reject: source pose |
| Native authoring, helper parent | 100 | 147.286246 | 5.93068e-8 | Reject: authored speed |
| 30 FPS import, helper parent | 100 | 79.073821 | 0.0161602341 | Reject: source pose |

The imported speed falling below 100 does not approve the clip: the original pose
comparison still fails. Native authoring passing the pose comparison does not
approve its 100-degree/s limit. World-matrix element error is not a position-only
distance or a rotation-angle measurement. These deliberately small fixtures
establish transport and rejection behavior, not anatomical calibration or motion
quality. Studio does not yet invoke this separate audit during export; connecting
retained author intent to the final selected motion remains next.

The first hosted run at `fbff40f` completes 19 checks
and fails two on each OS: native authoring passes, while 30 FPS import reports a
0.0161602341 maximum source-world element error and fails the original pose
comparison. A scene-root bone also exposes a path-resolution failure. The
mapping now uses the actual imported skeleton resource for that case; tests
retain the import discrepancy as a measured rejection. A following clean-clone
run reports 23 setup errors because the ignored `reports` parent is absent;
creating that parent repairs CI setup. Both failed runs and their logs are retained.
Limits, pose tolerances and release criteria are unchanged. The local retry
defers without starting a worker after 600.672 seconds under the unchanged
2,776,629,248-byte / 15-stable-second admission guard. Available RAM peaks at
2,706,571,264 bytes. All 595 resource observations independently replay the
deferral; no local numerical completion is claimed. The complete hosted execution
and fresh replay above remain distinct, with the original failed attempts saved.
