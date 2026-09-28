# Why the first wider-path step was rejected

The running wider-path experiment has completed its first retained proposal set. Its initial sampled peak penetration is23.46593mm. All eight backtracking steps were rejected, so the accepted trajectory remains unchanged. The inner constrained solve reports a positive directional derivative and retains21.71mm restoration slack; that slack is not an acceptance tolerance.

`reports/bounded-path-guard-diagnostic-v1` captures the exact history bytes used and reconstructs contact-event skin geometry for the initializer and all eight proposals. All nine event poses meet the measured region-area and20° opposing-normal screens. This does not certify their surrounding motion.

The full proposed step reduces the sampled peak to22.24508mm. Its per-frame regressions are frame70 (0→1.56450mm) and event75 (1.89284→4.43759mm), both still under the pre-existing5mm evaluation screen. The half step reduces the peak to22.18712mm and keeps event depth1.85562mm, but adds2.29235mm at frame70. The current step-selection rule rejects any per-frame increase above an approximately1µm floor, including these below-screen increases.

Seven of eight proposals introduce no new5mm failing sample and do not worsen any already-failing sample. The quarter step fails that diagnostic because frame74.5 rises from21.00653 to21.04008mm. These are sparse fitting samples, not a full geometry audit. Their peaks remain far above5mm regardless.

The live experiment and its completion helper remain unchanged. The next recorded method can compare a screen-preserving step rule against the strict one, while retaining exact edit limits, event-region/orientation checks, the fixed5mm evaluation threshold and full exported-motion validation. This would change optimizer step selection, not declare an intersecting final motion acceptable. No candidate from this diagnostic has been exported, selected or promoted.
