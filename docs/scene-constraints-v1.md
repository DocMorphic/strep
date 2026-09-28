# Shared scene coordinates and interaction baseline

2026-09-26. This is groundwork within the active full-project goal, not a scene-aware model or completed interaction workflow.

`scripts/scene_constraints.py` implements a shared 30 fps clock, actor placements, rigid object tracks with position/quaternion interpolation, and contact targets in world, object-local or another actor's joint-local coordinates. Oriented boxes are the first supported collision shape. Motion sources remain immutable. Actors must have the same duration; incomplete object tracks, invalid quaternions, unknown targets and escaped input paths are rejected. `tests/test_scene_constraints.py` checks transformations, moving object grips, oriented-box depth and invalid references.

`scripts/run_scene_baseline.py` re-evaluates the original raw box-lift and high-five outputs for five existing seeds (11/22/33/44/55), checking every source against its generation record. All ten scene specifications, resolved target tracks, source hashes and measurements are in `reports/scene-baseline-v1`. This uses the original provisional scene placements from `benchmarks/v0.json`, not calibrated or held-out release fixtures. All hand measurements currently use explicitly labeled **uncalibrated wrist proxies** (zero local offset), so they cannot certify palm-surface contact.

## Observed limitations

At high-five frame 60, the wrist-to-wrist gaps for seeds 11/22/33/44/55 are approximately 0.629/1.309/1.371/1.241/0.628 m under the declared placements. Both actors are independent single-character samples using the same seed, not joint inference. Reported target misses retain null first-valid-contact times. Partner collision, coordinated reaction and dynamic support remain unavailable.

For box lifting, the maximum wrist-to-grip errors over the initial requested grasp frames 60–62 range from approximately 0.522 to 0.660 m across both hands and five seeds. The retained v1 report also measures the static fixture over frames 60–179 (up to 1.167 m). That longer-window statistic is **not a valid moving-box grasp score**: it compares against an unmoving authored box, because no generated object trajectory or attachment exists. Attachment remains explicitly null/missing. Next evaluation must separate initial grasp from maintained contact against an actual authored or solved moving box.

The box collision check skins all 18,056 vertices with all eight weights and measures vertices inside the oriented box for every frame. No vertices penetrate these fixtures, but that does not demonstrate a successful pickup—the hands miss the box. This check cannot detect every triangle/edge intersection or enclosed object and is not continuous collision detection. No partner/self collision is implemented.

## Next implementation decision

Build a shared scene preview with both actors, object geometry and target markers; calibrate actual palm/grip offsets and feasible placements before scoring corrected interactions. Add object motion/attachment and actor-to-actor target tracking, preserving the unchanged baseline and labeling every deterministic correction. Feed feasible contacts to constrained generation as a separate condition rather than relying only on prompt wording.

The pinned upstream `vendor/kimodo/kimodo/constraints.py` supports full-body, root and end-effector constraints. Its `EndEffectorConstraintSet` also constrains root position/heading and joint rotations; a hand target alone is not a sufficient adapter. Build valid reference poses and explicit coordinate transforms before supplying these constraints. No upstream vendor code was edited and no training data/model was acquired in this step.

Reproduce the measurement with `.venv\Scripts\python.exe scripts/run_scene_baseline.py` into its fresh default directory; it refuses to overwrite an existing result. The original files and all failures are preserved. This initial scene schema is currently a Python/JSON workflow, not yet part of Studio's scene editor.
