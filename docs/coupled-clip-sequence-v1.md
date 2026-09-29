# Coordinated correction across complete clips

The [nine-case block study](coupled-breadth-conic-v1.md) improved one small window in each development clip but restored none of the original root-acceleration peaks. This follow-up measures errors across each complete clip and visits several remaining problem regions. It does not change the broad action scope or use held-out release examples.

## Proposal conditioning

The stopped cases have different failure modes. Backpedal / 02 and exhausted walk / 02 reject geometrically invalid proposals; beckon / 01 reaches proposals that no longer improve the serialized motion. Beckon / 03 encounters numerical solver errors at all three fixed trust bounds.

`conic_linear_screen.py` removes an affine inequality only when its lowest value over the entire allowed step box is positive, including a floating-point reserve. This uses the sign-selected corner of the box. Near-boundary, invalid and overflowing inputs are retained or rejected rather than silently discarded. Every norm constraint remains in the proposal, and every original nonlinear constraint remains in actual step acceptance. This is a simplification of the local affine problem, not a relaxation of floor checks.

The fixed comparison `reports/coupled-screen-diagnostic-v1` tests all four stopped cases, both full and screened rows, and all three original trust bounds: 24 proposals total. It unlocks actually feasible improving trials for beckon / 03 at 1e-5 and 1e-6. It does not unlock the other three stopped cases. The 42,425 linear rows in that case reduce to 14, 10 and 6; summed proposal time is 2.446 seconds versus 0.999 on this laptop. These timings exclude the full animation workflow and are not a general speed claim. The other cases similarly retain 1–114 rows; all discarded affine rows remain covered by the independent full-row prediction and nonlinear checks.

## One budget across several windows

`reports/coupled-clip-sequence-v1` starts from the nine previously verified corrected clips. It selects up to four windows per clip from all remaining root failures, ranked by measured acceleration with deterministic frame ties. Windows contain up to five editable frames and preserve two keys at each endpoint. Centers affected by an already selected window are covered before choosing another. The complete frozen population contains 29 windows.

Each window gets at most six conic iterations, the same three trust bounds and eight safeguard fractions. Earlier windows remain in the working clip, but the 1 cm root radius always refers to the **original whole-support source**, not the last window. The original absolute root/joint and adjacent-edit budgets remain. Foot contacts, floor, anchors and rotation checks retain their original reference; per-center root caps also protect the verified starting clip within the unchanged 0.0036 m/s² numerical allowance. A regression test confirms that two individually small 6 mm changes cannot silently become an allowed 12 mm correction.

The objective is the sum, over every clip center, of `max(root acceleration magnitude − original raw peak, 0)²`. An exported result must reduce that whole-clip value by at least 0.1% relative to its verified starting clip, pass the independent preservation audit and pass actual engine import. This differs from the earlier local-window objective and uses additional optimization work; it is not an equal-compute model comparison. Input coordinates were independently reconstructed against all nine starting GLBs to maximum matrix error below 1.8e-15; new runs check this binding before solving.

## Completed first population

All nine cases complete with zero execution errors and 3,180 actual Godot actor-frame checks. Eight pass the whole-clip improvement and preservation criteria. Backpedal / 03 improves its objective but is rejected for a floor discrepancy. None restores its original whole-clip root peak. Raw inputs, starting clips, all block parameters/proposals, final files and rejected output remain retained locally.

The backpedal / 02 objective decreases 47.331029 → 44.543349 (5.890%), while its worst peak remains 11.661140 m/s². Its first, worst window still stops. A separate diagnostic reproduces the actual geometry guard for every rejected trial and identifies half-frame floor depth at frame 76.5 as the blocker, rather than anchor or joint-rotation limits. The smallest fraction preserves geometry but no longer changes the serialized objective. Future proposals need to account for this between-key constraint directly.

## Matching the audit clock

The rejected backpedal / 03 exposes a separate sampling mismatch at frame 108.5. The old guard samples at 3.6166666666666667 seconds, while the file auditor samples the float32 clock at 3.616666555404663. The guard measures a 0.996434 µm floor increase; the actual audit measures 1.000406 µm and correctly fails the unchanged 1 µm allowance. Reconstructing at the audit clock reproduces the exported transform exactly.

`SerializedPose` now has an explicit float32 sampling option; its default float64 behavior is preserved for other callers. Coupled correction uses the same float32 clock as its independent auditor. Tests cover both clock modes and verify that the retained failed candidate now fails step geometry while the old clock would accept it. No physical tolerance was widened.

`reports/coupled-clip-sequence-v2` keeps all eight independently accepted sequences and repeats only backpedal / 03 from the same original starting clip, windows and budgets. The retry passes all independent criteria and adds 300 actual Godot actor-frames. The combined population now has **9/9 accepted whole-clip numerical improvements**, zero execution errors, and **0/9 restored original root peaks**. Twenty-eight focused tests pass, including affine box bounds, overflow rejection, shared edit budgets, starting-pose binding, clock consistency and existing solver/export guards.

| Action / rig | Whole-clip objective reduction | Starting → selected root peak, m/s² |
| --- | ---: | ---: |
| Backpedal / 02 | 5.890% | 11.6611 → 11.6611 |
| Backpedal / 03 | 6.141% | 11.4420 → 11.3907 |
| Beckon / 01 | 0.237% | 1.8412 → 1.8412 |
| Beckon / 02 | 0.122% | 1.1297 → 1.1295 |
| Beckon / 03 | 1.278% | 5.4215 → 5.4204 |
| Kneel / 01 | 0.468% | 3.8306 → 3.8271 |
| Tie shoe / 01 | 0.602% | 1.4032 → 1.4032 |
| Exhausted walk / 02 | 2.805% | 7.2086 → 7.1861 |
| Exhausted walk / 03 | 0.139% | 7.3467 → 7.3433 |

The failed-center count is not uniformly improved: beckon / 01 goes from six to five, while tie-shoe / 01 goes from seven to eight despite a lower total objective. The fixed per-center numerical allowance can permit a near-threshold crossing. This remains a reported regression, not evidence that every part of a clip improved. Further work must address remaining constraints and actual usability rather than treating a lower aggregate score as release approval.

These are numerical development corrections on five action types and three rigs. They do not establish realistic dynamics, confirmed contact labels, scene/partner behavior, animator quality or release readiness. All fourteen project release capabilities remain unapproved.
