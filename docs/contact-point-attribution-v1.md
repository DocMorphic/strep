# Inspect contact-point deformation ownership

The [interpolated contact study](equatorial-torso-contact-v1.md) found that its five selected points on each hand are predominantly influenced by Pinky1, despite the contact IDs referring generally to a grip. Bone-subtree ownership does not identify a palm. A new source-bound point-inspection command exposes actual influences before a contact author decides which material surface to use.

Supply original `[mesh node, primitive, vertex]` references in a JSON file:

```json
{"vertices": [[6, 0, 0], [6, 0, 1]]}
```

Those numbers illustrate the format; they are not a selection for your character. The command accepts 1–256 distinct existing references, preserves their supplied order, includes every positive influence across all eight supported slots, combines repeated node IDs and sorts by descending normalized weight with node-ID tie breaking. Names are reported as source labels; they do not determine ownership or anatomy.

```powershell
python scripts/material_patch_bundle.py points CHARACTER.glb POINTS.json FRESH_ATTRIBUTION_FOLDER
python scripts/material_patch_bundle.py verify-points FRESH_ATTRIBUTION_FOLDER
```

The fresh folder retains copied character/point inputs, implementation snapshots, request/result hashes and a terminal pipeline record. Verification replays the complete influence table from the copied asset and checks exact input/method/file populations, order, labels, dominant nodes, normalized weights, counts and false approval flags. Altering a copied input and updating its hash cannot make a stale attribution table pass. Failed inspection retains its bound request, inputs and failure record. This is portable relative to the original source files; verification uses matching current method bytes and does not execute archived Python.

This command reads static skin data. It does not sample animation, deform a complete mesh, inspect normals, infer an anatomical palm, edit a clip, measure contact conditions or approve motion. Character input remains bounded to 128 MiB and the point JSON to 128 KiB. Existing explicit material-patch inventory/selection/transfer commands retain their prior outputs.

## Articulated patch experiment

A separate direct-surface fit adds the eight positively influencing finger-base joints (Index1, Middle1, Ring1 and Pinky1 on each hand) to the eleven previously edited arm/torso joints. Finger edits have explicit **30° original-relative rotation-norm caps**; original arm/torso caps remain **45°/15°**. These are artist-chosen edit bounds, not anatomical limits. It attempts the same preselected native keys **60, 90 and 121**, initialized from the torso-assisted guide, retaining all original translations, other local rotations, root and feet.

The direct constraints retain the original ten skin-point positions within **5 mm**, complete incident-face normals within **15°**, **0.5 mm** backface allowance and normal reliability thresholds. It replaces the derived rigid-patch wrist goals with these actual skin conditions: changing finger shape makes the prior rigid wrist surrogate inappropriate. This is explicitly a different fitting formulation, not a change to contact acceptance limits. Temporal contact, complete body geometry and force conditions are not assessed by this three-pose experiment.

| Diagnostic | All contact conditions pass | Candidate edit caps pass | Solver outcome |
| --- | ---: | ---: | --- |
| Direct SLSQP, 200-iteration budget | 0/3 | 1/3 | All stop in the least-squares subproblem |
| Positive inactive area-slack saturation, same limits/budget | 0/3 | 0/3 | All stop with a line-search directional-derivative failure |

The second diagnostic changes only the numerical magnitude of positive, inactive triangle-area slack: `min(1, area / threshold − 1)` has the same feasible sign condition as the first version. The area threshold remains **1e−14 m²** and coherence remains **0.1**. It does not fix convergence. Raw candidate position errors are **8.08–13.67 mm**, with worst opposition errors **26.64–27.92°** across the six attempts. Candidate source caps are assessed per joint; a maximum overall angle below 45° does not imply that 15° torso or 30° finger limits pass.

All raw failed candidates remain saved. The diagnostic NPZ retains a candidate at a key only if its source edit caps pass; otherwise it retains the original source pose at that key. It does not substitute the successful torso pose or quietly clip invalid candidates. These diagnostic files are not finished animation and are not admitted as model guidance. Independent replay checks each version’s three candidates, 57 source caps and 30 point/normal/side correspondences, protected source arrays and actual retained float32 guide; both exported guides have **0/3** complete contact passes. Original poses at rejected keys still have their original large contact errors.

Independent receipts are `8ac3ef66571d56698f832c0c754d2e8bc1f1fa14d06ed74b5086295f64047d22` and `7a4251bc752c60db66f50477c7c8400dbde25c4a67e55273da686272717b412c`. Their scope covers separately implemented candidate FK, scalar skin blending, complete incident-face cross sums, normal reliability, opposition, side and pass arithmetic, plus protected arrays and retained-guide evaluation. Asset parsing, static skin preparation, source interpolation, SciPy rotation conversion and the original nonlinear solver remain shared or outside independence.

The producers complete in **12.922 s / 60.094 s** with **37 / 74** resource observations; independent audits complete in **2.219 s / 1.125 s** with **eight / seven** observations. All resource traces replay under the unchanged scoped 1,024 MiB + 600 MiB reserve. Full-body audits retain the separate 2,048 MiB + 600 MiB policy.

These local solver failures do not prove that every articulated solution is impossible or justify training. The next authored contact revision must use explicitly inspected material references, retain this failed version and report the new selection separately. Full geometry, temporal contact, anatomy, actual physics/engine playback and genuine developer/animator review remain required. All quality, training and release flags stay false.

Local candidate and audit snapshots are under ignored `reports/equatorial-articulated-patch-v1` and `reports/equatorial-articulated-patch-v2`. Generated character payloads and study outputs stay outside the public repository.

## Source and real-asset validation

The relevant material/patch/revision/Studio-region regression run passes **204 checks**. After explicitly normalizing float32 weights with a float64 sum, all **20 focused attribution checks** pass, including the new nonbinary-sum regression. Fixtures exercise unordered skin joint slots, repeated influences across eight slots, multiple meshes/primitives, misleading names, invalid references, portability without original files, re-signed changed inputs, altered weights/labels/counts, extra files, changed method snapshots and false approval claims. Existing material authoring outputs stay unchanged. The source inventory remains 436 Python modules / 41 Node suites.

The real-asset command inspects all ten original contact references and replays every positive influence against the previously saved native tables. The documented `verify-points` CLI also completes against the portable copy. The worker forbids `RigAsset.vertices` during API production/replay, confirming that this static diagnostic does not evaluate a complete posed mesh. Static parsing and skin loading remain shared; this is not an independent animation or geometry check. Portable result SHA256: `0b87fc73829e156bcfc0c166a5e7654e8b19121f1e07b9e95dafc2c7213ec4dc`. All eleven resource observations independently replay.
