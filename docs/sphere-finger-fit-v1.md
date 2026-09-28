# Floor-valid sphere and bounded finger comparison

The first sphere grasp study used an object path that intersected the floor. This paired development experiment separates that input defect from hand fitting. The [placement edit](object-floor-placement-v1.md) raises the same sphere trajectory by 52.000004 mm, giving a conservative 2 mm floor gap. Both fits use exactly the same corrected scene, actor, grip-local points and contact times. The original failed scene and fitted outputs remain unchanged.

The control uses v8. Experimental v9 adds 38 native finger rotation controls with the edit budgets previously used in `paired_finger_fit.py`: 8 degrees for each thumb base, 5 degrees for other finger bases, and 12 degrees for distal joints. These are rotation-vector norm bounds relative to the preprocessed input, not anatomical axes or physiological ranges. Ten fingertip `End` joints remain fixed. The body-pose loss retains its original normalization; finger edits have a separate pose regularizer. Object samples, body controls and optimizer iteration budgets are unchanged.

Both full 180-frame fits completed under the resource supervisor. V8 took 161.5 seconds with approximately 0.992 GiB peak process-tree RSS; v9 took 172.9 seconds with approximately 1.061 GiB. No checkpoint training or new motion generation occurred.

## Independent exported results

Each variant is decoded at 717 key and quarter-frame samples, including the complete contact window `[60,121)`. Each hand has 244 contact samples. The comparison checks exact source-scene equality, audit/export/engine hashes, and actual exported local finger rotations against the declared budgets.

| Measurement | V8 control | V9 with finger edits |
| --- | --- | --- |
| Left grip maximum error | 21.363 mm | 24.186 mm |
| Right grip maximum error | 27.425 mm | 24.964 mm |
| Each hand within 30 mm | 244/244 | 244/244 |
| Each hand within 5 mm | 0/244 | 0/244 |
| Maximum skin/object penetration | 29.597 mm | 31.703 mm |
| Left palm maximum normal error | 11.781 degrees | 12.281 degrees |
| Right palm maximum normal error | 11.342 degrees | 14.341 degrees |
| Left palm peak speed near release | 0.375 m/s | 0.372 m/s |
| Right palm peak speed near release | 0.595 m/s | 0.606 m/s |
| Peak sampled joint acceleration | 51.273 m/s² | 46.388 m/s² |

Both candidates pass the provisional 30 mm scene contact and 15-degree palm-orientation diagnostics, while failing the stricter 5 mm point target and 10 mm skin/object clearance screen. Neither introduces sampled actor/floor penetration. The object floor defect is absent in both. Temporal measurements are descriptive; a lower acceleration peak does not override collision or contact failures.

All declared finger edit budgets pass independent export checks, including preservation of the ten unedited fingertip rotations. The largest v9 finger correction is only 0.806 degrees, on `RightHandPinky2`, well below its 12-degree allowance. Finger freedom alone did not improve clearance under this objective and optimization budget. This does not prove that the allowed poses are infeasible. Parameter scaling, contact/collision formulation and the solver's use of those degrees of freedom need investigation before expanding edit limits.

Actual Godot imports pass 720 actor-frame observations across the two input/candidate pairs, checking all 77 bones at every frame. This count includes the same input clip twice and does not imply four independent motions. Maximum position error is below 0.36 micrometres. Object physics, rendered skin, self-collision and human naturalness are not certified by these checks.

## Reproduction and retained failure

On the provisioned development workspace:

```powershell
.venv\Scripts\python.exe scripts/prepare_sphere_floor_trial.py reports/sphere-floor-trial-v1
.venv\Scripts\python.exe scripts/study_sphere_contact_fit.py reports/sphere-floor-fit-v8 --source reports/sphere-floor-trial-v1/palm.json --solver-version 8
.venv\Scripts\python.exe scripts/study_sphere_contact_fit.py reports/sphere-floor-fit-v9 --source reports/sphere-floor-trial-v1/palm.json --solver-version 9
```

Use new output names when reproducing; these commands reject existing study directories. Run `audit_primitive_grasp_fit.py` and `run_godot_scene_import.py` for each result, then `compare_sphere_finger_fits.py`. The completed audit and engine directories use the respective study path plus `-audit` and `-engine`.

The first comparison tool incorrectly required the ten fixed `End` joints to appear among the 38 editable joint declarations. That comparison failed and is retained in `reports/sphere-finger-comparison-v1`. The repaired comparison separately validates editable budgets and zero edits on those endpoints. `reports/sphere-finger-comparison-v2` completes successfully; no motion, budget or numerical tolerance was changed to fix the reporting error.

Sixteen focused tests cover sphere and rotating-box placement, edit budgets and finite gradients, primitive scene geometry, and explicit preview paths. Raw outputs and source snapshots remain in ignored local reports. V9 is an experimental CLI option; it is not promoted as a successful correction or a Studio default. All release capabilities remain unapproved, and reserved evaluation inputs and human-review requirements remain untouched.
