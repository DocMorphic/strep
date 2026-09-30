# Coupled cylinder boundary paths

The cylinder clip now passes every exported quarter-frame geometry and original edit-budget check while retaining its passing grasp. Peak joint speed and acceleration fall substantially. Some approach fingertip acceleration peaks increase, so the result is not motion-quality or release approved.

## Method and scope

The input is the [boundary and floor correction](cylinder-guide-boundaries-v1.md). Two windows are fitted separately: approach keys **49–59** and release keys **122–132**. Within each window, all eleven keys and eight arm joints are optimized together. The shoulder, upper arm, forearm and wrist on each side may change; **158 other keys**, all root positions and non-arm local rotations remain exactly equal to the input. This preserves grasp/guard keys 60–121 and the prefix floor correction.

`regional_boundary_path.py` maps each arm edit into its original source-relative rotation ball. The objective includes second differences of physical local rotation matrices and world joint positions, including two protected neighbor keys on each side. It also checks all 18,056 skin vertices with all eight influences at 49 integer/quarter-frame times per window, using geodesic local rotation interpolation, linear bone offsets and the cylinder's signed distance. Geometry uses a 0.1 mm fitting reserve and 0.05 mm residual scale. Rotation curvature uses a 0.02 matrix scale, position curvature 2 mm, and weak position-reference guidance 50 mm.

These are **soft fitting terms**, not hard clearance or exact endpoint-velocity constraints. The rotation-matrix curvature is not physical angular acceleration. Native norm bounds do not replace independent exported subframe bound checks. No contact times, geometry, guide points, acceptance thresholds or object track are changed.

Each window uses 264 variables and a three-minute resource budget. Both terminate at that budget without convergence: 164 and 168 evaluations respectively, about 180.6 and 180.8 seconds. The best objective decreases from 3222.472504 to 518.525254 for approach and 8623.978453 to 629.869933 for release. Those weighted sums are not quality scores. Real-character central directional derivative checks differ from automatic differentiation by 8.90e-7 and 3.37e-5, within the declared absolute 0.002 / relative 0.0002 comparison. Maximum observed process RSS is about 1.45 GB.

## Export repair and provenance

The first export preparation failed an exact-preservation assertion. The existing general reconstruction helper normalizes every local rotation, changing 635 frozen matrix entries by up to 5.96e-8. The failure, original implementation snapshots, solver histories and best/last raw vectors remain under `reports/cylinder-boundary-path-v1`.

The new assembly path preserves stored local precision and performs FK without normalizing frozen keys. A regression test includes a slightly nonorthogonal float32 frozen rotation, which must remain bit-exact. The saved optimizer results were rebuilt under `reports/cylinder-boundary-path-recovered-v1`; **optimization was not repeated**. The recovery hashes and records its original optimization protocol and windows. Independent NumPy/SciPy replay matches the recovered arrays exactly, and the fresh engine/export checks measure any numerical drift rather than assuming it harmless.

## Exported evidence

| Measurement | Boundary + floor input | Coupled paths |
| --- | ---: | ---: |
| Full-clip geometry failures | 8 / 717 | **0 / 717** |
| Original subframe edit-budget failures | 0 / 717 | **0 / 717** |
| Grasp contact failures | 0 / 482 | **0 / 482** |
| Extra guard contact failures | 0 / 8 | **0 / 8** |
| Peak joint speed | 1.878351 m/s | **1.306499 m/s** |
| Peak joint acceleration | 155.944946 m/s² | **39.769477 m/s²** |
| Approach-window peak acceleration | 133.918655 m/s² | **38.821825 m/s²** |
| Release-window peak acceleration | 155.944946 m/s² | **39.769477 m/s²** |

Minimum exported cylinder clearance is 2.077600 mm in approach, 2.099883 mm during grasp, and 2.302137 mm in release. Minimum whole-clip floor height remains 2.000020 mm. All 49 frames previously exact to the original uncorrected source remain exact. The original, superseded guide points still fail all 482 comparisons; this study concerns the explicitly recorded calibrated guides, not a solution to the original fixed-guide problem.

The independent before/after audit measures every joint in both windows, including entry and exit joins. **33 approach joints increase their peak acceleration by more than 0.01 m/s².** The largest increase is the right index fingertip, 30.506635→38.821825 m/s². This 0.01 grouping is a reporting aid, not a new acceptance tolerance; the report records every increase above 1e-5. Release has no increases above 0.01, though smaller numerical changes remain. The whole-clip acceleration peak moves to the right ring fingertip at frame 133. The original uncorrected source remains lower at 27.444606 m/s².

Six path-specific tests pass, covering interpolation against SciPy, derivatives, stationary rotations, cylinder distances, FK, protected joins/budgets and exact assembly. Sixty-one related checks also passed. Actual Godot import verifies all 180 frames and 77 bones, preserving a skinned surface and non-looping playback; maximum joint-position discrepancy is 3.661e-7 m. This proves actor playback fidelity, not rendered appearance or dynamics.

## Next decision

Preserve this geometry-passing candidate. Extend the temporal objective and independent preservation checks to the hand descendants, whose acceleration can grow even when wrist and forearm motion improve. Use the measured per-joint failures, preserve passing grasp/guard/geometry and original edit bounds, and compare boundary velocities as well as acceleration before choosing a candidate. Further fit effort should be justified by those residuals, not by increasing acceptance tolerances.

This remains one development cylinder clip. It supplies no continuous triangle-interior collision, self-collision, anatomy, balance, force, semantic, animator-rating or cleanup-time approval. Broad actions, rigs, objects, partners, editing/style and full-system evaluation remain open. All fourteen release capabilities remain unapproved.

## Reproduction

Local licensed assets and retained input studies are required; use fresh output directories. Normal execution includes the corrected assembly:

```powershell
.venv\Scripts\python.exe scripts/study_regional_boundary_path.py reports/cylinder-guide-floor-v1 reports/<new-path>
.venv\Scripts\python.exe scripts/audit_regional_wrist_track.py reports/cylinder-guide-track-v2 reports/<new-review> --boundary-patch reports/cylinder-guide-boundaries-v1 --floor-patch reports/cylinder-guide-floor-v1 --path-patch reports/<new-path>
```

For the retained first optimization, append `--saved-fit reports/cylinder-boundary-path-v1` to rebuild its saved parameters without rerunning fitting. Evidence is under the recovered path directory, `reports/cylinder-boundary-path-review-v1` (including `path-comparison.json`) and `reports/cylinder-boundary-path-engine-v1`. Public CI remains separate from the local Torch/asset-dependent checks.
