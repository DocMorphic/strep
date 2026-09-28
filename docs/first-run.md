# First local generation — 2026-09-24

The laptop generated a new four-second running sample from text: 120 frames at 30 fps, SOMA77 skeleton, seed 11, 100 diffusion steps, no postprocessing. The unchanged motion checkpoint ran locally with cached original-precision text conditioning. This is an experimental encoder-loading variant, not yet a verified unchanged full-system baseline.

## Outputs

- [Preview](../runs/run_loop/seed-11/unprocessed/actor-A/attempt-002/inspection/preview.html)
- [Editable BVH](../runs/run_loop/seed-11/unprocessed/actor-A/attempt-002/source/motion.bvh)
- [Original NPZ](../runs/run_loop/seed-11/unprocessed/actor-A/attempt-002/source/motion.npz)
- [Run record](../runs/run_loop/seed-11/unprocessed/actor-A/attempt-002/record.json)
- [Inspection metrics](../runs/run_loop/seed-11/unprocessed/actor-A/attempt-002/inspection/report.json)
- [Loop endpoint comparison](../runs/run_loop/seed-11/unprocessed/actor-A/attempt-002/inspection/loop-seam.json)

Motion execution took 28.03 seconds including startup, preflight, and inspection. The denoising loop took about seven seconds. Summed process-tree working-set peak was 1.68 GiB; GPU peak was not measured. The preview was inspected at two side-view poses and left playing in the app.

## Observed limitations

Structural validation passed: finite positions, valid rotation matrices, matching arrays, 77 joints and six foot-contact channels. This is not an animator quality rating.

The sample is **not seamless**. After removing root translation, start/end joint RMS difference is 0.360 m, about 9.94 times the median adjacent-frame difference. This proxy has no heading alignment or cycle matching. Predicted-contact foot speed averages 0.0534 m/s, with p95 0.141 m/s. Maximum joint ground penetration is 0.00848 m; mesh collisions have not been assessed. Root movement is about 8.78 m forward with 0.40 m lateral drift.

The motion is on the source skeleton. Character retargeting, engine import, native cleanup, interaction contacts, and the remaining seed/case grid are pending. No training occurred.

## Encoder and reproducibility

All three pinned encoder repositories are acquired and hashed in `models/manifest.json`. Five fixed prompts were encoded offline in about 185 seconds including hash checks, streamed adapter merging, and inference. The BF16 base and FP32 PEFT adapters retain original precision; upstream tokenization, pooling and forward computation are reused. Derived MNTP merges are separate cache files. The supervised adapter remains active. No vendor source was edited.

The cache at `models/prompt-cache-v0-offload` passed exact serialization round-trip. Two synthetic small-model comparisons passed exact equality for the dispatch wrapper and streamed adapter loader. Full 8B resident equivalence and live-vs-cache motion comparison remain untested; do not claim those checks passed.

The first encoder supervisor incorrectly measured the Windows launcher rather than the worker, so **encoder peak RAM is unknown**. Its system-available-RAM branch remained active. The report records that correction. Process-tree accounting and termination are now fixed and tested using a real child process allocating 64 MiB. All 11 pipeline tests pass.

Next: run the remaining explicit cases/seeds, retain raw outputs and failures, then implement and compare deterministic loop/contact corrections and rig transfer. Preserve the broader action-generation and clip-editing scope.
