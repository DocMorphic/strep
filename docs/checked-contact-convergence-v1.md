# Longer checked-contact solve: improvement with residual failures

The four-stage, 120-iteration-per-stage run has completed. It uses the same original get-up clip, checked pin, held window, source rate ceilings, quarter-frame position/floor/rate objectives and hard edit bounds as the shorter sampled-pin trial. It does not initialize from that trial's result or change any acceptance limit.

| Decoded export measurement | Two stages × 60 | Four stages × 120 |
| --- | ---: | ---: |
| Maximum pin error | 5.78466 mm | 5.00165 mm |
| Pin samples exceeding 5 mm | 15 / 81 | 1 / 81 |
| Maximum floor penetration | 2.19082 mm | 1.46246 mm |
| Per-time added floor depth | 0 | 0 |
| Hold acceleration excess | 5.07631 m/s² | 0 |
| Release speed excess | 0.0135039 m/s | 0.0000795925 m/s |

Approach speed/acceleration, hold speed/acceleration and release acceleration all stay below the checked ceilings in the longer exported result. The remaining release-speed and point-position failures are retained without tolerance padding. Inferred support and added-joint-speed flags also remain; this is not a motion-quality approval.

The numerical work took 1,178 seconds for fitting and evaluation, with 1,028 objective evaluations. Each stage used all 120 iterations. Stage evaluation counts were 139, 197, 281 and 407, plus accepted-point recomputations. Final projected-gradient infinity norms were 97.38, 3.77, 5.97 and 52.39. The extra work substantially improves constraint accuracy, but the solve has not demonstrated convergence to a fully feasible result.

## The remaining failure precedes export

The fitted point exceeds 5 mm by 1.6643 micrometres; the exported point exceeds it by 1.6487 micrometres. The fitted release speed exceeds its source ceiling by 0.0000794067 m/s, versus 0.0000795925 m/s in the export. These violations exist inside the optimization result; treating them as export rounding would be incorrect.

All 717 decoded floor samples preserve the source's per-time depth, and all 160 outside-window samples preserve the source within numerical tolerance. The floor proxy differs from decoded full-skin heights by at most 1.36e-7 m for the source and 1.13e-7 m for the candidate. Actual Godot playback passes 407 pose observations, two requested-boundary marker events, forward/reverse playback, four callback-mutation rejections and unloading. Maximum actor matrix component error is 1.27e-6. Four file routes resolve through direct handler checks. No HTTP/browser rendering or human review was performed.

The run is reproducible with the longer command in [the sampled-pin study](checked-sampled-pins-v1.md). Numerical inputs, mesh and implementation hashes were verified throughout. Local evidence is in `reports/contact-jobs/studio-sampled-pins-convergence-v1` and `reports/studio-sampled-pins-convergence-v1`, including `comparison.json`, `verification.json` and the separate `residual-origin.json` diagnosis. The 29 focused implementation tests from the preceding change remain the relevant tested code; this result does not claim additional test executions.

Next test a constrained feasibility correction from this retained candidate while keeping the original source as the reference for edit bounds and rate ceilings. Every proposed step must be rechecked against the full export constraints. Another blanket iteration increase or an acceptance-threshold change is not justified by this result. The full project and all release capabilities remain open.


Follow-up completed: [a bounded root-height correction](checked-root-feasibility-v1.md) removes the remaining pin/rate residuals in the decoded export while preserving original budgets and floor samples. Broader support/quality failures remain; this does not approve the retained clip.
