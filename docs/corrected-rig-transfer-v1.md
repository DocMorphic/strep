# Pose fitting followed by target-rig clearance, 2026-09-27

The four retained native pose-fitting candidates now pass through target-rig transfer, the existing edit-envelope splice, and bounded mesh correction. All four meet the provisional 5 mm floor-depth screen inside the editable region, including half-frame samples. Both dance clips also meet it over the whole clip. The jump clips preserve source frames that already penetrate by 24 mm, so they still fail overall. Contact and transition quality remain unapproved; Studio defaults are unchanged.

## Experiment

`study_corrected_rig_transfer.py` uses the `guided_pose_only` outputs from `motion-correction-v2`: jump seeds 205/204 on the imported Cesium rig and dance seeds 203/204 on the Quaternius rig. No inference, text encoding, training, model changes or new motion data. These are four reused failures, not held-out coverage.

For each case it preserves the old raw splice, aligns the corrected native motion using the original origin, exports the unblended transfer, applies the original smooth edit envelope, and runs the unchanged v3 mesh-clearance fitter. The target height is the scaled native foot-surface height, clamped at the floor and blended with source heights near the fixed edges. The solver preserves horizontal foot-surface positions relative to its input, not physical planted contacts. It keeps all outside frames and two frames at either end fixed, with the existing root, joint and adjacent-edit bounds. Original predicted contact annotations are retained as predictions.

| Case | Raw splice editable depth | Pose fitting + splice | Plus mesh correction | Editable half-frame depth | Whole-clip depth |
|---|---:|---:|---:|---:|---:|
| Jump 205 | 70.71 mm | 72.40 mm | 0.36 mm | 0.47 mm | 24.06 mm |
| Jump 204 | 62.57 mm | 75.38 mm | 0.62 mm | 1.94 mm | 24.06 mm |
| Dance 203 | 14.38 mm | 23.21 mm | 2.36 mm | 2.37 mm | 3.00 mm |
| Dance 204 | 20.75 mm | 25.17 mm | 2.19 mm | 1.97 mm | 3.00 mm |

The 14 fixed jump frames and 24 fixed dance frames are preserved within 1.2e-7 in world matrix elements. Thirteen frozen jump frames exceed the floor screen. Their failure cannot be repaired while also keeping those frames unchanged.

## Pose accuracy and remaining motion regressions

Native anchor positions remain within 0.0031 mm and mapped target rotations within 0.0003 degrees. The target pelvis is within 6e-8 m. The unblended transfer is measured before the splice restores original poses, so preservation cannot conceal a transfer error.

Target joint positions are not equally exact: Cesium has up to 3.99 mm mismatch while Quaternius is within 0.0013 mm. `jump-205/source-local-translation-diagnostic.json` shows non-root source translations differing from reference by roughly 0.4–3.0 mm at legs, torso and arms. Current transfer restores reference bone offsets. A separate four-anchor diagnostic retaining source local translations and unmapped transforms reduces mapped positional error to 0.0019 mm for jumps and 0.0013 mm for dances (`source-context-diagnostic.json`). That diagnostic has not been applied to these exported candidates.

Accurate poses and low penetration do not imply smooth contact. Maximum adjacent joint rotations, raw splice to final candidate, are 23.68→22.63°, 24.52→24.60°, 28.66→28.55° and 20.28→21.15°. Jump 205's entry transition improves but its return transition worsens, from 20.85 to 22.63°. Jump 204's predicted right-support speed p95 increases from 0.079 to 0.233 m/s; dance 203's left/right values increase from 0.213/0.199 to 0.244/0.253 m/s. The mesh stage largely preserves the sliding already introduced by pose fitting. Contact masks are matched across stages and remain unconfirmed; jumps contain only one predicted left-support step.

Jump fits hit six sweeps with 5 and 11 unsuccessful subproblems; dance 204 also reaches six sweeps. Dance 203 stops after five with a zero update, which is not an optimality certificate. All final edit bounds pass independent verification. Solver logs retain SciPy's intermediate clipping warning; no limits were relaxed.

## Verification and deliverables

`verify_corrected_rig_transfer.py` independently assembles desired mapped orientations, source-relative root placement and each node's SciPy Slerp splice. Calibration is shared with the established adapter. Transfer/splice errors are below 4e-7. It measures decoded target skin at every integer and half frame, root derivatives, endpoint neighborhoods and contact-speed proxies. `verify_rig_clearance.py` separately checks every edit bound, fixed transforms, root track, unchanged contact/timeline metadata and skin motion.

Twelve focused clearance/native-correction tests pass in 9.60 seconds with four existing Torch warnings. No full-suite rerun is claimed. Sixteen GLBs pass validation with zero errors and inherited warnings (one per Cesium file, six per Quaternius file). Actual Godot imports verify every joint over 1,388 frames; maximum position error is below 5e-7 m. These are format/playback checks, not physics or semantic acceptance.

The [comparison viewer](http://127.0.0.1:8767/reports/corrected-rig-transfer-v1/viewer.html) includes the prior mesh-only candidates where available. Four candidate ZIPs preserve current stages, recipes, audits, solver history and implementation snapshots, plus the original authoring ZIP with raw motion, character assets, licenses and provenance. Every archive entry and all HTTP-delivered ZIP/GLB bytes are verified. The source Studio jobs remain unchanged.

Next: preserve source animated translations and helper transforms during imported-clip editing, then address contact and transition changes jointly. A separate source-repair operation is required if an author wants to change frozen, penetrating context; it must not happen silently. Broader actions, scenes, partners, meaningful style controls, offline installation, held-out evaluation and independent animator cleanup evidence remain release gates under the same project goal.
