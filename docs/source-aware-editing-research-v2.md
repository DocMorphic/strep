# Source-aware editing decision, 2026-10-11

Strep's section-regeneration pilot still has five failed quality screens; see
[the recorded raw, transfer and splice results](prompt-edit-v1.md). Exact source
preservation and successful import did not establish useful motion editing.
This recheck changes neither those results nor the release acceptance matrix.

## What is available

[MotionFix](https://motionfix.is.tue.mpg.de/) describes TMED as a diffusion editor
conditioned on source motion and edit text. That is a closer architectural
precedent for relative editing than Strep's four-boundary-frame replacement.
It does not establish scene contacts, arbitrary-rig transfer or Strep performance.

The authors' repository was captured at revision
`e6b437e6a17f26b2066f9c142600146f035da6bf`. Six small source/configuration files
and their hashes are retained locally under `reports/motionfix-source-review-v2`;
no third-party code was executed and no checkpoint, motion data or body asset
was acquired. The inspected
[training entry point](https://github.com/atnikos/motionfix/blob/e6b437e6a17f26b2066f9c142600146f035da6bf/train.py)
constructs a Lightning trainer and calls `trainer.fit`. The evaluation script
has separate source/target lengths and source-motion conditioning. An available
trainer is not a compatible SOMA77 or arbitrary-game-rig training workflow.

## Terms and compatibility remain separate

The pinned [LICENSE](https://github.com/atnikos/motionfix/blob/e6b437e6a17f26b2066f9c142600146f035da6bf/LICENSE)
contains MIT terms. Its
[README](https://github.com/atnikos/motionfix/blob/e6b437e6a17f26b2066f9c142600146f035da6bf/README.md)
also describes code use as non-commercial scientific research. This discrepancy
is recorded rather than resolved by choosing the more permissive statement.
The README links a checkpoint but does not establish separately verified
deployment rights for that downloaded payload. No product integration is
qualified by this inspection.

The [MotionFix dataset terms](https://motionfix.is.tue.mpg.de/license.html)
describe CC BY 4.0 metadata including edit text, video URLs and AMASS extraction
timestamps. Those annotations are distinct from underlying motion recordings.
The [AMASS terms](https://amass.is.tue.mpg.de/license.html) restrict their dataset
to non-commercial uses and expressly prohibit training methods for commercial
use. Annotation permission does not establish motion, body-model or checkpoint
permission. The repository's setup also requires separate body assets. No AMASS
acquisition or training follows from this review.

The README reports testing on Ubuntu 20.04 with Python 3.10 or newer; its pinned
requirements and body-model setup have not been reproduced on this Windows
laptop. No local VRAM estimate, install success or inference performance is
claimed. Model/data rights and compatibility must be established before an
alternate editor is acquired for this product.

## Next implementation decision

[NVIDIA's constraints documentation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/constraints.html)
states that full-body input rotations derive constrained joint positions; they
are not exact local-rotation constraints. Its
[best-practices documentation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/limitations.html)
also identifies conflicting constraints and transition time as limitations.
These support investigating boundary feasibility and transfer separately; they
do not explain every recorded failure by themselves.

After the current sequential contact/engine validation, use the retained pilot
failures for a matched development comparison. First localize original and
edited floor/contact failures to protected versus editable regions, and check
whether the requested boundary poses and action timing are compatible. Then
compare unchanged generation, unchanged transfer and support-aware corrected
transfer, with raw outputs and outside-edit preservation kept explicit. Already
invalid protected source poses must remain visible rather than being repaired
silently. Action completion and naturalness still require human evidence.

A licensed source-motion residual editor remains a research option if these
comparisons demonstrate failures that deterministic correction cannot address.
The current held-out prompts, seeds and rig reservations remain untouched;
none of this source research is a release trial, model adaptation or quality
approval.
