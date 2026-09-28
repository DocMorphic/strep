# Shortest reproducible baseline path

**Execution update:** Read [next-steps.md](next-steps.md) first for the installed environment, verified checkpoint load, current commands, and gated-access blocker. This document retains the original planning rationale; next-steps.md supersedes its installation and implementation status.

## 1. Resolve access and memory before large downloads

The diffusion GPU requirement looks compatible with this RTX 3070 Ti when the text encoder is offloaded. The complete unchanged encoder does not fit comfortably in this laptop's 16 GB system memory. Do not treat the upstream “below 3 GB VRAM” statement as a total memory requirement.

Preferred baseline candidate: an existing 24 GB NVIDIA GPU machine with 32 GB+ system RAM, keeping the entire pipeline local to that machine. Alternatively test a larger-RAM CPU text-encoder host. No service is selected; before renting anything, quote current GPU/hour, estimated setup + generation + retry hours, storage, and transfer costs with an explicit spending limit.

For this laptop, an exact embedding cache for the fixed prompts could decouple encoding from diffusion using the upstream `load_model(..., text_encoder=...)` injection point. Create it on a feasible machine with unchanged encoder weights, dtype, prompt normalization, and batch size one; record all hashes. This adapter is future work, not implemented here. It does not satisfy arbitrary new offline prompts. Quantized or substituted encoders belong in a separate comparison condition.

The [official install guide](https://research.nvidia.com/labs/sil/projects/kimodo/docs/getting_started/installation.html) requires approved access to [Meta Llama 3 8B Instruct](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct). User completes that account step and local `hf auth login`. Never paste credentials into chat or project files. No default token/cache was found here; access through another configuration was not checked.

## 2. Install an isolated environment on the chosen machine

Use Python 3.10 or 3.11 (upstream installation examples use 3.10; prefer this over the overly broad `>=3.8` package metadata). With uv available, a project-local environment can be created using `uv venv --python 3.10 .venv`; this may download Python. Install the appropriate CUDA-enabled PyTorch wheel from the [official selector](https://pytorch.org/get-started/locally/), then install the pinned `vendor/kimodo` base package with `uv pip install --python .venv/Scripts/python.exe -e ./vendor/kimodo` on Windows (adjust the interpreter path on Linux).

These are proposed setup steps, not commands executed in this session. Do not install the demo/SOMA mesh extras for the first source-skeleton smoke test. Verify `torch.cuda.is_available()`, device name, and an actual CUDA tensor operation. Save `pip freeze`/uv lock, Python/PyTorch/CUDA versions, and hardware report. Inspect native MotionCorrection build requirements if the upstream-cleanup condition needs them; a failure there must not erase the unprocessed smoke result. Native Windows compatibility has not been demonstrated.

## 3. Stage immutable models and prove offline loading

Use the repo IDs and exact revisions in `benchmarks/sources.lock.json`. Download the motion checkpoint to `models/checkpoints/Kimodo-SOMA-RP-v1.1`, using Hugging Face `snapshot_download(..., revision=...)`. Download the exact LLM2Vec base, adapter, and gated Llama dependency into a dedicated cache, including tokenizer/config files and transitive adapter base dependencies. Record file hashes. Merely pinning the top-level checkpoint is insufficient.

The upstream wrapper loads adapter base dependencies by repository name; inspect the installed Transformers/PEFT resolution and dedicated cache refs to ensure all resolve to the pinned revisions. Do not modify weights or silently update cache refs. The code supports `CHECKPOINT_DIR`, `TEXT_ENCODERS_DIR`, and `HUGGINGFACE_CACHE_DIR`; use these only after validating how adapter dependencies resolve. The planner assumes a correctly populated dedicated Hugging Face cache for encoders and a local checkpoint directory for motion.

Set `TEXT_ENCODER_MODE=local` to prevent automatic encoder-server probing. Set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` for scored runs; `LOCAL_CACHE=True` alone is insufficient because upstream falls back to network if cache lookup fails. Validate a run with network unavailable. Initial package/model acquisition needs internet; final inference should not.

## 4. Smoke test before the grid

On hardware with enough RAM, in an activated environment and from this project root:

```powershell
$env:TEXT_ENCODER_MODE = 'local'
$env:TEXT_ENCODER_DEVICE = 'cpu'
$env:CHECKPOINT_DIR = Join-Path (Get-Location) 'models/checkpoints'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:LOCAL_CACHE = 'True'
kimodo_gen 'A person runs steadily forward in a straight line.' --model Kimodo-SOMA-RP-v1.1 --duration 2 --seed 11 --num_samples 1 --diffusion_steps 100 --no-postprocess --output runs/smoke/attempt-001/source/motion
```

This deliberately saves NPZ first without optional export/postprocessing dependencies. Capture logs, exit code, time, memory, and any failure with `benchmarks/run-record.template.json`. Record a separate attempt on retry. On a sufficient-memory GPU, the encoder can instead run on CUDA; record the resulting placement as an experimental detail and check reproducibility.

Validate array shapes, finite values, frame count, FPS, actual skeleton/joint names, rest pose, root motion, and foot contacts. Source code uses SOMA77 I/O despite the checkpoint card's 30-joint internal description. Then test `--bvh --bvh_standard_tpose`, inspect a preview, and separately test upstream cleanup.

## 5. Freeze the scene and run the four cases

Run `node scripts/plan-baseline.mjs` to validate files and write the 50-job grid. `generated-plan.json` provides argument arrays, not a tested executor. It performs no downloads or inference. Commands have separate actor/seed/condition paths, explicit model/seed/durations, and NPZ/BVH output settings. Implement a logging executor using argument arrays (not string-built shell commands) and the run-record template when the environment is ready.

Calibrate CesiumMan scale, facing, bone mapping, and hand offsets. Freeze `v0.json` scene targets before measuring. The current targets are provisional. Run every seed, including failures. For high-five, assemble A and B in the shared scene and measure actual contact; independent plausible gestures do not establish interaction success. The unchanged model does not emit box motion, so record missing attachment and object awareness explicitly.

## 6. Transfer, measure, and import

Preserve each source NPZ/BVH. Retarget copies to the character and separately implement deterministic corrections, root/contact extraction, gameplay markers, and preview exports. These components are not yet built. Evaluate metrics from `research-plan.md`; keep unmeasured values null. Choose the engine before an import pass; Godot is available but has not been selected. BVH alone is not a finished engine-ready skinned character asset.

Only after a completed baseline decide whether to invest in a learned editor or scene-aware model. Fixed-prompt caching, a successful smoke test, or a source-skeleton demo does not prove the full offline authoring product.
