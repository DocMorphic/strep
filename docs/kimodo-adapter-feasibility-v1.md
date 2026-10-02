# Kimodo adapter gradient and memory feasibility

Checked 2026-10-02. A local rank-8 feedforward adapter probe completes on the
existing RTX 3070 Ti Laptop GPU, with the acquired Kimodo checkpoint unchanged.
This establishes a narrow gradient/allocation path for a future adaptation
experiment. It does not establish a trainer, learned improvement, scene-aware
generation or release approval.

## Why examine adaptation

The [breadth study](breadth-baseline-v2.md) and [profile response study](profile-response-v1.md)
retain action, floor, support and control-response failures. The latter's squat
and kick directional proxies fail across the transferred rigs. More UI controls
do not repair those generator failures. A small adaptation experiment is worth
testing, provided its targets have reliable motion quality and training rights.

[LoRA](https://arxiv.org/abs/2106.09685) freezes a base model and learns low-rank
residuals. Its published language-model results do not demonstrate motion quality
for Kimodo. This probe tests only whether that parameterization differentiates
on this checkpoint and fits this laptop.

## Exact local experiment

`scripts/kimodo_adapter_probe.py` loads only the local denoiser, without loading
the Llama text encoder or contacting an encoder service. It verifies every
acquired checkpoint file against the pinned manifest, verifies the vendor
checkout, archives the audit/backbone/loading sources, acquires the shared
worker lock and retains partial results on failure. A fresh output directory
is mandatory. No vendor or published checkpoint file is written.

The checkpoint revision is `6c9233af1180b8151e3c4703477104af5dce9dd5`, with
weights SHA-256 `ef0a0ca45a6089ab4532dde609785771ae3f38755b4ae6cf314b0213e07cd4a3`.
Vendor revision is `58e781898b3d7e328a676a75d3e338c45dce3ad9`.
The loaded module has 283,281,777 parameters, 369 motion channels and five
global-root channels. This count is from the instantiated denoiser, rather
than a rounded model-card figure.

Both stages' 16 transformer layers receive rank-8, alpha-8 residuals on
`linear1` and `linear2`: 64 modules and 1,572,864 adapter parameters, about
0.555% of the base count. Base parameters are frozen. A is randomly initialized;
B starts at zero. The initial output matches the base exactly. The modules and
original parameter trainability flags are restored even on an exception.

PyTorch's fused transformer evaluation can read the underlying linear weights
without calling the residual wrapper. The probe explicitly disables that
fast path in a restoring context, and a model hook rejects accidental use with
it enabled. This is an audit-only wrapper, not an integrated production
adapter loader, merge implementation or saved adapter format.

Inputs are batch-one FP32 Gaussian motion tensors, all-valid frame masks,
zero text features of shape `(1, 1, 4096)`, timestep 500 and zero first heading.
The installed backbone pads these features to its 50 text tokens. Seed 1234
controls synthetic allocation inputs and adapter initialization; it is not a
new animation-generation seed. The loss is the mean square of the prediction,
solely to exercise backward propagation. There is no clean motion target,
optimizer, optimizer state, update, checkpoint save or generation-quality score.

## Observed results

Actual worker handle 58511 completed. Evidence is retained locally in
`reports/kimodo-adapter-probe-v1/result.json`, including per-module gradient
presence, finiteness and norms, source/checkpoint hashes and before/after base
fingerprints. PyTorch is `2.10.0+cu128`, CUDA runtime 12.8.

| Frames at 30 fps | Forward/backward seconds | Peak allocated bytes | Peak reserved bytes |
| --- | ---: | ---: | ---: |
| 30 | 0.252046 | 1,316,355,072 | 1,344,274,432 |
| 120 | 0.135097 | 1,467,118,592 | 1,526,726,656 |
| 300 | 0.144214 | 1,725,057,024 | 1,753,219,072 |

Every output and recorded gradient is finite. Each B receives a nonzero
gradient on the combined root/body loss. Each A receives an exactly zero
first-step gradient because B is still zero; the small CPU fixture separately
checks nonzero A/B gradients after setting a nonzero B. No frozen base
parameter receives a gradient. There are zero optimizer steps.

The existing training branch detaches the root-to-local-body conversion.
A body-only loss consequently produces zero root-adapter gradients and nonzero
body-adapter gradients in the actual checkpoint. Any future root adaptation
must supply a root-stage objective; body cleanup loss alone cannot train it
through this branch. The probe does not change that behavior.

Initial adapted-output maximum delta is exactly zero. Restored base state
fingerprints match, and every checkpoint file hash is unchanged. The longest
case peaks at approximately 1.607 GiB allocated / 1.633 GiB reserved by PyTorch.
These counters exclude other processes and some driver allocations. Timings
exclude loading, text encoding, data preparation, optimizer steps and quality
evaluation; they are single measurements with warm-up effects, not training
throughput or cost estimates. Batch sizes, mixed precision, long sequences,
optimizer allocation and simultaneous text encoding were not tested.

Ten CPU PyTorch tests pass in the existing inference environment. They verify
zero-output equivalence, the actual nonzero residual, both-factor gradients,
frozen base parameters, exact restoration on exception, fused-path rejection
and invalid configuration rejection. They need PyTorch but no model, rig,
network, browser or GPU. They are separate from the existing model-free CI
selection; the previously published 1,648-test / 14-JS suite was not rerun for
this standalone audit addition. Hosted checks for preceding commit `8f4434d`
completed successfully on Windows and Linux.

## Additional primary-source checks

The upstream [fine-tuning issue](https://github.com/nv-tlabs/kimodo/issues/25)
remains open. Its one inspected comment describes a community attempt to adapt
interaction data, not a maintainer training recipe or validated release.
The local code inspection and this probe should not be presented as an official
NVIDIA fine-tuning workflow.

[LIGHT](https://github.com/wzyabcas/LIGHT/blob/62f43cda66e6494e9c4ddf65974d3e9fcb73ec4b/README.md)
now describes released human-object training, evaluation and checkpoints, and
the inspected training loop actually contains loss/backward/optimizer code.
However, the README also retains incomplete dataset-specific support notes.
Its MIT code license does not by itself qualify the linked checkpoints,
datasets or required SMPL+H/DMPL/SMPL-X assets for this product. PyTorch3D and
its separate environment would require Windows/local feasibility testing.
It remains a method reference and acquisition candidate, not a selected model.

[HY-Motion's pinned README](https://github.com/Tencent-Hunyuan/HY-Motion-1.0/blob/4e426f5a1021cbcf7f375458c37b840ee7225229/README.md)
lists 26 GB and 24 GB minimum VRAM for standard and Lite, respectively.
Its [published license](https://github.com/Tencent-Hunyuan/HY-Motion-1.0/blob/4e426f5a1021cbcf7f375458c37b840ee7225229/License.txt)
excludes the EU, UK and South Korea from its territory and restricts using
outputs to improve other AI models. It is not qualified for this project's
general distribution path. No alternative weights, body models or datasets
were acquired and none of that external code was executed.

The acquired Kimodo license and the [current NVIDIA terms](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/)
permit derivative models subject to their terms. That does not license raw
training data. The existing BONES-SEED restriction remains unchanged.
Primary-source text/code snapshots and issue/comment metadata are stored under
ignored `reports/model-adaptation-research-v1`, with hashes and pinned revisions.

## Next evidence needed before training

1. Build a reviewed correction corpus with explicit training rights, original
   clip identity, prompt, rig normalization, edited target, contact schedule and
   cleanup time. Generated failures are useful inputs, not automatically clean
   supervision. Keep animation/performer/rig provenance and related permissions.
2. Verify the 369-channel encoding, normalization, root/body objectives,
   diffusion target/noise schedule, masks and text-feature conditioning against
   pinned inference code. Implement train/save/reload/resume and unchanged-base
   canaries before calling it a usable trainer. Do not train the text encoder
   as a prerequisite for this first denoiser experiment.
3. Predeclare small development training/validation splits by capture/action,
   rather than adjacent frames. Compare unchanged Kimodo, deterministic edits
   and adapted output at identical prompts/seeds. Measure learning curves for
   increasing licensed data; no quantity is promised sufficient.
4. Check action preservation, support/contact/penetration and style response,
   forgetting on untouched development families, rig transfer, engine import
   and timed human cleanup. Reserve the formal 72-by-5 release set until the
   release protocol is ready.

Feedforward adapters cannot introduce missing finger, object, partner or
scene input/output channels. Conditioning/representation changes for those
capabilities require a separate design and evaluation. This audit does not
approve any of the 14 release capabilities or complete the project goal.

## Reproduce on a provisioned workspace

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_kimodo_adapter_probe.py
.venv\Scripts\python.exe scripts/kimodo_adapter_probe.py --output reports/kimodo-adapter-probe-new --frames 30 120 300 --rank 8 --seed 1234
```

The second command requires the already acquired pinned Kimodo dependencies
and CUDA GPU. It refuses an existing output directory, and the shared worker
lock excludes simultaneous model jobs. Model payloads, study tensors/results,
research snapshots and personal machine details remain outside public Git.
