# Execution plan and status

**Current milestone complete:** two individual source-space controls tested at three levels, including held-out seed 55. Three torso levels and compact arm range qualify; wider arms retain loop failures. [Control results and reproduction](control-calibration-results.md) · [Viewer](http://127.0.0.1:8767/reports/control-calibration-v1/viewer.html). Thirty-six tests pass and 39 character exports validate.

**Next proposed experiment:** improve large-arm seams with a new reserved seed; solve target angles directly on each rig; evaluate combined controls and blind human naturalness. Keep target foot placement and engine import open. Automatic agility/strength/stamina mappings are not supported by this study.

Earlier baseline, loop and stance experiments are preserved. The following setup phases are archival; their pending statuses describe the time they were written and are superseded by the current result above. Do not restart downloads or rerun the old grid unnecessarily.

## Phase 1 — local foundation (completed)

- Created isolated `.venv` with Python 3.10.21, PyTorch 2.10.0+cu128, and pinned upstream Kimodo source. Package snapshot: `benchmarks/environment.windows.txt`.
- Verified floating-point matrix multiplication on RTX 3070 Ti with CUDA synchronization.
- Downloaded the exact 1,133,185,036-byte motion weight file and supporting checkpoint files; all 11 files hashed in `models/manifest.json`.
- Loaded the unchanged motion checkpoint on CUDA: 283,281,777 parameters, SOMA30 internal / SOMA77 output, 30 fps, 1,175,117,312 bytes allocated GPU memory at load. This was **load-only**, with a rejecting encoder placeholder: no text was encoded, no motion was sampled, and no substitute embeddings were used.
- Implemented attempt recording, offline environment settings, checkpoint hashing, fixed prompt-cache tooling, motion validation, numeric proxies, root CSV, predicted foot-contact intervals, and a standalone HTML viewer.
- Verified the viewer's play/pause, frame slider, and side view in the browser. Preview source is a bundled upstream example, not generated here. Legacy 30-joint example files omit root/local arrays, so those are explicitly derived in memory for inspection only.
- Exported that labeled legacy example through a separate derived NPZ to standard-T-pose BVH and back to NPZ: 150 frames, 77 joints, maximum pelvis round-trip error 0.000000954 m. This tests skeleton-format conversion, not target-rig transfer or engine import.

## Phase 2 — local original-precision encoder experiment (in progress)

The user completed Hugging Face login. An authenticated request to the pinned Meta Llama config succeeded; see `reports/doctor-online.json`. The former access blocker is resolved. Pinned base weights and both adapters are being acquired into the project cache. A running one-shot pipeline waits for acquisition, attempts five fixed prompt embeddings, and then attempts run-loop seed 11:

- Stage/outcome: `reports/first-local-run.json`
- Acquisition log: `reports/encoder-download.log`
- Encoder log and memory outcome: `reports/encoder-offload.log` and `.json`
- Cache, only if successful: `models/prompt-cache-v0-offload/manifest.json`
- Generation attempt and preview: path recorded by the pipeline on completion.

Do not start a second downloader or encoder while this pipeline is running. To inspect the current stage:

```powershell
cd C:\wassup\strep
Get-Content reports\first-local-run.json
Get-Content reports\encoder-download.log -Tail 5
```

The encoder has roughly 16 GB of base weights and this laptop has only ~4 GiB available RAM. Full CPU loading retains its conservative 20 GiB available-RAM guard. The new experimental route streams CPU MNTP adapter merges one matrix at a time into derived cache files, leaves the supervised adapter active, and uses Accelerate disk offload for GPU execution. Original BF16 base precision, PEFT's FP32 adapters, upstream tokenization, pooling, and forward computation are retained. No quantization or training is used.

The normal upstream two-adapter factory failed a synthetic disk-dispatch test with a PEFT offload-index KeyError. The external streamed loader avoids that factory path and does not edit vendor source. Two small-model comparisons passed exact tensor equality: resident vs dispatched wrapper, and resident PEFT vs streamed merge plus active adapter. These do **not** establish full 8B numerical equivalence. Outputs must be labeled as an experimental original-precision execution variant until that comparison is possible.

After acquisition finishes, the standalone guarded encoder command is:

```powershell
.venv\Scripts\python.exe scripts\guarded_encoder.py
```

The supervisor stops the encoder if available RAM drops below 600 MiB or its working set exceeds 7 GiB. The exporter records source/model hashes, placement, precision, validation scope, and batch size one, then checks tensor serialization round-trip. It preserves previous cache directories. If the cache succeeds, one motion attempt can be run with:

```powershell
node scripts\plan-baseline.mjs
.venv\Scripts\python.exe scripts\strep.py doctor --embeddings models\prompt-cache-v0-offload\manifest.json
.venv\Scripts\python.exe scripts\strep.py run --job run_loop/seed-11/unprocessed/actor-A --embeddings models\prompt-cache-v0-offload\manifest.json
```

The replayer rejects unknown prompts and mismatched benchmarks, source revisions, model revisions, or tensor hashes. Before claiming an unchanged full-system baseline, compare against resident upstream encoding on a suitable host and compare cached/live conditioning with the same device/seed. Those full-model comparisons remain pending. This cache is for the fixed study only. No cloud service has been selected or purchased.

The first attempted run is recorded under `runs/run_loop/seed-11/unprocessed/actor-A/attempt-001/record.json` as **blocked at preflight**, not a motion-generation failure. Later attempts always get a new directory.

## Phase 3 — run and score all four cases

After the first validated NPZ/BVH: freeze scale/contact targets, execute all five seeds, compare source vs transferred copies, and inspect each failure. The recorder currently runs one selected job at a time. Add resumable grid execution only after the first real run succeeds.

Upstream cleanup needs `MotionCorrection` native bindings. Initial installation failed because CMake/C++ tools are absent; inference installed using the official `SKIP_MOTION_CORRECTION_IN_SETUP=1` switch. The source remains unchanged. Build and test the native library before the cleanup condition. Do not silently label unprocessed output as cleaned.

Tests cover malformed/non-finite motion, invalid rotations, absent contact vs zero slide, known slide speed, contact ordering, event boundaries, source preservation, blocked-run retry records, output path containment, cache integrity/copy isolation/unknown prompts, and explicit legacy derivations. A separate manual integration check covers legacy-example BVH conversion. Real generation and cached-vs-live numerical equivalence remain untested.

## Phase 4 — asset workflow

Implement CesiumMan rest-pose/bone mapping and scale calibration, retargeted copies, interaction scene assembly, deterministic contact/transition correction, and event extraction. Then choose and test the target engine. High-five remains two independent actor generations; the box has no generated object trajectory. Report those limitations as failures/unsupported outputs.

Do not begin model training until this comparison demonstrates specific remaining failures. Preserve the broader locomotion/object/social/combat and rough-clip-editing product scope.
