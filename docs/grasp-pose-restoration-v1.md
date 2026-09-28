# Joint grasp-pose restoration

The [pose feasibility study](grasp-pose-feasibility-v1.md) reached both grip points but left 26.666 mm of sphere penetration. A restricted analytic bound ruled out fixing that frozen body pose through finger edits alone. This experiment therefore allows the original body, wrist and finger controls to move together, while retaining the original grip, hand-normal, floor and rotation-norm limits.

This is one development pose at frame 60 of the existing sphere fixture. It does not establish motion quality, temporal continuity, anatomical validity, balance, self-collision clearance or generalization to other actions, objects or rigs. The checkpoint is unchanged; no training or reserved evaluation samples are used.

## Method

`restore_grasp_pose.py` reuses the existing elastic hand-step solver. Temporary nonnegative slack applies only to object-surface constraints. It is never counted as accepted clearance. The two grip points, two hand normals and floor remain unrelaxed. The objective gently limits changes from the current accepted pose while the elastic penalty encourages clearance.

The original rotation-ball map enforces all 58 joint edit budgets; root lift stays within its original range. Each of eight outer steps tries preimage trust boxes of 5, 2.5 and 1.25 degrees, with a 2 mm root trust range. These are local coordinate steps, not replacements for the physical rotation-norm limits. Each proposed step is backtracked up to eight times. An independently reconstructed candidate is retained only when every protected gate passes and the worst exact object-clearance violation falls by at least 1 micrometre.

All 18,056 vertices and all eight skin weights participate. The optimization uses a conservative smooth maximum with 0.1 mm temperature; final gates use exact geometry. The initial exact floor passes even though its conservative smooth surrogate is slightly infeasible. This discrepancy is recorded, not treated as an exact geometry failure. Numerical reconstruction tolerances remain 1 micrometre for distances and 0.0001 degrees for normals.

The resource guards are 300 seconds, 2 GiB process RSS and at least 1.25 GiB available memory per invocation. Source snapshots, input hashes, rejected proposals, backtracking audits and final pose arrays are retained in immutable local reports.

## Results

The first invocation accepted all eight outer steps, reducing penetration from 26.666 mm to 1.072 mm. Its final grip errors are 4.993 and 4.569 mm, normals 9.596 and 9.425 degrees, and minimum floor height 3.610 mm. Joint/root edit bounds pass. It used 1,059 evaluations in 102.860 seconds, with sampled peak RSS about 580 MiB.

Every inner SLSQP invocation hit its iteration limit. Its success flag therefore supplies no positive evidence. Acceptance is based on the independent geometry checks. The final pose still misses the required 2 mm outward clearance by 3.072 mm and is not a full pose witness.

Because all eight stages improved clearance while preserving the protected gates, a second invocation continues from that saved pose with exactly the same method and limits. It is sequential development evidence, not an independent test case or a controlled algorithm comparison.

The second invocation is complete: all eight stages were accepted, with 1,536 evaluations in 148.093 seconds and about 576 MiB sampled peak RSS. Final penetration is 0.395 mm. The required 2 mm outward clearance still has a 2.395 mm deficit, so neither run supplies a full pose witness. The continuation's last accepted improvement is only 3.766 micrometres.

| Final continuation measurement | Result |
| --- | --- |
| Left / right grip errors | 5.000537 / 4.997594 mm |
| Left / right normal errors | 10.000056 / 9.999998 degrees |
| Minimum floor height | 6.154 mm |
| Root lift | 4.082 mm |
| Maximum controlled rotation edit | 21.350 degrees |
| Joint/root budget check | Pass |
| Vertices inside the sphere | 10 |
| Full pose witness | Fail |

The left point and normal are microscopically above their nominal thresholds but inside the pre-existing numerical audit tolerances. These exact values are reported rather than rounded into an apparent strict pass. The left pinky base uses 99.635% of its 5-degree budget; several other finger bases exceed 99%. Worst vertex 7073 is mainly weighted to LeftHandPinky1. Both normal constraints and several finger budgets are nearly tight. This does not prove global infeasibility, local optimality or that increasing budgets would solve the problem.

The next diagnostic should test feasible physical-coordinate descent directions with the original norm constraints and full-skin nonlinear checks. This can distinguish an improving local direction from a stationary constrained compromise. Repeating more outer stages or relaxing the authored tolerances would not resolve that question. A static witness, if subsequently found, would still need temporal integration and whole-clip validation.

## Verification and reproduction

`audit_grasp_restoration.py` checks report, input, source and pose hashes; independently implements the bounded-coordinate map in NumPy; replays proposal trust bounds, backtracking fractions and acceptance decisions; and reconstructs the final SciPy/NumPy full-skin pose. Saved pose arrays must match exactly. The geometry reconstruction is shared with the pose audit, so this is independent of the optimizer, not an independently implemented entire physics system.

The first run's 22 recorded decisions and eight accepted stages replay successfully. Torch and NumPy skinning differ by at most 0.055 micrometres. Seven focused tests cover the independent map, changed audit fields, object-row units, protected contact rejection, elastic helper and hard rotation bounds. Raw reports remain local and excluded from Git.

The second run's 19 decisions and eight accepted stages also replay successfully, including trust boxes and backtracking order. Its saved pose arrays match the separate reconstruction exactly; Torch/NumPy skin discrepancy remains below 0.055 micrometres. Reports are `reports/grasp-pose-restoration-v1`, `reports/grasp-pose-restoration-v2`, their respective `-audit-final` and `-audit` directories, and `reports/grasp-pose-restoration-v2-diagnosis.json`. An earlier first-run audit is retained; the final audit adds explicit trust/schedule verification.

```powershell
.venv\Scripts\python.exe scripts/restore_grasp_pose.py reports/sphere-floor-fit-v13 reports/grasp-pose-reachability-points-v1 reports/new-restoration
.venv\Scripts\python.exe scripts/audit_grasp_restoration.py reports/new-restoration reports/grasp-pose-reachability-points-v1 reports/new-restoration-audit
```

These commands require the earlier locally generated study artifacts and separately acquired licensed asset. The public repository is source and methodology, not a bundled copy of those assets.

No Studio default, engine-ready clip or release gate is promoted. All 14 release capabilities remain unapproved; full animation integration and broad held-out/developer/animator review remain necessary.
