# Smooth native-control seeds around a supplied contact

Two declared temporal blends clear the Quaternius crawl's sampled floor failures and preserve its authored touch, but introduce additional original-rate failures. Both remain rejected against the previously retained clip. The experiment motivates a different initialization branch; it does not establish realistic crawling or justify weaker acceptance limits.

## Inputs and fixed proposal recipe

The starting clip is the [exactly replayed bilateral continuation](native-responsive-soft-objective-v1.md), SHA-256 `bfced13e10292f5e60e2b0063a0ebdf71d37e5743aaa3814a2fb8a25e6337a9f`. It has 351 original-rate failures and five failed floor times. The original character, source animation, 477-key clock, 16 permitted rotation tracks, explicit editable start/preserved end, 30-degree rotation limits, 0.22-m joint displacement bound, four original 120-Hz/four-bin rate-cap arrays and 5-mm floor/touch limits remain unchanged.

Only permitted nodes 62, 61, 60 and 59 are blended. Their correction controls at native key 12 (0.10000000149011612 s) supply the anchor. This is the existing authored calf-surface-to-world touch, not an inferred planted knee or support interval. No additional contact target is invented. Other local tracks, every zero-weight key and the complete anchor controls remain unchanged.

For original controls `c(t)`, anchor `a`, and weight `w(t)`, the proposal is `(1-w(t))*c(t) + w(t)*a` on those four tracks. Weights stay in [0,1], so this construction stays within the original control-vector unit balls; full decoded edit, displacement, contact, rate and geometry checks are still necessary. Export retains the original native keys and interpolation. No model inference, learned editor or optimizer runs.

Both weights use `f(s) = 1 - 10s³ + 15s⁴ - 6s⁵` for clamped `s` in [0,1], with exact values one and zero at the support boundaries:

- **Plateau:** `s=(t-0.15)/0.5`, giving a constant anchor through 0.15 s and zero weight from 0.65 s onward.
- **Centered:** `s=abs(t-anchor_time)/width`, with width 0.35 s before the anchor and 0.55 s after it. At the original anchor key, the weight is exactly one.

Both proposals are fixed before evaluation. No parameter search chooses a favorable clip afterward. Complete control/weight archives, request bindings, source methods, exported clips and every failure remain local.

## Complete decoded measurements

| Clip | Original rate failures | Failed floor times | Worst normalized excess | Squared positive excess | Peak floor depth |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reproduced start | 351 | 5 | 345.953947 | 713,338.340066 | 5.258764 mm |
| Plateau | 499 | 0 | 16.787599 | 4,087.873910 | 4.860700 mm |
| Centered | 528 | 0 | 16.787599 | 4,019.179421 | 4.881983 mm |

All three preserve zero root error, zero decoded edit failures and the same 4.934019947-mm touch error. All four source-cap arrays remain identical. Both blends fail the original rate acceptance and the complete per-condition no-worsening test against the starting clip. A smaller worst error or floor-only pass cannot override that rejection. No animation is automatically selected for game use.

The plateau GLB SHA-256 is `9e39f4e7abbb9a5846899a4e86a93c852403350f044e226ac2aa45b30f708679`; the centered GLB SHA-256 is `b41504002b28996f0fff03c71f1cbaa704638a8ca34bf132afaa440ce4f794e7`. This is one development actor and an explicit plane/contact policy. It adds no self-intersection, force-balance, object/partner, held-out, engine, animator or cleanup-time evidence.

## Interrupted execution and continuation

The original guard stops for `available_ram_guard` after 215.796 seconds, with peak sampled process-tree RSS 402,317,312 bytes. It observes available memory below the unchanged 600 MiB floor; all 215 resource observations replay. Baseline and plateau exports finish before the stop. The centered export and contact report exist, but its geometry file is partial. The original run remains marked failed, and its partial outputs are preserved.

The first fresh continuation stops before evaluation because its bookkeeping accesses a lazily populated row count too early. Its 47.781-second/49-observation resource trace replays as a failure. A separate corrected continuation derives the original offset from the bound complete observations and verifies it against the freshly evaluated population. It reuses both completed cases and evaluates only the interrupted centered case. The reconstructed centered GLB matches the interrupted export exactly. This continuation completes in 97.578 seconds with peak sampled RSS 413,376,512 bytes; all 98 resource observations replay.

The evaluation/continuation attempts and initial replays use the declared 768 MiB CPU estimate/cap, additional 600 MiB free-memory floor, 15-second admission stability and 1,200-second supervisor limit. The later single-case profile is described below. No guard is bypassed and no raw failed run is relabeled complete. A separate completion manifest references the two earlier complete cases and the new third case.

