# Primitive geometry in scenes

Scene sampling, skin-vertex collision measurements, contact-normal compilation, solver-v8 object penalties, and GLB object export now share a box/sphere geometry descriptor. Original `shape: box` / `size_m` scene records remain readable. New objects use:

```json
{
  "geometry": {
    "schema": "strep-object-geometry-v1",
    "shape": "sphere",
    "radius_m": 0.3
  },
  "keyframes": [
    {"frame": 0, "translation_m": [0, 0.3, 0], "rotation_xyzw": [0, 0, 0, 1]}
  ]
}
```

Do not combine `geometry` with legacy shape/dimension fields. Surface grips are object-local material points: they rotate with the object even when a sphere's silhouette is unchanged by rotation. Inward normals come from the corresponding analytic surface. Box-edge ambiguity remains rejected. The scene API retains its existing inclusive contact `end_frame`; it differs from target-rig fitting's `end_frame_exclusive` contract.

The v8 contact solver samples vertices near either primitive and differentiates the corresponding clearance penalty. Existing box-face inflation is preserved. Earlier solver versions reject non-box objects explicitly. Mathematical distance/gradient tests do not establish a successful fitted spherical grasp; a measured fitting study remains pending.

The Studio scene preview constructs the matching primitive and dimensions. Its helper has seven Node checks, and its explicit server route is tested. Browser rendering was not verified in this change because the existing browser access restriction remains in effect.

## Export and actual engine evidence

The exported GLB includes a canonical descriptor, complete translation/rotation/unit-scale tracks, and the preview mesh's approximation bound. The 0.3 m sphere fixture has 8,192 triangles and a conservative radial inset bound of 0.293 mm. Runtime packaging rejects mismatches between versioned scene geometry and the GLB's declared geometry.

The first actual Godot import, retained in `reports/primitive-scene-import-v1`, failed the fixed 10 micrometre mesh check: the default import shifted sphere vertices by up to 15.16 micrometres. The second import disables object mesh compression using Godot's documented [GLTFDocument import flag](https://docs.godotengine.org/en/stable/classes/class_gltfdocument.html#enumerations). The check was not loosened. Both the audit importer and shared scene runtime apply that flag to object meshes; actor import behavior is unchanged.

`reports/primitive-scene-import-v2` passes actual imported geometry, normals, material-point transforms and all 62 object-frame observations for a translating/rotating box and sphere. Imported vertex coordinates match the exported GLB to numerical precision; sphere analytic-surface vertex error is about 0.015 micrometres. This last error measures vertices, not the planar triangle inset.

`reports/primitive-scene-runtime-v1` passes 405 pose observations with an existing actor and a newly authored spherical playback fixture. Automatic playback, event ordering, callback mutation rejection and unload checks pass. The fixture reuses a recorded box trajectory as an authored track and removes its old contact claims; it is not a spherical dynamics experiment.

`reports/primitive-box-runtime-regression-v1` passes 1,160 pose observations across the existing paired, released-box and moving-platform scenes, plus three invalid-load controls. These checks protect playback compatibility; they do not approve the underlying animation quality.

## Remaining limits

Physics release still accepts only legacy box scenes and rejects versioned primitive requests before simulation. Sphere mass/inertia math exists, but sphere engine collision shapes, release validation and dynamics audits are not yet connected. Arbitrary meshes, handles, articulated/deformable props, force allocation, reaction motion and full generated interactions remain incomplete. No held-out reservations were used, no new checkpoint was trained, and no release gate was approved.

Raw outputs and implementation snapshots stay in ignored local reports. The source repository contains the methods and this result summary. Earlier box-only gap and geometry-core documents describe their original snapshots; this document records the subsequent integration.
