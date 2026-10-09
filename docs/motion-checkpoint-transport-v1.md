# Exact checkpoint transport for offline motion generation

The optional `cuda-streamed` transport creates large learned Linear and MultiheadAttention layers on CUDA and reads the pinned motion checkpoint one tensor at a time. Upstream architecture, float32 weights, statistics, diffusion, skeleton conversion and CPU positional-buffer arithmetic remain unchanged. This avoids constructing a complete second CPU checkpoint state. It does not quantize, prune, train or replace the model.

`generate_actions.py` keeps its established upstream loader by default. To select the transport in an isolated sequential model worker, after preparing the exact request's conditioning directory:

```text
python scripts/generate_actions.py REQUEST.json EXISTING_BATCH_DIR --checkpoint-transport cuda-streamed
```

Each new attempt records the transport receipt and implementation digest. Existing generated attempts retain their original provenance. Arbitrary action descriptions, timing, profiles, constraints and seeds use the existing request/conditioning path; transport adds no prompt whitelist. The studies below reuse existing conditioning and do not demonstrate new text encoding or full resident 8B encoder equivalence.

## Integrity and isolation

The loader verifies the pinned vendor revision, model revision and all acquired model-file hashes before and after loading. It checks the complete checkpoint key population, exact shapes/dtypes, aliasing and per-tensor byte limits before mutation, rechecks the file after header validation, compares every copied tensor's bits and checks the final checkpoint hash. The pinned payload has 408 tensors, 1,133,127,108 logical bytes and a largest tensor of 16,777,216 bytes. No dtype conversion or partial checkpoint acceptance is permitted.