The initial combined cold replay also stops at the available-memory floor after 109.375 seconds; all 110 resource observations replay as a failure. It completes the starting export/contact/geometry stages but not the full case receipt. The follow-up uses three sequential, individually guarded complete-case workers so a later interruption cannot discard an earlier verified case. Each still reconstructs its declared kernel and full controls, re-exports the actual GLB, compares every observation/contact/geometry result and replays the original retention decision. This changes checkpoint granularity, not numerical or memory limits.

The baseline case replay completes in 105.547 seconds with peak sampled RSS 418,975,744 bytes, including exact GLB bytes, complete observations/reports, unchanged channel/anchor values and retention. All 106 resource observations replay. The plateau case then stops at the free-memory floor after 114.891 seconds with peak sampled RSS 297,627,648 bytes; all 115 observations replay as a failure. The verified baseline remains checkpointed.

A fresh plateau attempt adds a stricter preflight: at least 2 GiB free over 60 seconds of samples, with a 600-second waiting bound. Only after that does it enter the original declared guarded policy. The sampled preflight passes after 140.891 seconds; the complete plateau replay passes in a further 98.282 seconds with peak sampled RSS 419,659,776 bytes. All 99 resource observations replay. Its native GLB bytes, declared curve/full controls, complete measurements and rejection decision match exactly. Baseline and plateau now have separate complete receipts.

The centered case's same additional preflight expires after its bounded wait; no numerical worker starts. The next attempt declares a measured single-case profile: 512 MiB expected/maximum owned RSS, unchanged 600 MiB execution free-memory floor, 60-second admission stability, 600-second admission bound and unchanged 1,200-second supervisor limit. The already complete case peaks below 420 MB justify distinguishing this one-case audit from the earlier multi-export cache profile; the owned-process cap is tighter and stability longer. The replay worker, all samples, numerical conditions and comparisons are identical.

Admission succeeds after 224.640 seconds, but this centered attempt still stops at the execution free-memory floor after 247.312 seconds overall (22.578 execution seconds). Peak sampled worker RSS is only 97,878,016 bytes; observed available RAM falls to 511,287,296 bytes. All 247 resource observations replay as a failure. Readiness cannot guarantee that unrelated memory use stays constant.

After a new physical-memory observation rises from 539,648 to 1,918,584 KiB, a fresh centered attempt uses the same single-case worker, 512 MiB cap, 600 MiB free-memory floor and 60-second admission stability. Admission succeeds after 85.032 seconds. The complete replay finishes in 176.907 seconds overall (90.828 execution seconds), with peak sampled RSS 417,280,000 bytes; all 176 resource observations replay. No numerical condition, sample population or comparison changes.

The sealed three-case receipt checks all three separate completion records, exact input bindings and their resource audits. It verifies the plateau's additional sampled preflight and the centered case's measured tighter process cap. All declared kernels/full controls, native GLB bytes, complete contact/geometry/observation arrays, unchanged channel/anchor values and original rejection decisions reproduce. No optimization reruns. The baseline and plateau are not rerun to recover the final case. These cold replays share reader/curve/skin code; they do not provide independent physical, engine or animator validation.

## Separate correction branch

The next bounded experiment starts from the verified but rejected plateau controls. This does not adopt that seed over the earlier 351-rate-failure comparison. It selects three already-permitted tracks (62, 61, 60) over native keys 0–84, giving 765 variables within the existing 768-control ceiling and covering the complete smooth-seed support. Every other control and nonselected local channel remains fixed. The original rotation/displacement limits, source-cap reference, touch, full geometry policy and root remain unchanged.

The public source-bound interval command uses one iteration, trust 0.02, difference step 0.001, four decoded backoffs and the existing 750-second proposal budget, with the declared 768 MiB/600 MiB free-memory/15-second stability/1,200-second wider-study guard. The starting GLB must reproduce the plateau exactly. Every returned candidate still needs complete per-condition retention and a standard fresh replay. This is an initialization experiment, not a new release gate or a quality-approved asset.

Evidence remains under ignored `reports/crawl-anchor-curve-seeds-v1`, both `reports/crawl-anchor-curve-seeds-continuation-v*` attempts, `reports/crawl-anchor-curve-seeds-replay-v1`, the checkpointed `reports/crawl-anchor-curve-seeds-replay-*` folders and `reports/crawl-plateau-interval-restoration-v1`. All fourteen release capability/calibration gates remain unapproved; the entire-project goal stays active. The rejected-seed branch must not silently replace the earlier retained comparison clip or inherit approval.
