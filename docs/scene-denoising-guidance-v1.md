# Scene energy during motion sampling

Experimental development path, 2026-10-18. The default generator and acquired
checkpoint remain unchanged. No release capability is approved.

The existing matched-seed hand/full-body guide studies improved targeting but
failed actual skin contact and collision checks. The recent complete affine
correction also fails depth nonregression. A different experiment now exposes
scene geometry during sampling through an opt-in clean-prediction hook.

## Research and integration point

[NVIDIA's constraint documentation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/constraints.html)
describes reduced skeletal pose/root conditions and separate optimization after
generation. The [model card](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1)
retains limitations around scene-object awareness. The local pinned checkout
`58e781898b3d7e328a676a75d3e338c45dce3ad9` predicts clean motion through its CFG
wrapper, then sends that prediction to the DDIM sampler. These stages give a
concrete integration point without editing vendor code or loading a new model.

[Guided Motion Diffusion](https://arxiv.org/abs/2305.12577) is research precedent
for bringing spatial constraints into motion diffusion. This implementation is
a separate bounded clean-prediction descent experiment; it does not reproduce
that paper's feature projection, imputation or dense-guidance method.

## Implemented behavior

`scripts/kimodo_scene_guidance.py` temporarily hooks the caller-owned complete
CFG prediction. The base denoiser runs once. Geometry autograd operates on a
detached prediction outside the surrounding inference mode, then the unchanged
sampler receives the result. No denoiser gradient or weight update is required.
The hook is removed on normal exit or an exception and duplicate installation
rejects. The caller pins the model, scene, code and outputs.

Disabled guidance returns the exact original prediction object without calling
the energy or consuming random numbers. An explicit optional schedule selects
**mapped base timesteps**, not sampler call counts. Each active call permits
one to four steps with an explicit L2 feature budget and the fixed backtracking
fractions 1, 1/2, 1/4. Every accepted proposal strictly lowers the complete
declared energy, stays in that budget and preserves all observed/padded
prediction channels. Mask preservation does not establish target adherence.
No improvement yields an unchanged prediction and a retained reason. Invalid
energies, masks, gradients and exceeded record budgets reject explicitly.

`scripts/kimodo_skin_scene_energy.py` accepts the actual motion decoder and the
existing sparse `LinearSkinOperator`. It checks every supplied frame, skin
vertex and influence. Frame activation checkpointing bounds temporary memory
while preserving the complete population and gradient. It supports floor
planes, supplied convex half-space tracks and explicit skin-point targets.
The initial adapter handles one complete actor clock, at most 300 frames.
Convex interior depth is a guidance surrogate; complete triangle, partner,
self-collision, force and continuous-time checks remain separate requirements.
Arbitrary mesh/partner energy adapters and Studio authoring are still required.

## Validation and next evidence

The guarded tensor suite passes **26 cases: 23 new plus three existing sparse
skin checks**. It covers inference-mode interoperability, exact disabled
behavior, padding/observed-channel preservation including negative zero,
rejected wrong-gradient proposals, nonfinite/invalid inputs, hook ownership and
cleanup, complete-frame skin/gradient equivalence at multiple chunk sizes,
convex/contact terms and invalid target clocks. CPU tensor tests enter the
existing adapter job and the opt-in focused Ubuntu/Windows workflow; they are
kept outside the dependency-light NumPy source manifest.

The first real decoder probe stopped at a preview return-value unpacking error
after its gradient/descent calculations. The preserved v1 attempt is not a
completed result. A fresh v2 probe checks all 120 frames of an existing
seed-77 generated clip, its pinned SOMA369 decoder, SOMA77 expansion, 18,056
skin vertices and eight influences. Its cube and point-offset targets are
explicit derivative fixtures, not approved authored intent or human examples.
It loads normalization/rig data but no denoiser weights. Complete results,
resource receipts and any failures stay under ignored `reports/`.

Before any production claim, execute matched-seed unchanged versus guided
checkpoint sampling, preserve all attempts, and evaluate raw/saved motion,
actual rig transfer, all mesh/contact/depth conditions, semantics, style,
engine import and real review/cleanup. Energy descent alone cannot qualify an
asset. Existing failed benchmarks, the qualified partial reference, Studio
selection, held-out reservations and the full release contract remain intact.
