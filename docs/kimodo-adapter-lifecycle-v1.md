# Kimodo adapter checkpoint lifecycle v1

Small adapter weights, AdamW moments and Torch random-generator state can now
be saved and restored without serializing Python objects. A numerical canary
on the pinned Kimodo denoiser reproduces two interrupted updates exactly while
leaving its frozen base unchanged. This is training infrastructure validation,
not a trained motion model or evidence of better animation.

## Format and validation

`scripts/kimodo_adapter_state.py` writes a fresh directory containing
`adapter.safetensors`, `training.safetensors` and a manifest written last.
The first file contains only named FP32 low-rank factors; the second contains
standard AdamW counters/moments and optional Torch CPU/CUDA generator state.
Both have SHA-256 checksums. Existing output directories are refused.

The manifest binds exact model and vendor revisions, checkpoint hash,
configuration hash, live base-state fingerprint, objective identifier, data
manifest hash, adapter names/shapes/scales, completed step and sequential cursor.
The loader recomputes the live frozen base fingerprint and requires every
installed adapter to be included. Matching metadata alone cannot load weights
onto a changed base. The caller must independently verify configuration, data
and source inputs before supplying their bindings.

All tensors and metadata are checked before application, including exact factor
order, finite values, nonnegative second moments and consistent optimizer
counters. The loader backs up adapter weights, optimizer state and ambient
Torch RNG and restores those backups if application fails. Both quality and
release approval flags must remain false. Studio does not load this format.

The supported optimizer is one FP32 standard AdamW group with explicit
nonfused/noncapturable settings. Resume requires the same recorded Torch
version, thread count, deterministic policy, transformer fastpath setting,
TF32 setting and cuBLAS workspace configuration. RNG restoration also requires
the same generator/device layout. These checks are necessary conditions, not
a promise of identical results across GPUs or processes. Weight-only loading
does not require an identical runtime.

Only Torch CPU and already initialized CUDA generators are captured. Python,
NumPy, shuffled samplers, loader workers, schedulers, gradient accumulation and
mixed-precision scaler state are not supported. The optional cursor records
`epoch` and `next_example` for a sequential stream; this is not a corpus trainer
or a complete data-admission workflow.

## Real-checkpoint numerical experiment

`scripts/audit_kimodo_adapter_resume.py` runs offline under the shared model
worker lock, preserves every fresh attempt and archives imported methods.
It checks the acquired checkpoint files before and after execution.

The final local attempt is `reports/kimodo-adapter-resume-canary-v2`.
It uses Kimodo-SOMA-RP-v1.1 revision
`6c9233af1180b8151e3c4703477104af5dce9dd5` and vendor commit
`58e781898b3d7e328a676a75d3e338c45dce3ad9`, PyTorch 2.10.0+cu128,
CUDA 12.8 and an RTX 3070 Ti Laptop GPU. The 283,281,777-parameter base stays
frozen; 64 feedforward modules receive rank-8/alpha-8 residual adapters with
1,572,864 trainable parameters.

Inputs are Gaussian tensors of batch 1 and 30 frames, a zero text tensor,
timestep 500 and heading zero. The target is a zero feature tensor, **not valid
motion supervision**. Seed 1236 and deterministic FP32 settings are declared
before execution. AdamW uses learning rate 0.0001.

Three updates precede the save. Two reference updates follow it. The adapters
are removed, new adapters and a new optimizer are created with a deliberately
different seed and learning rate, and the saved weights, moments, hyperparameters
and Torch RNG are restored. The two updates are replayed. This is five logical
steps and seven physical optimizer updates per attempt. The earlier v1 attempt
is retained separately; v2 additionally verifies the live base binding.

| Final v2 check | Result |
| --- | --- |
| Replayed inputs and losses | Exactly equal to reference steps 4 and 5 |
| Maximum factor difference | 0 |
| Maximum optimizer-state difference | 0 |
| Frozen base gradients | Absent |
| Restored base fingerprint | Exactly unchanged |
| Checkpoint inputs and imported methods | Unchanged |
| Peak allocated GPU bytes | 1,405,761,024 (about 1.31 GiB) |
| Peak reserved GPU bytes | 1,428,160,512 |

Reference and replay losses are 0.4731941223144531 and 0.43277591466903687.
These numbers measure a synthetic objective; their decrease says nothing about
motion quality. The saved step-3 factors occupy 6,306,056 bytes, training state
12,637,272 bytes and manifest 15,344 bytes. Timing excludes a complete training
or generation pipeline and is not a throughput estimate.

The GPU replay uses the same base instance in one process with freshly installed
adapters and optimizer. Fresh-process, cross-device and real-corpus resume
remain untested. No prompts, clips or reserved release seeds were generated.
All numeric adapter artifacts remain local and unapproved. Any future model
distribution must satisfy the NVIDIA model terms; those terms do not grant
rights to raw training data.

## Source checks and next work

44 local CPU tests pass: 10 adapter component tests, 25 native-target/objective
tests and 9 checkpoint lifecycle tests. Lifecycle checks include interrupted
continuation on an independent tiny base copy, exact inputs/weights/moments,
binding/rank/scale/checksum rejection, corrupt moment and factor rejection,
transactional rollback after an RNG application failure, live-base rejection,
runtime-policy rejection, weight-only loading and refusal to invent optimizer
state or quality approval.

Hosted run 37005535386 passed all four Windows/Linux jobs for the preceding
commit. This change adds safetensors 0.8.0 and the lifecycle test file to the
separate CPU adapter jobs. The existing 169 geometry test files and 14 JS
suites are unchanged; their full local suite was not repeated for these
standalone modules.

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_kimodo_adapter_probe.py tests/test_kimodo_denoising_target.py tests/test_kimodo_adapter_state.py
.venv\Scripts\python.exe scripts/audit_kimodo_adapter_resume.py reports/kimodo-adapter-resume-canary-new
```

The canary needs the separately provisioned pinned model and CUDA runtime.
CPU tests need neither model weights nor vendor assets. Next work is reviewed,
licensed corpus admission, a real trainer with predeclared learning curves,
fresh-process resume and unchanged-baseline comparisons for improvement and
forgetting. Object, partner and finger representation work and human cleanup
evidence remain separate requirements. All 14 release capabilities remain
unapproved and the single broad project goal stays active.
