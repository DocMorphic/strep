# Export-aware fitting reserves for the coupled high-five

The measured fitting reserves allow a full step within the 0.2-degree control trust radius to pass the unchanged exported motion checks, compared with a one-eighth step in the [first coupled proposal](coupled-pair-proposal-v1.md). This is a useful solver improvement, not a cleared interaction. The complete sampled mesh audit and the specific surface-approximation failure are recorded below.

## Matched comparison

The source pair, 72 controls, 3,045 surface rows, 5,434 norm rows, source-relative caps, event pose and trust radius are unchanged. The new runner verifies that every base linearization array is exactly equal to the retained first study before applying a reserve. Native edit cones are not tightened or relaxed by this option.

For each motion row, calibration computes the largest positive difference between its actual exported norm and its affine prediction across the four earlier retained fractions. The fitting reserve is twice that observed difference. It therefore accounts for both curvature and serialization on those observed trials, rather than assuming all error is float32 rounding. There is no silent clipping if a reserve exceeds its source cap.

The calibration contains 2,646 speed and 2,700 acceleration rows, plus 88 unchanged edit rows. Maximum fitting reserves are 0.000199321 m/s for speed and 0.017740950 m/s2 for acceleration. These are fitting margins with mixed physical units, not new final acceptance tolerances. The original exported motion tolerance remains 1e-5; the original 5-degree edit limit and separately declared 0.0001-degree export tolerance remain unchanged.

An independent replay uses explicit velocity and acceleration stencils and reconstructs the constraint ordering without the fitter's row helper. It checks **21,384 motion norms** and reproduces the reserves within 3.42e-13. Source arrays, calibration inputs, solver output, exported tracks and verification artifacts are bound by hashes.

## Motion and engine results

The conic solve reports Solved after 38 iterations and 1.39 seconds. The **full step passes both actors' exported motion and edit checks**, with zero rate failures. The runner independently verifies 3,696 peak values over all 77 joints, six windows and 597 quarter-frame times per actor. Protected keys/channels, contact/release samples, translations and finger bounds retain their separate preservation checks. Maximum original-reference edits are 5.000050359 and 5.000050143 degrees, within the existing export tolerance.

Ideal float64 and exported kinematics both pass. Exported acceleration-peak shifts still reach 0.000113695 m/s2 for A and 0.000098361 m/s2 for B; passing does not mean rounding disappeared. The new direction exceeds the calibrated reserve in 62 speed rows and 13 acceleration rows by more than 1e-8. Maximum excesses are 0.000001719 m/s and 0.000094024 m/s2 respectively. Available slack keeps the actual source-cap excesses below the unchanged 1e-5 tolerance. **Empirical reserves are not universal error bounds.** Every new export still needs independent checks.

Fresh Godot validation passes **600 actor-frame observations** across two source and two candidate clips. Maximum position error is 4.16e-7 m; each clip retains 77 bones, a skinned surface, original duration and nonlooping import behavior. Engine import is not a quality rating.

## Completed sampled mesh comparison

The audit is terminal and covers all **57 quarter-frame times and 114 directional queries** across frames 63-77. Source and candidate skins each have 18,056 vertices; source queries are reused only after exact identity and time-population checks.

| Measure | Source | Reserved full step |
| --- | ---: | ---: |
| Maximum partner penetration | 23.556264 mm | 22.956420 mm |
| Times exceeding the 5 mm screen | 25/57 | 24/57 |
| Times exceeding their source-or-5-mm allowance by more than 1 micrometre | 0 | 1 |

Peak depth improves by **0.599844 mm**, versus 0.075037 mm for the previous one-eighth step. Two sampled depths increase by more than 1 micrometre; the largest increase is 58.169 micrometres, still under that time's 5 mm allowance. The other increase exceeds its source allowance by 10.510 micrometres and is diagnosed below. No new time crosses the 5 mm screen. Maximum floor depth does not increase, but inherited floor failures remain. Contact frame 75 retains its original 21/17 regional vertices within 3 mm, 5.199358-degree opposing-normal error and 1.896658 mm maximum penetration.

