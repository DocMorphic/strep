# Native motion targets and denoising objective audit

The next adaptation component now converts existing native SOMA motion into
checkpoint-normalized targets and verifies conditional clean-motion gradients.
The final local audit completes 54 checks on nine segments from seven developed
actions, with unchanged source motions, encoder cache and model checkpoint.
A separate developer-review packet identifies contact disagreements without
approving any examples for training.

This follows the [adapter memory probe](kimodo-adapter-feasibility-v1.md).
There is still no learned adapter, usable trainer or measured motion-quality
improvement. All 14 release capabilities remain unapproved.

## Target conversion

`scripts/kimodo_denoising_target.py` requires explicitly ordered native SOMA77
local rotation matrices and root positions, at 30 fps in the native metre/Y-up
convention. It checks finite FP32 values and proper rotations, extracts the
checkpoint's SOMA30 subset, and rejects motion in omitted joints that the
relaxed-hands expansion cannot reproduce. A supplied game rig requires a
separate, validated transfer into this representation; arbitrary 77-joint rigs
are not accepted by joint count alone. Finger articulation is not supported by
this body codec.

The [pinned representation](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/kimodo/motion_rep/reps/kimodo_motionrep.py)
has 369 channels: smooth root position 3, heading cosine/sine 2, local joint
positions 90, global rotation 6D values 180, joint velocities 90 and contacts 4.
The root stage supervises the first five; the body stage supervises the other
364. Features are recomputed from local rotations/root positions, rather than
copying potentially inconsistent auxiliary prediction channels.

The first smoothed planar root translation is removed and recorded for inverse
reconstruction. Heading is retained and passed explicitly to the denoiser.
Each segment is processed separately, including smoothing and terminal
velocity duplication. Segment boundaries remain requested conditioning times,
not independently detected action labels.

The acquired split root/body statistics normalize features as
`(x - mean) / sqrt(std**2 + 1e-5)`. Decoding restores the removed translation
and expands the SOMA30 motion back to the relaxed native SOMA77 skeleton for
comparison. This is numerical fidelity, not physical or semantic approval.

## Noise and objective

The [pinned inference step](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/kimodo/model/kimodo_model.py)
passes the denoiser output to the sampler as a clean prediction. This motivates
an explicit experimental **x0**, rather than epsilon, target.
The original training loss and its weights are not supplied by this audit.

`capture_full_noise_schedule` copies the exact coefficient tables from a fresh,
full 1,000-step [vendor diffusion instance](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/kimodo/model/diffusion.py).
It rejects an already respaced schedule and keeps the captured tables separate
from later sampler mutation. Recomputing mathematically equivalent square roots
from base alphas did not reproduce the pinned FP32 operations exactly; the
final implementation uses the vendor tables and matches `q_sample` bit for bit.

Inputs carry bool frame-validity masks, float observation masks and normalized
clean values only at selected observations. Padded frames contain no observations
and use zero noisy inputs. A training example needs at least two contiguous
valid frames because the root/body conversion derives velocities.

The proposed objective is root-channel mean squared error plus body-channel
mean squared error, each with weight one by default. This keeps the five root
channels from being numerically diluted by the 364 body channels. Those weights
are a declared experimental choice, not recovered NVIDIA training weights.
Known observation channels and padded frames contribute to neither numerator
nor denominator. An entirely known example is rejected. A fully known root
stage contributes zero while an unknown body stage retains gradients.

Direct conditional-denoiser calls use the existing exact prompt cache; the
text encoder is not reloaded or trained. Classifier-free dropout, additional
geometric/physical losses, data sampling and optimizer/checkpoint lifecycle
remain to be designed and tested. Body gradients still cannot cross the
published training branch's detached root conversion, so a root objective
remains necessary.

## Actual developed-motion audit

The frozen local protocol is `reports/kimodo-target-audit-protocol-v1.json`.
It selects seven existing seed-77 development clips: jump/land, crawl, dance,
wave, kick, get-up and run/roll/stand. The last clip contains three prompts,
yielding nine target segments and 1,020 frames. Despite the historical source
folder's `body-holdout` name, these are already developed examples, not the
reserved release population.

For each segment the audit checks timesteps 0, 500 and 999, with no constraints
and with the first/last full pose observed: 54 forward/backward rows. Rank-8
feedforward adapters remain at their zero-output initialization throughout.
There are **zero optimizer steps** and no saved learned adapter.

Final worker handle 43632 completed under the shared model lock. Result and
48 archived imported implementation files are retained under
`reports/kimodo-target-audit-v3`. Original model, request, motion, generation
record and encoded-text files are bound by hashes and reverified after the run.

