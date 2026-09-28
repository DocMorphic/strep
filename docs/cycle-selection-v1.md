# Cycle selection in Studio — 2026-09-26

This is development evidence under the single full-project goal. No release criterion or motion category is declared complete.

## What works

Characters → Make a loop → Find candidate cycles searches user-selected start/period ranges. The existing root mode, turn and blend settings apply to every candidate. A fixed integer stride makes the grid reproducible. Searches reject changed GLB hashes, invalid ranges, more than 400 candidates or more than 40,000 total candidate frames. The local API uses the same origin checks as other Studio writes and serializes searches with a dedicated lock.

Five proposals display joint steps, pose/velocity mismatch, root acceleration, predicted support disagreement, sampled mesh penetration and annotated patch sliding. Selecting one changes the loop range; Create loop remains the explicit action that exports it. Changing the source or search settings invalidates stale proposals, including an in-flight response. The original source and every generated loop remain available.

Every search saves its complete ranking, request, source hash, support masks, authored patch intervals, source report and implementation snapshots under `reports/rig-loop-searches/<id>`. This references the immutable source job; it is not a self-contained portable source package. The complete JSON ranking is downloadable from Studio.

## Fixed heuristic and limits

The rank is the sum of maximum local joint step / 10 degrees, aligned return/head pose gap / 45 degrees, angular velocity gap / 300 degrees per second, root acceleration / 10 metres per second squared, and predicted support disagreement fraction. These are ranking scales, **not acceptance thresholds**. No weights were fitted to these clips.

The actual loop assembler is used for kinematic evaluation. Maximum steps include the step after wrap. Pose/velocity gaps compare the source head and cycle-aligned continuation throughout the blend. Predicted support disagreement compares the two sources during positive-weight blending. Missing or partly unknown prediction evidence returns null rather than a zero disagreement claim; that lineage now survives loops, joins and retiming. An available model prediction is still unconfirmed support.

Only the five kinematic winners receive integer-frame mesh diagnostics. The rank does not optimize floor depth or mesh patch sliding and can prefer quieter, shorter or incomplete actions. The supplied tempo bounds and subsequent content review matter. There is no semantic suitability classifier, automatic acceptance, self/partner collision check, wrap-aware contact solver or continuous collision proof. Partial blend weights count in patch sliding; sparse annotations do not establish whole-cycle support. Source events still need periodic mapping. The baked three-cycle output does not prove a runtime engine cycle/root-motion consumer.

## Frozen comparison

Same source GLBs, root modes, blend=8, turn=0; start/period changed only. Wave grid: starts 0–30, periods 30–90, stride 5 (88 valid pairs). Imported locomotion grid: starts 0–15, periods 20–45, stride 5 (21 valid pairs). These are two development examples, not held-out action coverage.

| Measurement | Wave manual | Wave proposal | Locomotion manual | Locomotion proposal |
|---|---:|---:|---:|---:|
| Start / period frames | 10 / 60 | 25 / 45 | 0 / 30 | 10 / 20 |
| Maximum joint step (degrees) | 22.91 | 19.35 | 24.47 | 18.04 |
| Return/head pose gap (degrees) | 122.90 | 26.78 | 112.01 | 95.60 |
| Velocity gap (degrees/s) | 401.29 | 277.18 | 700.63 | 411.83 |
| Root acceleration maximum (m/s²) | 0.753 | 0.829 | 17.679 | 17.679 |
| Integer-frame floor depth (mm) | 3.01 | 3.01 | 50.44 | 15.32 |
| Half-frame floor depth (mm) | 3.01 | 3.01 | 50.65 | 14.09 |
| Annotated patch horizontal speed p95 (mm/s, one cycle) | 0.484 | 0.691 | 10.913 | 10.913 |

The wave's remaining peak is the right hand at source frames 58→59, preserved outside the return blend. Its earlier manual peak was the right upper arm inside that blend. The locomotion peak is the left lower leg at source 18→19, also outside the blend. This localizes the maxima; a maximum alone does not establish an unnatural action. Both candidates retain the source-window maximum step rather than creating a larger one. The wave has slightly greater sliding and root acceleration than its manual baseline despite the lower rank. Locomotion still fails the unchanged 5 mm floor screen in 8/21 samples; its short cycle and 95.6-degree mismatch need action/phase review. Neither is production-approved.

Jobs: wave baseline `20260926-213335-362828ae`, proposal `20260926-215001-012ea007`; locomotion baseline `20260926-212922-5f10b11e`, proposal `20260926-215013-58f47dfd`. Search IDs `20260926-215001-03d5b8a9` and `20260926-215012-accfbef3`. UI repeated the wave search as `20260926-215033-469dec40` with the same winner. Final API provenance check `20260926-215459-62f03491` confirms a loop derived from an unannotated source still reports unknown predictions.

## Verification

- `reports/cycle-selection-v1/selection-verification.json`: all 109 grid scores reproduced, HTTP JSON matched, predicted metrics matched independently decoded winners; both baseline/winner metrics and bone/frame localization retained.
- `reports/cycle-selection-v1/verification.json`: independent SciPy Slerp reconstruction, all-frame transforms, three-cycle accumulation, original seam, half-frame floor, patch sliding, exact HTTP GLB hashes and every archive entry.
- Eight GLBs: zero validator errors; inherited six Quaternius / one Cesium warnings per file.
- `reports/godot-cycle-selection-v1/verification.json`: actual Godot 4.7.2 import, 628 samples across 19/65-bone rigs and all skinned surfaces; maximum joint-position discrepancy 3.74e-7 m. Finite mode preserved; no hidden engine wrap.
- 298 full tests passed with four upstream Torch deprecation warnings. After adding peak localization and unknown-lineage preservation, 38 affected tests passed (11 search tests included). Do not describe the final total as a new full-suite run.
- Browser: search completion, choosing proposal 1 (start 25 / period 45), invalidation after changing turn, three-cycle version loading and the rendered grey character checked. No independent animator ratings or cleanup time collected.

Next: preserve phase closure while correcting contact defects, map periodic source events, and implement the deliberate runtime cycle/root/event consumer. Interleave remaining semantic editing, scene/partner, style, offline packaging and held-out review gaps; cycle selection is only one part of the project.
