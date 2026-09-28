# Pose-guided generation — 2026-09-26

Strep now passes authored pose guides to the unchanged Kimodo checkpoint during generation. Studio's **Use pose** button captures the currently displayed clip variant and frame. The composer lets the author choose a hand, foot, whole-body or root guide and target frame; removing guides restores text-only generation. Existing custom end-effector groups remain editable when reusing a request. Drafts retain guides. The inspector shows target errors and jumps to the guide frame.

This is an experimental generation control, not solved scene interaction or a trained editor. It does not constrain fingers, skinned palm surfaces, objects, partner collision or physical support. No release capability is marked complete.

## Request contract and upstream behavior

Optional `generation_constraints` entries contain `type`, project-relative SOMA77 `motion` NPZ, `sha256`, `source_frames` and output `frame_indices`. `end-effector` also requires distinct `joint_names` from LeftHand, RightHand, LeftFoot and RightFoot. Types: root2d, fullbody, left/right-hand, left/right-foot and end-effector. Target frames are zero-based on the complete 30 fps output timeline. Sources are assumed 30 fps; only selected poses are transferred. Coordinates remain native Y-up metres, with the generated clip's initial smoothed root XZ origin at zero. No automatic scene alignment is performed.

The adapter rejects path traversal, missing/changed files, invalid frame counts, nonfinite/improper rotations, non-SOMA77 input and disagreement between pose arrays and forward kinematics. Overlapping guides are rejected because they carry shared implicit root conditions; use one combined end-effector guide for simultaneous hands/feet. It snapshots selected poses in upstream JSON form and records source hashes and adapter version. Invalid sources fail before text encoding; generation checks again before loading the checkpoint, including on resume.

Pinned upstream code converts SOMA77 constraints to SOMA30. Hand guides constrain wrist position/rotation and hand-end position **plus root path, hip height and heading**. Full-body guides constrain joint positions rather than explicit local rotations. Root guides here include path and heading. These implications appear in the UI and provenance. Pose-conditioned outputs retain the normal raw NPZ/BVH, SOMA GLB, root track, predicted foot contacts and request timeline.

Primary source inspected: `vendor/kimodo/docs/source/user_guide/constraints.md`, `vendor/kimodo/kimodo/constraints.py`, and `vendor/kimodo/kimodo/model/kimodo_model.py`, all at pinned commit `58e781898b3d7e328a676a75d3e338c45dce3ad9`. No vendor source or checkpoint was modified.

## Matched-seed pilot

`reports/action-jobs/pose-guided-generation-v1` contains eight newly generated takes: waving and kicking, text-only versus one effector pose at frame 60, seeds 77 and 88. Targets are the seed-11 source clip's peak hand/foot-height pose. These actions and targets are in-sample; seed 77 was already used in earlier project studies. `provenance-clarification.json` corrects the original freeze's loose “new seeds” wording. No held-out/generalization claim.

Exact text features were copied from the validated original action cache, with revision, manifest and tensor checksums. Original BF16 base/FP32 adapters and experimental disk offloading remain qualified: full 8B resident equivalence is untested. Checkpoint weights are unchanged, 100 denoising steps, separated CFG [2,2], no postprocessing.

Maximum conditioned-joint position error at the target frame:

| Action / seed | Text-only | Pose-guided | Guided effector rotation | Guided peak skin-floor depth |
|---|---:|---:|---:|---:|
| Wave 77 | 22.35 cm | 2.89 cm | 4.95° | 0.97 cm |
| Wave 88 | 17.88 cm | 2.29 cm | 4.66° | 1.03 cm |
| Kick 77 | 54.01 cm | 1.52 cm | 9.89° | 0.59 cm |
| Kick 88 | 52.42 cm | 2.03 cm | 5.55° | 0.79 cm |

All four guided takes pass the provisional 3 cm/15° conditioning-channel screens. This does not measure action correctness or naturalness. Wave 88 still exceeds the 1 cm surface threshold on 11/120 frames; the inspector preserves that failure. Kick 88's predicted-contact foot-speed p95 increases from 10.60 to 12.06 cm/s. All eight full skin surfaces were audited at every frame using all 18,056 vertices and eight skin weights. No object/self/partner or continuous collision claim.

The first guided attempt failed before sampling because upstream `crop_move` recreates sparse joint indices on CPU while our initial adapter moved frame indices to CUDA. The corrected adapter keeps sparse indices on CPU and pose values on CUDA, matching upstream's own multiprompt transition construction. `source-snapshot`, `freeze.json`, failed attempt/log, `failed-pipeline-before-device-fix.json`, `source-snapshot-amended` and `freeze-amended.json` preserve the change. The two successful text-only baselines were reused byte-for-byte on resume. Targets, seeds, prompts and screens did not change.

## Sequence boundary failure

`reports/action-jobs/pose-guided-sequence-smoke-v1` generates two 60-frame segments using the same wave description, with guides on frames 59 and 60. This tests actual CUDA multiprompt generation and output indexing, not semantic transition quality. It exports 120 frames correctly, but the boundary guide reaches **4.32 cm position error and 30.24° rotation error**, failing both screens. Root-path error remains below 0.54 mm. The failure is retained in its constraint audit and Studio flag. The runtime/indexing integration works; reliable boundary pose adherence does not yet.

## Verification and reproduction

176 Python tests pass, including CUDA sparse-index interoperability, guide frame cropping across a segment boundary, pose/FK consistency, root-error detection, hashing and rejection before encoding. Nine exported GLBs validate with zero errors/warnings; every exported joint pose is checked against raw motion. All nine ZIP contents and their localhost HTTP responses match saved bytes. Browser checks verify pose capture, invalid target rejection without launching a job, retained original composer text, displayed accuracy/floor failure, frame-60 jump, terminal-frame rendering and clean console.

From the project root, with a new output directory:

```powershell
.venv\Scripts\python.exe scripts/prepare_pose_generation_study.py reports/action-jobs/pose-guided-repeat
.venv\Scripts\python.exe scripts/run_actions.py reports/action-jobs/pose-guided-repeat/request.json --output reports/action-jobs/pose-guided-repeat
.venv\Scripts\python.exe scripts/audit_body_ground.py reports/action-jobs/pose-guided-repeat
.venv\Scripts\python.exe scripts/compare_pose_generation.py reports/action-jobs/pose-guided-repeat
node scripts/validate_action_exports.mjs reports/action-jobs/pose-guided-repeat
```

Next: connect scene-authored feasible poses to this generation path and measure independent surface/partner contacts; investigate sequence-boundary guide drift without relaxing thresholds. Continue broader rig transfer, rough-clip editing, controls and held-out action/animator release work under the same project-wide goal.
# Explicit starting origin

The Python request runner now accepts an optional request-level `"guide_origin": "start_pose"`. It requires a guide at target frame0 and translates every guide by that anchor's smoothed-root XZ offset. This makes an arbitrary captured starting pose compatible with Kimodo's canonical starting origin while preserving relative target placement. Source files, heights, rotations and scene geometry remain unchanged. Each compiled guide's provenance records the shared translation. Omit the option to preserve the previous source-placement behavior.

This option is currently available through request JSON; a Studio control has not been added. A world-space scene or partner placement still needs its own explicit transform. It is not a collision or animation-quality correction. The complete canonical-start study still has missing action phases, guide residuals and floor penetration.
