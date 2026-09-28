# Source-context-preserving rig transfer, 2026-09-27

Prompt-based clip editing now retains the source character's animated non-pelvis bone translations and unmapped helper transforms. Previously, transfer reset them to reference values, losing detail before the edited section was blended back into the source clip. Mapped orientations and pelvis placement still come from the generated motion and existing calibration. Plain transfer without source context keeps its previous behavior.

## Implementation and scope

`retarget_rig.transfer` accepts validated per-frame `context_local` transforms. They must be finite, affine and rigid, with matching frames and node count. Scale, shear and reflection are rejected. The input is not mutated. `rig_prompt_edit.py` passes the selected source section and records the policy in its audit. The independent prompt-edit verifier supports both old and new audits. This change is in the real Studio worker path; optional native pose fitting and experimental clearance corrections remain separate.

## Matched comparison

`study_context_transfer.py` reuses four development failures: jump seeds 205/204 on Cesium and dance seeds 203/204 on Quaternius. Each has the same raw and previously pose-fitted native input, transferred with reference offsets or preserved context, and exported before and after the original splice. These are 32 GLBs representing four underlying motions, not 32 independent examples or held-out evidence. The study performs no inference or training.

For pose-fitted Cesium inputs, unblended mapped anchor position error drops from 3.988296 mm to 0.001895 mm. Maximum non-root local translation loss drops from 3.013603 mm to numerical noise. Quaternius already had matching translations and remains near 0.001276 mm. Natural helper motion coverage is limited; a separate test deliberately animates an unmapped helper. Raw generation still misses requested boundary poses. The fix preserves source detail; it does not fix floor contact or certify realistic action.

## Verification

Seven new tests cover animated context preservation, desired mapped orientation/root behavior, input immutability, shape mismatch, nonfinite transforms, nonaffine matrices, scale and reflection. The focused suite passes 45 tests. The full suite passes 357 tests in 90.46 seconds with four existing Torch deprecation warnings. Report code added afterward was exercised separately.

`verify_context_transfer.py` independently reconstructs hierarchy and per-node SciPy Slerp, sharing only established calibration. Every decoded comparison frame passes its transfer/splice oracle and fixed-frame checks. It also measures all-frame source transform preservation, unblended anchors, target skin at integer/half frames and joint rotation steps. All 32 GLBs validate with zero errors and inherited asset warnings; HTTP bytes match their saved hashes. Actual Godot imports and joint playback pass over 2,656 frames.

A fresh Studio API edit, job `20260927-004526-f9764f83`, repeats jump seed 205 using the unchanged checkpoint. Inference took 4.92 seconds; the raw NPZ is byte-identical to the earlier run. The production export retains non-root translations within 6.7e-16 m and 14 fixed frames within 1.2e-7 in world matrix elements. Its 115-entry authoring package and HTTP downloads verify. Two additional Godot imports pass across 122 frames. Combined engine evidence is 34 files / 2,778 frames.

That fresh edit still has 102.55 mm raw boundary error and 70.72 mm target floor penetration. Both failures remain visible in Studio. Export correctness is distinct from motion quality.

The [comparison viewer](http://127.0.0.1:8767/reports/context-transfer-v1/viewer.html) shows matched stages, metrics, current GLBs and original asset/license packages. The [fresh Studio edit](http://127.0.0.1:8768/studio?rig_job=20260927-004526-f9764f83) has its own full authoring package. The report's final UTF-8 text and grey character preview were checked in the browser.

Next work must address contact and temporal quality together, then broaden evaluation across actions and rig proportions. Frozen penetrating source frames require an explicit context-repair operation, not silent preservation relaxation. Scene/partner support, style controls, offline installation and independent animator cleanup evidence remain open release gates. The same full-project goal remains active.