| Check | Observed result |
| --- | ---: |
| Target segments / original clips | 9 / 7 |
| Completed gradient rows | 54 / 54 |
| Maximum local-rotation reconstruction error | 7.153e-7 matrix element |
| Maximum root reconstruction error | 4.768e-7 m |
| Maximum native joint reconstruction error | 1.176e-6 m |
| Maximum difference from pinned `q_sample` | exactly 0 |
| Peak PyTorch allocation | 1,562,731,008 bytes, approximately 1.455 GiB |
| Total measured forward/backward time | 6.385381 seconds |
| Changed base weights / input files | 0 / 0 |

All 64 adapter B factors receive finite nonzero gradients in every row, and
all first-step A gradients remain zero because B is zero. No frozen base
parameter receives a gradient. Loss values are normalized feature errors,
not realism scores. Timing excludes target preparation, loading, text encoding,
optimizer updates and evaluation; memory counters exclude other applications
and some driver allocation. These results are not training throughput estimates.

Two failed attempts remain intact. Handle 90229 exited before gradient rows
because the vendor unbatched a target call; the converter now supplies an
explicit batch and lengths, with a regression test. Handle 91509 retained nine
targets and 32 gradient rows before the original noise formula exceeded its
declared comparison tolerance. A retained diagnosis measures a maximum
2.384e-6 feature difference on get-up at timestep 500, with two elements outside
the comparison bound. The final coefficient snapshot fixes this without
loosening the bound. Failed implementations, results and diagnosis are retained.

## Contact labels and developer review

Pose-derived contacts use the vendor's full 3D foot-speed threshold of 0.15 m/s
and foot-height threshold of 0.10 m. These are heuristics, not measured support
forces or anatomical sole contact. The original predicted contacts stay in the
unchanged raw clips; neither version is assumed correct.

| Segment | Predicted versus pose-derived disagreements | Compared channel values |
| --- | ---: | ---: |
| Jump/land | 6 | 480 |
| Crawl | 45 | 480 |
| Dance | 17 | 600 |
| Wave | 0 | 480 |
| Kick | 10 | 480 |
| Get-up | 83 | 720 |
| Run | 16 | 240 |
| Roll/rise | 43 | 360 |
| Stop/stand | 0 | 240 |
| Total | 220 | 4,080 |

`scripts/prepare_kimodo_target_review.py` creates a fresh unapproved packet
binding original native previews/NPZs, encoded targets and audit. Every
disagreement records the original frame/time, named foot joint, both contact
flags and source joint position. Reviewer, semantic/motion/contact review,
correction file, cleanup time and rights evidence remain empty. Filling a
draft does not itself implement training admission or release approval.

The actual packet is `reports/kimodo-target-review-v1/draft.json`: nine items
and all 220 disagreements, with original preview/target/source hashes checked.
This supports the user's selected developer review first. Independent blinded
animator ratings and timed release cleanup remain separate unmet requirements.

## Verification and next work

35 local CPU PyTorch tests pass: 10 adapter tests and 25 target/objective tests.
They cover stage balancing, excluded padding/observations and their gradients,
exact captured coefficients despite subsequent schedule mutation, explicit
batching, finite/mask/type checks and rejection of omitted joint motion.
A new separate Windows/Linux CPU job runs these without weights or vendor
assets; the existing 169 geometry test-file selection and 14 JS suites remain
unchanged. Previous hosted run 37002588015 succeeds. The full geometry suite was
not repeated locally for these standalone modules.

Next, combine reviewed corrections and verified training rights with validated
target preparation, then implement train/save/reload/resume and unchanged-base
canaries. Predeclare development learning curves and forgetting/control tests
before promoting an adapter. Keep the formal 72-by-5 release population
untouched. Missing scene/partner/finger channels require separate representation
work; this objective cannot invent those channels or certify physical motion.

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_kimodo_denoising_target.py tests/test_kimodo_adapter_probe.py
.venv\Scripts\python.exe scripts/audit_kimodo_denoising_targets.py reports/kimodo-target-audit-protocol-v1.json reports/kimodo-target-audit-new
.venv\Scripts\python.exe scripts/prepare_kimodo_target_review.py reports/kimodo-target-audit-new/result.json reports/kimodo-target-review-new/draft.json
```

The audit needs the pinned provisioned model and the locally specified action
job/cache. It refuses reused output directories and retains failures. The public
repository contains methods and findings; model weights, motion/character
payloads, review drafts and generated targets stay in ignored local storage.
