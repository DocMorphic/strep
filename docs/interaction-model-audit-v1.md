# Interaction-aware model feasibility

Checked 2026-09-28. This audit follows the measured partner-contact failure: the fitted clip improves hand proximity but increases partner penetration relative to raw motion. It does not authorize a replacement model, training run or release claim.

## Uni-Inter

The [paper, version 2](https://arxiv.org/html/2511.13032v2) describes a common spatial representation for human, object and scene interactions. It conditions human motion on supplied object motion; it does not generate the object's trajectory. Its reported setup uses 40-frame sequences, a 48-cubed grid and up to 500,000 training steps. The human-human results report distributional metrics, not Strep's mesh-contact and engine-export gates. These results motivate testing scene-conditioned approaches, but do not establish that this model would fix our forearm crossing or produce production assets.

The paper links the [official repository](https://github.com/Darkdawner/Uni-Inter). Its README describes preprocessing several datasets into body meshes, training with four GPUs and running inference against a trained checkpoint. The inspected repository has no release assets or tracked model weights. This is a bounded observation of that repository, not proof that weights cannot be obtained elsewhere. Its [license](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/LICENSE) is CC BY-NC-SA 4.0. Do not incorporate it into the commercial product without separately resolving permission.

Source audit is pinned to commit `0d5248c9948939d47382f482b06f6e86b037b012`. Retained read-only source files, tree, release response and SHA-256 records are in `reports/uni-inter-source-audit-v1/`; no repository code was imported or executed and no weights were downloaded.

The inspected [inference entry point](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/infer.py) consumes `MixedDataset` test batches, predicts 22 joint locations over 40 frames and writes GIF comparisons. It is not an arbitrary-rig asset exporter. Its [configuration](https://github.com/Darkdawner/Uni-Inter/blob/0d5248c9948939d47382f482b06f6e86b037b012/configs/config.py) names a local checkpoint and uses batch size 4; do not conflate that with the paper's batch size 32 or infer actual hardware requirements from a launcher alone. Training-data and body-model rights require separate checks before any adaptation.

## Decision

Retain Kimodo and the raw failure evidence. Complete the fixed component study before changing the contact solver. Our retained skin-weight attribution identifies the largest collision on the two forearms, so the next geometric hypothesis concerns their approach paths, with the original raw motion and final 5 mm screen retained as references. Finger posture alone has not improved the sampled peak.

Before evaluating another learned interaction model, require usable weights, relevant rights, a measured local-memory estimate, input/output adapters and the same raw-versus-corrected evaluation. A paper's aggregate scores cannot substitute for our rig, mesh, timing, engine and animator checks. No release gate changes from this audit.
