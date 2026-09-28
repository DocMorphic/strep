# Target-rig trim, speed and local pose editing

Development evidence, 2026-09-26. The full-project goal and all release review gates remain open. No model training or new inference was needed for this change.

## Workflow

In Studio Characters, choose a motion result and its version, then **Edit timing and pose**. Choose inclusive first/last source frames and a speed multiplier, optionally add smooth local bone rotations, and apply. A new immutable job preserves the selected input, original character/motion, recipe, contact drafts and output. Input and edited preview versions use their own frame counts; switching maps the displayed frame through the saved source clock, rounded to the closest available frame and clamped outside the trim.

The interface explicitly shows the source pose until the edit is applied. Pose curves use start, peak and end source frames. The XYZ delta becomes one local rotation vector, smoothly scaled with cubic smoothstep on both sides of the peak and postmultiplied onto the source bone rotation. Unedited local poses and every local translation are preserved; world placement is retained. At most 24 curves are accepted, combined rotations cannot exceed 90 degrees, and overlapping curves on the same bone are rejected. This is deterministic pose editing, not text-driven semantic motion editing.

Speed is 0.25–4x. Output stays at 30 fps, includes both trim endpoints, and cannot exceed 30 seconds. The frame count is the nearest integer number of output intervals, with half ties rounded up; the exact effective speed is reported. Geometry, predicted-contact intervals and authored-contact intervals share this frame mapping. Intervals use half-open discrete membership; intervals missed by downsampling are explicitly listed in the audit. Authored world targets stay fixed and must be reviewed after edits. Root tracks describe the mapped pelvis, not engine root extraction.

## Reproduced evidence

| Job | Input / edited frames | Edit |
| --- | --- | --- |
| `20260926-204805-38b5db10` | 61 / 21 | Original Cesium embedded animation after an earlier contact edit; trim 10–40, speed 1.5, LeftArm local Z +10° peaked at source 25 |
| `20260926-204848-eaceb96b` | 120 / 31 | Generated, retargeted Quaternius female wave after an earlier contact edit; trim 30–90, speed 2, RightArm local Z −8° peaked at source 60 |
| `20260926-205132-5726f4ae` | 31 / 31 | A subsequent contact correction on the edited wave, proving the retimed annotation clock survives another authoring job |

The imported clip was authored through the actual Studio UI. Its heel interval 21–25 became 8–10 on the edited clock. The UI showed input frame 40/60 when comparing edited endpoint 20/20, and input frame 12/60 when comparing edited frame 1/20. Contact inspection reports 3/21 frames over 5 mm floor depth, maximum 10 mm: this remains a failed floor screen. No source support predictions are invented for imported animations.

The wave retains its original model-predicted contact provenance. These are unconfirmed support annotations. Subsequent contact correction passes its limited numerical screens; that does not establish naturalness or correct dynamics after a speed change.

`verify_clip_edit_study.py` decodes saved input/output GLBs and checks all local matrices against independently calculated edit curves, root tracks, contact membership/targets, served GLB hashes and every ZIP entry. Maximum local matrix error is 7.66e-8. The two edit archives contain 40 and 42 entries. `verify_mesh_contact_study.py` independently rechecks the chained contact job's exported metrics, bounds, untouched poses, root tracks and package bytes.

Evidence lives in `reports/clip-edit-authoring-v1` and `reports/clip-edit-contact-chain-v1`. Actual Godot import evidence is in `reports/godot-clip-edit-authoring-v1` and `reports/godot-clip-edit-contact-chain-v1`: six files, 295 frames total, 19/65 bones, all skinned surfaces present; maximum position error 3.74e-7 m. All six GLBs have zero validator errors, with inherited warnings (one on each Cesium file, six on each Quaternius file). The first validator invocation encountered a manifest absolute-path join error; the manifest writer was fixed to use relative paths and validation rerun successfully. No artifact encoding tolerance was relaxed.

Full regression suite: 273 tests passed with four upstream Torch deprecation warnings. Additional tests cover malformed recipes, clock quantization/endpoints, exact local pose preservation, contact remapping, selected input-version metadata and native annotation hash/clock integrity through contact chaining.

## Remaining scope

No physical realism, animator, semantic, force balance, continuous collision or scene-contact approval is implied. Pose/time changes may create invalid support or dynamics. Loops, transition preservation, object/partner time synchronization, prompt-based semantic editing, a broader independently selected clip/rig set, and measured animator cleanup time are still required. These implementation fixtures are not held-out release evidence.
