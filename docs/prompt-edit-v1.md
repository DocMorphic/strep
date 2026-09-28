# Prompt-based section regeneration, 2026-09-26

Studio can replace a selected finite section of an existing target-rig animation from a description, keeping the surrounding animation. This is experimental: all four fixed pilot takes and the additional UI-authored take fail motion-quality screens. The full-project goal and release gates remain open.

## Authoring and implementation

Characters → Edit timing and pose → Regenerate a section from a description. Choose the first/last frames, replacement action, blend length and seed. The saved recipe is bound to the exact source GLB hash. Source duration is unchanged. The range must contain 30–270 frames; blends must not overlap and contain at least four frames. Periodic clips are currently rejected: regenerate their finite source before making a loop. Timing/pose sliders are separate operations.

`rig_motion_bridge.py` inverts the saved rig profile's global orientations and pelvis calibration into SOMA77. Missing joints use rest local rotations; bone lengths, helpers and finger detail are approximate. Zero contact channels in this bridge mean unknown annotations. Mapped orientation/root roundtrip errors are checked, with separate whole-mesh diagnostics.

`rig_prompt_edit.py` canonicalizes the section's initial horizontal position, uses the derived initial heading and poses at frames 0, 1, n−2 and n−1 as full-body guides, then runs the unchanged Kimodo checkpoint. It retargets the result and splices local translations and geodesic rotations with a smoothstep envelope. Two samples at each edge and every frame outside the section remain unchanged within GLB numerical precision. Raw model samples, anchor errors, aligned samples and the final splice remain separately available. This is boundary-guided replacement, not a trained source-motion/relative-text editor.

Existing event timing is retained, with events on modified poses marked for review. Contact predictions remain distinct from confirmed contacts; partial blends conservatively intersect predictions. Existing authored targets are retained for review, not automatically satisfied. Source files, implementation snapshots, licenses, recipes and generation records travel with the package.

Exact matching descriptions can reuse validated local conditioning tensors through `reuse_action_conditioning.py`; revisions and hashes are checked. Other descriptions use the existing offline encoding path. This pilot used cached descriptions and does not establish held-out prompt performance or original-precision full-resident encoder equivalence.

## Fixed pilot and failure localization

Checkpoint revision `6c9233af1180b8151e3c4703477104af5dce9dd5`, 100 diffusion steps, separate CFG [2,2], model postprocessing disabled. No training or checkpoint change. Design and raw evidence: `reports/prompt-edit-v1`.

| Replacement / seed | Job suffix (20260926-) | Raw guide error | Native mesh floor depth | Retargeted / final floor depth |
|---|---|---:|---:|---:|
| Dance / 203 | 231039-29827f32 | 44.40 mm | 14.18 mm | 14.38 mm |
| Dance / 204 | 231129-6dfb83a6 | 62.09 mm | 14.24 mm | 20.75 mm |
| Jump and land / 203 | 231220-d497822b | 83.00 mm | 16.92 mm | 79.08 mm |
| Jump and land / 204 | 231304-7a8565eb | 69.36 mm | 4.50 mm | 62.57 mm |

Dance replaces frames 10–109 of a 120-frame corrected Quaternius wave; jump replaces frames 5–55 of a 61-frame imported Cesium locomotion clip. Blend length is eight frames. These are two existing rig families and two known descriptions, not a broad or held-out semantic test. The original clips already penetrate the floor by 3.01 mm and 26.01 mm respectively.

All four fail the existing 30 mm raw guide screen and 5 mm output floor screen. Native versus target mesh measurements show an additional transfer problem, especially on Cesium; the exported splice retains approximately the same worst depth as the raw retargeted take. The solver must not attribute all defects to generation or mask them by restoring endpoints. Maximum adjacent local-joint rotation steps also worsen (dance 19.35° baseline to 28.66°/20.28°; jump 18.04° to 28.75°/24.52°). Position guides do not constrain exact local rotations. Fixed duration and incompatible action/end poses may also contribute; causality needs a matched experiment.

Model generation takes 4.40–6.45 seconds per fixed take, excluding surrounding preparation/export work. Different seeds produce distinct files; this alone does not prove meaningful style control.

## Verification and UI take

Independent `verify_prompt_edits.py` reconstructs raw target poses, per-node SciPy Slerp, source preservation, native SOMA30 guide error, integer/half-frame skinned floor penetration, root/events and every HTTP/ZIP byte. Established rig calibration is shared with the implementation. Preserved world matrix errors are at most 1.20e-7; splice oracle errors at most 3.77e-7. Dance preserves 24 frames, jump 14. Half-frame floor results agree that all exports fail.

Godot 4.7.2 actually imports all eight fixed-study input/output GLBs and checks 724 joint-pose frame samples (`reports/godot-prompt-edit-v1`). glTF validation reports zero errors and inherited warnings. This proves import fidelity, not natural motion, GPU skin, physics or animator acceptance. Core full suite: 333 passed, four Torch warnings, 81.66 seconds; later UI review-summary changes were checked separately in the browser and through syntax checks.

An additional take was authored through the actual Studio form: `20260926-231829-75e87cd5`, “Jump section authored in Studio - seed 205.” It is a UI smoke test, not another preplanned fixed-study case. Raw guide error is 102.55 mm; native floor depth 0.95 mm becomes 70.71 mm after transfer/splice. Fourteen frames are preserved. Its separate verifier, two-GLB validator and actual Godot 122-frame import check pass (`reports/prompt-edit-ui-v1`, `reports/godot-prompt-edit-ui-v1`). The visible UI reports the failed guide screen and 54 output frames exceeding 5 mm penetration. The grey character remains visible. Five model takes total; no training.

## Next experiment

Address the measured anatomy/ground-transfer error and boundary feasibility. Compare raw generation, raw transfer and corrected transfer with matched seeds and preserved surrounding motion; add support intent rather than assuming every frame has planted feet. Test changes on these retained failures and additional action/rig cases. Evaluate action completion and transition naturalness separately from file correctness. Variable timing and richer source context may be needed. Scene/partner reliability, meaningful style controls, offline installation, held-out actions and independent animator cleanup-time evidence remain essential project work.

## Research basis

- [Kimodo constraints documentation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/constraints.html), cross-checked against pinned local `constraints.py`, `kimodo_model.py` and `postprocess.py`: full-body guides are positional constraints; native axes, reduced skeleton and heading conventions matter. Do not describe them as exact rotation constraints.
- [MotionFix](https://motionfix.is.tue.mpg.de/) provides a trained motion-editing precedent using source motion and edit text. No MotionFix data or weights were acquired or used here; this implementation does not claim equivalent editing ability.
