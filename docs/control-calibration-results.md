# Running controls — executed calibration milestone

Completed 2026-09-24. [Open the local comparison](http://127.0.0.1:8767/reports/control-calibration-v1/viewer.html).

The experiment supports three torso-lean settings and one compact arm-swing setting under the frozen engineering rules. Bigger arm swings hit their requested angles but fail some loop checks, so those levels remain experimental. The prototype exposes the measured choices and retains every failure. It does not calibrate agility, strength, stamina or fitness.

## What ran

Seven descriptions (six new control descriptions plus a neutral reference) were encoded locally with the existing experimental BF16/FP32 offload encoder. Each was generated at seeds 11, 22 and 55: **21 text-conditioned clips**. The neutral corrected loop at each seed received six separate explicit upper-body edits: **18 edited clips**, for **39 character exports** altogether. No combined arm-plus-torso edit was tested.

Seeds 11/22 were development seeds; 55 was reserved for evaluation. The new control editor was tested on a previous seed-11 neutral clip. Its implementation and the benchmark were frozen before applying it to the new grid. Seed 55 was used in older unrelated baseline work, so this is held out from this control implementation, not an entirely unseen seed across the project. No threshold or editor tuning followed its new results.

All generations use the unchanged Kimodo-SOMA-RP-v1.1 checkpoint/revision, pinned source, 120 frames at 30 fps, requested straight 3 m/s path, 100 denoising steps and guidance [2,2]. Full raw, selected-cycle, corrected and transferred measurements remain separate. The existing loop/stance quality thresholds were unchanged. New encoding and generation took about 6 minutes 14 seconds; measured encoder process-tree peak was 3.08 GiB. No training, paid service or new training data was used.

[Frozen protocol and primary sources](control-calibration-protocol.md). Kimodo's guidance supports concise behavior descriptions and warns that conditioning can be missed; this motivates measuring response instead of assuming an adjective is a calibrated control. [Official guidance](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/limitations.html).

## Supported levels and failures

| Source-space control | Tested targets | Qualified levels | Remaining failures |
|---|---|---|---|
| Arm range, mean bilateral p95–p5 shoulder-to-wrist sagittal span | 20°, 45°, 70° | 20° | 45° fails the pose-seam screen at seed 55; 70° fails at all three seeds |
| Torso forward lean, median Hips-to-Neck1 sagittal angle | 0°, 10°, 20° | All three | No source/control-screen failure at these settings |

“Qualified” means passing this small study's numerical gates, not professional realism or support for every value between endpoints. Fourteen of 18 direct edits pass all source checks. Twenty of 21 text takes pass source quality checks; upright/low-lean seed 55 fails requested speed and path tolerance. File validity, source quality and control fidelity are separate outcomes.

Every direct edit reaches its measured source target within 0.00003°. Root and lower-body joint positions are unchanged to the stored precision, contact labels are unchanged, and maximum local edit is 26.92°. The other source angle descriptor is unchanged within numerical tolerance. This demonstrates mathematical control accuracy, not biomechanics: rotating the spine is not a physical simulation of whole-body balance.

Control offsets are applied **after** loop/stance cleanup. The raw and selected-cycle descriptors attached to direct trials describe the unchanged neutral input; they are not evidence of control effects before editing. The editor's internal angle diagnostics tile a cycle without travel; use the main summary speed screens and GLB reports for world speed, not non-angular fields in that internal diagnostic. Upper-body changes can still worsen seams, as the arm failures demonstrate.

## Text response versus explicit control

None of the six text control/seed combinations meets the frozen minimum separation across all three levels after processing (10° adjacent arm separation; 5° torso separation). Some responses increase in the intended direction but too weakly; others reverse. This is not a claim that every text response is non-monotonic.

The direct editor is given numerical targets while the model receives adjectives. This is an authoring-method comparison, not a claim that the model failed an equivalent numeric conditioning interface. Exact target fitting is expected from the editor. The substantive tests are preserved quality, unrelated motion, target-rig response and held-out behavior.

Selecting loops can weaken full-clip characteristics. Raw, selected raw and processed values are retained in `analysis.json`; no selected clip is labeled as the full raw generation. Character effects are also not identical to source angles because the skeletons have different proportions and rest geometry. All direct responses remain ordered after transfer, with response-delta error against the matched neutral baseline at most 4.33° under the frozen 5° tolerance. The other target angle changes by less than 0.00001°.

In particular, the held-out 20° source lean appears as **9.60° measured torso lean on CesiumMan**, compared with its approximately −4.47° neutral posture. It must not be sold as an exact 20° control for arbitrary characters. A future rig-specific angle solver should address that distinction.

All direct exports retain the neutral foot defects: sampled floor penetration is zero at measured keys/midpoints, but predicted-support foot mesh height reaches 1.91 cm, and sliding remains measurable. No independent contact annotation, continuous collision, self-collision, balance validation, animator rating or engine import was performed.

## Per-seed processed responses

Triplets are low / medium / high, in degrees. Source arm targets: 20 / 45 / 70; source torso targets: 0 / 10 / 20. Source-accurate rows can still fail loop quality.

| Control | Seed | Text / source | Direct / source | Direct / character |
|---|---:|---|---|---|
| arm | 11 | 11.90 / 24.89 / 16.12 | 20.00 / 45.00 / 70.00 | 19.51 / 44.55 / 69.65 |
| arm | 22 | 31.91 / 42.97 / 43.94 | 20.00 / 45.00 / 70.00 | 18.90 / 43.62 / 68.62 |
| arm | 55 (held-out) | 13.91 / 19.49 / 24.55 | 20.00 / 45.00 / 70.00 | 21.34 / 46.30 / 71.27 |
| lean | 11 | 3.97 / 10.13 / 11.03 | -0.00 / 10.00 / 20.00 | -4.69 / 2.98 / 10.63 |
| lean | 22 | 4.22 / 3.25 / 5.70 | 0.00 / 10.00 / 20.00 | -3.84 / 3.84 / 11.50 |
| lean | 55 (held-out) | 3.89 / 9.27 / 9.42 | 0.00 / 10.00 / 20.00 | -5.71 / 1.96 / 9.60 |

## Using the prototype

Choose arm swing or torso lean, low/medium/high and a take. Compare the edited result with its matching neutral corrected loop or a separately generated text-only take. The neutral comparison shares timing/phase; the text comparison does not. Playback, scrubbing, camera and half-speed controls are available. The shorter clip holds its final pose in unequal-duration comparisons.

GLB, BVH, NPZ and edit evidence are downloadable for every condition. Qualified levels enable an authoring request export, also shown as copyable JSON. Failed levels remain reviewable but cannot produce a qualified request through the UI. Exports select already measured takes; they do not trigger new browser-side inference.

`authoring-mapping.json` versions the tested source-angle choices and application order. Capability mappings are explicitly null. A game designer may later define transparent stat-to-style rules, but high agility does not inherently imply one arm angle, and this short running experiment cannot validate strength or endurance.

## Verification and reproduction

- 36 tests pass, including exact angle response, unchanged feet/root/contact, bone-length preservation, input immutability, invalid requests and preventing a held-out or rig failure from qualifying a control.
- All 39 GLBs have zero Khronos validation errors. Each retains one inherited non-root skinned-mesh warning and 76 informational notices from the original asset.
- Every exported animation was read back and CPU-skinned at all keys, with vertex error below 0.00001 m. Edited BVHs round-trip within 0.0001 m.
- All 18 direct edits independently reproduce identical saved arrays. Generated motions are hash-verified; this milestone does not independently regenerate all 21 text takes.
- All 40 prior raw files (25 baseline plus 15 profile-pilot) retain their recorded hashes. Previous reports remain intact. Full-size resident encoder equivalence remains untested.

Artifacts and logs: `reports/control-calibration-v1/`. `text/` holds 21 raw/corrected/generated results and `direct/` holds the 18 edited results. `analysis.json`, `authoring-mapping.json`, `verification.json`, the two implementation-freeze records and per-stage logs preserve evidence. The implementation snapshot preserves source/configuration versions.

To reproduce in a **fresh directory** using this prepared environment:

```powershell
cd C:\wassup\strep
.venv\Scripts\python.exe scripts/reproduce_control_study.py --output reports/control-calibration-repeat
.venv\Scripts\python.exe -m pytest tests -q
```

The wrapper rejects an existing output directory and reuses the hash-checked prompt cache. It repeats generation, processing, edits, exports, measurements and verification; it is not a new blind evaluation. Keep the folder directly under `reports/` for the viewer's relative local dependency links. If the server is stopped, run `.venv\Scripts\python.exe -m http.server 8767 --bind 127.0.0.1` from the project root.

The original staged runner is `scripts/run_control_study.py`; `scripts/run_profile_pilot.py` with `--study benchmarks/control-calibration-v1.json --output reports/control-calibration-v1/text` supplies its generation stage. Completed stage journals permit continuation without silently replacing original artifacts. A partial direct-edit failure requires inspection and a fresh reproduction directory.

## Next decision

Keep the supported posture choices and compact-arm result. Improve large-arm seam continuity in a new version and evaluate it with a newly reserved seed rather than relaxing the present thresholds. Calibrate requested angles directly on the target rig, then assess combined controls and human naturalness. Game-stat mappings should follow action-specific tests of acceleration, turning, stopping and jump/landing; this study supplies no automatic capability conversion.
