# Matched contact search-step comparison

The current development box-lift still passes zero of 62 complete physical contact keys. Saved-pose recovery preserves useful improvements from an interrupted fit, but does not establish contact quality or completion of that fit's coverage window.

The next experiment compares normalized proposal search steps of 0.03 and 0.10, starting from the same independently verified recovered motion and the same completed V11 schedule. Each branch attempts one identical failing three-frame window. Both use the conic proposal backend, eight fit iterations, a 300-second local fit budget and ten proposal solve iterations. Original contact, object, floor, reference, joint and root limits, saved-pose checks and whole-interval retention gates remain unchanged. Search trust is an optimization parameter, not a relaxed physical tolerance.

The two branches share only an owned in-memory replay of their verified starting ancestry. The second cannot inherit the first branch's edited motion. Stored protocols, starting arrays including precision, complete original row labels/slacks, selected frames and fit budgets must match. Overall branch times are not comparable because the first includes full ancestry replay; per-fit budgets are matched. Coverage schedules remain branch-specific and neither branch is automatically promoted.

The comparison records metrics for the actually retained motion. A rejected proposal's improved diagnostics are not credited. Counts of passing contact keys are computed from per-frame checks; the existing all-keys boolean is reported separately.

Before execution, the unchanged independent local and complete-interval numerical auditors were copied and frozen for each branch. Their only adaptations are branch paths and eligibility of a completed branch after a later sibling stops. Completed outputs require separate numerical replay and resource/lifecycle verification before any adoption. Partial outputs remain diagnostic evidence.

The comparison helper, owned-session batch integration and recovery checks pass 102 focused tests. The new comparison suite is included in the Linux and Windows native CPU CI job. This is a development-fixture search experiment, not held-out evaluation, animator review, engine validation or release approval. All fourteen release capabilities remain unapproved and the single project-wide goal remains active.

Local artifacts are preserved under `reports/contact-trust-comparison-v1/`; generated poses and private fixture payloads are not published with the source.

## Execution and independently verified first branch

The first branch completes frames 102–104 at trust 0.03. Its local search takes 162.078 seconds, retains one backoff, and stops with `linear_start_unavailable`. The complete branch takes 923.734 seconds including history replay, baseline construction and whole-interval evaluation. It records 37 local observations, 22 proposal queries, two margin-start records and two correction records.

The producer begins the 0.10 branch from the same recovered parent using verified in-memory history reuse, but available RAM falls below the unchanged 600 MiB floor during baseline construction. The guard stops and reaps the worker after 952.516 execution seconds; its sampled peak is 1,164,054,528 bytes. Independent resource replay checks all 990 observations and the stop decision. The second branch has no completed fit/result. **The matched comparison remains incomplete; no setting wins or is automatically promoted.** The root comparison and second branch processing records remain raw interruption evidence, rather than being rewritten as completed experiments.

Three previously frozen independent auditors run in fresh Torch-free processes after the producer is reaped. They bind 4,633 source/artifact files and verify all 37 local records/111 native poses, one accepted step, five margin attempts, two correction proposals and 18 proposal archive files. Complete baseline/proposed geometry reconstructs all 22,720 original rows, boundaries, previous parameters and saved-pose retention without original passing loss or protected regression. Separate saved-array checks confirm exact recovered origins and preservation of all 177 unselected keys. The full-audit guard completes after 75.359 execution seconds, with a sampled peak of 263,327,744 bytes; all 487 resource observations replay. Admission still requires the full 2 GiB estimate plus 600 MiB reserve despite the smaller observed peak.

| Selected frame | Baseline penetration | Retained penetration | Retained left-hand orientation error |
|---|---:|---:|---:|
| 102 | 20.297 mm | 19.421 mm | 20.251° |
| 103 | 21.746 mm | 20.874 mm | 20.706° |
| 104 | 22.612 mm | 21.509 mm | 21.455° |

The original orientation limit is 10°. Complete physical and keyed contact passes remain **0/62**. Squared normalized row violation falls from 3107.173069317048 to 3086.784413388589; worst normalized violation remains 2.484240303152088. This is a modest verified saved-key correction, not a solved lift or motion-quality approval.

The completed 0.03 branch is now a verified diagnostic continuation state and has a separate complete schedule with **14/21 attempted windows and seven remaining**. The earlier recovery and V11 schedule remain the original starts for finishing the 0.10 comparison. Its interrupted branch does not advance coverage or become a resume state.

Editable baseline/candidate body-only GLBs contain all 180 keys at 30 fps and preserve the source mesh/materials/eight influences. The export checks fixed-skeleton reconstruction and serialization at every key, copies the upstream license and binds the independent audit receipts. Maximum position reconstruction error is 1.302 micrometres and maximum serialization position error is 0.102 micrometres. Object scene context, events, between-key contacts, dynamics, engine playback and human quality remain uncertified. Its guard completes in 12.812 execution seconds, with a sampled peak of 124,719,104 bytes and 77 independently replayed resource observations. No model generation or training is performed.

Key local receipts:

- Completed stage: `9f48f7f9e9db183f7afb96448eff74490d05b8146d0e528708ab561bde5b472e`.
- Complete branch/schedule: `ce2d24de78b2cab170e87072ac5f6674dc97a7049f8ca1627a283932050c3cb7`.
- Independent local replay: `32f4effebef11cc57024682225c57e29aea11d6f20c6dc11ca1548b76469732c`.
- Independent interval replay: `aae291e2e03641a586bd648156564abff54c93e626fee23f629f3ad306e69f9f`.
- Three-process audit execution: `5d30bfe151bb388938e238a08d4631a670494e6c57741cbb42e068034a745553`.
- Interrupted producer resource replay: `a1c4cc397469b6d433339d200fc936ede90bbed0af178fdf9379513f58358212`.
- Saved-array/record arithmetic: `5cc6b4df9a6fecb72e102a1cffefe644ae75147411efa9f7a977dd85c9102046`.
- Editable body export verification: `29406ce147db38ba50e49aed51663b122d524ec92c4af0a65b781b809acc8eef`.

All fourteen release capabilities remain unapproved. Actual ratings and cleanup trials remain absent, and current hosted CI is pending. Continue the larger-step branch from the same original parent/schedule in a fresh guarded directory, then compare independently verified results; continue broader action, scene/partner, rig, editing/style, transition, engine, dynamics and genuine review work under the single active project-wide goal.
