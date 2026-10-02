# Reviewed native correction corpus v1

`scripts/kimodo_training_corpus.py` connects the native target codec to a
source-bound correction submission. It prepares development supervision only
after completed human reviews and a correction-specific rights attestation.
The current nine-segment packet remains unreviewed: **zero real targets have
been admitted, and no motion-training run has been performed**.

## Review and provenance contract

Keep the original `strep-native-target-review-draft-v1` unchanged. Generate a
separate submission template; every audited segment must receive either
`accept_corrected` or `exclude`. The template deliberately fills neither human
review nor permission fields. Passing it back unchanged is an error.

```powershell
.venv\Scripts\python.exe scripts/kimodo_training_corpus.py template reports/kimodo-target-review-v1/draft.json reports/kimodo-correction-submission-new/unreviewed.json
```

An accepted row declares its development split (`train` or
`development_validation`), three completed human judgments (semantic action,
motion quality and contact schedule), measured active cleanup seconds, review
notes, corrected native payload and rights attestation. Reviewer identity,
developer/animator role and timezone-qualified timestamp are mandatory.
An excluded row needs a reason and leaves the remaining fields null.

The submitted draft hash, original completed audit hash, protocol, source
motion, native preview and originally encoded target are checked. A draft
cannot substitute a different prompt, segment clock or original source take
by supplying another valid file checksum. The corrected payload and rights
evidence have their own exact hashes. All external inputs are checked again
after encoding and publication. The original audit and raw motions stay intact.

These are machine checks of declared human evidence. They cannot establish that
the named reviewer actually performed the review or determine legal rights.
Developer review is permitted for this development corpus; it does not replace
the independent animator review and timed cleanup study required for release.

## Native correction payload

The correction is a safetensors file with exactly three tensors:

| Tensor | Shape and type |
| --- | --- |
| `local_rotations` | FP32 `[frames,77,3,3]`, native SOMA77 local rotations |
| `root_positions` | FP32 `[frames,3]`, metres, right-handed Y-up |
| `foot_contacts` | Boolean `[frames,4]`, full explicitly reviewed schedule |

It preserves the original segment length at 30 fps, with 2–300 frames. Its
metadata has exactly these string fields: `schema=strep-native-correction-v1`,
`skeleton=somaskel77`, `fps=30`, `units=metres`,
`coordinates=right-handed-Y-up`, `joint_names` and `contact_joints`.
The two name lists are compact JSON strings using `separators=(',', ':')`.
Joint order must equal the pinned skeleton's complete 77-name order; contact
order is `LeftFoot, LeftToeBase, RightFoot, RightToeBase`.

The existing codec checks proper orthonormal rotations and rejects moving
omitted/finger joints that SOMA30 cannot represent. It recomputes positional,
rotation, velocity and root features from corrected geometry. Only the last
four normalized channels are then replaced with the supplied contact labels.
Geometry channels and heading remain exact. The heuristic disagreement count
is retained for diagnosis; neither that heuristic nor a label is a force or
balance measurement. Editing a label alone does not correct a sliding foot.

The payload must be created from genuinely reviewed/authored correction work.
There is no automatic conversion of existing generated failures into approved
labels, and no GUI correction-submission form or general mocap importer yet.

## Rights attestation

Each accepted correction references a local JSON file with schema
`strep-native-correction-rights-attestation-v1` and these exact fields:

```json
{
  "schema": "strep-native-correction-rights-attestation-v1",
  "authorized_by": "The responsible human",
  "attested_at": "2026-10-02T12:00:00+00:00",
  "source_motion_sha256": "<exact original motion hash>",
  "correction_sha256": "<exact corrected payload hash>",
  "source_kind": "model_output_and_authored_correction",
  "use": "commercial_generative_game_motion_training",
  "permitted": true,
  "evidence_files": [{"path": "retained-evidence-file", "sha256": "<exact evidence hash>"}],
  "obligations": "Applicable license and attribution obligations",
  "notes": "Basis for the permission and ownership of the correction"
}
```

