# Joint contact and clearance convergence

The V12 development trial reduced full-skin sphere penetration below the current 10 mm screen but left grip errors of 25.582/31.208 mm. The right grip failed even the 30 mm scene screen, and both missed the 5 mm solver target. That finite run does not establish infeasibility under the existing edit limits.

V13 runs six outer augmented-Lagrangian stages instead of three. The per-stage 100-iteration limit, penalty growth, body/finger controls and hard edit budgets, release guards, frozen object tracks, geometry samples and target thresholds remain unchanged. A validated per-call stage override avoids mutating global solver settings; existing versions retain three stages. The experiment uses the same six-second development input and is not a new action or independent evaluation case.

The full run starts from the original preprocessing because V12 did not save all optimizer and multiplier continuation state. Its first three objective/constraint records must reproduce the completed V12 control within tight numerical tolerance. The comparison also checks exact preprocessing arrays, original contact specifications, scene context, release guards, finger settings, selected sample count and shared configuration. No quality claim follows merely from running more iterations.

## Reproduction

The frozen pre-run plan is `reports/sphere-convergence-plan-v1/protocol.json`. Reuse V12 as the control:

```powershell
.venv\Scripts\python.exe scripts/study_sphere_contact_fit.py reports/sphere-floor-fit-v13 --source reports/sphere-floor-trial-v1/palm.json --solver-version 13
.venv\Scripts\python.exe scripts/audit_primitive_grasp_fit.py reports/sphere-floor-fit-v13 reports/sphere-floor-fit-v13-audit
.venv\Scripts\python.exe scripts/run_godot_scene_import.py reports/sphere-floor-fit-v13/fit reports/sphere-floor-fit-v13-engine
.venv\Scripts\python.exe scripts/compare_sphere_finger_fits.py reports/sphere-floor-fit-v12 reports/sphere-floor-fit-v13 reports/sphere-convergence-comparison-v1
.venv\Scripts\python.exe scripts/diagnose_grasp_collision_samples.py reports/sphere-floor-fit-v13 reports/sphere-collision-samples-v13
```

Keep output directories immutable. Full exported skin, contact error throughout the authored interval, normal alignment, entry/release speeds, joint acceleration, edit bounds and actual engine import remain separate checks. Missing sampled vertices remain a known limitation. More stages cannot certify anatomical validity, self-collision, dynamics, continuous-time clearance or naturalness. No Studio default promotion, training, held-out trials or human approval is implied.

## Measured result

The six-stage run completed 650 objective evaluations in 289.8 seconds, versus 324 evaluations and 167.1 seconds for V12. Peak process-tree RSS was 1.062 GiB. All first-three-stage objective and violation records reproduce the control, and the input/configuration comparison passes. The independent collision diagnostics confirm identical selected-vertex arrays (1,362 vertices).

| Dense/exported measurement | V12: three stages | V13: six stages |
| --- | --- | --- |
| Left grip maximum error | 25.582 mm | 19.949 mm |
| Right grip maximum error | 31.208 mm | 26.077 mm |
| Left samples within 30 mm | 244/244 | 244/244 |
| Right samples within 30 mm | 233/244 | 244/244 |
| Each hand within 5 mm | 0/244 | 0/244 |
| Full-skin maximum object penetration | 5.113 mm | 4.287 mm |
| Selected-vertex maximum penetration | 1.076 mm | 0.344 mm |
| Poses with full-skin penetration over 10 mm | 0/717 | 0/717 |
| Left palm maximum normal error | 10.909 degrees | 9.718 degrees |
| Right palm maximum normal error | 10.089 degrees | 7.835 degrees |
| Left palm peak speed near entry | 0.227 m/s | 0.216 m/s |
| Right palm peak speed near entry | 0.315 m/s | 0.290 m/s |
| Left palm peak speed near release | 0.160 m/s | 0.203 m/s |
| Right palm peak speed near release | 0.472 m/s | 0.385 m/s |
| Peak sampled joint acceleration | 38.212 m/s² | 38.516 m/s² |

All 38 finger edit bounds and ten fixed fingertip rotations pass, with maximum finger edit 9.040 degrees. The largest edit over all controlled joints is 16.626 degrees; this does not establish that every individual finger budget has unused capacity at the worst frame. Actor and authored-object floor screens remain clear. Godot imports 360 source/candidate actor-frame observations across all 77 bones, with maximum position error below 0.36 micrometres. Thirteen focused software tests pass.

Both worst grip errors remain at frame 60. Maximum full-skin penetration occurs at frame 112 on omitted vertex 17255, dominated by RightHandPinky2. The 0.344 mm sampled penetration corresponds to 2.344 mm violation of the solver's requested 2 mm outward clearance. The dense diagnostic reproduces the earlier audit exactly and independently verifies that final sampled constraint magnitude.

Additional stages improve point, normal and clearance results enough for this clip to pass the current 30 mm scene-point and 10 mm penetration screens. They do not achieve strict 5 mm contact: neither hand has a passing contact sample. Constraint improvement is not monotonic across stages. Left release speed and peak joint acceleration regress slightly; measured kinematics do not establish realism. Missing vertices, continuous-time geometry, self-collision, anatomy and human quality remain unresolved.

V13 remains experimental. The result supports additional optimization effort as one contributor to V12's failure, but repeated stage increases alone are not a sufficient next strategy. Next, test an isolated-frame reachability/clearance witness under the same edit bounds to distinguish pose feasibility from whole-clip temporal coupling, while retaining the full-clip failures. A failed local solve would not prove infeasibility, and a successful isolated pose would not prove a usable animation. Reuse existing kinematic/Jacobian machinery where applicable; do not duplicate earlier paired-hand work or silently loosen budgets.

Evidence is in `reports/sphere-convergence-plan-v1`, `reports/sphere-floor-fit-v13` and its audit/engine folders, `reports/sphere-convergence-comparison-v1`, `reports/sphere-collision-samples-v13`, and `reports/convergence-integration-v1`. All 14 release capabilities remain unapproved; the wider goal and its held-out/human requirements remain intact.
