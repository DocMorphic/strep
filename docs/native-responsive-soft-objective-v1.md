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

The next bounded real-clip experiment starts from the exactly replayed selected-track parent and complete original controls. It selects native keys 84–115 and the eight already-permitted bilateral leg tracks (62, 61, 60, 59, 57, 56, 55, 54), keeping 768 variables. Their full native interpolation support covers every saved late failure. The original early touch, all fixed channels and all source conditions remain protected; an early fixed failure must remain visible even if late corrections improve. The study keeps one iteration, trust 0.02, difference step 0.001, four decoded backoffs, a 750-second proposal budget and the existing 768 MiB/1,200-second wider-study guard. It is a development case, not held-out evidence.

Generated evidence remains local under ignored `reports/native-fixed-soft-regression-before-v1` and `reports/native-responsive-soft-validation-v1`. All fourteen capability/calibration gates remain unapproved; the full-project goal stays active.
