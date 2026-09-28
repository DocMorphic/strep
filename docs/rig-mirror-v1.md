# Explicit motion mirroring

2026-09-28. Development capability; the single project-wide release goal remains active.

The profile-response study found possible side-identity failures in kick prompts. An author can now explicitly mirror an existing finite clip in Studio: **Characters → Edit timing and pose → Mirror motion · swap sides → Prepare side swap**. Inspect the bone pairs and fixed vertical plane, name the variation, then create it. The result offers original and mirrored versions at the same frame, a root track, annotations, audit, recipe and ZIP. This is an authored variation, not automatic action recognition or a learned correction. It reflects the whole action, including turns and root travel; it does not replace just one limb.

The operation swaps reference-relative rotation deltas between explicitly paired descendants of the mapped pelvis. The destination retains its own bone lengths and reference axes. It mirrors root positions across the selected plane. The default plane passes through the first pelvis position with a horizontal normal defined by the reference thighs. Authors can change its heading. A saved involutive hierarchy map is required; saved canonical roles take priority over name matching. Extra descendants use exact side-name matches, and ambiguous or incompatible hierarchies reject. The displayed draft is not proof of anatomy.

World rotations with only nominal unit-scale float drift (orthogonality and determinant error at most 1e-5) are projected to proper rotations; actual scaled/sheared rigs reject. The double-mirror check compares against this explicitly projected input. Export separately checks full transforms and skinned vertices at every 30fps key against a 1e-5 limit. Original source bytes remain preserved. Nonlinear/STEP source interpolation between sampled keys is not preserved by the finite linear export.

Contact role labels swap while the canonical role-to-node mapping and frame intervals retain their meaning. They remain predictions, with renewed review required. Every gameplay marker is flagged for review; free-text names are preserved with lineage rather than guessed. Authored mesh patches, world targets and prior contact review stay under `input/` only. Scene geometry, partner placement, object ownership and periodic runtime contracts are not mirrored. A previous loop becomes a finite clip and needs a newly verified loop contract. Old solver success and human/engine approval flags are not copied into the new report.

## Evidence

`reports/rig-mirror-v3` contains a frozen nine-case study: left beckon, grapevine dance and jab/cross/retreat, each on Cesium and female/male superhero rigs. All 1,530 exported frames and 3,051 key/midpoint samples pass the specified reflection, counterpart rotation, protected-context and inverse checks. Maximum root reflection error is 2.55e-8 m; maximum exported inverse matrix error is 6.44e-7. Actual Godot imports pass for all nine clips, with a maximum world-position discrepancy of 1.61e-6 m. This is a known development population, not held-out quality evidence.

Floor defects remain. Cesium beckon changes from 60.048 to 59.453 mm penetration, dance from 64.345 to 64.523 mm, and combat from 59.686 to 59.927 mm at the sampled times. The six superhero clips have no sampled skin-floor penetration in this study. Those numbers do not establish foot contact, lack of self-intersection or naturalness. Asymmetric proportions and skin weights mean reflected skeleton deltas need not produce an exactly reflected surface.

`reports/rig-mirror-v1` preserves a preflight failure caused by name matching overriding explicit Cesium roles. `v2` preserves a failure caused by accumulated nominal scale drift. Both were fixed before the passing v3 study. The later source-validation extraction adds `validate_recipe` for API reuse; the Studio test uses that shipped version, and the study keeps its earlier implementation snapshot.

`reports/rig-mirror-studio-v1` records a real browser-created, 65-bone wave job, `20260928-144324-1d427424`. Original/mirrored switching preserves frame 60; playback starts at zero and stops at 119. Both versions pass Godot checks for another 240 actor-frames. All 74 packaged source/output files match their local hashes. The main server at port8768 serves the verified bundle and mirror API. Screenshots and DOM evidence are retained. There were no captured browser console errors. Software tests cover asymmetric axes/proportions, animated parents, exact symmetric reflection, involution, malformed correspondence, scale rejection, sidecar identity/timing, stale snapshots/quality flags and recipe clocks.

No new model inference/training, human ratings, cleanup timings, portable-distribution validation or release approval is implied. The authoring tool improves explicit variation control; calibrated agility/strength/stamina and reliable scene interactions remain open work.

## CLI

```powershell
.venv\Scripts\python.exe scripts/rig_mirror.py SOURCE.glb RECIPE.json NEW_OUTPUT_DIR --contacts CONTACTS.json --events EVENTS.json
```

The exact schema is `strep-rig-mirror-v1`, with source SHA256, 2–901 frames at 30fps, pelvis node, complete descendant correspondence, unit horizontal plane normal, plane point and label. The output directory must be new. Use a normalized single animation with the recipe's exact duration. Studio saves a complete example at `reports/rig-jobs/20260928-144324-1d427424/mirror.json`.
