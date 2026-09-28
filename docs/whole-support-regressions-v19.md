# Whole-support correction: temporal tradeoffs across actions and rigs

This is a read-only analysis of the frozen19/24-complete snapshot, not a new release screen. Five unfinished cases remain in the denominator. Source clips and the live solver are unchanged.

`scripts/analyze_support_regressions.py` checks the snapshot/protocol, source/candidate GLB hashes and retained trace/verification hashes. It requires matching clocks and predicted-support masks before comparing per-frame values. It preserves all24 population rows in `reports/whole-support-regressions-v19/traces.json` and records the complete pointwise root and support-speed curves for the19 completed cases.

Findings:

- Fourteen of19 cases increase peak root acceleration by more than0.0036m/s². Twelve increase the sum of squared root acceleration. These are observed changes; the0.0036 bin is not being introduced as a release threshold.
- Eleven of19 cases increase at least one predicted-support foot-speed peak by more than0.001m/s. There are15 such foot peaks across those cases; all15 lie within two frames of a predicted support-mask boundary. The boundary convention is the first active or first inactive step-end frame, with endpoints clipped to the measured clock.
- Floor improvement and lower support-speed P95 can coexist with worse transition peaks. The newly completed exhausted walk on rig01 reduces floor depth67.711→2.123mm and improves both feet's P95, but raises the right-foot support peak0.061934→0.190239m/s and root peak2.132354→2.530842m/s².

Predicted contacts are model annotations, not independent ground truth. Boundary proximity does not prove the solver causes every spike or that a fast movement is semantically wrong. The retained per-frame data and clip previews remain necessary for animator interpretation. Missing support samples are recorded as missing, never zero-speed evidence.

## Implementation implication

The live solver's `support_curvature.root_curvature_pair` evaluates second differences of its root-correction parameters. It is accurately described as correction curvature; it does not include the original root trajectory. Reducing this regularizer does not guarantee lower acceleration of the delivered motion. Likewise, reducing an aggregate contact error or percentile does not prevent a release-boundary peak.

The next broad correction formulation should operate on actual exported/world trajectories, include the approach and release boundary steps as explicit constraints, and retain the current achieved floor/contact bounds. Evaluate all declared cases, preserve no-improvement/infeasible outcomes, and report peak, percentile and pointwise changes separately. Use the same explicit source motion, rig and annotations; do not invent physical meaning for agility/stamina from these quantities.

The present long-running whole-support study stays frozen until it finishes. This report is evidence for a changed method afterward, not authorization to alter its current implementation or silently replace its candidates. Existing joint/root cleanup, object/partner studies and independent animator evaluation remain separate requirements. No release gate is promoted.
