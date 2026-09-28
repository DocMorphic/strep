# Target-rig orientation and bounded contact correction

2026-09-26. Development evidence under the existing project-wide goal. Target-rig transfer remains **in progress**; no model training, new inference, release promotion or independent animator approval occurred.

## What changed

The direction-only transfer baseline tilted CesiumMan's sole surfaces by approximately 44 degrees in the standing wave. Its ankle-to-toe joint vector is not an anatomical sole axis. `retarget_rig.py` now supports explicit `axis_alignment_xyzw` overrides in checksum-bound rig profiles. These map target reference world axes into the SOMA neutral world frame. The Cesium profile v2 uses identity overrides for both feet and toe bases, preserving their authored neutral sole orientation. Other roles retain the original directional alignment. The original profile and all original transfer outputs remain unchanged.

`target_rig_contact.py` adds editable target-mesh contact specifications and deterministic fitting. Each specification binds to the input GLB hash, names explicit vertex patches, defines half-open contact intervals and world targets, selects editable joints, and sets edit limits. The convenience draft derives three sole patches per foot from reference geometry and skin weights, then drafts support intervals from model foot/toe predictions. Drafted contact targets need review; they are not confirmed contacts or gameplay events. Profiles lacking suitable mapped toes or flat reference soles must supply explicit patches instead of silently using a guessed fallback.

Fitting edits the pelvis world translation and selected local rotations, preserving all nonroot translations/bone lengths and all unselected local rotations. The least-squares objective includes support patch errors, **all active target-mesh vertices** against a flat floor, pose/root deviation and previous-frame edit deviation. The cached skin evaluator matches a separate CPU skin evaluator to floating-point precision. Acceptance is recomputed using that separate evaluator, then recomputed again from the exported GLB; solver success alone cannot pass a clip.

The frozen bounds are 4 cm horizontal pelvis shift, 12 cm vertical shift, 15 mm change of pelvis correction per frame, local rotation changes of 25° for hip/foot, 35° for shin and 15° for toe, and 5° change of joint correction per frame. Conservative component boxes lie inside those vector/angle budgets. These are **edit budgets, not anatomical joint limits or calibrated physical capability statistics**. Provisional screens require floor depth ≤5 mm and patch-centroid error ≤2 cm, solver convergence and every edit bound. Frames remain at 30fps; clips are neither looped nor stretched.

## Experiment and trade-off

The same three previously used seed-77 clips and same Cesium rig were evaluated. This is not a held-out study. The first fit (`target-rig-contact-v1`) weighted rotation deviation by 0.035 metres/radian. It passed the wave contact screen but changed a knee by up to 28.7°. A second, explicitly recorded objective (`target-rig-contact-v2`, 0.15 metres/radian) reduced unnecessary joint changes in the wave. It did **not** improve every metric or every action and has not replaced a product default.

| Case | Original floor depth | Axis-calibrated depth | v1 corrected depth / patch error | v2 corrected depth / patch error | v2 screen |
| --- | ---: | ---: | ---: | ---: | --- |
| Wave | 83.90 mm | 59.36 mm | 1.31 / 0.39 mm | 0.52 / 0.51 mm | Provisional pass |
| Kick | 82.36 mm | 65.52 mm | 6.33 / 10.89 mm | 6.12 / 25.01 mm | Reject: floor and patch |
| Get-up | 217.31 mm | 217.31 mm | 97.31 / 63.69 mm | 97.31 / 90.42 mm | Reject: floor and patch |

The v2 wave's largest local joint edit is 2.3°, versus 28.7° in v1. Its maximum vertical pelvis shift is 56.27 mm; horizontal shift 7.31 mm. Predicted-support patch-speed p95 is 0.027 cm/s. Neither numerical pass proves balance, absence of self-collision or naturalness.

The kick's worst floor vertex occurs at frame 46 and belongs to the left toe. The get-up's worst vertex at frame 11 is 97.6% head-weighted; editing only lower-body joints cannot move it relative to the pelvis. An optimistic analytic bound, computed after the experiment, proves at least 97.31 mm penetration remains with the declared 120 mm upward pelvis limit; 61 frames are provably infeasible. The stronger-prior fit fails the actual floor screen on 90 frames. The bound ignores temporal/contact restrictions, so it is a lower bound, not an estimate of achieved quality.

