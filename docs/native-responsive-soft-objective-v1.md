# Correcting one interval when another still fails

The shared `native_scene_conic.direction` proposal solver now minimizes the worst positive affine excess among soft rows with a nonzero recorded derivative, before minimizing control norm. Complete decoded acceptance still checks every original row. This addresses a measured obstacle to correcting long clips in bounded windows; it does not make a failed animation acceptable.

## Reproduced failure

The [selected-track crawl trial](native-interval-track-selection-v1.md) leaves 45 early rate failures and 332 later failures. The early edit window cannot affect the later native channels. Conversely, a later window would inherit an early normalized excess of 345.953947, larger than every late excess (at most 24.960087).

Previously, each exactly fixed failed soft row placed a lower bound on the worst-excess variable. Once that larger constant determined the objective, the minimum-control-norm phase could choose zero motion even when another editable target could be repaired. Four small actual-solver cases reproduce this with dense and sparse derivatives and fixed excesses of 2 and 20: the editable target retains approximately 0.4 excess instead of reaching its target. The failing batch is retained; its 19.297-second guard and all 21 resource observations replay.

## Proposal policy and unchanged acceptance

For fixed positive excess `F` and responsive worst positive excess `R(x)`, full affine worst excess is `max(F, R(x))`. Minimizing `R(x)` also minimizes that full maximum, while selecting useful progress within a plateau created by `F`. The minimum-norm phase must preserve the responsive optimum, rather than reopening that plateau.

Only rows with exactly zero stored Jacobian entries are treated as fixed. No small slope is thresholded away. Rows proved passing over the entire affine trust box retain their existing conservative screening rule. All responsive hard cones and original control boxes remain; any fixed failed protected row still stops with `FixedProtectedConflict`. A fixed failed soft row remains failed in full predicted merit and independently decoded acceptance. Neither its source cap nor its residual changes.

Reports distinguish `fixed_soft_excess`, `responsive_soft_rows`, and `soft_objective_policy: responsive_rows_then_minimum_control_norm`. `affine_optimum`, `primary_affine_soft_excess` and minimum-norm bound comparisons describe the responsive objective. Additional `primary_affine_global_soft_excess` and `minimum_norm_affine_global_soft_excess` retain the complete soft maximum; `predicted_norm_merit` still covers all original rows. These are proposal diagnostics, not approval or proof of nonlinear feasibility.

The separate explicitly budgeted solver and historical archived implementations are unchanged. Previously completed studies retain their original methods, outputs, failures and replay receipts. The new default applies to callers of the shared solver, including public native-key interval restoration. Full native export, complete per-condition no-worsening retention, geometry, engine, semantic and human-quality gates remain necessary.

## Validation and experiment

All **169 affected checks pass in 252.60 seconds**, including the four regressions that fail before the change. Coverage includes dense/sparse fixed-failure cases, fixed protected conflicts, all-fixed cases, approximate secondary-solve safeguards, original norm/contact/geometry proposals, actual affine exports, selected tracks, seeded restoration, replay and continuation. The guard completes in 269.203 seconds with peak sampled process-tree RSS 151,662,592 bytes; all 265 resource observations and archived bindings replay. The declared CPU profile retains a 512 MiB estimate/cap, additional 600 MiB free-memory floor, 15-second admission stability and 900-second supervisor limit. No model generation, training or release approval is implied.

The bounded real-clip experiment starts from the exactly replayed selected-track parent and complete original controls. It selects native keys 84–115 and the eight already-permitted bilateral leg tracks (62, 61, 60, 59, 57, 56, 55, 54), keeping 768 variables. Their full native interpolation support covers every saved late failure. The original early touch, all fixed channels and all source conditions remain protected; an early fixed failure remains visible even if late corrections improve. The study keeps one iteration, trust 0.02, difference step 0.001, four decoded backoffs, a 750-second proposal budget and the existing 768 MiB/1,200-second wider-study guard. It is a development case, not held-out evidence.

The primary solver reports `Solved` after 35 iterations over 482,068 norm rows, with 355,609 protected rows, 2,760 active cones and 1,439 responsive soft rows. Its responsive affine excess is 9.287111462 while the complete soft maximum remains the fixed 345.953947221. Fifty fixed failed soft rows remain recorded, including the early failures; no source limits are reset. The secondary minimum-norm point fails the separate hard-row recheck and is not used.

| Decoded clip | Original rate failures | Failed floor times | Squared positive excess | Retained |
| --- | ---: | ---: | ---: | --- |
| Exactly reproduced start | 377 | 5 | 715,406.124497 | Baseline |
| Full step | 331 | 14 | 712,250.677675 | No: floor conditions worsen |
| Half step / final | 351 | 5 | 713,338.340066 | Research continuation only |

The half step retains complete per-condition no-worsening, removes 26 rate failures and preserves all original cap arrays, inactive controls and nonselected native rotation channels. Contact error stays exactly 4.934019947 mm, root error remains zero, peak sampled floor depth stays 5.258763935 mm, and the complete maximum normalized excess remains 345.953947221. Thus the same worst residual can accompany useful localized progress; neither that progress nor the solver status approves the asset. All 351 motion-rate failures and five floor failures remain visible. The final GLB SHA-256 is `bfced13e10292f5e60e2b0063a0ebdf71d37e5743aaa3814a2fb8a25e6337a9f`.

The production guard completes in 610.578 seconds with peak sampled process-tree RSS 494,014,464 bytes. All 600 resource observations and archived bindings replay within the unchanged wider-study CPU policy. The separate standard replay verifies all four returned GLBs byte-for-byte, complete observations, contact/geometry reports, both retention decisions and the full final native-control archive. Its guard completes in 282.469 seconds with peak sampled RSS 570,204,160 bytes; all 280 resource observations replay under the same 768 MiB CPU cap, additional 600 MiB free-memory floor, 15-second admission stability and 1,200-second supervisor limit. No solver or Jacobian reruns. Shared reader/curve/skin/audit code does not provide independent physical, engine or human-quality evidence.

Generated evidence remains local under ignored `reports/native-fixed-soft-regression-before-v1`, `reports/native-responsive-soft-validation-v1`, `reports/crawl-late-bilateral-interval-v1` and `reports/crawl-late-bilateral-interval-replay-v1`. All fourteen capability/calibration gates remain unapproved; the full-project goal stays active.
