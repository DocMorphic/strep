# First breadth result: waving passes its pin but misses a rate ceiling

The first case from the [eight-case frozen study](contact-breadth-v1.md), wave seed 11, has completed fitting, root-repair attempt, decoded export audit and actual Godot playback. The other seven cases are not included in this result; the original batch has advanced to crawling.

The authored foot point stays within **3.927542 mm** of its target at all 81 checked times, below the unchanged 5 mm limit. The exported full mesh has zero floor penetration at all 477 sample times. All 80 outside-window observations preserve the source within numerical tolerance. The existing body/support comparison reports no flags. These measurements do not establish action correctness or naturalness.

The exported point's approach speed is **0.020978876744 m/s**, slightly above its unchanged **0.020978116942 m/s** ceiling: an excess of **7.5980e-7 m/s**. All other phase speed/acceleration limits pass. This small excess remains a recorded failure; no acceptance padding was introduced. Global joint speed and acceleration remain below their original ceilings.

## Fit and attempted repair

Pose fitting and its evaluation took 1,482.07 seconds, with 1,789 objective evaluations. The four stages used 120, 120, 120 and 55 iterations, with 450, 505, 688 and 142 evaluations plus accepted-point recomputations. The last stage stopped on relative objective reduction while its projected-gradient infinity norm was 0.95445. An optimizer success flag did not establish contact feasibility.

The speed violation already exists before export: 1.3766e-7 m/s in the fitted record, 2.4832e-7 m/s in the float32 candidate's export proxy, then 7.5980e-7 m/s in the decoded GLB. Export increases it, but is not its only cause.

The fixed root-height repair rejected its first linear proposal as infeasible and preserved the fitted candidate exactly. It changed no root coordinates. Its independent cache and derivative checks passed. Repair preparation, attempted solve, body evaluation and export audit took another 31.84 seconds. The whole recorded case, including orchestration checks, took 1,528.13 seconds before the separate engine test.

## Why the linear repair rejected the step

A read-only analysis of the retained subproblem identifies one decisive row: the already-passing global joint-speed constraint centered at frame **48.875**. Its normalized slack is **1.75405e-5**. Even the best independent linear improvement permitted by the original root bounds and 10-micrometre trust box can raise that row's slack only to **1.80395e-5**. The repair requires **1e-4** extra interior slack on every movable row. That stronger search target is unreachable for this row, even before coupling it to the other inequalities.

This proves the configured linear subproblem cannot meet its extra margin; it does **not** prove the original motion constraints are infeasible. As a diagnostic only, retaining the same constraints, Jacobian and coordinate bounds while using zero extra margin gives a feasible linear proposal with a maximum coordinate step of 1.03823e-7 m. That initial diagnostic did not evaluate the proposal nonlinearly or export it. The separate numerical follow-up below also leaves the frozen batch result unchanged.

Horizontal point-rate lower bounds also stay below the original ceilings for all three phases and both derivative orders. They do not prove feasibility, but they do not establish a root-only impossibility here. After the frozen batch finishes, a justified follow-up is to distinguish preservation of already-passing rows from the additional numerical headroom sought on failed rows, then validate every nonlinear and exported constraint. Uniform extra margins should not be confused with the original acceptance limits.

## Engine evidence and remaining scope

Actual Godot playback passes **284 pose observations**, two requested-boundary marker events, four callback-mutation rejections, forward/reverse playback and unloading. Maximum actor matrix component error is 1.17e-6. Global exported peaks are 3.866853 m/s and 455.565282 m/s² against original ceilings of 3.866922 and 455.601356. These global references do not certify realistic per-joint dynamics.

Local immutable fit/repair evidence is under `reports/contact-jobs/contact-breadth-v1-wave-11-fit` and `reports/contact-jobs/contact-breadth-v1-wave-11-repair`. The case record is `reports/contact-breadth-v1/cases/wave-11.json`; engine evidence and the retained-subproblem diagnosis are in `engine/wave-11/verification.json` and `wave-11-root-diagnosis.json` beneath that suite. Source, implementation, asset and output hashes were checked throughout.

No fitting source, fixed protocol, original limits or candidate artifact changed during this analysis. No new test execution is claimed beyond the preceding 34 workflow tests. No browser rendering, HTTP interaction or human review was performed. The contact screen remains failed. The current cohort status is recorded in the breadth study; Studio defaults remain unchanged and no release capability is approved.


