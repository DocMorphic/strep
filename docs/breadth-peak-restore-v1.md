# Restoring original acceleration peaks: scope and limits

The previous root-cleanup study reduced total acceleration energy but left 15 of 24 development clips above their original raw-transfer root peaks. This experiment includes **all 15 remaining failures**, preserving their source population and retaining the other nine as explicit exclusions. It uses the same whole-support inputs, original edit budgets, 1 cm root-correction radius, endpoint constraints and contact/geometry guards. Repeated experiments do not accumulate displacement budgets.

The only solver change is an additional second-order-cone constraint on every root-acceleration sample: its magnitude must not exceed the maximum measured directly from that case's original raw GLB. No model inference, training, threshold relaxation or reserved release trial occurs. Source files, the 63 implementation files, solver bootstrap and engine binary are frozen under `reports/breadth-peak-restore-v1`.

## Completed results

All 15 attempts completed without execution errors. Three saved candidates meet the original peak cap within the existing 0.0036 m/sÂ² export tolerance and pass the separate root, contact, hover, geometry and edit-bound checks. Their 510 frames also pass actual Godot import. Maximum position discrepancy is below 0.50 Âµm and basis-element discrepancy below 1.13e-6. The other 12 retain their previous selected output; their imports were already checked in the parent study and were not rerun.

| Motion and rig | Original peak | Earlier cleanup peak | New peak (m/sÂ²) | Energy change versus earlier cleanup |
|---|---:|---:|---:|---:|
| Kneel/rise, Quaternius female | 4.992532 | 5.122557 | 4.992463 | +0.2971% |
| Kneel/rise, Quaternius male | 5.058782 | 5.087939 | 5.058787 | +0.0751% |
| Jab-cross-retreat, Quaternius female | 7.034612 | 7.059500 | 7.034606 | +0.0121% |

These are alternatives with a measured tradeoff: lower peaks, slightly greater total acceleration energy than the earlier cleanup, while still improving energy against the whole-support input. No automatic preference or animator approval follows. Knee/hand support, action semantics, physical balance and human cleanup time remain unverified.

The solver reports `PrimalInfeasible` on the other 12. That numerical status concerns this conservative root-only model; it is not a certificate that the requested animation is impossible. The separate geometric diagnosis below provides stronger evidence for nine of them.

## Independent necessary bound

`scripts/diagnose_root_peak_bounds.py` decodes the original and whole-support GLBs without using optimizer matrices or a solver certificate. With all rotations fixed, a root displacement changes a skin vertex by its root-influence weight times that displacement. Preserving each vertex's current floor depth places a lower bound on vertical root displacement; preserving active foot hover places an upper bound. The hover calculation allows any patch vertex to become lowest, making it less restrictive than the solver's fixed witness. Original vertical edit bounds, the correction radius and fixed endpoint pairs also apply. The existing export tolerances are included.

Let `[L, U]` be each frame's resulting allowed vertical displacement interval and `a` the source vertical acceleration. At each interior frame, any root-only correction must lie in:

`[a + 900 (L_previous - 2 U_current + L_next), a + 900 (U_previous - 2 L_current + U_next)]`.

The interval's distance from zero lower-bounds the absolute vertical acceleration and therefore the full acceleration magnitude. All omitted constraints are relaxed; not exceeding the target does not prove feasibility. The diagnosis preserves every interval and violating frame in `reports/breadth-peak-bounds-v1`.

Nine cases have a bound above their original peak plus the existing numerical allowance. For example, backpedal on the female rig has a necessary vertical peak of at least 11.0205 m/sÂ² versus a 7.4952 original full-vector peak. Beckoning on the male rig is at least 5.2029 versus 0.7096. Increasing root-only solver iterations cannot resolve these contradictions while keeping the declared constraints.

The nine exclusions are backpedal on both Quaternius rigs, beckon on all three rigs, kneel/rise and tie-shoe on CesiumMan, and exhausted walking on both Quaternius rigs. The three other numerical failuresâ€”CesiumMan jump, exhausted walk and jab-cross-retreatâ€”are not excluded by this vertical bound and need further diagnosis.

Six selection/cap tests and seven bound tests pass. Tests cover missing/duplicate/unknown population records, a cap measured from the original export, affine interval extrema, serialized weight roundoff, changing the lowest vertex and static vertices. An actual export check on all three rigs verifies the assumed weighted root displacement at every mesh vertex to 1e-12 m. All 15 real cases were diagnosed, including the three successful controls; none of those controls is incorrectly excluded.

Next, introduce coordinated root/leg edits for demonstrated root-only conflicts while preserving the original comparisons and contact targets. Do not weaken these constraints simply to report a pass. No release capability is approved by this study.
