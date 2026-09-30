# Cylinder pose: full-residual feasibility search

The full-residual search makes larger corrections than strict monotone restoration, but **none of its retained poses passes the original contact checks**. No Studio clip is replaced or release capability approved.

## Method and fixed conditions

This follows the [simultaneous-collision restoration comparison](cylinder-pose-bundle-v1.md), whose strict per-vertex safeguard could not accept a step. It starts from exactly the same bounded frame-96 pose and keeps the original targets, patches, triangle selections, source-relative rotation/root budgets and final acceptance thresholds.

`scripts/regional_pose_full_residual.py` exposes all **36,518 residuals** instead of reducing each clearance family to its worst vertex. Positive violations enter bounded trust-region reflective least squares. Each full-skin or patch clearance family's squared residuals are averaged; gap/radius/spacing triples are averaged; area, centroid, normal and anchor rows have unit weight. Every row has a strictly positive weight, so zero objective requires all modeled inequalities. A small average does not certify any individual clearance.

Intermediate tradeoffs are allowed during this exploratory search. Original independent serialized-pose acceptance remains unchanged. The diagnostic separately retains the smallest unweighted peak, smallest weighted cost and terminal point, including the starting pose in selection. No variant is promoted automatically. Fixed optimizer triangle witnesses may still miss other feasible correspondences; independent contact review searches the full authored patch.

`scripts/torch_jacobian_operator.py` supplies forward and transpose Jacobian products using automatic differentiation. The solver does not construct the dense **36,518 × 175** derivative matrix. The full-skin directional check agrees within **2.013e-6**, and the tested adjoint inner-product discrepancy is zero at recorded precision. Unit tests also compare both products against a known dense nonlinear Jacobian and exercise SciPy least-squares integration and resource interruption.

The study permits 150 function evaluations, 180 seconds, and at most 30 iterations per inner LSMR solve. It uses the existing smooth bounded rotation map and root bounds. The run finishes after **150 evaluations / 103.735 seconds**, with peak observed process RSS **665,714,688 bytes**. It constructs 114 operators and records 3,253 forward and 2,756 transpose products. Termination is the function-evaluation limit, not successful convergence.

## Independent pose results

| Measurement | Starting pose | Smallest peak | Smallest cost / terminal |
| --- | ---: | ---: | ---: |
| Full-skin object penetration | 21.040 mm | 10.538 mm | 10.564 mm |
| Left anchor error, 5 mm limit | 13.158 mm | 5.008 mm | 5.007 mm |
| Right anchor error, 5 mm limit | 9.278 mm | 8.102 mm | 5.624 mm |
| Left patch penetration | 2.623 mm | 4.246 mm | 4.285 mm |
| Right patch penetration | 5.200 mm | 6.845 mm | 6.880 mm |
| Left/right distributed triangle witness | Absent / absent | Absent / present | Absent / present |
| Minimum skin-floor height | 2.069 mm | 2.345 mm | 2.331 mm |

All retained variants pass their original edit bounds. Root XZ coordinates and foot-contact labels are unchanged. Both complete hand contacts fail in every variant: a right-hand triangle alone does not solve its patch clearance or guide anchor. The small left anchor error above 5 mm is still a failure, not rounded into a pass. Patch penetration regresses despite improved whole-body penetration and anchors.

Independent replay verifies all input/method hashes, source seed, selection rules, weighted/unweighted scores and serialized motion arrays for all three retained variants. The best-cost and terminal poses coincide. This is isolated native-pose evidence; there is no new clip, export, engine, dynamics, visual, human-review or cleanup-time validation.

## What this establishes

The best-cost pose still has **679 failing whole-skin object-clearance rows**, 50 failing left-patch rows and 59 failing right-patch rows. Its weighted cost is 7.208021: 0.641499 from whole-skin object clearance, 1.186639 from the left patch, 3.496661 from the right patch, and 1.883222 from scalar contact conditions. Floor cost is zero. This exposes the tradeoffs made by family averaging; final quality remains governed by individual thresholds.

The infinity norm of the half-squared-objective gradient is **9.074110** at the best-cost point. Its largest rotation-budget fraction is **91.723%**, at `RightHandThumb1`. Neither measurement establishes stationarity or impossibility under the original budgets. Before changing targets or articulation limits, the next diagnostic should check inner-solve accuracy and convergence of this full-residual formulation. Any continuation must retain the current failed output and report additional compute explicitly.

## Reproduction and evidence

Requires the separately acquired character assets and retained bounded development study:

```powershell
.venv\Scripts\python.exe scripts/regional_pose_full_residual.py reports/cylinder-pose-bounded-v1 reports/<new-full-residual-study>
.venv\Scripts\python.exe -m pytest tests/test_torch_jacobian_operator.py tests/test_regional_pose_full_residual.py tests/test_regional_pose_bundle.py tests/test_regional_pose_bounded.py -q
```

All 25 targeted tests pass locally. These Torch/asset-dependent tests are separate from the public model-free CI suite. Frozen raw evidence is under `reports/cylinder-pose-full-residual-v1`; independent verification and cost/gradient diagnosis are under `reports/cylinder-pose-full-residual-review-v1`. Generated assets remain excluded from Git. No held-out reservation or new model training is involved; all fourteen release capabilities remain unapproved.


Follow-up: the [actual inner-system comparison and continued search](cylinder-inner-solve-v1.md) retain the original failed output, quantify additional compute and examine the remaining local conditioning problem.
