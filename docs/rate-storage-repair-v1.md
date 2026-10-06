# Storage repair across positional and angular rates

The [registered repair experiment](axis-pair-repair-v1.md) stopped with two positional-acceleration violations because its planner proposed only angular-acceleration support. `scripts/native_rate_storage_search.py` adds a separately versioned planner for positional speed, positional acceleration, angular speed and angular acceleration. The older search and completed receipts remain unchanged.

The planner uses the original rate clock and exact derivative support: two pose samples for speed and three for acceleration. It finds every permitted rotation key that brackets those samples. Positional rates use strict ancestors of the measured joint: rotating a joint itself does not move that joint's origin. Angular rates also include the joint itself. All four quaternion components and both absolute neighbors remain available; existing choices can be restored or replaced. Duplicate choices from shared support are removed. Choices are finite guidance rather than a feasibility certificate.

The unchanged acceptance rules require fixed continuous controls, original control boxes, every native actor/time, original caps and scales, exact reported versus independently decoded residuals, original track limits and the acknowledged absolute storage envelope. Every exported probe remains archived. The greedy search accepts only a passing result or a strict improvement in its original native merit. It may exhaust its budget or stop without finding a solution.

`scripts/native_rate_axis_pair_repair_job.py` wraps the existing registered-study preflight and explicitly resumes a completed, independently replayed repair. The outer schema is `strep-native-rate-axis-pair-repair-job-v1`, with these fields:

- `base_request`, `resume_result`, `resume_replay`: each contains a file `path` and exact `sha256`.
- `settings`: integer `maximum_stages` from 1 to 8 and `maximum_probes_per_stage` from 1 to 64.
- `label`: a nonempty name for a separate diagnostic clip.

The original registered request, selected fraction, controls, inputs, current and archived implementation, every probe/artifact, and complete independent rate/static/reference replay must match. No receipt schema is relabeled. The resumed start must export exactly the saved final probe's bytes, worlds and residuals. Source and resume artifact populations and bytes remain immutable after preflight. New output must be fresh and outside all bound study directories.

With the required completed local receipts and original assets available:

```powershell
python scripts/native_rate_axis_pair_repair_job.py --request reports/rate-axis-pair-repair-v1.request.json --output reports/offline-rate-axis-pair-repair-v1
```

These ignored inputs and generated outputs are not bundled in the public repository. A standalone header cannot substitute for the original assets and complete artifact population.

Final geometry and separately appended clips are produced only after stored motion and original reference bounds pass. Original clips remain selected. Export success, parser tests and successful constraint repair do not establish realistic motion, collision-free geometry, engine playback or human cleanup time.



## Completed generated-fixture experiment

The resumed full-step proposal retains all ninety continuous controls, **1707 native samples** and **1673 geometry times**. The initial 35 absolute storage choices become 43, within the unchanged 64-choice policy. Eight accepted stages test **81 neighbors**, retaining **82 complete actual exports**. Every export still has two stored-motion violations and zero contact violations. Original reference bounds pass.

The largest normalized positive excess falls from **4.6448720645814974e-5 to 4.058848724422138e-5**, a **12.616566%** reduction. Squared positive excess falls from **2.3673429535011585e-9 to 1.857284600642522e-9**. The search exhausts its eight stages without passing motion. No final geometry audit or appended clip follows this failed gate. This numerical reduction is not evidence of better-looking animation.

A separate consumer manually reconstructs all 82 probe payloads, fixed controls, native worlds, residuals and absolute choices using the legitimate original replay context. It recomputes original rate arrays and Float64 static references and matches all final reference bounds, without importing the repair, search, storage, job, model or proxy implementation. No receipt is normalized into another schema. A second replay-bound audit independently reproduces every merit vector and the acceptance threshold for each of the eight stages.

**31 planner/native-evidence tests** and **24 resume/protocol tests** pass with zero skips. Coverage includes every metric and first/last sample stencil, irregular key bracketing, strict versus inclusive ancestors, duplicate choices, restore/replace behavior, real GLB preservation, original cap/actor/clock/residual rejection, pinned replay/static/rate/reference bindings, immutable output boundaries, and input-byte/population mutation. Protocol fixtures do not claim completed model/solver replay. The actual experiment above is separate evidence. Both suites join Linux/Windows CI; hosted success is not claimed.

The current finite search accepts the first strict merit improvement. This trace shows slow progress under its stage budget; it does not prove the remaining two violations are infeasible. The next experiment should compare stronger candidate ordering or best-improvement while preserving all original acceptance gates and recording every failure.

Collision-free motion, production-character realism, arbitrary action correctness, engine playback and animator cleanup remain unverified. All fourteen release evidence arrays stay empty; the full-project goal remains active.

Immutable ignored local receipts:

- Complete all-rate repair: `2d1cd0863c7c05556664312c843cc4c0e34242d679c7ac3525d984833f3d7d4f`.
- Independent every-probe replay: `15ddc471236ff89c04a26a2dbee8c44d1dac62c6a3887480fde227245608d774`.
- Independent merit/stage audit: `650695e9a60efe2191a4bfdf62fb0f123e2e6d6c0deef21675179760223ccc39`.