## Zero-margin numerical follow-up

A later diagnostic evaluated that same linear proposal in memory. It preserves every previously passing row but leaves two small nonlinear speed violations: minimum normalized slack is -4.4019e-8. Independent full interpolation/skin evaluation agrees. Casting the hypothetical pose to float32 happens to flip those rows to passing, with only 1.3350e-9 m/s of approach-speed headroom. No NPZ, GLB or BVH was written, and no replacement was accepted.

This rules out treating linear feasibility as sufficient. Rounding can change the classification in either direction; the float32 proxy alone does not prove the actual export will pass. The evidence supports testing targeted interior headroom with full nonlinear and decoded-export checks, rather than simply deleting every margin. The retained diagnostic is `reports/contact-breadth-v1/wave-11-zero-margin-diagnosis.json`; it binds the original input, seed, prior diagnosis and its own implementation.


## Seed 22: a feasible proxy still fails the exported speed limit

The fifth completed breadth case, wave seed 22, passes all 81 left-foot pin samples (maximum 2.949718 mm), all 477 full-floor observations, outside-window preservation and five of six point-phase rate ceilings. The remaining approach-speed excess is **6.6606743e-8 m/s**: decoded candidate speed 0.02002894048658828 m/s exceeds the frozen ceiling 0.02002887387984566. The failure remains recorded without acceptance padding. Body evaluation reports no regression flags.

The fitted double-precision point-rate record already has a 5.326309e-9 m/s approach-speed excess. After native serialization, the root problem's minimum normalized slack is positive (1.7951661e-5), including the independently evaluated full interpolation proxy. `solve` therefore exits before proposing any step. Native candidate arrays remain byte-identical to the seed. Actual GLB decoding then crosses the limit again. This result demonstrates that neither native serialization nor a passing interpolation proxy substitutes for checking the final export.

The decoded source itself has approach speed 0.02002969300578262 m/s, above the native-derived ceiling; the candidate is slower than that decoded source. Both comparisons are retained because they answer different questions. The declared study budget remains unchanged. Future protocol design must specify the representation used for source-derived limits, while explicit user limits must still be checked on the delivered assets. This observation does not retroactively pass the fixed study.

All 80 outside-window observations pass numerical preservation (maximum skin error 6.61e-8 m). Exported global joint peaks are 3.825921 m/s and 264.776990 m/s², below original ceilings 3.826025 and 264.923092. Actual Godot playback passes 284 pose observations, two requested boundary events, four callback-mutation rejections, forward/reverse playback and unload; maximum actor matrix error is 1.12e-6. No human realism or cleanup evidence is available.

Fit/repair time was 798.76 seconds before separate engine checking. The fit used 888 evaluations: stage iterations 120, 38, 41 and 37, evaluations 342, 173, 167 and 202 plus four accepted-point recomputations. Only the first stage reached its iteration cap; the other stages stopped on relative objective reduction. Root verification/export took 31.80 seconds with zero proposals.

Evidence remains in `reports/contact-breadth-v1/cases/wave-22.json`, `engine/wave-22/verification.json` and the immutable `reports/contact-jobs/contact-breadth-v1-wave-22-*` jobs. Five of eight cases are complete, with one full contact-screen pass so far. A one-run follow-up worker independently rechecks saved Godot records and verifies each remaining export when ready; it does not alter the numerical methods. After the batch, export failures need to trigger correction even when the proxy is feasible, with targeted headroom and actual exported revalidation. The failed uniform-margin and zero-margin diagnostics above still constrain that design.


## Isolated targeted-headroom experiment

A separate two-seed experiment now uses the observed positive difference between exported and proxy speed peaks, plus 1e-4 normalized headroom, only for the failing approach-speed group. All other rows retain their original zero-slack limits. It calls the existing linear step on shifted search residuals, checks every original nonlinear inequality, preserves already-passing rows, and independently audits native serialization and actual export. Both declared seeds and every failed attempt are retained. None replaces the frozen breadth outcomes.

