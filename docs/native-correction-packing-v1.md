# Packing native corrections v1

`scripts/pack_native_correction.py` converts an existing native SOMA77 NPZ
and explicit contact intervals into the safetensors correction accepted by
[reviewed corpus preparation](kimodo-training-corpus-v1.md). This removes the
need to write a custom Python exporter. It does not perform human review,
approve rights, admit training data or fix an animation by changing its labels.

## Authoring steps

Choose one segment ID from the native review draft. For example:

```powershell
.venv\Scripts\python.exe scripts/pack_native_correction.py template reports/kimodo-target-review-v1/draft.json wave-segment-0 reports/my-wave-annotation
```

This creates `recipe.json` with all contact states unknown and a separate
`model-suggestions.json` showing the original predicted contacts. Suggestions
remain labeled unreviewed and are not copied into the recipe. Watch the original
preview and any authored candidate; use the original segment's frame bounds
from the draft to find the correct interval. A model prediction is not proof
that a foot was planted.

To pack a different authored native NPZ, declare its corresponding window:

```powershell
.venv\Scripts\python.exe scripts/pack_native_correction.py template reports/kimodo-target-review-v1/draft.json wave-segment-0 reports/my-edited-wave-annotation --candidate reports/my-authored-wave/motion.npz --candidate-start 0
```

Candidate start is required when selecting a different file. It can be zero
for an already cropped candidate. The selected window must contain exactly the
original segment's number of 30 fps frames. Geometry must already be native
SOMA77 FP32 local rotation matrices and root positions, in metres and
right-handed Y-up. Existing native correction jobs export this NPZ format.
Edited target-rig GLB files need a separately validated native conversion;
this tool does not silently reinterpret their joints or clock.

Edit the four recipe contact channels into complete on/off intervals. For a
90-frame segment, one channel could be:

```json
{
  "joint": "LeftFoot",
  "intervals": [
    {"start_frame": 0, "end_frame_exclusive": 30, "contact": true},
    {"start_frame": 30, "end_frame_exclusive": 45, "contact": false},
    {"start_frame": 45, "end_frame_exclusive": 90, "contact": true}
  ]
}
```

These numbers illustrate the format, not labels for the wave clip. Indices are
local to the selected segment, start at zero and end exclusively. Each channel
must cover the entire clock in order with no gaps or overlaps. Off intervals
must be explicit; unknown/null or numeric states are rejected. Channel order
is LeftFoot, LeftToeBase, RightFoot, RightToeBase. The recipe binds original
draft/source/preview and candidate file hashes, frame start, joint order, FPS,
units and coordinates.

After completing the annotation:

```powershell
.venv\Scripts\python.exe scripts/pack_native_correction.py pack reports/my-wave-annotation/recipe.json reports/my-wave-correction
```

The fresh output directory contains the exact selected rotations/roots and
expanded Boolean schedule in `correction.safetensors`, copied recipe/draft
evidence, an unreviewed rights template, an unreviewed review-row template and
`result.json` written last. Inputs are checked again before publication; the
saved correction is read back and compared against the input tensors. Original
NPZs and previews are never rewritten. Proper rotation matrices, finite FP32
geometry, native joint order and the declared coordinate/clock contract are
required; geometric contacts, balance and semantic quality are not certified.

Complete actual review and rights evidence separately following the corpus
contract. Templates leave human judgments, measured cleanup, permission,
reviewer identity and timestamp unset. After editing a referenced file, update
its SHA-256 in the submission; old hashes are deliberately rejected. Evidence
hashes can be obtained with PowerShell `Get-FileHash -Algorithm SHA256` and
converted to lowercase. Neither a completed pack result nor a file checksum
admits a target for training. The GUI review/submission form remains unfinished.

## Verification

92 focused CPU tests pass, including 20 new packing tests. They cover exact
geometry/contact/metadata roundtrip, separate unknown annotations and model
suggestions, complete interval coverage, gaps/overlaps, invalid states,
coordinate/clock/joint-order mismatch, stale source bindings, invalid geometry,
independent candidate windows, retained evidence and refusal to overwrite.

The local numerical canary `reports/native-correction-pack-canary-v1` packs
nine existing development segments, totaling 1,020 frames. It creates explicitly
synthetic candidates by adding 0.01 m to root X and deliberately inverts model
contact suggestions. All tensor values match those declared numerical inputs;
all nine unknown schedules reject before writing a correction directory.
These are exporter test artifacts, not human corrections, contact truth or
improved animations. They remain unapproved and no training data is admitted.

The actual CLI also creates a fresh unreviewed wave recipe and packs one
numerical wave candidate. It checks the pinned vendor source and parses native
joint metadata under the shared worker lock, without loading a denoiser,
encoder or GPU. No optimizer updates or reserved release trials are run.
Raw inputs and imported methods remain unchanged and local artifacts stay
ignored. Hosted run 37010591338 passed all four Windows/Linux jobs for the
preceding corpus-preparation commit. This change adds packing tests to the
separate CPU jobs; the geometry/JS job remains unchanged.

Next work is usable review submission, verified corpus loading and the real
trainer/learning curves using actual reviewed licensed corrections. Native
conversion from edited target rigs, scene/partner/finger representations,
meaningful controls and independent animator cleanup remain unfinished.
The broad goal stays active and all 14 release capabilities remain unapproved.
