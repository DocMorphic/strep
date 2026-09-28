# Contact constraints at release boundaries

Scene contacts store inclusive integer start/end keys and emit the end event at `end_frame + 1`. The V10 fitter enforced the last contact key but did not enforce the following release boundary. In the floor-valid sphere development fixture, both hands had their largest dense grip errors at frame 120.75, after the final enforced key at 120 and before the event at 121.

The experimental V11 solver adds a point target at that boundary using the actual world/object material target at the new frame, transformed into actor-native coordinates. It extends normal and tangent enforcement to the same key and recomputes contact fade from the extended solver track. Authored scene contacts, event times and object paths remain unchanged. A contact ending at the final clip key needs no added key because playback and the object track both hold their final sample. An overlapping same-effector handoff is rejected instead of silently extending through another contact. Actor-relative targets remain unsupported by this guard compiler.

This is one additional discrete constraint, not a guarantee of continuous contact. The comparison retains the full `[start_frame, end_frame + 1)` dense audit interval and the original point/normal/clearance screens. Body and finger edit budgets, physical-angle finger coordinates, objective weights, preprocessing and optimization iteration limits remain fixed. Only the solver contact interval, boundary surface frame and resulting fade are changed.

## Reproduction and evidence

The frozen plan is `reports/sphere-release-guard-plan-v1/protocol.json`. The completed V10 control is reused. Run the candidate once, then audit its exported geometry and actual engine import:

```powershell
.venv\Scripts\python.exe scripts/study_sphere_contact_fit.py reports/sphere-floor-fit-v11 --source reports/sphere-floor-trial-v1/palm.json --solver-version 11
.venv\Scripts\python.exe scripts/audit_primitive_grasp_fit.py reports/sphere-floor-fit-v11 reports/sphere-floor-fit-v11-audit
.venv\Scripts\python.exe scripts/run_godot_scene_import.py reports/sphere-floor-fit-v11/fit reports/sphere-floor-fit-v11-engine
.venv\Scripts\python.exe scripts/compare_sphere_finger_fits.py reports/sphere-floor-fit-v10 reports/sphere-floor-fit-v11 reports/sphere-release-guard-comparison-v1
```

Output directories are immutable: use new directory names for intentional new trials. The comparison requires exact source scenes, preprocessed arrays, authored contact specifications and base scene context. It separately verifies the added guards and effective solver specification against the original object trajectory. It binds both dense audits, engine import records and exported finger-edit budgets.

No Studio default change, checkpoint training, held-out evaluation or human quality approval is implied by this development experiment.

## Measured result and retained failures

V11 completed 322 objective evaluations in 168.4 seconds with 1.062 GiB peak process-tree RSS. The source/preprocessing/configuration comparisons pass. The separate exported-skin audit evaluates 717 poses and 244 contact samples per hand. All 38 finger-edit budgets and ten fixed fingertip rotations pass; the largest finger edit is 8.912 degrees. Godot imports all 360 source/candidate actor-frame observations across 77 bones, with maximum position error below 0.36 micrometres.

| Dense/exported measurement | V10 control | V11 release guard |
| --- | --- | --- |
| Left grip maximum error | 20.102 mm | 12.910 mm |
| Right grip maximum error | 17.797 mm | 14.702 mm |
| Left samples within 5 mm | 0/244 | 8/244 |
| Right samples within 5 mm | 0/244 | 0/244 |
| Each hand within 30 mm | 244/244 | 244/244 |
| Maximum skin/object penetration | 18.444 mm | 20.910 mm |
| Samples with penetration over 10 mm | 246/717 | 252/717 |
| Left palm maximum normal error | 10.759 degrees | 10.189 degrees |
| Right palm maximum normal error | 9.335 degrees | 8.924 degrees |
| Left palm peak speed near release | 0.298 m/s | 0.206 m/s |
| Right palm peak speed near release | 0.556 m/s | 0.383 m/s |
| Left palm peak speed near entry | 0.231 m/s | 0.284 m/s |
| Right palm peak speed near entry | 0.369 m/s | 0.394 m/s |
| Peak sampled joint acceleration | 44.579 m/s² | 37.790 m/s² |

Actor and authored-object floor checks still pass. The left grip's worst error remains at frame 120.75; the right worst error moves to frame 70. Maximum penetration occurs at frame 62. The sphere retains the historical object ID `box` in this fixture; its actual geometry is a sphere.

This result supports enforcing the intended release boundary but exposes a tradeoff: grip and release kinematics improve while full-hand penetration and entry speeds worsen. Strict point contact and the unchanged 10 mm clearance screen still fail. The left normal also remains slightly outside the solver's 10-degree target. Measured kinematics do not establish naturalness or anatomical validity.

V11 is not promoted to the Studio default or accepted for release. Next work must address contact and full-hand clearance jointly, preserve entry/release checks, and distinguish optimizer sample omissions from failed constraint convergence before changing the solver. Do not enlarge edit budgets or relax the acceptance screens to make this example pass. Broader object/partner/rig/action coverage and human review remain open; all project release capabilities remain unapproved.
