# Repairing a rejected native step without weakening its limits

A tiny cached-Jacobian repair makes a previously rejected half step retainable against its original research seed. It repairs 14 source-rate failures while preserving sampled floor clearance, compared with six repairs from the ordinary quarter step. The resulting clip still has **485 rate failures** and is not approved for game use. This is one development case, not held-out or animator evidence.

## Original bounded correction

The [verified plateau seed](native-anchor-seed-study-v1.md) has 499 original-rate failures and zero sampled floor failures. It remains rejected against the earlier 351-rate/five-floor comparison; this experiment starts a separate research branch. The public interval command changes only already-permitted tracks 62, 61 and 60 at native keys 0–84: 765 variables within the existing 768-control ceiling. The original character, clock, rotation/displacement permissions, source-cap arrays, touch, geometry policy and root stay unchanged.

The one-iteration recipe uses trust 0.02, difference step 0.001, four decoded backoffs and the existing 750-second proposal budget. Its 482,068-row norm model has 355,609 protected rows. The primary solver reports `Solved` after 46 iterations. It minimizes responsive affine excess to 3.790998491 while the full maximum remains the fixed 16.787598863; 306 fixed failed rows remain reported. The approximate minimum-norm point fails its hard-row recheck and is not selected.

| Decoded output | Original rate failures | Failed floor times | Squared positive excess | Retained against seed |
| --- | ---: | ---: | ---: | --- |
| Exactly reproduced start | 499 | 0 | 4,087.873910 | Reference |
| Full step | 503 | 0 | 3,707.573624 | No |
| Half step | 485 | 0 | 3,879.506160 | No |
| Quarter step / final | 493 | 0 | 3,979.061273 | Research continuation only |

All four outputs pass the decoded edit/contact/root prefix. The quarter step has zero root error, touch error 4.944748046 mm and peak sampled floor depth 4.799615264 mm, against the unchanged 5-mm touch/floor limits. Every original cap array, inactive control and nonselected local rotation channel is preserved. The final GLB SHA-256 is `5ddd0129cda3f106ccb598a761edb508aff65f13f8d9fd67208e3e2e7ed5e6e8`.

Production completes in 610.390 seconds with peak sampled process-tree RSS 497,528,832 bytes; all 600 resource observations replay. The standard fresh replay verifies all five returned GLBs byte-for-byte, complete arrays/contact/geometry results, all three backoff decisions and final native controls. Its 347.437-second guard peaks at 624,590,848 bytes, with all 343 observations replayed. Both use the declared 768 MiB CPU cap, additional 600 MiB free-memory floor, 15-second admission stability and 1,200-second supervisor limit. A separate complete comparison confirms the quarter step is ineligible against the earlier 351-rate/five-floor clip. No selected asset changes.

## Why the half step was rejected

A read-only saved-row diagnostic distinguishes repaired, newly failing and worsened existing conditions instead of interpreting net counts as repairs:

| Step | Repaired rate rows | Newly failing rate rows | Worsened existing failures |
| --- | ---: | ---: | ---: |
| Full | 14 | 18 | 29 |
| Half | 14 | 0 | 1 |
| Quarter | 6 | 0 | 0 |

No floor or geometry condition worsens. The half step's single offending row is right-calf angular speed over 0.5–0.508333333 s. Its original source-bin cap is 0.605182927 rad/s. The already failed seed value, 0.911885243 rad/s, is the unchanged no-worsening limit for this step. The affine model predicts 0.911812620, but the decoded export measures 0.911901936: an increase of 0.000016693 rad/s. That still fails; no rounding waiver is applied. The diagnostic completes in 17.219 seconds with all 19 resource observations replayed and no solving or export. The discrepancy alone does not isolate finite-difference, nonlinear or storage error.

## Cached repair pilot

The pilot reuses the original native-row Jacobian and anchors its norm vectors to the actually decoded half step. It protects all 352,780 native norm rows using the original per-condition no-worsening limits; known source-rate failures are not reclassified as passing. Only the offending search target is tightened by 0.0001 rad/s. The original source-rate arrays and decoded acceptance limits do not change.

One conic repair uses trust 0.00001 in the same 765 controls. No new finite differences or model generation run. The solver reports `Solved` after ten iterations; the returned maximum control step is 0.0000055732551. Its secondary point fails the hard-row check and is not selected. The cached model is only a proposal: full decoded floor/geometry, contact, root, edit and every rate-retention condition still decide retention.

The repaired export passes that complete retention test against the 499-failure seed. It has 485 rate failures, zero sampled floor failures, zero root error, 4.958739842-mm touch error, 4.799615264-mm peak sampled floor depth and squared positive excess 3,879.500906. Its maximum normalized excess remains 16.787598863. The GLB SHA-256 is `3fb4e787e3c7ffb8a7b710c67e393f62d4e74fc578d8d2fcdca0507d670a3446`. This retains a larger useful step without excusing its original violation, but does not satisfy original motion acceptance or adopt a new game asset.

The repair guard completes in 92.500 seconds with peak sampled RSS 478,851,072 bytes; all 93 observations replay under the 768 MiB study profile. A separate fresh native-control/export replay verifies exact GLB bytes, complete observations/contact/geometry reports, unchanged original cap arrays and original-start retention without rerunning optimization or the Jacobian. It completes in 92.360 seconds with peak sampled RSS 405,651,456 bytes; all 93 observations replay under the 512 MiB CPU profile. Both retain the additional 600 MiB free-memory floor. These use shared readers/curve/skin methods, not independent physical or engine validation.

Generated evidence remains local under ignored `reports/crawl-plateau-interval-restoration-v1`, `reports/crawl-plateau-interval-restoration-replay-v1`, `reports/crawl-plateau-step-diagnosis-v1`, `reports/crawl-cached-native-repair-v1` and `reports/crawl-cached-native-repair-replay-v1`. The next implementation decision is whether to expose this bounded recourse in the general correction workflow. One successful pilot does not establish broad coverage. All fourteen capability/calibration gates remain unapproved; the entire-project goal stays active.
