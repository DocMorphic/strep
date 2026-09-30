# Cylinder pose: feasibility-first comparison

This development experiment follows the failed [nearest-pose diagnostic](cylinder-pose-witness-v1.md). It changes the local optimization formulation, not the character, source pose, hand targets, patches, triangle selections, physical edit limits or final acceptance thresholds. No clip is overwritten and no held-out motion reservation is consumed.

## Method

Let `s(x)` be the original dimensionless geometric inequality vector, feasible when every entry is nonnegative. Phase I optimizes normalized pose coordinates and one nonnegative scalar `t`:

```text
minimize t
subject to s(x) + t >= 0
           original rotation norm limits
           original rotation component and root-height bounds
```

Rotation coordinates are divided by their corresponding joint rotation limit; root height is divided by the original maximum root lift. The Jacobian includes that coordinate transformation. Initial `t` is the largest geometric violation at the unchanged seed, so the augmented geometric constraints start feasible. No edit limit receives slack. The objective has no competing nearest-pose penalty.

Positive `t`, a successful optimizer termination, or temporary trial values do not establish contact acceptance. The independent serialized-pose audit continues to enforce the original full-skin clearance, authored patches, anchors, normal limits and distributed contact witnesses. Even zero optimizer slack would still require that audit, and even a passing isolated pose would not establish temporal quality, support, balance or naturalness. A local failure is not an infeasibility proof.

The matched run retains the 150-iteration/180-second budget and memory guards. Frozen methods and inputs are saved under `reports/cylinder-pose-phase-one-v1`. The original nearest-pose output and snapshots remain immutable.

## Reproduction

Requires the separately acquired character assets and retained completed development fit:

```powershell
.venv\Scripts\python.exe scripts/regional_pose_witness.py reports/scene-region-jobs/cylinder-contact-v1/fit reports/<new-phase-study> --frame 96 --mode phase_one
```

`nearest` remains the default diagnostic mode; Studio fitting is unchanged. Eleven model-free tests cover feasible/infeasible toy systems, parameter scaling, analytic Jacobians, hard inequality/variable bounds and invalid inputs. They are included in the Windows/Linux public source workflow. The initial targeted local group contains 27 tests, while the selected public Python suite contains 69 tests.

## Completed Phase-I result: rejected terminal trial

The run hit its 180-second solve guard and finished auditing after **182.437 seconds**, with peak observed process RSS **611,934,208 bytes**. The initial geometric slack is **38.356391**, with minimum augmented slack zero. At interruption, the last callback holds a grossly infeasible trial: its reported slack is 2.925857 but its original maximum geometric violation is **922.238362**, and minimum augmented slack is **-919.312505**. The temporary scalar is not an upper bound on the nonlinear violation at an infeasible iterate.

The final saved diagnostic pose fails independent edit bounds: maximum rotation is **69.282034 degrees**, at a component-box corner that exceeds the corresponding 40-degree rotation norm limit. Left/right anchor errors are **668.590/922.650 mm**; neither hand has a contact triangle. The pose's object clearance cannot count as success because it has moved the hands away from their targets. This output is retained as failure evidence and is never installed into a clip.

Independent verification replays the serialized pose and original acceptance exactly. Inputs, seed, triangle selections and all physical limits match the first diagnostic; only the adapter and diagnostic driver methods differ. The normalized full-skin directional derivative check agrees within **1.139e-6**. The verifier and its hash-bound output remain under `reports/cylinder-pose-phase-one-review-v1`.

Declaring a nonlinear inequality hard does not guarantee SLSQP intermediate iterates satisfy it. Resource interruption can preserve such an iterate. This result therefore motivates a bounded coordinate map and explicit separation of best bounded and terminal trial outputs, not larger iteration budgets or relaxed contact screens.

## Follow-up: bounded coordinates

`scripts/regional_pose_bounded.py` reuses the established smooth rotation mapping from `grasp_pose_witness_bounded.py`: each joint's mapped rotation vector remains inside its original norm ball for every finite trial coordinate. Root height retains its direct bounded coordinate. The unchanged seed is reproduced before solving.

The search uses trust-region reflective least squares of positive original geometric violations, with exact full-skin extrema and all regional rows retained. This changes both the coordinate map and the optimizer; it is not a one-factor ablation. It retains the best evaluated bounded pose by maximum normalized violation, then squared violation sum, including the seed. The terminal trial is saved separately. Original independent acceptance remains authoritative, and neither numerical improvement nor solver success grants approval.

The follow-up retains the 180-second guard and permits 150 function evaluations; function evaluations are not equivalent to the previous iteration budget. Four additional tests verify seed preservation and independent serialized edit bounds at extreme coordinates and root-height endpoints, bringing the targeted group to 31 passing tests. Reproduction uses a new output directory:

```powershell
.venv\Scripts\python.exe scripts/regional_pose_bounded.py reports/scene-region-jobs/cylinder-contact-v1/fit reports/<new-bounded-pose-study> --frame 96
```

### Completed bounded result: limits hold, contacts still fail

The bounded search terminates on `xtol` after **46 evaluations / 24.031 seconds**, with peak observed process RSS **613,605,376 bytes**. Every recorded trial uses at most **80.657314%** of its applicable rotation budget; both the selected and terminal serialized poses independently pass original edit bounds. This fixes the preceding diagnostic's trial-bound problem, not its contact problem.

| Independent native-pose measurement | Unchanged seed | Selected bounded pose |
| --- | ---: | ---: |
| Full-skin object penetration | 36.356 mm | 21.040 mm |
| Left anchor error, 5 mm limit | 4.636 mm | 13.158 mm |
| Right anchor error, 5 mm limit | 8.602 mm | 9.278 mm |
| Left patch penetration | 9.349 mm | 2.623 mm |
| Right patch penetration | 8.918 mm | 5.200 mm |
| Left/right distributed triangle witness | Present / present | Absent / absent |
| Minimum skin-floor height | 2.024 mm | 2.069 mm |

The selected pose remains rejected. There are **1,632 penetrating vertices**, and **1,895 vertices** fail the 2 mm object-clearance requirement. Best-of-evaluated selection, seed equivalence, input/method hashes and both serialized outputs replay independently. The normalized geometric Jacobian preflight agrees within **1.488e-6**. Raw output lives in `reports/cylinder-pose-bounded-v1`; verification and probes live in `reports/cylinder-pose-phase-one-review-v1`.

The three worst vertices (13000, 8559 and 1268) belong predominantly to right pinky and left ring joints. Their depths agree within 0.000062 mm, exposing a near tie in the maximum-clearance residual. A local probe using individual gradients or their unweighted mean does not improve the maximum. A second probe chooses the minimum-norm convex combination of the three gradients; a normalized step of 0.001 reduces the original maximum violation from **23.039575 to 22.516516**. Its independent penetration is **20.517 mm**, but it worsens 11 already-failed geometric rows and both anchors. Both probes are retained, and neither becomes a replacement clip or accepted pose.

This demonstrates an available local descent direction despite `xtol` termination, while also showing why reducing only the worst collision is insufficient. The next solver comparison should account for simultaneous active collision vertices and protect the separate contact constraints from regression. Static feasibility remains unresolved. The full-project goal and all fourteen release capabilities remain open; these diagnostics provide no new engine, visual, dynamics, animator-review or cleanup-time approval.
