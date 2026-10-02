# Reviewed native corpus trainer

Strep now has an experimental sequential adapter trainer that consumes verified
native targets, keeps development-validation examples out of updates and saves
bound checkpoints. A fresh-process CPU canary reproduces interrupted training
exactly. This is training infrastructure: no real correction corpus has been
admitted and no improvement in generated animation has been demonstrated.

## Training behavior

`scripts/kimodo_corpus_trainer.py` accepts the verified reader's example table,
an already loaded frozen base with installed adapters, exact prompt features,
the captured full diffusion schedule and an explicit plan. It uses one example
per update, in the corpus's recorded order, across a fixed number of epochs.
Both train and development-validation populations must be nonempty.

The experimental objective is the existing stage-balanced clean-motion x0 loss:
mean squared error for five root channels plus mean squared error for the
364 body/contact channels. It supports unconstrained supervision or observed
first/last poses. Observed channels are excluded from loss; endpoint supervision
requires at least one unobserved interior frame. This is a local experimental
recipe, not an NVIDIA-provided fine-tuning workflow.

Training draws noise and timesteps from the original full schedule. Only FP32
adapter factors receive standard AdamW updates. Every factor must have a finite
gradient; clipping is explicit and frozen base gradients are rejected. Nonfinite
updated factors, changed data or changed methods fail the attempt. All losses,
input hashes, timesteps, gradient norms and completed updates are retained.

Validation uses fixed per-example/per-timestep noise and an isolated random
generator with ambient Torch RNG restored afterward. It runs in evaluation mode
without gradients. Its losses describe denoising error, not prompt correctness,
contacts, realism, transitions or animator cleanup. No checkpoint is
automatically selected or promoted into Studio.

Checkpoints bind the exact corpus manifest, prompt tensors, example order,
training plan, noise schedule, implementation files, acquired model and caller
input files. Resume requires a pinned checkpoint manifest, matching bindings,
the same recorded runtime, and an epoch/example cursor consistent with the
completed step. Stop counts are absolute. Fresh attempt directories preserve
previous runs and failures. Source/evidence/target bindings are rechecked before
checkpoint publication; the initial state is also checked and saved.

## Offline entry point

`scripts/train_kimodo_adapter.py` uses the acquired pinned Kimodo checkpoint,
independently verifies the corpus with a CPU representation and validates
existing ActionEncoder caches. All reviewed prompts must have exact cached
conditioning; missing or conflicting embeddings are rejected. Only after these
checks does it load the CUDA denoiser and install the adapters. The entry point
does not acquire data, generate substitute supervision or encode missing prompts.

The JSON run plan has these fields:

```json
{
  "schema": "strep-kimodo-reviewed-training-plan-v1",
  "training": {
    "schema": "strep-native-adapter-training-v1",
    "seed": 91,
    "epochs": 10,
    "learning_rate": 0.0001,
    "weight_decay": 0.01,
    "gradient_clip": 1.0,
    "checkpoint_every": 10,
    "condition": "unconstrained",
    "validation_seed": 77,
    "validation_timesteps": [0, 500, 999]
  },
  "rank": 8,
  "alpha": 8,
  "corpus": {"path": "prepared-corpus/manifest.json", "sha256": "PINNED_SHA256"},
  "conditioning": [{
    "request": {"path": "action-job/request.json", "sha256": "PINNED_SHA256"},
    "manifest": {"path": "action-job/conditioning/manifest.json", "sha256": "PINNED_SHA256"}
  }]
}
```

Paths are resolved against the plan directory. Replace the placeholder hashes
with independently retained hashes of an actual reviewed corpus and its existing
conditioning caches. Multiple caches are supported. This example is a starting
configuration, not tuned hyperparameters or evidence of data permission.

```powershell
.venv/Scripts/python.exe scripts/train_kimodo_adapter.py training-plan.json reports/my-training-run
```

Use `--until-step N` for a planned interruption. Resume into a fresh output
directory with `--resume CHECKPOINT_DIRECTORY --resume-manifest-sha256 HASH`.
Keep the same plan and bound inputs. The wrapper runs offline under the shared
worker lock, records model/input hashes, archives imported source and retains
failure receipts. Windows/CUDA and the separately acquired dependencies remain
entry-point prerequisites. This is neither a portable trainer installer nor a
production inference adapter loader.

## Evidence and remaining work

All 155 focused CPU checks pass, including 16 trainer tests. They exercise
updates on verified fixture targets, split isolation, fixed validation draws,
exact same-process and fresh-process resume, plan/text binding, required
validation, endpoint limits, changed evidence, nonfinite gradients and cursor
rejection. Reviews, rights and the motion codec in these fixtures are explicitly
mock declarations; they are not human supervision or permission evidence.

The retained local canary `reports/kimodo-trainer-numerical-canary-v1` performs
four uninterrupted updates, a separate two-step prefix and two resumed updates
in a fresh Python process. All final adapter, AdamW and Torch RNG tensors match
exactly; continuation noise, timesteps, losses and gradient norms also match.
This is eight physical updates on a tiny CPU transformer with static prompt
tensors and a mock motion codec. Real Kimodo optimizer updates and real training
admissions remain zero. Inputs and run methods are hashed and archived.

The actual offline CLI also refuses a hash-bound copy of the existing
unreviewed packet as a corpus: it retains a failed receipt before creating a
trainer directory or loading the CUDA denoiser. No human review was fabricated
for that refusal test.

The unchanged previous commit `cb7de0c` passed all four Windows/Linux hosted
jobs in run `37018383922`. Trainer checks join the separate CPU CI selection;
the 169-file geometry selection and 15 JS suites are unchanged and were not
rerun for this isolated trainer addition.

Real reviewed licensed corrections and a development split are needed to train
the acquired model. Actual CUDA training/resume memory, generated motion,
learning curves, forgetting comparisons and independent human review remain
unverified. The denoiser still lacks scene/partner/finger channels. All 14 release
capabilities remain unapproved and the full project goal remains active.
