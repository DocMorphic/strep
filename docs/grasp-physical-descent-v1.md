# Physical-coordinate grasp correction diagnostics

The previous [joint restoration](grasp-pose-restoration-v1.md) reduced sphere penetration to 0.395 mm but still missed the requested 2 mm outward clearance. Several finger bases were near their edit limits and both hand-normal constraints were nearly tight. These diagnostics test local corrections in physical rotation-vector coordinates, avoiding the shrinking derivatives of the previous bounded-coordinate map near its boundary.

The fixture, frame 60, unchanged checkpoint, full skin, original grip points, normal targets, root range and physical joint budgets remain fixed. This is development evidence from one pose. It is not a held-out action test, a full animation, or an infeasibility proof.

## First-order local steps

`grasp_physical_step.py` solves a linear epigraph problem: minimize the largest predicted object-clearance violation while preserving the linearized grip, normal, floor and joint-norm constraints. Temporary epigraph violation applies only to object geometry. A second LP minimizes total normalized displacement without materially changing the first optimum, preventing arbitrary movement of joints that do not affect the objective.

For each joint, the norm constraint is `1 - ||theta||^2 / limit^2 >= 0`. The linear model subtracts an upper bound on `||delta||^2 / limit^2` over the entire trust box. Since this constraint is quadratic, that remainder makes the proposed endpoint's rotation norm conservative rather than confusing a component box with a rotation ball. Original root bounds also constrain the proposal.

`descend_grasp_pose.py` uses trust boxes of 0.25, 0.05, 0.01 and 0.002 degrees. Root trust is 0.5 mm at the largest angular box and scales with it. Each of 12 steps permits eight backtracks. Protected linear rows request a 1e-5 normalized interior margin; final exact geometry retains the previous numerical tolerances. Accepted steps must reduce worst exact clearance violation by at least 1 micrometre.

The LP includes every object vertex within 3 mm of the current worst object violation, giving 232–241 rows in this run. Every proposed pose is independently checked against all 18,056 vertices, including omitted objects and vertices. Floor optimization uses the conservative smooth maximum with 0.1 mm temperature. Fixed-selection directional derivatives agree with finite differences to 3.54e-8 in normalized units. Limits include 500 active rows, 300 seconds, 2 GiB RSS and 1.25 GiB minimum available memory.

All 12 steps accept an improvement. Penetration falls from 0.394873 to 0.369802 mm, a reduction of only 0.025071 mm. Runtime is 76.719 seconds and sampled peak RSS is about 604 MiB. The final left/right grip errors are 5.000980/4.950367 mm, and normal errors are 9.999941/9.983458 degrees. The left grip passes only the pre-existing 1-micrometre numerical allowance. Minimum floor height is 6.141054 mm, and joint/root bounds pass. The 2 mm outward-clearance requirement still fails by 2.369802 mm.

Larger linear proposals do not preserve the curved grip constraints. For example, the first 0.25-degree proposal predicts improvement but gives 6.752 mm left grip error and is rejected. Smaller proposals require further backtracking. The accepted directions establish some local progress; they do not establish a stationary point, a global solution or a reliable path to full feasibility.

## Nonlinear local refinement

`refine_grasp_pose.py` starts independently from the same preceding restoration pose. It applies the existing elastic nonlinear solve directly in physical rotation vectors, with explicit nonlinear norm inequalities. Local trust boxes of 0.5, 0.1 and 0.02 degrees and a 1 mm root trust keep proposals near the current accepted pose. Original norms, points, normals, floor and final full-skin clearance gates remain unchanged. Object slack is still only optimization assistance, never accepted clearance.

This is an adaptive follow-up to the observed linearization failure, not a preplanned single-factor comparison. The physical-coordinate variant differs in local step construction and trust schedule. It must not be reported as a controlled measurement of parameterization alone.