The `pread` backend must be available; there is no silent mapped-file fallback. This implementation requires PyTorch 2.10 and Safetensors 0.8, as tested locally. The underlying APIs are documented in [PyTorch Linear](https://docs.pytorch.org/docs/main/generated/torch.nn.Linear.html), [Safetensors loading](https://huggingface.co/docs/safetensors/index), and the [Safetensors Python implementation](https://github.com/safetensors/safetensors/blob/main/bindings/python/py_src/safetensors/torch.py).

Constructor interception is temporary and restricted to a single Python main thread. Explicit allocation arguments remain explicit; module classes and default device/dtype do not change. CPU positional encoding must remain on CPU during construction: computing sine/cosine on CUDA could change its bits. All intercepted methods are restored after success or exceptions. This is an opt-in worker technique, not a thread-safe general-purpose loader for a shared server process.

## Validation on the pinned checkpoint

All **22 focused tests pass**, including a real tiny CUDA forward comparison. CPU fixtures cover full checkpoint/forward parity, nonpersistent buffers, scalar buffers, float64 adjacent/subnormal values and signed zero, complete preflight failures, changed-file/alias rejection, constructor restoration, worker/thread restrictions, upstream failure restoration and explicit generation backend selection. Hosted CPU runs skip the CUDA smoke. The new module is included in both Windows and Linux adapter CI; the separate NoTorch inventory remains unchanged.

The final combined check passes **39 tests**: these 22 plus 17 existing action-request regressions, including unlisted free-text motions and explicit sequences. Four upstream TorchScript deprecation warnings remain; no checks fail. The separate model-free inventory still contains 413 Python modules and 41 Node suites. Hosted CI for this new change remains pending until it runs on the published commit.

A fresh load-only worker independently reads all 408 original tensors on CPU and compares complete byte digests with the final CUDA model. It also recomputes both positional buffers through the upstream CPU implementation and verifies exact equality. The model retains 283,281,777 parameters, its 30-joint internal/77-joint output skeletons and 30 fps. Load time is 13.594 seconds; verification takes 17.969 seconds including loading. Sampled process-tree peak is 963,272,704 bytes; CUDA peak allocation is 1,175,973,376 bytes. Independent resource replay verifies all 38 observations and termination.

The initial load-only verifier looked for unwrapped keys in Kimodo's classifier-free-guidance wrapper and failed with `KeyError` after loading. The corrected fresh verifier follows `.denoiser.model`; the failed worker, log and 45 resource observations remain recorded. It does not weaken checkpoint matching to accommodate the wrapper.

A separate worker replays the four original unprocessed cases with seed 11: run, run-to-roll, box lift and high-five. Every field of every NPZ matches the earlier output bit for bit: 28 full array comparisons, no tolerance. Diffusion uses 100 steps, separated guidance `[2, 2]`, one sample, five transition frames and no postprocessing. Loading plus replay takes 40.469 seconds. Sampled process-tree peak is 1,621,659,648 bytes; peak CUDA allocation is 1,227,189,248 bytes. Independent resource replay verifies all 65 observations and exit zero.

Checkpoint revision: `6c9233af1180b8151e3c4703477104af5dce9dd5`. Checkpoint SHA-256: `ef0a0ca45a6089ab4532dde609785771ae3f38755b4ae6cf314b0213e07cd4a3`. Full tensor/buffer digest report SHA-256: `210e35b8bdeb1c68784d59754a493858f361d859f6ac72520ab8121e2be15557`. Four-case comparison SHA-256: `ba64af3a94f0425d68101b41bb260eecaac66ce8f9eff8e5f654b30aa016d354`.

## Wider generation CLI replay

The actual `generate_actions.py --checkpoint-transport cuda-streamed` CLI completes the unchanged seven-request development batch with seeds 11 and 22: jumping/landing, crawling, dancing/turning, waving, kicking, getting up, and run/roll/standing. It uses the existing exact ActionEncoder cache. A separate fresh process verifies all **14 clips / 98 complete motion arrays** against their historical outputs, including dtype, shape and every byte, plus prompt/request, seed, model, timeline, diffusion, guidance, postprocessing and constraint provenance. Older records predate explicit empty-guide and default-zero-heading fields; those are interpreted using the actual default model-call behavior. No fields are sampled or compared with tolerance. This study exercises the authoring CLI and receipt persistence, not newly encoded prompts or calibrated styles/contact constraints.

The first guarded attempt stops at 603,652,096 available bytes, below the unchanged 600 MiB reserve, after six completed clips. Its sampled process-tree peak is 1,589,628,928 bytes. The interrupted wave attempt remains incomplete; it is never treated as a valid result. After host headroom recovers, a fresh guarded resume reuses the six completed records and creates a new wave attempt. The 18 earlier record/NPZ/BVH files remain byte-identical. Resume exits zero after 108.984 seconds, with a sampled peak of 1,656,680,448 bytes. Independent resource replay checks all 96 first-attempt and 106 resume observations, including the stop, admission and exit decisions. No other application is closed or killed.

The independent fourteen-clip audit exits zero with seven resource observations and 53,055,488 bytes sampled peak. Its comparison SHA-256 is `89d94a57dfc9a166e2ba07ed02cbde3ac01f42dc223813f923858af45e503c2e`. Guard protocol hashes: first CLI attempt `80cfb7ba86ebcca23f84c482841c8920a23807b220290ead8723fff29512b2e0`, resume `98fd7d09d7c71b01ad905195740ea5211f1f78fc56b753974b1340992443da72`, independent output audit `4f705f4e07853eaaa673ddebe1f6a43cc80c47366e682b8c6aa6bac44ad47fd2`. The resume keeps the original failed protocol/log/trace and unfinished record.

## Scope

These are finite sampled memory observations on one laptop, not a controlled comparison with the upstream loader or a guaranteed memory bound. The historical upstream load report gives post-load RSS rather than a sampled peak; it is not an interchangeable baseline. Full Studio generation retains its 4 GiB estimate plus 600 MiB reserve. Native contact fitting/auditing retains 2 GiB plus 600 MiB, with unchanged runtime guards and retention gates. These smaller bounded loading/replay probes do not change either admission policy.

No existing animation, preview, model weight or human rating is replaced. Bitwise reproduction preserves the original clips' defects, including single-character object/partner limitations. Contact quality, broader held-out actions/rigs/objects/partners, calibrated controls, transitions, engine and human cleanup evidence still require validation. All fourteen release capabilities remain unapproved and the full-project goal stays active. Detailed workers, protocols, outputs, tensor/array digests and resource traces stay under ignored `reports/cuda-motion-transport-v1/` and `reports/cuda-motion-transport-v2/`.