`floor_lower_bound()` now records this feasibility check before future fitting. Existing runs keep separate `feasibility-diagnostic.json` files marked `computed_after_fit: true`; the diagnostic was not retroactively claimed as a preflight of those runs. A zero bound does not prove feasibility. Supporting this get-up requires permitted upper-body/neck/head correction and appropriate surface/support constraints, a different rig reference strategy, or a consciously revised edit budget; repeatedly increasing foot-solver weights cannot solve its invariant head geometry.

## Verification and artifacts

- Nine GLBs (axis calibration, v1 fit, v2 fit × three actions): zero Khronos validation errors, one inherited `NODE_SKINNED_MESH_NON_ROOT` warning each.
- Actual Godot 4.7.2 import/seek: 1,260 frames × 19 target bones. Maximum world position error 2.10e-7 m and basis-element error 6.36e-7. Mesh surfaces import, but this is headless bone playback evidence, not GPU skin, physics, gameplay-event or semantic approval.
- Reloaded final GLBs preserve untouched local transforms within 7.4e-8 and nonroot translations within 7e-16 m. Corrected root sidecar positions match within 3.0e-8 m. Exported skin diagnostics and rejection flags agree with pre-export evidence.
- Six editable clip packages (v1/v2 × three cases) retain both passes and failures. Each contains the corrected finite GLB, corrected pelvis track, editable contact spec, solver/audit evidence, source transfer, rig profile, implementation snapshot and license files. ZIP entries and all six HTTP download hashes were verified. The packages reproduce deterministic fitting with the project runtime; they do not contain raw SOMA generation/model weights or reconstruct the complete original inference environment.
- Regression suite: 222 tests passed; four upstream Torch deprecation warnings. The final guard converts newly animated matrix-based helper joints to legal glTF TRS while preserving their reference transforms.
- Frozen executed solver/importer sources reside in each candidate and the study's `authoring-source`. Axis-calibration source hashes match the export records. The later feasibility-check addition does not alter the recorded optimization objective or fitted output.

The review page compares original/calibrated/corrected stages at the same frame, shows edit magnitudes and failures, jumps to the worst corrected floor frame, and links downloadable clips/specifications/evidence. Studio's default NVIDIA SOMA character and existing authoring flows are unchanged. CesiumMan is a separate licensed target-rig fixture shown in grey for this review.

Review: `http://127.0.0.1:8767/reports/target-rig-contact-v2/viewer.html`.

## Reproduce

From `C:\wassup\strep`, install the pinned `threadpoolctl==3.6.0` dependency if not already installed. NumPy/SciPy and the existing project runtime are also required. The thread limiter prevents parallel BLAS oversubscription during the per-frame solver.

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-rig-contact.txt
.venv\Scripts\python.exe scripts/retarget_rig.py transfer --character assets/characters/cesium-man/CesiumMan.glb --profile assets/characters/cesium-man/rig-profile-v2.json --source reports/action-jobs/body-holdout-seed77/takes/wave-seed-77/motion.npz --output reports/new-axis-transfer/wave
.venv\Scripts\python.exe scripts/target_rig_contact.py draft --transfer reports/rig-axis-calibration-v1/wave --output reports/new-contact-spec.json
.venv\Scripts\python.exe scripts/target_rig_contact.py fit --transfer reports/rig-axis-calibration-v1/wave --spec reports/new-contact-spec.json --output reports/new-contact-fit
.venv\Scripts\python.exe scripts/run_target_rig_study.py --study reports/rig-axis-calibration-v1 --output reports/new-contact-study --rotation-prior 0.15
.venv\Scripts\python.exe scripts/audit_target_rig_preservation.py --study reports/new-contact-study
node scripts/validate_rig_exports.mjs reports/new-contact-study
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/new-contact-study --output reports/new-contact-engine-check
.venv\Scripts\python.exe -m pytest tests -q
```

The single-clip `draft` retains the original 0.035 rotation prior; edit its objective explicitly to reproduce v2, or use the study runner's `--rotation-prior 0.15`. Choose fresh output directories. The source profile, contact targets and solver settings are all inspectable JSON; no motion-type whitelist is introduced.

## Next within the full goal

Bring character import, reference-pose mapping and axis editing into Studio, with feasibility feedback before fitting. Then test independently selected rigs/proportions and broaden target-surface support to upper-body contacts. Keep rough-clip editing, transitions, style controls, scene/partner correctness, offline installation and independent animator/cleanup-time evaluation open. Do not treat the successful wave as a completed rig-transfer release gate or keep tuning only these three motions.