The run finishes after three accepted stages and a fourth stage with no acceptable proposal. It uses 1,446 evaluations in 155.734 seconds and about 576 MiB sampled peak RSS. Final penetration is 0.366240 mm, leaving a 2.366240 mm outward-clearance deficit. Left/right grips are 5.000026/4.999997 mm, normals 10.000002/10.000003 degrees, floor height 6.275053 mm, and root lift 4.203450 mm. All joint/root bounds pass. Tiny nominal point/normal excesses pass only the existing numerical tolerances. Every inner solve reaches its iteration limit; no solver success or pose witness is claimed.

The independent replay verifies all 49 nonlinear backtracking decisions, three accepted stages, original bounds and exact saved pose arrays. Skin discrepancy remains below 0.054 micrometres. A separate regression replay also verifies the earlier bounded-coordinate run after adding physical-coordinate audit support.

## Local constraint sensitivity

`diagnose_grasp_local_constraints.py` freezes the last first-order linearization and its 0.25-degree trust box. Before solving, it records named row omissions: each grip, each normal, floor, all finger budgets, all body budgets, and both normals together. These omissions are diagnostic only; no relaxed pose or approved animation is produced.

| Omitted rows in the frozen linear model | Extra predicted reduction versus unchanged model |
| --- | --- |
| Left grip point | 0.468314 mm |
| All finger edit budgets | 0.206198 mm |
| Left normal, or both normal targets | 0.065465 mm |
| Right grip, right normal, floor, or all body budgets | 0 mm |

These values describe that particular local linear model, not achievable nonlinear improvements or global constraint importance. They suggest focusing the next investigation on left-hand placement and finger geometry. They do not justify loosening the grip tolerance, joint budgets or release gate.

Next, inspect the rotational freedom that preserves the authored point and normal, then test a small predeclared set of alternative wrist/hand starting poses with the original gates. A different feasible grasp arrangement could escape this local compromise; its existence remains unproven. Repeating the same local iterations or treating a row-omission prediction as a valid grasp would not answer that question.

## Verification and scope

`audit_grasp_descent.py` replays all 212 first-order backtracking decisions and 12 accepted stages. It verifies saved linearization hashes, trust/root bounds, epigraph feasibility, norm remainders, nonlinear full-skin decisions and exact final pose arrays. Torch/NumPy skin discrepancy is below 0.053 micrometres. Stored linear rows and shared geometry are acknowledged dependencies; this is not an independent whole-physics implementation or optimality certificate.

`audit_grasp_restoration.py` now reads an explicit physical-coordinate mode for the nonlinear variant while retaining bounded-coordinate replay for earlier reports. Unit tests cover competing surface constraints, protected contact rejection, impossible protected constraints, unused-coordinate tie breaking, exact norm remainders at box corners, and the existing bound-map/replay controls.

All 11 focused tests pass. Local artifacts are `reports/grasp-physical-descent-v1`, its `-audit`, `reports/grasp-physical-refinement-v1`, its `-audit`, `reports/grasp-local-sensitivity-v1`, and `reports/grasp-restoration-replay-regression-v1`. Both study processes are terminal. Their raw failures and rejected proposals remain retained.

```powershell
.venv\Scripts\python.exe scripts/descend_grasp_pose.py reports/sphere-floor-fit-v13 reports/grasp-pose-restoration-v2 reports/new-physical-descent
.venv\Scripts\python.exe scripts/audit_grasp_descent.py reports/new-physical-descent reports/grasp-pose-restoration-v2 reports/new-physical-descent-audit
.venv\Scripts\python.exe scripts/refine_grasp_pose.py reports/sphere-floor-fit-v13 reports/grasp-pose-restoration-v2 reports/new-physical-refinement
.venv\Scripts\python.exe scripts/audit_grasp_restoration.py reports/new-physical-refinement reports/grasp-pose-restoration-v2 reports/new-physical-refinement-audit
```

Reproduction needs the earlier local study artifacts and separately acquired licensed assets. Raw pose reports remain excluded from Git. No Studio defaults, engine-ready clips, human ratings, reserved evaluations or release gates are promoted. The full project goal and its broader actions, objects, partners, rigs and editable animation requirements remain open.
