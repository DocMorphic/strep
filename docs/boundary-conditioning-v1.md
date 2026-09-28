# Boundary conditioning diagnosis, 2026-09-27

Twenty-four matched model runs did not identify a reliable parameter or coordinate change that fixes the rough-editor's boundary poses. Production generation and the checkpoint remain unchanged. The evidence now separates constraint encoding, the learned position output, rotation-based reconstruction, and target-rig transfer rather than treating them as one error.

## What was verified

`study_boundary_guides.py` temporarily wraps the model's sampling method to save its observed values, masks and final feature tensor without altering the return value. Six baseline replays across the two studies reproduce the original saved NPZ bytes exactly. All use the pinned checkpoint revision `6c9233af1180b8151e3c4703477104af5dce9dd5`, 100 diffusion steps, unchanged cached text tensors and no model postprocessing. No training or new text encoding occurred.

The independent `verify_boundary_guides.py` implements NumPy feature denormalization from checkpoint mean/std arrays and local forward kinematics. It does not use the model's inverse decoder or constraint loader for those checks. Guide encoding differs from the intended poses by at most 2.31e-6 m. Rotation conditioning masks contain zero active channels. Native previews match every generated pose within 6e-7 m and preserve all eight skin weights. All 24 GLBs pass validation with zero errors and zero warnings. Five focused guide/canonicalization/diagnostic tests passed, with four existing Torch warnings, in 7.19 seconds; no full-suite rerun is claimed.

The [official constraint documentation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/constraints.html) says full-body guides derive positional targets from rotations; they do not explicitly constrain those rotations. The pinned `constraints.py` confirms this. `kimodo_motionrep.py` decodes positions and rotations separately, then normally reconstructs exported joint positions from the predicted rotations. `twostage_denoiser.py` and `cfg.py` use learned conditioning and guidance, with no final hard projection of every full-body target.

For jump seed 205, baseline maximum error is 90.39 mm in the position output and 102.55 mm after rotation FK. Root error is only 24.07 mm; removing root displacement still leaves 98.41 mm of pose error. Dance seed 203 has 27.93 mm position-output error and 44.40 mm after FK, with only 6.09 mm root error. A global coordinate offset cannot account for these failures. These results do not prove every integration path correct or every possible guide infeasible; they localize the four tested failures.

## Smoothed root and boundary context

`reports/boundary-guides-v2` contains eight runs on the saved jump-205 and dance-203 failures. Baseline uses two guide samples at each end. Smooth uses upstream `get_smooth_root_pos` on the bridge and canonicalizes its first XZ point; world poses are preserved after restoring the recorded offset. Dense supplies eight samples at each end. Combined applies both. Every comparison below uses the same four original endpoint samples; separate full audits cover all additional guides.

| Case | Baseline FK error | Smooth | Dense | Smooth + dense |
|---|---:|---:|---:|---:|
| Jump 205 | 102.55 mm | 104.98 mm | 88.82 mm | 88.63 mm |
| Dance 203 | 44.40 mm | 44.81 mm | 47.97 mm | 46.63 mm |

All fail the existing 30 mm screen. Extra context helps one example and worsens the other. It is not promoted.

V1 failed during relative-path request setup before inference. V2 initially stopped after its first baseline inference because the preview helper returns four values, not two. The export bug was fixed and the failed run resumed using the verified saved raw/feature hashes; the baseline was not regenerated. Both failures and implementation snapshots remain. Resume now validates design, saved request, guide, raw tensor, checkpoint and CFG provenance, and a rejected invocation cannot relabel a completed study as failed.

## Constraint guidance strength

`reports/boundary-guidance-v1` contains 16 runs: four saved case/seed combinations, each with text guidance fixed at two and constraint guidance 2, 3, 4 or 6. Original four-sample boundaries are retained.

| Case | Constraint 2 | Constraint 3 | Constraint 4 | Constraint 6 |
|---|---:|---:|---:|---:|
| Jump 205 | 102.55 mm | 89.98 mm | 115.05 mm | 178.76 mm |
| Jump 204 | 69.36 mm | 66.07 mm | 61.10 mm | 168.73 mm |
| Dance 203 | 44.40 mm | 58.66 mm | 73.62 mm | 80.07 mm |
| Dance 204 | 62.09 mm | 61.10 mm | 68.45 mm | 45.29 mm |

These are maximum FK errors, not action-quality ratings. None passes. More guidance does not monotonically improve constraint accuracy. Native mesh floor and adjacent rotation diagnostics are retained separately, including cases where floor depth improves while boundary accuracy worsens. No seed/setting was cherry-picked into the production path.

## Artifacts and limits

[Local report](http://127.0.0.1:8767/reports/boundary-guidance-v1/review.html) shows all results and filters by case. It links exact NPZ/GLB files, records and audits; UI filtering was verified. `feature-capture.npz` retains normalized observed/returned features and separately decoded positions. Each case retains source guide, compiled constraints, seed, encoder provenance, BVH, preview and raw output hashes. Preview and checkpoint licenses are included in the report folder. No new game-engine check was needed for this diagnostic: existing native export code was checked directly against every source frame, and these candidates are not promoted game assets.

This is a development study of two known descriptions and two source rig families, not held-out action coverage. Baseline full resident-encoder equivalence, prompt correctness, original source timing compatibility, dynamics, contact validity and independent animator cleanup-time evidence remain unresolved. The full project goal stays active.

## Next substantive comparison

Build the pinned official `MotionCorrection` extension and apply its deterministic postprocessor to the exact retained raw samples. Its code explicitly consumes full-body keyframes, which the raw learned model need not satisfy. Keep raw and processed outputs distinct, audit pose boundaries, transition derivatives and skin contacts, and compare against the existing splice and clearance candidates.

The package is currently unavailable (`find_spec('motion_correction')` returned None). CMake, MSVC, GCC and Clang were not available through the checked toolchain paths; the usual Visual Studio/MSYS directories were absent. The [official build script](https://github.com/nv-tlabs/kimodo/blob/main/setup.py) supports a Windows MinGW path; the pinned local `MotionCorrection/CMakeLists.txt` requires C++17, Python development files, pybind11 2.11.1 and Eigen 3.4.0. Prefer a project-local reproducible toolchain and verify dependencies/licenses. Do not use an unverified community wheel or change the checkpoint merely to work around a missing build dependency. Evaluate this existing upstream correction before deciding a trained editor is necessary.
