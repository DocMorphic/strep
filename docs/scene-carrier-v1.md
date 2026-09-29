# Carry a character clip with a moving object

Studio's **Scene motion edits → Carry actor with object** selects an actor, carrier object and reference frame. The actor keeps its original world pose at that frame; the object's translation and rotation carry the clip across its full duration. The original scene remains available for comparison. CLI equivalent:

```powershell
.venv\Scripts\python.exe scripts/carry_scene_actor.py SOURCE OUTPUT --actor A --object platform --reference-frame 0
```

This is useful for authoring motion on platforms or vehicles. It preserves the animation already in the clip, including existing foot movement. It does not generate balance reactions, plant feet, simulate an attachment or repair other contacts. Ground, other-object and partner constraints must be reviewed after carrying.

The exported transform uses `O(t) O(reference)^-1 P A(t)`, where `O` is the exported object's rigid pose, `P` the actor's scene placement and `A` the original animated asset. Separate static and animated parent nodes retain the original interpolation instead of re-baking a product of rotations. Meshes, rigs, materials, object exports and event times remain intact. Native joint/root tracks, optional smoothed root and heading are updated; predicted foot labels remain predictions.

Current scope is native SOMA scenes of 3–901 frames with a unit-scale root carrier using LINEAR/STEP tracks. The object must already exist in the saved scene. This is whole-clip carrying, with no attachment/detachment interval or automatic initial placement. Arbitrary external rigs and physical reactions remain separate requirements.

## Retained evidence

An authored development fixture combines the existing box-lift actor with an elevated platform that translates, lifts and rotates by 1.2 radians. Actor placement also has a nonzero translation and yaw. Across **717 quarter-frame samples**, maximum object-relative full-mesh error is **0.076 micrometres**, while world displacement reaches **0.979 m**. The character follows the platform without changing its existing motion relative to it.

Foot material-point p95 speed illustrates the distinction. The right foot changes from **0.05155 to 0.15332 m/s in world coordinates**, but remains **0.05155 m/s relative to the platform**. That residual relative movement has not been corrected or approved as a planted foot. These measurements cover the full clip, not inferred stance intervals.

Godot passes **407 pose observations**, two authored events, four callback mutation rejections, automatic/reverse transport and unload. Maximum actor/object matrix component discrepancies are below **8.16e-7 / 1.80e-7**. Evidence and implementation snapshots are retained in `reports/scene-carrier-v1`.

An actual Studio job independently verifies source snapshots, execution, five download/bundle routes and the full-mesh audit. Its actor, platform, runtime manifest and runtime script are byte-identical to the engine-tested files. Native scene collision evaluation drops platform penetration from 100 mm in the uncarried source (the platform moves through the stationary actor) to zero at all 180 sampled carried poses. The carried mesh has no sampled world-floor penetration. Neither result certifies continuous collision safety or stable support. Evidence: `reports/studio-carrier-v1` and `reports/scene-trim-jobs/studio-carrier-v1`.

Twenty-seven distinct Python tests pass, plus the offline Node editor check. These cover rotated/nonzero-reference transforms, native heading/root updates, predicted-label preservation, invalid carriers/references, saved-scene worker behavior and desktop build preservation. A final preflight change rejects malformed actor/object types; execution functions remain unchanged from the actual job. No HTTP/browser rendering, human review or new model generation is claimed. All fourteen release capabilities remain unapproved.
