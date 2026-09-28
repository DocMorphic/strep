# Sampled object-clearance constraints

V11 improved contact near release but worsened full-hand penetration. A separate diagnostic reconstructed its exact frozen vertex selection from saved preprocessing, contact overrides, surface-normal faces and primitive geometry. Current implementation files were required to match the fit snapshot, and the reconstructed sample count matched the saved recipe. The diagnostic independently decoded all 717 exported poses, reproduced the prior dense audit exactly, and reconstructed the original sampled-object objective to within 0.00000021.

The 1,362 selected vertices missed the worst fingertip (vertex 1261, dominated by LeftHandPinky4), which penetrated the sphere by 20.910 mm at frame 62. Sampled vertices still penetrated by up to 17.317 mm. Of 49,510 vertex/sample observations deeper than 10 mm, 43,585 involved omitted vertices. These counts are repeated observations, not distinct vertices or independent failures. Both sampling omissions and unresolved sampled constraints exist.

## Experimental formulation

V12 retains V11's frozen samples, body/finger controls, edit budgets, contact/release targets, objective weights and three optimization stages. Only sampled object clearance changes. Each object/frame has one signed inequality: the maximum inflated-primitive violation over selected vertices. Its value is negative when every sampled vertex is outside the inflated shape. Sphere inflation is radial; box inflation retains the previous face-based semantics.

The augmented-Lagrangian merit is `(relu(lambda + rho*g)^2 - lambda^2)/(2*rho)`. Initial `lambda=0` and `rho=2*old_collision_weight` reproduce the old squared penetration objective and gradients. After each stage, multipliers become `relu(lambda + rho*g)` and the penalty grows by the existing factor of four. Feasible negative slack allows multipliers to decrease. A per-frame maximum avoids diluting collisions by averaging many nonpenetrating vertices, but remains nonsmooth and sampled.

This does not guarantee feasibility. The trial deliberately retains the known sample omissions to isolate the optimization change. Full exported-skin auditing remains separate and compulsory, and no edit budget or acceptance tolerance is expanded.

## Reproduction

The frozen plan is `reports/sphere-object-inequality-plan-v1/protocol.json`. Reuse the completed V11 control and run V12 once:

```powershell
.venv\Scripts\python.exe scripts/study_sphere_contact_fit.py reports/sphere-floor-fit-v12 --source reports/sphere-floor-trial-v1/palm.json --solver-version 12
.venv\Scripts\python.exe scripts/audit_primitive_grasp_fit.py reports/sphere-floor-fit-v12 reports/sphere-floor-fit-v12-audit
.venv\Scripts\python.exe scripts/run_godot_scene_import.py reports/sphere-floor-fit-v12/fit reports/sphere-floor-fit-v12-engine
.venv\Scripts\python.exe scripts/compare_sphere_finger_fits.py reports/sphere-floor-fit-v11 reports/sphere-floor-fit-v12 reports/sphere-object-inequality-comparison-v1
```

Use new output directories for intentional additional trials. The collision diagnostic is `scripts/diagnose_grasp_collision_samples.py`; it requires matching current implementation and saved snapshot and binds its output to the exact fit, mesh, exported GLB and dense audit. The initial diagnostic mistakenly requested a per-sample array from the compact audit summary; that failure is preserved locally, and the corrected diagnostic reads the detailed candidate artifact. No original fit or audit was modified.

All work uses one existing development scene. There is no new checkpoint training, held-out evaluation, human review or Studio default promotion.

## Measured result

V12 completed 324 objective evaluations in 167.1 seconds with 1.063 GiB peak process-tree RSS. Exact preprocessing, authored constraints, release guards, finger settings and sample counts match V11. The separate sample diagnostics also confirm the complete selected-vertex arrays are identical. Nine focused tests pass, including initial cost/gradient parity. The exported audit covers 717 poses and 244 contact samples per hand. Godot imports all 360 source/candidate actor-frame observations across 77 bones, with maximum position error below 0.36 micrometres.

| Dense/exported measurement | V11 fixed penalty | V12 clearance inequalities |
| --- | --- | --- |
| Full-skin maximum object penetration | 20.910 mm | 5.113 mm |
| Selected-vertex maximum penetration | 17.317 mm | 1.076 mm |
| Poses with full-skin penetration over 10 mm | 252/717 | 0/717 |
| Left grip maximum error | 12.910 mm | 25.582 mm |
| Right grip maximum error | 14.702 mm | 31.208 mm |
| Left samples within 30 mm | 244/244 | 244/244 |
| Right samples within 30 mm | 244/244 | 233/244 |
| Left/right samples within 5 mm | 8/244 and 0/244 | 0/244 and 0/244 |
| Left palm maximum normal error | 10.189 degrees | 10.909 degrees |
| Right palm maximum normal error | 8.924 degrees | 10.089 degrees |
| Left palm peak speed near entry | 0.284 m/s | 0.227 m/s |
| Right palm peak speed near entry | 0.394 m/s | 0.315 m/s |
| Left palm peak speed near release | 0.206 m/s | 0.160 m/s |
| Right palm peak speed near release | 0.383 m/s | 0.472 m/s |
| Peak sampled joint acceleration | 37.790 m/s² | 38.212 m/s² |

All finger edit bounds and fixed fingertip rotations pass, with maximum finger edit 8.180 degrees. Actor and authored-object floor screens remain clear. The V12 worst penetration is an omitted right pinky vertex (17255) at frame 119. Its sampled-object maximum remains inside the sphere by 1.076 mm, corresponding to 3.076 mm violation of the solver's 2 mm outward-clearance target. The diagnostic independently reproduces that final constraint magnitude; its reconstructed fixed-penalty value is only a proxy for V12, not its multiplier-based objective.

The current 10 mm full-skin penetration screen passes, but both strict 5 mm contacts fail and the right hand now fails the looser 30 mm scene screen. Both worst grip errors occur at frame 60. Both palm normals slightly exceed the solver's 10-degree target, though they pass the 15-degree diagnostic screen. Right release speed and peak joint acceleration worsen. This is an explicit tradeoff, not a successful grasp or a release-ready animation.

Next work should test joint feasibility/convergence under the existing edit limits, including entry and release. Three augmented-Lagrangian stages are not proof that the constraints are infeasible. The remaining omitted-vertex gap is also real and must remain visible when improving the solver. Do not promote V12, loosen tolerances or expand budgets to hide these failures.

Local evidence: `reports/sphere-collision-samples-v11`, `reports/sphere-floor-fit-v12` and its audit/engine directories, `reports/sphere-object-inequality-comparison-v1`, `reports/sphere-collision-samples-v12`, and `reports/object-inequality-integration-v1`. All 14 project release capabilities remain unapproved.
