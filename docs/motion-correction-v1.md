# Native motion correction experiment, 2026-09-27

The pinned NVIDIA postprocessor successfully fits all four retained boundary failures: maximum SOMA30 joint error falls from 44–103 mm to 0.0016–0.0031 mm, with global rotation errors below 0.0003 degrees. This establishes a useful deterministic pose-fitting component. It does not establish clean contacts: full correction increases native skin penetration and often increases predicted-support sliding. Production defaults remain unchanged.

## Local build

Built the unmodified `vendor/kimodo/MotionCorrection` C++ extension with portable [w64devkit 2.10.0](https://github.com/skeeto/w64devkit/releases/tag/v2.10.0) and [CMake 3.31.8](https://github.com/Kitware/CMake/releases/tag/v3.31.8), downloaded from official releases and checked against published SHA256 digests. Tools live under `.cache/motion-correction-toolchain`; no system installation or persistent PATH change. Source dependencies are pybind11 2.11.1 commit `8a099e44b3d5f85b20f05828d919d2332a8de841` and Eigen 3.4.0 commit `3147391d946bb4b6c68edd901f2add6ac1f31f8c`, fetched from the upstream CMake-declared repositories. Eigen uses the upstream EIGEN_MPL2_ONLY definition. Retained license files include NVIDIA Apache-2.0, pybind11 BSD, Eigen MPL2 and MinGW runtime notices.

The importable extension lives in `.cache/motion-correction-package`, separate from normal Studio imports. DLL imports are python310.dll, KERNEL32.dll and msvcrt.dll. Build warnings are preserved in `reports/motion-correction-build.log`. This is a local AVX/CPython 3.10 build, not a portable signed installer or cross-machine validation.

`scripts/build_motion_correction.ps1` successfully rebuilt offline using retained source dependencies. Reconfiguration/relinking changed the binary SHA; byte-reproducible binaries are not claimed. The second build produced exactly the same four guided motion NPZ files as the first. V2 initially copied the initial build manifest; `rebuild-provenance.json` and `rebuild-replay.json` explicitly correct that metadata, and the second extension binary is retained. Future runs capture the loaded extension SHA directly. No vendor source or checkpoint changed.

## Matched comparison

`study_motion_correction.py` takes the four exact baseline NPZ files from `boundary-guidance-v1`, selects the SOMA30 local rotations and four contact channels, applies `post_process_motion`, and expands through the upstream SOMA77 export path. Contact threshold is 0.5 and root margin is 0.04 m. Original contact labels remain unconfirmed model predictions. Stale smooth-root data is not copied to corrected outputs.

V1 compares raw, contact cleanup without pose constraints, and guided correction. V2 compares raw, guided correction, and guided correction with solver contact input suppressed. Each corrected case is computed twice and is exactly deterministic. Both studies have 12 exported outputs, including duplicated raw/control outputs; they represent four known source/seed cases, not 24 independent motions. There is no new inference, encoder work or training. Applying correction after export is not a claim of equivalence to upstream multiprompt generation with per-segment correction and re-encoding.

| Case | Raw boundary error | Guided boundary error | Raw floor depth | Guided + contacts floor | Guided pose-only floor |
|---|---:|---:|---:|---:|---:|
| Jump 205 | 102.55 mm | 0.00303 mm | 0.95 mm | 20.50 mm | 12.29 mm |
| Jump 204 | 69.36 mm | 0.00303 mm | 4.50 mm | 40.24 mm | 9.81 mm |
| Dance 203 | 44.40 mm | 0.00159 mm | 14.18 mm | 49.03 mm | 21.78 mm |
| Dance 204 | 62.09 mm | 0.00159 mm | 14.24 mm | 35.66 mm | 17.76 mm |

Both guided modes have the same boundary errors. All corrected variants fail the existing 5 mm native surface-floor screen. Dance guide anchors themselves penetrate by roughly 7.3 mm after native expansion, so exact anchors and a 5 mm skin-floor requirement conflict for those targets. Jump anchors clear the floor; remaining jump penetration occurs between them. Contact cleanup alone also worsens jump boundary accuracy and skin depth.

The pose-only ablation reduces penetration compared with full guided cleanup, but this does not prove accurate contacts or remove all regressions. For jump 205, full correction raises maximum boundary joint steps from 16.07 to 19.18 degrees; pose-only is 18.60 degrees. Predicted-support centroid speeds and sample counts are recorded per foot, along with root displacement, speed and acceleration. Some support samples are sparse (one left-foot step for jumps). No physical realism claim follows from these proxies.

## Verification and limitations

`verify_motion_correction.py` independently reconstructs hierarchy FK in NumPy and rotation geodesics in SciPy. It compares targets on SOMA30 and export geometry on SOMA77. Those hierarchies must not be conflated: extra helper/terminal bones and relaxed poses make a slice of SOMA77 world transforms a different reference. An initial audit made that mistake; its failed/intermediate logs are retained. The corrected audit reproduces the previous raw boundary measurements and verifies all guided targets. Another initial audit incorrectly used an integer-only sampler for half frames; it now uses the existing glTF interpolation sampler. No output data or tolerance was altered to fix those audit errors.

All 24 exported GLBs validate with zero errors and warnings. Every frame, all eight skin weights, and all 18,056 vertices at integer and half frames are audited. Source NPZ bytes and predicted contact arrays are preserved; HTTP-delivered GLBs match disk hashes. Five focused tests pass in 7.20 seconds with four existing Torch deprecation warnings, including compiled correction on all four sources and the hierarchy-space regression. No full-suite or new engine-import run is claimed. These remain diagnostic candidates, not promoted engine assets.

The [comparison viewer](http://127.0.0.1:8767/reports/motion-correction-v2/viewer.html) exposes all four stages at the same frame. Current evidence covers two known descriptions and two source rig families. It does not cover held-out actions, target-rig transfer of the new corrections, action semantics, animation dynamics or independent animator cleanup time.

Next: use verified pose fitting as an explicit stage, combine it with mesh-aware contact constraints and target feasibility checks, then measure retargeted section boundaries against the earlier splice/clearance candidates. Preserve exact anchors only where they are feasible; report conflicts instead of hiding them. Keep broader scene/partner, style, offline installation and held-out release gates open.
