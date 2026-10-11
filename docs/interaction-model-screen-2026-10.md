# Interaction and rig-model screen — 2026-10-10

The last independently verified box-lift state still has zero full physical/keyed passes across 62 keys. The remaining eight bounded native windows are being tested with unchanged retention limits. This motivates screening scene/partner and rig-aware research, but neither those failures nor a paper's demonstrations establish that a replacement solves Strep's supplied-rig, editable-asset workflow.

| Candidate | Relevant published support | Current acquisition/integration decision |
|---|---|---|
| [UniMate author code](https://github.com/Friedrich-M/UniMate) and [checkpoint card](https://huggingface.co/Linzhan/UniMate) | The author's current repository announces preview weights on 2026-09-27 and custom GLB/glTF/FBX rig preprocessing on 2026-10-05. The recommended v3 checkpoint generates 60 frames at 30 fps and admits 5–70 joints. Longer sequences use expansion. The model card reports contact sliding, drift, hovering and penetration, and weak rare-motion coverage. | Code is MIT; weights are CC BY-NC 4.0. No product integration or weight acquisition. A later non-commercial research comparison would need its own exact checkpoint, permitted fixtures, offline dependency preparation and resource estimate. The author's card also leaves third-party weight/output rights unresolved. Use the author repository rather than a stale fork claiming checkpoints are still forthcoming. |
| [InteractMove official code](https://github.com/Cxhcmhhh/InteractMove) and [aligned-motion card](https://huggingface.co/datasets/cxhcmhhh/InteractMove) | Text, moving objects and scene context; separate hand/object affordance and motion models, with checkpoint links and evaluation scripts. Repository and dataset card display MIT. Their preparation instructions require ScanNet scenes and GRAB/BEHAVE object meshes. | Promising architecture precedent; exact checkpoint license and upstream asset/data permissions remain unverified. An MIT label on a derived catalog is not treated as permission for every upstream asset. No data/checkpoint download, training or third-party execution. |
| [InterMask official code](https://github.com/gohar-malik/InterMask) and [software license](https://github.com/gohar-malik/InterMask/blob/main/LICENSE) | Joint two-person generation; published pretrained models, 22-joint motion arrays and a text-prompt inference script. The repository's software license is MIT. | Checkpoint-specific terms remain unverified. Its [InterHuman source](https://github.com/tr3e/InterGen) declares non-commercial data/material terms; the Inter-X path additionally needs SMPL-X. Do not assume the software license grants product rights to model/data/body dependencies. No acquisition or integration. |
| [InterPose official code](https://github.com/Mael-zys/InterPose) | Web-video-derived interaction research, physics/kinematic paths and a zero-shot evaluation command; the README requires processed data, SMPL-X and ProtoMotions/MaskedMimic. Its optional HOI-Agent uses an OpenAI API key. | Inference for Strep: the optional API agent would violate offline execution; an isolated local path would require a separate dependency/checkpoint/asset audit. This screen does not verify those terms or laptop feasibility. No acquisition or execution. |
| [InterAct official code](https://github.com/wzyabcas/InterAct) | Provides text-to-interaction training/checkpoint/evaluator links and contact-guided sampling. Its data-access instructions explicitly request non-commercial authorization and preserve source dataset terms. | Relevant comparison methodology; no product training/import rights inferred. No request form submitted, agreement accepted, data acquired or code run. |

These are primary-source observations checked on this date, not performance measurements on Strep. The sources' code, model weights, body models and training data must be considered separately. Existing Kimodo remains the unchanged generation baseline. This screen changes no model, training corpus, rig, numerical gate, release capability or held-out reservation.

## 2026-10-12: supplied-rig editing contract inspection

The availability/license screen above remains unchanged. A source-only review
of UniMate at revision `b78c7807df7cf4231d4e67f8d0ece29c5e11025b` adds two
integration requirements. No external model code was executed or weights acquired.

The [joint-mask builder](https://github.com/Friedrich-M/UniMate/blob/b78c7807df7cf4231d4e67f8d0ece29c5e11025b/unimate/inference/motion_editing.py)
warns about unmatched requested names. If the whole batch has no matches, it
returns an all-false mask and sampling proceeds without those constraints.
That behavior accommodates heterogeneous upstream batches. A Strep adapter
must resolve every explicitly requested kept joint per actor before execution,
reject missing/ambiguous matches and archive the complete index mapping.
This is an integration requirement, not a reported failure of a generated clip.

The [mesh-driving entry point](https://github.com/Friedrich-M/UniMate/blob/b78c7807df7cf4231d4e67f8d0ece29c5e11025b/data_process/mesh_animation/animate_motion.py)
defaults to FK recovery. Its
[rotation recovery function](https://github.com/Friedrich-M/UniMate/blob/b78c7807df7cf4231d4e67f8d0ece29c5e11025b/unimate/utils/motion_utils.py)
reconstructs local rotations and the integrated root trajectory, while keeping
non-root positions at rest offsets. Inference for Strep: preserving a generated
joint feature row does not itself prove preservation of the driven joint's
world position or of a skinned hand/foot patch. A qualified editor must compare
the requested preserved quantities in the decoded export, including root,
parent transforms and contact geometry. That comparison has not been run here.

The [rig-preprocessing guide](https://github.com/Friedrich-M/UniMate/blob/b78c7807df7cf4231d4e67f8d0ece29c5e11025b/data_process/rig_preprocess/README.md)
also describes pruning bones and baking a canonical asset. Strep must retain the
supplied original and an explicit mapping/inverse transform; an altered
canonical rig cannot inherit original-asset fidelity approval.

Seventeen small pinned source/terms snapshots across UniMate, HY-Motion, MotionFix
and Uni-Inter are retained in `reports/model-alternatives-source-v1`, totaling
247,397 bytes. The sampled edit call and replacement sampler also confirm that
the joint mask is passed through to feature clamping. The MotionFix and HY-Motion terms checks agree with the existing
documented decisions; their repeated availability checks add no performance
evidence. This review does not authorize acquisition, product integration,
training, held-out tuning or release approval.

## Next decision and experiment

Finish and independently replay the remaining bounded contact windows before selecting another correction method. Record the full attempted population, retained steps, protected-row losses, contact/normal/penetration errors and time; schedule exhaustion is not a proof of mathematical infeasibility. A preserved but inadequate result must stay visibly inadequate.

If local correction still fails, compare a scene-conditioned initialization or editor with the unchanged generator and the established deterministic pipeline on development fixtures. Use self-authored/captured or separately licensed interaction edits with synchronized object transforms, hand patches and partner clocks. Include fingers explicitly: the current body representation does not independently emit all SOMA articulated finger rotations, as recorded in the [representation audit](source-ledger.md). Do not substitute free mesh deformation for the supplied rig.

Before any learned trial, bind the data permission, independent train/validation/test group split, exact model/representation, proposed targets and resource budget. Keep the reserved release prompts, seeds, rigs, objects and pairings out of tuning. Measure learning curves at increasing fractions of the legitimately collected training set; do not predict that a small set or merely longer training will suffice. Report skipped/failed trials and action families separately. Asset fidelity, human usability and timed cleanup remain required alongside numerical contact checks. No learning trial is started by this screen.
