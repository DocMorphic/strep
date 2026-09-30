# Physical joint continuity in the moving cylinder grasp

The revised grasp passes all native and exported contact/clearance samples while keeping the alternative guides and original numeric gates fixed. The full clip remains rejected because approach/release paths intersect the cylinder, inherited floor failures persist and motion peaks remain above the source baseline.

## Change and controlled inputs

The [first trajectory](cylinder-guide-track-v1.md) preserved wrist targets but made large changes to internal arm configurations. `regional_wrist_track.project` now optionally penalizes differences between **physical local joint rotation matrices** and the preceding projected key. The first key prefers the calibrated reference pose. This replaces the tiny preference in unconstrained optimizer coordinates for this explicitly selected mode; the original default remains available.

The chordal rotation residual has weight **1**. Source-relative norm bounds still use the existing bounded mapping. A separate **3° per-native-key arm-step screen** rejects measured excess; the soft preference is not a hard optimization rate constraint. At 30 fps this corresponds to a sampled 90°/s development screen, not an anatomical speed certification. The original source's maximum arm step over the interval is 1.343511°.

Inputs, source GLB/motion, authored scene, guide bindings, target tracks, contact timings, 0.1 mm outward reserve, fitting budgets, edit limits and contact thresholds are identical to the first trajectory. A recorded comparison checks these fields and artifact hashes. The original failed trajectory is retained. No guide is selected anew during motion.

## Measured comparison

| Measurement | First trajectory | Physical continuity |
| --- | ---: | ---: |
| Native grasp/release-guard keys passing | 62 / 62 | 62 / 62 |
| Exported authored-grasp geometry failures | 11 / 241 | **0 / 241** |
| Exported authored hand-contact failures | 17 / 482 | **0 / 482** |
| Extra release-guard contact failures | 0 / 8 | **0 / 8** |
| Minimum full-skin clearance during grasp | 1.579537 mm | **2.099883 mm** |
| Largest native active arm step | 13.002255° | **1.927379°** |
| Full-clip geometry failures | 191 / 717 | 172 / 717 |
| Peak sampled joint acceleration | 197.226161 m/s² | **43.071866 m/s²** |
| Peak sampled joint speed | 1.451594 m/s | **1.587032 m/s** |

The new maximum decoded active arm angular speed is **57.821513°/s**. Both native and quarter-frame step screens have zero failures. All **717 decoded source-relative edit-bound samples** pass. The 241 grasp and four release-guard samples all meet their geometry and applicable region checks. These are discrete vertex/pose measurements, not continuous collision guarantees.

The run takes **60.187 seconds**, with peak observed RSS **581,337,088 bytes**. Sixty-one keys stop on numerical wrist-target tolerances; frame 60 terminates normally via SciPy's cost tolerance. Its maximum serialized wrist position error is about 5.492 micrometres, within the independently checked 0.1 mm reach screen. Solver termination is not used as a contact pass. All 84 edited frames replay; 96 frames remain exactly unchanged.

## Remaining failures and next work

The approach has **21 failing samples**, with up to **2.771948 mm** penetration. The release blend has **26 failures**, reaching **19.755111 mm** penetration. The unchanged pre-blend section retains **125 floor failures**, with minimum height **1.870318 mm** against the original 2 mm clearance gate. These account for all 172 full-clip geometry failures.

The new whole-clip speed is worse than both the source and first trajectory. Acceleration improves substantially from the first trajectory but remains above the source's **27.444606 m/s²**; source speed is **1.280603 m/s**. The new acceleration maximum is at **frame 131, right ring-finger endpoint**, inside the release blend. Do not turn one improved metric or the passing grasp interval into motion-quality approval.

Next, preserve the passing grasp keys and fixed guides while constructing collision-checked approach/release paths under the same edit limits. The release must also address the speed/acceleration regression. Correct inherited floor clearance separately without displacing the established grasp. Recheck complete exported motion and engine fidelity after changes; a smooth scalar blend is not a collision or motion-quality guarantee.

## Verification and reproduction

The independent auditor now checks physical local-rotation steps using SciPy relative rotations, recorded step-screen decisions and decoded quarter-frame angular speeds. It retains native reconstruction, physical finger shapes, immutable outside frames, full-skin geometry, original-guide comparisons, and dense edit bounds. All **482 original-guide checks still fail**, preserving the distinction from the alternative authored condition.

**43 focused tests pass**, including independent physical-rotation residuals and derivatives, angle wraparound, malformed priors, frame-local parity and explicit target stopping without contact approval. Godot verifies the revised clip's **180 frames and 77 bones**, preserving its skinned surface and non-looping playback; maximum joint-position discrepancy is below 0.402 micrometres. This checks actor playback fidelity only.

Local evidence is retained under `reports/cylinder-guide-track-v2`, `reports/cylinder-guide-track-review-v2` (`verification.json`, `comparison.json`, `diagnosis.json`), and `reports/cylinder-guide-track-engine-v2`. Public model-free CI remains separate from these local Torch/asset-dependent tests. With acquired assets and retained source studies, use fresh output directories:

```powershell
.venv\Scripts\python.exe scripts/study_regional_wrist_track.py reports/cylinder-guide-projection-v1 reports/<new-track> --continuity-weight 1 --maximum-step-degrees 3
.venv\Scripts\python.exe scripts/audit_regional_wrist_track.py reports/<new-track> reports/<new-review>
```

No model training, checkpoint replacement, Studio default, anatomical validation, self-collision/force approval, animator ratings or cleanup-time evidence is added. All fourteen release capabilities remain unapproved.
