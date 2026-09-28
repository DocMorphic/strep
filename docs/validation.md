# Setup validation — 2026-09-24

Current update: all encoder models acquired, five prompts encoded locally, and first new motion generated and structurally validated (120 frames / SOMA77 / NPZ and BVH). Eleven tests pass, including Windows worker accounting and termination. See `first-run.md` for evidence, loop failure, and memory-report correction. Earlier setup milestones below are historical.

## Execution follow-up

- Access update: local Hugging Face authentication and gated Llama access now verified. Encoder acquisition and the guarded first-clip pipeline are in progress; use `reports/first-local-run.json` for live state.
- Original-precision offload wrapper and streamed CPU PEFT merge both exactly matched resident GPU output on a synthetic two-layer model. See `reports/offload-wrapper-probe.json`. Full 8B equivalence remains untested; initial direct upstream disk-dispatch factory failed (preserved in `reports/offload-factory-probe.log`).

- Python 3.10.21 / PyTorch 2.10.0+cu128 installed; floating-point CUDA test passed. An initial ad-hoc integer-matrix probe used an unsupported CUDA dtype; the float32 check corrected the probe and passed.
- `uv pip check` reports all 84 installed packages compatible. Native MotionCorrection remains absent; official inference-only setup switch used after a missing-CMake build failure.
- Exact motion checkpoint acquired and hashed; offline GPU load-only probe passed, allocating ~1.1 GiB. This is not an inference peak or generated animation.
- Ten pipeline tests pass, including fixed-cache checks and legacy-example handling. The cache exporter has not run against the real gated encoder; full cached/live generation equivalence is pending.
- Local viewer inspected in browser, including pause, frame scrubbing, and side view. Source is a labeled upstream example.
- First baseline attempt preserved as blocked at preflight; gated access is unavailable and CPU encoder memory guard fails.
- Scripts compile successfully and upstream vendor working tree remains unchanged.
- Legacy example conversion required explicitly deriving missing local rotations/root positions into a separate `legacy-derived.npz`. Standard-T-pose BVH round-trip then passed (150 frames / 77 joints; max pelvis error 9.54e-7 m). Original source file preserved.

Historical initial validation follows; current state is in `next-steps.md`.

Executed `node scripts/plan-baseline.mjs` successfully using Node.js v24.13.1.

- Official Kimodo checkout matches `58e781898b3d7e328a676a75d3e338c45dce3ad9` and has no working-tree changes.
- CesiumMan SHA-256 matches its acquisition manifest.
- GLB 2 header, declared length, JSON chunk, skin/mesh binding, and joint references validated.
- Character: 438,044 bytes, one skin, 19 joints, one supplied third-party animation.
- Benchmark/model/seed checks passed; prompt sentence counts match segment durations.
- Plan generated 50 unique jobs representing 40 case-condition trials, all marked not run.

The first plan-writing attempt encountered a Windows sandbox ownership restriction on a directory created by the approved download. Re-running the same local validator under the user account succeeded. No benchmark command was executed.

Not validated: Python/PyTorch environment, checkpoint loading, gated access, RAM/VRAM peaks, source motion, visual animation quality, native correction bindings, BVH export, retargeting, contact/penetration metrics, or engine import. A 19-joint fixture cannot support detailed finger animation assessment.
