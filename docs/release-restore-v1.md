# Strictly feasible release correction

The coupled optimizer's retained full proposal passed the original development comparisons but violated two stricter internal per-center acceleration limits. This separate, frozen trial repairs feasibility while retaining the release target as a hard constraint. It does not revise the original trial's rejection or widen any limit.

Each attempt solves a linearized minimum-infinity-norm step using HiGHS. The protocol permits at most five attempts, a1e-5-radian coordinate trust bound per attempt and eight fixed safeguard fractions. A1e-4 normalized interior margin tightens the linear search target; actual nonlinear acceptance retains the previous−1e-8 feasibility tolerance. Locally constant constraint rows are checked separately. A proposed update must retain zero release-target excess, pass serialized half-frame floor and rotation checks, and reduce the worst infeasibility. Full GLB and engine validation remain independent.

Five focused tests pass: known linear repair, conflicting inequalities, absolute bounds/constant constraints, invalid inputs and rejection of a feasibility improvement that loses the release target. SciPy reports its documented pass-through of the single-thread option to HiGHS; those warnings are retained. The trial request, starting proposal, envelopes and implementation are frozen in `reports/release-restore-v1`.

## Completed and independently verified result

The first linear solve succeeded. Its full step and the next two fractions failed exact nonlinear checks; fraction1/8 passed. The actual maximum parameter change from the retained proposal is1.01606e-6 radians. The optimizer's minimum normalized constraint on affected frames becomes+1.92823e-6 while the release target remains satisfied. No additional attempts were needed.

`reports/release-restore-audit-v1` freshly decodes the exported surfaces and recomputes normalized acceleration, support speed, floor, hover and adjacent-edit constraints over the entire clip. All strict checks pass at the original−1e-8 tolerance. The smallest full-clip margins are−3.60e-14 for acceleration,−1.82e-10 for support speed and−4.44e-16 for adjacent edits; these are within the unchanged tolerance. Half-frame clearance, rotation and the exact target release also pass.

All16 original development checks and all11 release windows pass. Right release19 is3.4678628m/s² against3.4689001m/s². All142 unselected frames retain their decoded transforms within2.23e-16, and every root/protected correction parameter is unchanged. Another450 actual Godot actor-frames verify raw, held and corrected exports. The GLB diagnostic audit's physical-unit tolerances are no longer standing in for the stricter internal check; both are independently satisfied.

This establishes a numerically accepted correction on one inspected backpedal/check development clip. It does not establish anatomy, contact semantics, force balance, animator quality or generalization. No Studio default or production claim changes automatically. The complete original/held/intermediate/rejected/final history remains available.

## Follow-up population

`reports/release-method-eligibility-v1.json` screens all four completed held-support cases before selecting the next action. Dance/grapevine rig01 meets the current method's unchanged-root and initial-clearance prerequisites and has release failures to address. Backpedal rig01 is the already evaluated case. Backpedal rigs02 and03 have preexisting root-acceleration failures; a method that fixes their held root track cannot repair those failures. They remain documented requirements for a root-aware correction method, not removed benchmark cases. The next eligible action is the dance clip; it is still development data, not a held-out test.
