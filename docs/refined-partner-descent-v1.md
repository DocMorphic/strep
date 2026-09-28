# Further correction with the same timing controls

This finite development experiment starts from the independently verified result of [the timing-refinement trial](refined-partner-basis-v1.md). It tests whether recomputing local surface constraints around the improved motion permits another useful correction. It adds no knots, joints or physical edit budget.

`reports/refined-partner-descent-v1/request.json` freezes the same known pair and source poses,13 knots/312 scalar controls,30 fitting times, exact contact event, fixed roots, joint-rotation budgets and5° adjacent edit-vector limit. Proposals use3°,1° and0.25° trust radii with at most three buffer attempts each. Accepted fitting motion must improve peak overlap by at least1micrometre and obey every original sample allowance; allowances are not widened after rejection. All299 original warm poses are reproduced exactly before solving.

Conditional export must preserve sources and event, pass actual joint/root bounds, and undergo600 actual engine actor-frame checks and299 geometry samples per scene. Its full-clock comparison is a separate result from fitting acceptance. The same independent terminal verifier will check both. The candidate remains unapproved even if these checks pass: floor penetration, anatomy, naturalness, held-out generalization and human cleanup time are not established by this experiment.

The preceding worker is terminal, with its execution handle consumed. This is a new finite continuation with recorded provenance, not a restart of the prior trial.21 focused tests pass, including exact recovery of optimized controls in both the original and refined representations and rejection of changed physical/source protocols.

## Completed result

The worker exited successfully and independent terminal verification passed. Peak overlap decreased from22.715770 to22.107190mm; all12 failing samples remain. No new sample crosses5mm, and every sample respects its frozen allowance. However, frame69 worsens by0.112043mm while remaining below5mm. Therefore allowance preservation is not pointwise non-regression. The floor curve remains unchanged at11.959117mm peak, and the event mesh is exactly unchanged for both actors. All600 engine actor-frames pass. The original raw peak21.622598mm is still lower.

The [shared-frame review](http://127.0.0.1:8767/reports/partner-path-review-v1/viewer.html) retains original generation, earlier correction, timing refinement and this continuation. Browser checks cover all four versions, preserved frame selection, fractional peak jumps, playback through frame149 and hand close-up. Eight served GLB hashes match their recorded sources; no browser console errors were observed. The screenshot shows a remaining forearm intersection at frame67. This is software/visual inspection, not a human animation rating.

Further work now moves to the prepared cross-action support-iteration study rather than another immediate correction on this same known pair. All outputs and failures remain available.
