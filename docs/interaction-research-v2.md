# Interaction model feasibility, 2026-09-27

The immediate decision is to finish the unchanged-checkpoint breadth study and use its failures to select an adaptation experiment. No alternative weights, motion datasets or body models were acquired, and no third-party research code was executed. The running study's generator, encoder, exporters and environment remain frozen.

## What is actually available

| Candidate | Verified evidence | Implication for Strep |
|---|---|---|
| Kimodo | The pinned checkout supplies inference, constraint and benchmark code; the local file inventory did not identify a training entry point. The upstream fine-tuning question remains open, with no maintainer answer visible in the inspected issue. [Issue 25](https://github.com/nv-tlabs/kimodo/issues/25) | Do not promise an existing fine-tuning command. A new training implementation needs an explicit representation/loss/data audit and measured failure target. Keep the current licensed checkpoint as the comparison. |
| Uni-Inter | Public training/inference source now exists. Its README describes four-GPU training and points inference at a user-trained checkpoint; no motion-checkpoint download was identified in that README. [Author repository](https://github.com/Darkdawner/Uni-Inter) | Useful scene-conditioning precedent; not an immediately usable licensed replacement. This is an inspection result, not proof that no checkpoint exists elsewhere. |
| InterControl | The author repository provides training, published checkpoint links and single-GPU setup. It controls joint contact/separation using a motion control network and inference guidance. Code is MIT; dependencies and datasets have separate licenses. [Author repository](https://github.com/zhenzhiwang/intercontrol) | A relevant partner-control comparator. Exact checkpoint permissions, dataset/body-model requirements, Windows compatibility, memory and rig conversion remain unverified. No weights acquired. |
| InterAct | The author repository links text-to-interaction training, pretrained checkpoints, contact-guided inference and object/human prediction tools. It identifies research-license datasets and separate body-model dependencies; custom PointNet operations are required. [Author repository](https://github.com/wzyabcas/InterAct) | Relevant object-interaction research. Commercial model/data permissions and local compatibility are not established. Do not integrate a downloaded checkpoint merely because code or a download link is public. |

## Uni-Inter inspection

The paper conditions human motion on supplied interaction context; it explicitly does not generate the object-pose sequence. Its reported setup uses 40-frame sequences, a 48³ spatial grid and mixed interaction tasks. Its contact/retrieval metrics cannot be copied into Strep without the corresponding data and evaluation protocol. [Paper, implementation and evaluation sections](https://arxiv.org/html/2511.13032v2)

Public source snapshots are retained under `reports/interaction-research-v2/uni-inter`, with URLs, revision and hashes in `source-snapshot.json`. Revision: `0d5248c9948939d47382f482b06f6e86b037b012`.

The repository LICENSE identifies **CC BY-NC-SA 4.0**. Treat this source as research-only for the intended commercial product unless suitable separate permission is obtained. This is distinct from the paper's license and from underlying datasets. [Exact repository license](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/LICENSE)

The inspected `infer.py` loads a test dataset, a local checkpoint and context voxels; it exports joint-motion GIFs. It does not provide Strep's arbitrary-rig animation export workflow. The declared diffusion tensor has shape 40×22×48×48×48: one float32 tensor alone is about 371 MiB, excluding activations, weights, other tensors and training state. This arithmetic is **not** a VRAM feasibility measurement. No hardware-fit claim is made. [Pinned inference source](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/infer.py)

## Next experiment decision

1. Preserve all 390 planned actor clips, failures and missing context checks from breadth-baseline-v2. Separate raw action correctness from scene/partner correctness.
2. Review varied failed prompts across families before choosing a learned change. A successful contact solver cannot establish that a model performed the intended action.
3. For partner failures, compare current independent generation against an explicit shared contact plan using the existing licensed model, before adding a new model. Keep both actors' timing, root motion, visible skin collision and approach/recovery in the evaluation.
4. For object failures, include supplied geometry, grip/attachment/release timing and human response. A prop that follows a hand or deflects from a prescribed actor is insufficient evidence of a successful interaction.
5. If a learned adapter is justified, first establish rights to the exact training data and weights, freeze train/development/test separation, then measure learning curves and untouched-family regressions. The current breadth prompts become development evidence if used to guide changes; they cannot later be advertised as untouched release tests.

No alternative was selected for product integration by this survey. Independent animator participation and actual cleanup-time evidence remain required and missing.
