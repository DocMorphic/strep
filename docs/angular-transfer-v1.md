# Angular correction on two further development clips

The same projected correction method now passes all eight edited-joint peak comparisons on two additional selected clips: grapevine dance on rig01 and backpedaling on rig01. Each final export also passes all 16 original aggregate comparisons and all 14 preservation checks. The final engine checks cover 630 actor-frames for dance and 450 for backpedaling, counting raw, held and candidate variants. These are two development clips, not independent held-out validation or animator approval.

Full population and artifact hashes: `reports/angular-transfer-summary-v1.json`. There were six preparations, one failed preflight and five completed correction trials. Every completed trial accepted one correction step. Earlier outputs and failures remain intact.

| Clip | Final study | Targets corrected | Final joint comparisons |
|---|---|---|---|
| Grapevine dance | angular-dance-rig01-v2 | RightFoot edge179, RightShin edge136 | 8/8 |
| Backpedaling | angular-backpedal-rig01-v4 | RightFoot edges110 and88, LeftFoot edge99 | 8/8 |

The old fixed-root sources did not contain the later root-cap fields. `legacy_angular_source.py` creates a separately hashed certificate after verifying their original audit, freshly decoded constraints, normalized margins, exact root matrices and the original root-acceleration comparison. It derives per-center root safety caps from the unchanged source. It does not fabricate a root repair or rewrite the older studies. Certificate-aware validation also applies to the final independent audit. The earlier leaf auditor is retained by hash.

The first backpedaling preparation failed because two derivative probes switched the identity of the lowest foot vertex. `diagnose_angular_branch.py` retained that evidence. A separate frozen wrapper retries the same seeded direction at 1e-7 only when its 1e-6 probe changes this branch. Both perturbations must match the base branch; the same 2e-4 derivative-error limit still applies. Neither the solver budget nor actual acceptance tolerance changes. An unstable smaller probe still fails. The dance and backpedaling follow-ups use this wrapper; failed v1 was not rerun or overwritten.

Seven focused tests pass: four source/certificate validation tests and three existing piecewise derivative tests. Records are `reports/legacy-angular-source-tests-v1.json` and `reports/angular-branch-proof-tests-v1.json`. Real-character preflight and independent exported-motion checks accompany each trial.

Measured limitations remain. Relative to each original source, worst integer/half-frame penetration is unchanged: dance 3.341/2.256 mm, backpedaling 3.958/2.534 mm. Root matrices remain exact. Nonzero penetration is still present within the existing 5 mm guard.

Fresh rotation-tail measurements (`reports/angular-transfer-joint-dynamics-v1.json`) retain higher 95th-percentile rotation steps versus raw/prior: dance LeftFoot +0.1500, LeftToeBase +0.6242 and RightFoot +0.0046 degrees/frame; backpedaling LeftLeg +0.1531, RightLeg +0.0868 and RightFoot +0.2610 degrees/frame. Peak repair does not establish that the overall motion looks better. These are diagnostics, not newly invented acceptance limits.

No model training, inference, product-default promotion, UI/service change or release approval accompanies this experiment. The single project-wide goal remains active. Next: integrate a bounded, fully audited correction chain for eligible completed cases, retain failed/ineligible cases, and evaluate it on the broader development population. Rig02 contact-release failures and partner clearance remain unresolved; broader action support, held-out evaluation and independent ratings/cleanup evidence are still required.
