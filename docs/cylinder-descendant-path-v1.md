# Preserving hand motion during cylinder approach

The approach now passes separate exported speed and acceleration comparisons for all 54 joints whose positions depend on the edited arm rotations. This removes the fingertip regressions found in the [first coupled boundary fit](cylinder-boundary-path-v1.md), while preserving its passing contact, geometry and edit-limit checks. It remains one development clip, without release or human-quality approval.

## What changed

The prior objective smoothed eight arm joints. A wrist can improve while a fingertip attached to it accelerates more, so the new objective includes every affected descendant position. Shoulder origins are excluded because changing their own rotation does not move their position; upper arms, forearms, wrists and all finger joints/endpoints are included.

Only approach keys **49–59** are fitted. The release, grasp/guard, root positions, non-arm local rotations and **169 outside frames** remain exactly equal to the previous candidate. The independent NumPy/SciPy replay reproduces all saved arrays exactly. The original source-relative arm rotation budgets remain enforced by the bounded parameterization and checked on export.

For each affected joint, `boundary_motion.py` decodes two saved GLBs: the current coupled candidate and its preceding boundary/floor input. The lower peak from these two clips supplies that joint's speed comparison and acceleration comparison separately. The fitting targets are 99% of these values; the exported checks retain the original values, with a 1e-5 numerical comparison allowance. These are **relative preservation checks**, not universal realism thresholds or claims about physically acceptable acceleration.

Temporal sampling covers frames **47–61** at quarter-frame spacing. Speed comparisons cover edges within 48–60; acceleration centers cover 48–60 and include samples on both sides of each join. This measures norms of world-space velocity and second position differences. It does not enforce exact endpoint velocity vectors. Geometry fitting still checks all skin vertices at the original 49 samples within 48–60, with the same reserve and scales.

The added speed and acceleration excess residual scales are 0.001 m/s and 0.1 m/s². They are soft objective terms. Successful exported checks must be established independently, not inferred from the objective, native poses or optimizer status. The auditor now supports an ordered chain of path patches, replaying each against its actual predecessor and saving separate comparisons.

## Results

| Exported measurement | Previous candidate | Refined approach |
| --- | ---: | ---: |
| Approach-window peak acceleration | 38.821825 m/s² | **33.162127 m/s²** |
| Right index fingertip peak acceleration | 38.821825 m/s² | **30.021892 m/s²** |
| Per-joint speed comparison failures | — | **0 / 54** |
| Per-joint acceleration comparison failures | — | **0 / 54** |
| Full-clip geometry failures | 0 / 717 | **0 / 717** |
| Original subframe edit-budget failures | 0 / 717 | **0 / 717** |
| Grasp contact failures | 0 / 482 | **0 / 482** |
| Extra guard contact failures | 0 / 8 | **0 / 8** |

Every joint comparison passes strictly: minimum speed margin is **0.005045 m/s**, and minimum acceleration margin is **0.190803 m/s²**. None relies on the numerical comparison allowance. The right index fingertip's acceleration cap is 30.506635 m/s², inherited from the earlier input; its previous regression is removed.

Minimum approach cylinder clearance is **2.110764 mm**. Other phases retain their passing results. Whole-clip peak speed and acceleration remain **1.306499 m/s** and **39.769477 m/s²**, because the release is unchanged. The acceleration maximum remains the right ring fingertip at frame 133; the original uncorrected source's peak is 27.444606 m/s². Small numerical differences in unaffected world transforms remain visible in the all-joint comparison; the exact preservation claim concerns local non-arm rotations, root and outside frames.

The fit reaches its three-minute resource limit without convergence after 172 evaluations, taking 180.969 seconds. The weighted objective falls from 82095.861041 to 489.586972. It is not a quality score. The actual-character directional derivative check compares 3160050.204984 by central differences with 3160050.218439 by automatic differentiation: absolute error 0.013455, relative error about 4.3e-9, within the declared combined absolute/relative check. Best and last raw vectors, history and time-limit termination are retained. Maximum observed process RSS is about 1.44 GB.

Fourteen focused tests pass. They cover interpolation/derivatives, exact assembly, parent-to-descendant dependencies, fixed-neighbor join stencils, per-joint comparisons that reject hidden regressions, and keeping the fitting reserve separate from the original comparison caps. The four model-free motion tests are added to Windows/Linux CI; the Torch checks remain local. Actual Godot import verifies all 180 frames and 77 bones, preserving the skinned surface and non-looping playback with maximum position discrepancy 3.661e-7 m.

## Scope and next work

Retain this passing candidate and use the same per-joint and exported-geometry checks on another development interaction before promoting the correction to the product. Do not tune the reserved held-out trials. This single source, rig and cylinder does not establish broad action/rig/object/partner coverage. The untouched release acceleration, original fixed-guide failures, continuous surface collision, self-collision, anatomy, dynamics, semantic correctness and developer/animator cleanup evidence remain open. All fourteen release capabilities remain unapproved.

Evidence is retained under `reports/cylinder-descendant-path-v1`, `reports/cylinder-descendant-path-review-v1` (notably `path-2/path-comparison.json`) and `reports/cylinder-descendant-path-engine-v1`. No model, training data, Studio default, authored contact, object track or acceptance threshold changed.

## Reproduction

Local licensed assets and retained input studies are required. Use fresh directories:

```powershell
.venv\Scripts\python.exe scripts/study_regional_boundary_path.py reports/cylinder-boundary-path-recovered-v1 reports/<new-descendant-path> --phase approach --motion-reference reports/cylinder-guide-floor-v1
.venv\Scripts\python.exe scripts/audit_regional_wrist_track.py reports/cylinder-guide-track-v2 reports/<new-review> --boundary-patch reports/cylinder-guide-boundaries-v1 --floor-patch reports/cylinder-guide-floor-v1 --path-patch reports/cylinder-boundary-path-recovered-v1 --path-patch reports/<new-descendant-path>
```
