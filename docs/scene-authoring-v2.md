# Shared scenes, moving contact targets and retained failed fits

2026-09-26. The single project-wide goal remains active. This is development evidence, not release acceptance or a trained scene-aware model.

Studio's **Scenes** Dock app displays the actual eight-weight grey SOMA bodies and oriented boxes on a common 30 fps clock. It supports orbit/zoom, scrubbing, contact-frame jumps, palm close-ups, actor/object placement, contact error markers and scene JSON export. Placement edits update point distances immediately and invalidate the displayed saved collision measurements. Exported scene JSON references project motion files; it is not a standalone game package. Loading disables interaction controls to avoid acting on stale scenes.

## Preserved data and palm geometry

`reports/scene-preview-v1` contains ten original box/high-five scenes and wrist/palm measurement variants. Its ten distinct GLBs cover 15 actor instances. High-five A and B use the same native motion for a given seed and differ by authored placement: these are **not independent motion samples** or a jointly generated pair.

`palm_contacts.py` chooses central palm-side skin vertices from SOMA bind geometry and the finger bend direction. Left vertex 14712 and right vertex 16974 are evaluated using all eight skin weights, rather than approximating their motion by the wrist center. A browser close-up shows the right-hand marker on the palm surface. The candidates remain `anatomical_review_pending`; visual inspection by this agent is not independent animator calibration. Vertex numbers apply only to the recorded SOMA asset hash.

## Contact-track compiler

`compile_scene_contacts.py` turns explicitly selected scene contacts into actor-native `contact_spec` version 2 tracks. Each track carries one finite XYZ sample per inclusive interval frame and a fixed surface vertex. It supports shared world points, translating/rotating box-local grips, and frozen partner surface/joint tracks. It applies the inverse actor transform and records source hashes and target provenance.

Version 1 static/baseline/disabled rules remain supported. Version 2 track samples are endpoint-clamped outside their intervals for the existing fade weights. Malformed samples, overlapping same-region intervals, wrong vertices, bad source hashes and inconsistent clocks are rejected. The current floor solver requires yaw-only actor placement on world Y=0; elevated or tilted actors are rejected rather than silently solved against the wrong floor. Tracks do not fit palm orientations, generate an object trajectory, attach objects, or jointly optimize actors.

The existing contact editor retains and labels moving tracks, but editing their samples requires editing the scene trajectory and recompiling. It does not silently turn a moving track into a static pin. Arbitrary scene authoring and job submission are not yet integrated end-to-end in Studio.

Example:

```powershell
.venv\Scripts\python.exe scripts/compile_scene_contacts.py reports/scene-fit-fixtures-v1/moving-box.json --actor A --contact left-grip --contact right-grip --output reports/my-box-constraints
```

Use a fresh output directory. Original raw files are never overwritten.

## Two frozen exploratory scenes

`reports/scene-fit-fixtures-v1` freezes existing seed 11 motion and placements before fitting. The high-five requests both palms at [0, 1.5, 0] on frame 60; hand-to-hand distance is an additional measurement, not a reciprocal chase constraint. The box is 40 cm per side, with center [0, 0.2, 0.55] through frame 60, rising to Y=0.65 at frame 120, then holding through frame 179. Both object-local grips are requested on frames 60–120. This path is **authored**, not predicted or attached to either hand. The static original baseline remains intact.

`run_scene_fit.py` preserves raw, floor, previous body and final candidate motion. It exports GLB/BVH, actual pelvis tracks, predicted foot labels, requested contact events, source snapshots and measurements. Candidate motion is never promoted automatically.

Two solver conditions were retained:

* `reports/scene-fitting-v1`: the existing bounded v2 solver.
* `reports/scene-fitting-v2`: v3 separates per-region authored target loss from inferred support loss. This avoids diluting a one-frame hand target by hundreds of foot support frames. Existing contact editing still uses v2; v3 is experimental.

Both use soft contact fitting, a 40-degree per-editable-joint rotation budget relative to the prepared previous candidate, and a 22 cm vertical root budget relative to the limb baseline. These budgets are not anatomical limits. Object collision is measured after fitting and is not part of either solver objective.

| Measurement | Source | Solver v2 | Solver v3 |
|---|---:|---:|---:|
| High-five palm-to-palm gap, frame 60 | 53.37 cm | 35.38 cm | 30.09 cm |
| Either palm to shared meeting target | 28.96 cm | 19.48 cm | 16.88 cm |
| Box left-grip maximum error, frames 60–120 | 64.83 cm | 41.77 cm | 37.98 cm |
| Box right-grip maximum error, frames 60–120 | 64.20 cm | 45.36 cm | 40.98 cm |
| Peak body/box skin-vertex penetration | 0 cm | 14.84 cm | 18.44 cm |

Every scene fails the 3 cm requested-contact screen in both conditions. V3 also produces a high-five added-joint-speed flag. Smaller point error accompanied by deeper collision is not success. Zero box penetration in the source merely reflects missing the object. There are two unique raw native motions in this seed-11 experiment, not three independent actor samples. No held-out, semantic, dynamics, anatomical or engine-import claim is made.

The high-five v3 run stops after 33 objective evaluations with only about 3.13 degrees maximum rotation change, far below its 40-degree budget. Thus the evidence does not establish that the target is unreachable under the budget. Solver convergence and nonsmooth maximum-speed penalties need investigation before changing physical assumptions or collecting training data.

## Verification and next work

The project suite passed 126 tests, followed by two added normalization tests (128 tests in total). Tests cover inclusive tracks, independent target errors, palm bind reconstruction, rotating-box coordinates, inverse actor placement, rejection paths and sparse-target weighting. All ten original scene GLBs and six GLBs per fit condition validate with zero errors/warnings. Every exported pose and all eight weights are checked during export, including BVH round-trip verification.

`verify_scene_fit.py` independently checks original file hashes, exact root XZ and predicted foot labels, rigid bones, recorded root tracks, numerical root/finger rotation preservation, rotation/root budgets and decoded GLB contact points. The original matrices are orthonormalized during floor preparation, so rotation elements differ by up to about 3.6e-7 rather than being byte-identical. Maximum decoded GLB contact-point error is below 1e-6 m.

Browser checks: synchronized high-five frame 60; palm close-up; placement change A.X=0.1 changes the palm-to-palm gap from 30.1 to 24.2 cm, matching independent Python geometry, then placement restored; moving-box frame 179 holds without character disappearance; loading controls disable correctly; scene misses and 18.4 cm penetration are visible; no browser errors/warnings. Scene JSON download implementation exists but downloaded bytes have not been independently checked in this pass.

Next: diagnose convergence with feasible pose fixtures; add oriented hand contact and object clearance to the solve; implement explicit attachment/release; create a pinned Kimodo constraint adapter from feasible reference poses. Upstream end-effector constraints also fix root height/path/heading, so supplying hand coordinates alone is insufficient. Then test new seeds and broader object/partner actions before extending any success claim. Rig transfer, real-engine import, arbitrary rough-clip editing and independent animator evaluation remain required by the project-wide goal.