This example describes the format, not permission for any actual asset. The
evidence must cover the exact original motion and authored correction. The
preparer records `rights_status` as human attestation with bound evidence,
explicitly without an automatic legal determination. V1 supports reviewed
model-output corrections only; self-captured and separately licensed mocap
need additional provenance/import pathways.

The current [Kimodo model card](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1)
identifies the NVIDIA Open Model License and game/media animation as intended
use. The [NVIDIA terms](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/),
checked 2026-10-02, permit derivatives and commercial use subject to their
conditions and state that NVIDIA does not claim outputs. These provisions do
not supply rights to proprietary source recordings, other datasets, third-party
characters or someone else's authored corrections. Raw BONES-SEED remains
excluded under the project's existing source/license policy.

## Splits and preparation

Any reserved release ID, normalized exact prompt or reserved seed is rejected.
Normalization handles Unicode compatibility, case and punctuation. This is
not semantic near-duplicate detection. A human overlap audit is still needed.
Segments sharing an original motion hash cannot cross training/development
validation splits, and duplicate correction hashes cannot be counted twice.
Copied-but-modified source files and near-duplicate performances need further
grouping; no unseen-action or checkpoint-training-overlap claim is implied.

After completing a separate submission and providing its corrections/evidence:

```powershell
.venv\Scripts\python.exe scripts/kimodo_training_corpus.py prepare path\to\completed-submission.json reports\kimodo-reviewed-corpus-new
```

The CLI checks pinned representation/statistics and vendor source under the
worker lock and instantiates only the CPU motion representation. It loads
neither the denoiser nor the text encoder and performs no optimizer updates.
Targets contain `clean_features`, `first_heading` and explicit
`reviewed_foot_contacts`. The current V2 manifest explicitly binds the submission
and release reservation files for the [verified reader](kimodo-corpus-reader-v1.md).
It retains prompt, segment/source hashes,
split, cleanup time, codec report and contact disagreement count. Input review,
correction and rights evidence are copied with checksum verification; original
raw/model inputs remain externally bound. A fresh output directory is required
and the manifest is written last. Quality/release flags remain false.

## Verification and next work

72 focused CPU tests pass, including 28 corpus tests. They exercise real fixture
file hashes and correction tensors, stale source/evidence rejection, auditable
source substitution, incomplete reviews, full contact schedules, exact product
use attestations, reserved IDs/seeds/prompts, split leakage, explicit exclusion,
contact normalization, source races and refusal to overwrite. Fixture reviews
are declared numerical test data, not real people or licenses.

The local CPU representation audit `reports/kimodo-correction-encoding-v1`
checks nine existing segments/1,020 frames. It deliberately inverts all 4,080
contact labels to test wiring, retaining unchanged geometry and heading with
zero decoded label error. The targets match the earlier unchanged encoding
before label replacement. **These deliberately invalid numerical labels are
never admitted**. The real draft and fresh unreviewed submission are both
rejected; admitted targets and optimizer steps are zero. Inputs and archived
methods remain unchanged. No new animation, cleanup review or reserved release
trial was performed.

Hosted run 37008931915 passes all four Windows/Linux jobs for the preceding
checkpoint-lifecycle commit. This change adds the corpus suite to the separate
CPU jobs. The 169-file geometry job and its 14 JS suites remain unchanged and
were not repeated locally for these standalone modules.

Next work is the developer's actual corrections/reviews and rights evidence,
corpus loading verification, usable correction-submission tooling, a real
trainer with measured learning curves and fresh-process resume, and unchanged
baseline improvement/forgetting comparisons. Scene/partner/finger channels,
meaningful controls, rig transfer and independent animator cleanup evidence
remain separate unfinished requirements. All 14 release capabilities remain
unapproved and the full project goal stays active.
