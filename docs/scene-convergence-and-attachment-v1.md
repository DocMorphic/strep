# Contact convergence, corrected grip fixtures and explicit attachment

2026-09-26. Development continues under the single full-project goal. No candidate here is release-approved, and no model was trained or newly sampled in this study.

## Convergence diagnosis

`reports/contact-convergence-v1` contains a constructive reachability witness: a repeated real pose with a smoothly varying, at most 10-degree right-arm rotation. The target is evaluated on the resulting skinned palm vertex. Both solver v3 and an Adam-warm-start variant (v4) reach the single-frame target within 0.06 mm. The full moving track retains about 14 mm error because the original slide penalty competes with the moving target. This engineering fixture rules out a basic coordinate/skin gradient failure; it is not an animation-quality test.

The Adam variant uses the same objective and bounds as v3. Its real-scene runs (`reports/scene-fitting-v3`) do not solve the interactions. They are retained, including convergence history. This version is not the new default.

`support_contact_v5.py` instead parameterizes correction rotations with cubic controls six frames apart, applying the 40-degree bound **after** interpolation. This reduces the number of independent edit variables and prevents isolated frame edits from dominating the speed penalty. Its objective is otherwise the v3 objective. Root/finger/bone/export checks remain independent.

On the unchanged seed-11 high-five fixture (`reports/scene-fitting-v4`), palm-to-palm error falls from 533.7 mm to **5.31 mm** at frame 60. Each palm lies 4.05 mm from the shared target. The existing `pose_change_above_22cm` review flag remains. Actual skinned palm normals differ from the desired opposing orientation by **78.95 degrees**. The browser close-up visibly shows intersecting, misoriented hands. This is point matching, **not a solved high-five**; partner collision and independent animation review remain missing.

## Corrected anatomical grip assignment

Inspection of the source poses exposed a fixture error: the original left-hand target used X=-0.2 and the right used X=+0.2, requesting crossed arms through the box. SOMA's anatomical left hand lies on +X in this fixture. The old scenes/results are preserved without changes. `reports/scene-fit-fixtures-v2` explicitly corrects the two grip assignments, keeping box size, placement, trajectory, intervals and solver settings unchanged. This is a corrected exploratory fixture, not post-hoc adjustment of a held-out release test.

Solver v5 was then evaluated on existing seeds 11 and 22 (`reports/scene-fitting-v5`):

| Measurement over contact frames 60–120 | Seed 11 | Seed 22 |
|---|---:|---:|
| Left palm maximum point error | 3.95 mm | 5.04 mm |
| Right palm maximum point error | 5.13 mm | 6.46 mm |
| Peak skin-vertex box penetration | 6.42 cm | 10.08 cm |
| Left palm maximum normal error | 32.94° | 83.43° |
| Right palm maximum normal error | 13.28° | 40.80° |

Pose-change and inferred hand support regression flags remain. Some support estimates conflict with the authored lift; these cannot be silently waived without annotated contact intervals. Both cases remain failed overall despite meeting the 3 cm point screen.

`surface_normal_track` computes area-weighted normals from the actual skinned adjacent triangles. It recenters positions before cross products to avoid amplifying float32 skin-weight rounding at large world translations. The box diagnostic uses the inward normal of the unique face containing the grip; partner contact uses opposing actual normals. A 15-degree threshold is provisional, not anatomically or animator calibrated. Tests reject ambiguous edge/interior grips. No orientation constraint is applied by the current solver yet.

## Kinematic attachment and portable scene exports

`object_attachment.py` records the object's transform relative to a selected palm position and wrist rotation at grasp. It keeps that transform during the attached interval. At release it aligns the authored free trajectory with the predicted release pose. It does not add gravity, certify velocity continuity, or solve the second hand.

`reports/object-attachment-v1` applies left-hand grasp at frame 60 and release at frame 121 to both corrected box examples. Active attachment is [60, 121), matching the inclusive contact interval 60–120. Grasp and release markers are authored events, not automatic success detections.

The primary grip stays within 4 mm, but the secondary hand's maximum error grows to **10.44 cm** (seed 11) and **58.23 cm** (seed 22). Box penetration remains 7.28 cm and 10.08 cm. Binding an object to one moving wrist is therefore insufficient for two-hand manipulation. All failures remain visible in Studio and the downloadable evidence.

Each `scene-pack.zip` includes a combined animated **scene.glb**, object transform track, events, attachment recipe, contact/collision/orientation measurements, export verification and license. The GLB contains the unchanged eight-weight actor plus animated box on one clock. Skin mesh nodes remain scene roots while the skeleton receives actor placement; an initial glTF parent-transform warning was corrected. These are game-engine-compatible artifact candidates, not proof of import into a real engine.

## Verification

* Full project suite: **146 passed**, four existing Torch JIT deprecation warnings.
* New fit exports: six GLBs in fitting-v3, six in fitting-v4 and four in fitting-v5, all zero validator errors/warnings. Attachment report: two copied actor GLBs plus two combined scene GLBs, zero errors/warnings.
* Every-frame decoded GLB actor/object transforms agree with source tracks within 1e-5; measured maximum errors are below 2e-7. BVH/skin/bone/root/edit-budget verifications also pass for fitted actors.
* Both attachment examples preserve the recorded hand-relative transform over all 61 attached frames, within 6e-8 in matrix/position elements. ZIP contents and bytes served by Studio match local hashes. Engine import remains `null`.
* Browser: high-five frame 60 displays 0.5 cm point gap and the failed orientation screen; attachment end-frame playback retains the character and box; scene ZIP/GLB/event links are visible; no browser errors/warnings. Source clips remain unchanged.

Scripts: `diagnose_contact_solver.py`, `support_contact_v4.py`, `support_contact_v5.py`, `audit_scene_orientation.py`, `object_attachment.py`, `build_attachment_study.py`, `export_attached_scene.py`, `register_scene_artifacts.py`. Report source snapshots retain the implementations used in each fit. `register_scene_artifacts.py <report>` registers completed orientation and download sidecars without changing scene data.

Next work is an oriented contact and object-clearance solve that accounts for both hands together, followed by partner collision and feasible Kimodo constraint conditioning. Keep the broad action/rig/engine release objective intact; do not treat this small, already-seen set of source clips as held-out or universal evidence.
