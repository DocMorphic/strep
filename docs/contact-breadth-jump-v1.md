# Jump/landing result: sampled contact checks pass

Jump/landing seed 11 is the fourth completed case in the [frozen breadth study](contact-breadth-v1.md). Its corrected export passes all 61 requested foot-pin samples, the six original point-phase rate ceilings, per-time full-floor preservation and outside-window preservation. Body evaluation reports no regression flags. Actual Godot playback also passes. This is the first complete contact-screen pass among the four finished development cases; four declared cases remain pending.

## Correction and export evidence

The initial pose fit already placed the left-foot material vertex 8766 within 5 mm throughout frames 85–100. It retained a hold-acceleration excess of **0.000548564 m/s²**. The fixed root-height method accepted one full linear proposal after nonlinear rechecking; its maximum root change was **2.41814e-7 m**. Every previously passing sampled inequality remained passing. Both the nonlinear result and the serialized full proxy had positive minimum normalized slack, approximately 9.92e-5 and 9.96e-5 respectively.

The actual decoded GLB passes the original limits, independently of those proxy results:

| Check | Exported result |
| --- | --- |
| Foot-pin error | 3.546181 mm maximum; 0/61 failures |
| Hold acceleration | 2.662172 m/s², below original 2.662275 ceiling |
| Other five point-phase ceilings | All pass without acceptance padding |
| Full-mesh floor penetration | Zero across all 477 observations |
| Per-time added floor depth | Exactly zero in the decoded audit |
| Outside-window preservation | All 80 observations pass; maximum skin error 7.71e-8 m |
| Global joint speed | 8.738359 m/s, below original 8.739947 ceiling |
| Global joint acceleration | 505.525384 m/s², below original 505.620845 ceiling |

The pose fit used 1,166 evaluations. Stage iteration counts were 120, 62, 13 and 5, with 698, 297, 106 and 61 evaluations plus four accepted-point recomputations. The first stage reached its iteration cap; the remaining stages terminated on relative objective reduction. Those termination statuses alone are not feasibility evidence. Full case time was 1,045.21 seconds before separate engine verification, including 36.81 seconds for root correction, export and audit.

Actual Godot verification passes **284 pose observations**, two requested-boundary events, four callback-mutation rejections, forward/reverse playback and unload. Maximum actor matrix component error is 1.32e-6. Native BVH/GLB structural checks and all eight skin influences also pass.

## Scope

Local evidence is retained in `reports/contact-breadth-v1/cases/jump-land-11.json`, `engine/jump-land-11/verification.json` and the immutable `reports/contact-jobs/contact-breadth-v1-jump-land-11-*` jobs. The original source still defines every edit, rate and floor budget. No original failed take has been overwritten.

This successful small repair complements the root-only limitations measured in crawling and kicking; it does not resolve them. Finite sampled checks do not establish continuous collision safety, balance, semantic appropriateness or naturalness. No human review or cleanup time is available. The batch now continues with seed 22 under unchanged methods; Studio defaults and all release approvals remain unchanged.