The correction is **not promoted**. Neither a lower global maximum nor one newly passing time excuses a separately regressed constraint. These sampled vertex checks also do not certify continuous collisions, triangle intersections, self-collision, physical forces or naturalness.

## Surface error attribution

The complete-mesh audit detects an allowance failure at frame 65.75, actor B vertex 14797. A separate fresh query confirms that this vertex was already included in the fitting witnesses, with the same closest triangle (9426) before and after the step. The source pair's per-time depth allowance is 19.690034 mm; actual candidate penetration is 19.700544 mm, an increase of **10.510 micrometres beyond that allowance**.

The affine scalar gap sits exactly at the cap. Nonlinear motion changes its frozen-plane prediction by only 0.124 micrometres, and serialization adds 0.016 micrometres. The principal discrepancy is **10.650 micrometres between the actual signed distance and the exported gap projected onto the old direction**. This diagnostic distinguishes an inadequate local surface approximation from an omitted witness or closest-triangle switch.

Using the full separation vector to the retained barycentric surface point would flag this step: its affine predicted distance exceeds the allowance by 12.371 micrometres. The exported distance to that fixed surface point is 19.702148 mm, conservatively above the actual nearest-surface depth. This motivates a full-vector norm constraint for penetrating witnesses. Such a constraint still requires nonlinear export and full-mesh checks; a local affine vector is not a certificate for the final mesh or unseen vertices.

## Evidence and reproduction

The local evidence folders are `coupled-pair-reserve-v1`, `coupled-pair-reserve-review-v1`, `coupled-pair-reserved-proposal-v1`, `coupled-pair-reserved-engine-v1`, `coupled-pair-reserved-export-error-v1` and `coupled-pair-reserved-geometry-v1`, all under ignored `reports/`. The local one-vertex diagnostic is `coupled-pair-surface-error-v2`; its earlier scalar-only version is preserved. No licensed meshes, weights or generated motion payloads enter the public repository.

```powershell
.venv\Scripts\python.exe scripts/calibrate_coupled_pair_reserve.py reports/coupled-pair-proposal-v1 reports/coupled-pair-export-error-v1 reports/paired-approach-witnesses-v1 reports/<new-reserve>
.venv\Scripts\python.exe scripts/study_coupled_pair_proposal.py reports/paired-approach-witnesses-v1 reports/<new-study> --reserve reports/<new-reserve>
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/<new-study> --output reports/<new-engine>
.venv\Scripts\python.exe scripts/audit_coupled_pair_geometry.py reports/<new-study> reports/paired-approach-witnesses-v1 reports/<new-engine> reports/<new-geometry>
.venv\Scripts\python.exe scripts/audit_coupled_pair_export_error.py reports/<new-study> reports/paired-approach-witnesses-v1 reports/<new-export-audit>
.venv\Scripts\python.exe scripts/verify_coupled_pair_reserve.py reports/<new-reserve> reports/coupled-pair-export-error-v1 reports/<new-study> reports/<new-export-audit> reports/paired-approach-witnesses-v1 reports/<new-review>
.venv\Scripts\python.exe scripts/diagnose_coupled_pair_surface.py reports/<new-study> reports/paired-approach-witnesses-v1 reports/<new-diagnostic> --frame 65.75 --source 1 --vertex 14797
```

The default proposal remains unchanged when no reserve is provided. Reproduction requires the retained licensed development fixture, prior evidence and locally pinned solver; it is not a self-contained public demo. Thirty-seven focused tests pass. Five new model-free tests join Windows/Linux CI, including a regression showing that tangential movement can evade a frozen-normal gap while exceeding a full separation norm. No held-out trials, learned model update, human review or release approval is claimed.
