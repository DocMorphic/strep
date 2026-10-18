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

The same 26 cases pass on hosted Windows and Ubuntu at
`4576bf966ec3f6801bf22e9f46f90ae4bdbc7789`
([focused run 39119854099](https://github.com/DocMorphic/strep/actions/runs/39119854099)).
The initial dispatch failed before jobs started because a pip argument's
terminal colon required a YAML block. That setup failure remains recorded;
the corrected workflow parses and the actual CPU suites complete.

The first real decoder probe stopped at a preview return-value unpacking error
after its gradient/descent calculations. The preserved v1 attempt is not a
completed result. A fresh v2 probe checks all 120 frames of an existing
seed-77 generated clip, its pinned SOMA369 decoder, SOMA77 expansion, 18,056
skin vertices and eight influences. Its cube and point-offset targets are
explicit derivative fixtures, not approved authored intent or human examples.
It loads normalization/rig data but no denoiser weights. Complete results,
resource receipts and any failures stay under ignored `reports/`.

The completed v2 decoder probe verifies all **2,166,720 vertex/frame pairs**.
Sparse skin positions differ from the original complete LBS reference by at
most **5.0122e-7 m**. Two complete 44,280-feature directions agree with central
finite differences within 3.0758e-8 / 4.8928e-8. Two bounded steps lower mean
energy from 0.0004086393 to 0.0000603990 while preserving first/last feature
rows. **Worst convex penetration nevertheless increases from 75.747 to
83.954 mm**, and worst floor penetration stays at 9.399 mm. The result remains
unapproved. This measured tradeoff prevents energy descent from being treated
as a collision or animation-quality pass.

A separate model-free export replay checks both saved GLBs over all 120 frames:
**4,333,440 vertex/frame pairs**, every skin weight/index and all 36,108 faces.
Maximum skin-component error stays below 7.383e-7 m; the same worse convex
depth is reproduced. The replay excludes Torch, the new hooks/energy and the
sparse skin implementation. It shares the established GLB/skin libraries and
rechecks only the declared convex surrogate, not complete triangle collision.

Evidence: `reports/scene-denoising-source-tests-v1`,
`reports/scene-denoising-decoder-canary-v2` and
`reports/scene-denoising-export-replay-v1`. Tensor tests/decoder probes use an
explicit 1.5 GiB expected / 2 GiB maximum tree policy; the model-free export
replay keeps its 512 MiB cap. All retain the 600 MiB free-memory reserve and
bounded execution. The historical numeric studies and global guard defaults
are unchanged.

## Actual checkpoint pilot

`reports/scene-denoising-checkpoint-pilot-v1` executes three fresh CUDA samples
from the acquired, unchanged Kimodo v1.1 checkpoint: ordinary generation,
disabled hook, and guided. All use the same existing high-five description,
seed 77, 120 frames, 100 steps, CFG [2,2] and disabled postprocessing. The
existing validated cached text tensors and CUDA checkpoint transport are
retained. No new encoder, model/data download, weight update or training occurs.
This is one in-sample functional experiment with synthetic derivative targets;
it is not a held-out interaction benchmark or a clean training example.

**Every raw array is byte-identical between ordinary and disabled generation.**
Both hooked modes receive exactly 100 complete CFG calls. Guided mode activates
at the five declared mapped base timesteps [0,10,20,30,40], accepts five bounded
energy-decreasing steps and retains every call/trial record.

| Fresh sample | Maximum point-offset error | Maximum convex depth surrogate | Maximum floor depth |
| --- | ---: | ---: | ---: |
| Ordinary / disabled | 20.413 mm | 75.747 mm | 9.399 mm |
| Guided | 19.196 mm | 76.395 mm | 9.399 mm |

Improved point tracking trades against worse maximum cube penetration. This is
**not an approved improvement**. The raw outputs, proxies and failures remain
available; no Studio or reference switch occurs. The pilot completes under its
explicit 2 GiB expected / 3 GiB maximum tree policy, with 1,728,626,688-byte
peak RSS and the unchanged 600 MiB reserve. These figures establish local
execution feasibility for this case, not a general performance guarantee.

`reports/scene-denoising-checkpoint-replay-v1` independently replays all three
saved exports: **6,500,160 vertex/frame pairs**, original eight weights/indices,
all faces, pose arrays and the convex/floor/point observations. Disabled raw
array identity is rechecked. Maximum skin-component error is below 5.0e-7 m;
the same depth regression is reproduced. New guidance/decoder modules and
Torch are excluded from this replay, with baseline GLB/skin libraries shared.

Next add explicit per-metric retention and real authored scene/placement
wiring before expanding matched-seed object/partner and broad action tests.
Mean loss must not hide a worse depth, support, contact or motion metric.
General mesh/partner conditioning, rough editing, calibrated styles/stats,
retargeting, transitions, engine integration and genuine human review remain
part of the same full-project goal.

The completed checkpoint is `reports/scene-denoising-progress-v1`. Its bounded
streaming audit verifies 7,683 current code, checkpoint, cache, asset, output
and resource bindings, plus the prior whole-goal checkpoint receipt. It
finishes in 51.156 s with 75,157,504-byte peak tree RSS. It confirms all fixed
release criteria remain unchanged outside goal line 3 and the two progress
fields. All 14 release capabilities remain unapproved; the goal stays active.

Before any production claim, execute matched-seed unchanged versus guided
checkpoint sampling, preserve all attempts, and evaluate raw/saved motion,
actual rig transfer, all mesh/contact/depth conditions, semantics, style,
engine import and real review/cleanup. Energy descent alone cannot qualify an
asset. Existing failed benchmarks, the qualified partial reference, Studio
selection, held-out reservations and the full release contract remain intact.
