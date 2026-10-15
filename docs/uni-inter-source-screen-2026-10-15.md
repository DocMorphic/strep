# Uni-Inter source/artifact screen, 2026-10-15

The [paper](https://arxiv.org/abs/2511.13032) describes one representation for
human, object and scene interaction contexts. Its revised
[full text](https://arxiv.org/html/2511.13032v2) links the author's source
repository. This is relevant research precedent for the interaction failures
measured in Strep; it does not establish supplied-rig animation quality.

Inspected author repository commit:
[`0d5248c9948939d47382f482b06f6e86b037b012`](https://github.com/Darkdawner/Uni-Inter/tree/0d5248c9948939d47382f482b06f6e86b037b012).
The local ignored snapshot binds exact source-file bytes and the complete Git
tree. None of that code was executed, installed, copied into Strep production
source or used to train a model.

| Item | Inspected evidence | Consequence for Strep |
| --- | --- | --- |
| Code terms | The [repository LICENSE](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/LICENSE) is CC BY-NC-SA 4.0. GitHub's metadata says `NOASSERTION`; the actual file controls this observation. | Commercial integration permission is not established. Keep the code outside the product. The arXiv paper's displayed CC BY-NC-ND terms are a separate layer. |
| Motion checkpoint | The [configuration](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/configs/config.py) names a local `.pth` path. The inspected tree has no `.pt`, `.pth`, `.ckpt` or `.safetensors` files; the GitHub releases endpoint returns no releases. The [README](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/README.md) describes inference after training. | A reproducible pretrained motion checkpoint was not found in these inspected artifacts. This is not a claim that none exists elsewhere. |
| Product input/output | [Inference](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/infer.py) reads the mixed test dataset, predicts 40 frames of 22-joint voxel densities, then writes comparison GIFs. | This entry point is not an arbitrary supplied-GLB authoring/export workflow or a finger-articulated SOMA asset. |
| Partner conditioning | The [NTU loader](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/datasets/ntu.py) supplies one recorded person's moving body voxels as context and the other person's motion as the prediction target. | Do not treat this inspected path as jointly generating two characters from only text and initial placements. |
| Training/data setup | The README supplies a four-GPU training launcher and calls for dataset preprocessing plus SMPL/SMPL-X fits. | The launcher is an example, not a proved minimum GPU count. Data/body-model permissions and a laptop resource measurement are still missing. No training is admitted. |

One Float32 tensor at the declared `40 × 22 × 48 × 48 × 48` output shape contains
97,320,960 elements, or **389,283,840 bytes** (371.25 MiB). This is only the
calculated storage for one density tensor, excluding batch replication, model
weights, other diffusion tensors, activations and workspace. It is not a measured
RAM/VRAM requirement or proof that inference fits on this laptop.

Decision: retain Uni-Inter as a research reference. The inspected release is
not a currently verified commercial/offline replacement for the unchanged
Kimodo baseline. Continue the actual native interaction corrections and full
source-preserving evaluation. A future permitted scene-aware initializer/editor
must be compared on the same declared scenes, objects, partner contacts, rigs,
cleanup time and held-out actions; showing a different model's GIF is insufficient.