For **wave seed 11**, three proposals are accepted; the fourth cannot strictly improve the remaining -6.17e-14 search-target residual. The original constraints have positive slack, and the exported result passes all original contact/rate/floor checks: pin maximum 3.927560 mm (0/81 misses), zero floor penetration or added depth, all six point-phase ceilings and both global ceilings. Maximum root step is 1.250830e-6 m; rotations/root XZ and locked seed poses remain unchanged. Original-source lift stays within 0–0.190497 mm, below the original 220 mm bound. Body regression flags remain empty. No extra acceptance tolerance is introduced; the optional strengthened search target is distinguished from the original acceptance limits.

For **wave seed 22**, the first linear subproblem is infeasible and no step is taken. All original arrays and the 6.6606743e-8 m/s approach-speed failure remain. A retained geometric diagnostic explains a limitation of this margin policy: native horizontal approach speed alone reaches 0.020028057088088767 m/s. Against the original 0.02002887387984566 m/s cap, this bounds the possible normalized root-only speed headroom by **4.0780713e-5**, below the requested **1.2127720e-4**. Vertical root translation cannot reduce horizontal speed. This proves the stronger nonlinear target is unattainable in this subspace; it does not establish that the original speed cap is unattainable. Independent per-row linear trust-box bounds do not detect the conflict, illustrating the need for the nonlinear geometric bound. The decoded horizontal lower bound, 0.02002806134600597 m/s, also remains below the original cap.

Both separate exports pass 284 actual Godot pose observations each (568 new observations), including requested boundary events, callback protections, forward/reverse playback and unload. Body flags and original global rate checks pass for both. Engine compatibility does not pass seed 22's failed contact screen. No human review was added.

Evidence is retained in `reports/contact-breadth-v1/targeted-wave-repair-v1/`, with `targeted-wave-repair.py` and the corrected read-only `diagnose-targeted-wave22-v2.py`. The first diagnostic import failure is preserved separately and produced no result. Original source/seed/input hashes and frozen methods remain unchanged. The next search policy should bound extra headroom by geometric capacity while retaining actual export checks; this experiment is not yet integrated into Studio.


## Geometry-limited headroom: both waving seeds pass

The next separate paired experiment limits optional extra headroom to half the gap between the observed export/proxy discrepancy and the maximum headroom allowed by horizontal motion. In normalized units, with nonnegative discrepancy `d` and horizontal-capacity bound `h`, the search target is `d + min(1e-4, 0.5 * (h - d))`; `h <= d` is rejected rather than silently treated as repairable. This necessary geometric bound does not prove joint feasibility. Original source budgets and all acceptance limits remain unchanged, and every export is audited.

For seed 11, the bound leaves the previous target unchanged, and the native output reproduces the prior successful repair byte-for-byte. For seed 22, it lowers the optional target from 1.2127720e-4 to 3.1028955e-5, below the geometric capacity 4.0780713e-5 while covering the measured discrepancy 2.1277197e-5. Three full proposals improve the strengthened residual; a fourth cannot strictly improve its remaining -8.66e-17 value. The original native/full constraints have positive slack (minimum 2.7345004e-5). Maximum root step is 1.242890e-7 m, with rotations, root XZ and held seed keys unchanged.

Both actual GLB exports now meet every original point-phase/global rate cap, all 81 pin samples, zero full-floor penetration/added depth and outside-window numerical preservation. Body regression flags remain empty. Seed 22 approach speed is 0.020028763716261323 m/s, below the original 0.02002887387984566 ceiling by 1.101636e-7 m/s. Its pin maximum is 2.949718 mm; original-source lift stays within 0–0.075698 mm. Seed 11 retains its prior 3.927560 mm pin maximum and 0–0.190497 mm lift. These tiny precision repairs are not evidence of a perceptible animation-quality gain.

The changed-policy regression executes 568 additional actual Godot pose observations across both exports; requested events, callback rejection, forward/reverse playback and unload pass. Native BVH/GLB checks and full eight-weight skin checks also pass. Both original failed breadth cases, the rejected first targeted method and all diagnostic files remain intact. The six completed baseline outcomes are not relabelled.

Method, protocol and results are retained in `reports/contact-breadth-v1/targeted-wave-repair-v2.py` and `targeted-wave-repair-v2/`. This prototype is pending production integration after both frozen workers finish. Its current experiment targets point-phase export failures; global-only export failures, larger pose corrections and broader coverage remain to be addressed. No human review or release approval is added.
