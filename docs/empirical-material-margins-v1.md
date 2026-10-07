# Empirical material margins for complete-clock proposals

The [material storage search](material-storage-search-v1.md) leaves three original material failures. A distinct proposal solver now reserves per-row room for measured affine-to-export error. This is an empirical correction policy; the original actual checks still decide whether an output passes.

## Complete source-bound calibration

`native_empirical_material_margins.py` accepts complete actual and affine gap arrays, an authenticated material-model SHA256, ordered unique endpoint identities and every row index. The caller must bind the model identity to the frozen descriptors, original anchor and same-pose derivatives and authenticate the declared complete endpoint set. A matching string alone cannot authenticate files.

For each row, take the maximum positive `affine gap - actual gap` over all declared endpoints, then add the explicit proposal buffer. Reject incomplete, nonfinite or oversized populations whole, before numeric copies. Limits are 32 endpoints, 4,096 rows and 131,072 observations; margins above 0.1 m reject without clipping. Snapshots retain both complete arrays, margin values and digests. Validation recomputes the policy and rejects stale model identity or changed arrays/metadata.

The saved-data calibration covers all eight prior exports and all 1,710 original rows: 13,680 observations. Its explicit extra buffer is 100 nm. Margins range from 0.1 to 5.870069830224 micrometres. These are observed endpoint errors plus a chosen buffer, not an error guarantee at a new pose or between samples. The extra buffer changes proposal requirements; no actual collision tolerance changes.

## Original ceilings and hard rows

`native_component_trajectory_margin_step.py` computes original containment-depth and triangle-deficit ceilings from the original material model before applying any buffer. Subtract each row's margin from its conic right-hand side. Keep both original ceilings and every tightened per-row bound in each of the 81 strict ray checks. A retreat that returns to an unbuffered boundary must fail; there is no objective slack for material rows.

Retain the original norm caps/scales, edit/trust box, parameter equalities, full-mesh guards, all initially positive component pairs, complete sampled component objective and original trapezoidal weights. A buffered anchor need not pass the new margin requirement, but its original native and guard conditions must pass. Returned candidates remain provisional. Existing bound solver and search sources are unchanged.

## Validation and measured limits

All 70 new tests and 47 original solver regressions pass without skips. Tests cover directional complete endpoint envelopes, exact resource boundaries, copy isolation and mutation/stale-identity rejection, unchanged zero-margin conics, distinct row ordering, impossible-buffer retreat, strict tolerance, independent hard-gate conflicts, complete trajectories above the separate legacy limit and preserved solver statuses.

A separate reader manually reconstructs every actual saved gap and original affine projection, all margins and policy identities/digests, original ceilings and tightened rejection counts without calling the calibration or correction APIs. NumPy/SciPy serialization and sparse arithmetic are shared; no independent collision arithmetic is claimed. Retain the first pre-output manifest-key failure: Windows-separated archived names were indexed with a forward slash. A distinct repaired driver completes the calibration; no old scientific result is overwritten.

Every saved endpoint violates at least one tightened affine requirement, including the motion-passing quarter. This calibration produces no changed animation, new conic, native/skin/derivative query, export or full-scene scan. The smaller storage-search errors remain rejected. No endpoint or source is promoted.

Next run the buffered proposal and audit actual stored motion, every original material/mesh/component condition and complete scene only when storage reserve allows. Keep the earlier lower-depth branch and use fresh derivatives if the anchor changes. The workflow registers the new tests; hosted CI success is unverified. All fourteen release evidence arrays remain empty. No production rig, arbitrary-action, engine-import, animator or cleanup-time evidence is supplied, and the full-project goal stays active.
