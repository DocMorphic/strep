# Choosing the best checked rate-storage neighbor

The [first-improvement experiment](rate-storage-repair-v1.md) reduced the maximum normalized violation by 12.6% but exhausted eight stages with two motion violations remaining. `scripts/native_best_rate_storage_search.py` changes candidate selection while reusing its positional/angular rate planner and preserving the original native acceptance rules. Previous code and scientific receipts remain unchanged.

At each stage, it checks the explicitly budgeted prefix of planned absolute quaternion neighbors. A candidate qualifies under the original strict improvement threshold. Among qualifying candidates, the search selects the lowest `(maximum positive residual, squared positive residual sum)` in lexicographic order. Exact ties retain the first candidate. It may stop probing immediately on native pass because zero positive residual is already optimal for this motion gate. Geometry and animation quality remain separate requirements.

Every candidate still receives complete actor/time decoding and every original cap, scale, contact, control-box, track and storage-envelope check. Continuous controls stay fixed. A checked candidate may restore or replace an existing component neighbor; component steps never accumulate. This is best selection among eligible **probed** candidates, not an exhaustive search over all planned neighbors or nonlinear motions.

`scripts/native_best_rate_axis_pair_repair_job.py` uses schema `strep-native-best-rate-axis-pair-repair-job-v1`. It requires pinned `base_request`, `resume_result` and `resume_replay` files, explicit integer stage/probe budgets, and a diagnostic clip label. Its preflight binds the same registered study, original inputs, complete source/resume artifact populations, current and archived implementation, exact fixed controls and independent probe/rate/static/reference replay. Output must be fresh and outside all immutable study directories.

With the original completed receipts and assets available locally:

```powershell
python scripts/native_best_rate_axis_pair_repair_job.py --request reports/best-rate-axis-pair-repair-v1.request.json --output reports/offline-best-rate-axis-pair-repair-v1
```

The public repository does not bundle the ignored experiment receipts or asset payloads. A copied result header does not provide those dependencies.

The matched experiment starts from the same 35-choice, two-violation full-step result as the first-improvement experiment. Both retain ninety continuous controls, 1707 native samples, 1673 geometry times, the same original limits and the same eight-stage/64-probe ceilings. Actual query counts can differ because the earlier search returns at its first improvement. This comparison is not an equal-compute or timing benchmark.

Final geometry and separately appended diagnostic clips require passing stored motion and original reference bounds. Original assets remain selected and unapproved. Passing tests, lower numerical violations or successful export do not establish realistic animation, collision-free geometry, engine playback or human cleanup time.


## Source validation and running experiment

**61 tests pass**, zero skips. Tests cover later stronger candidates, stable ties, secondary merit, no improvement, explicit probe budgets, early native pass, every original rate support stencil, actual GLB preservation, pinned resume/static/rate/reference replay, and immutable output/input bounds. Synthetic selector/protocol fixtures do not claim a completed solver/model replay. Both suites join Linux/Windows CI; hosted success is unverified.

The matched study has started and its owned worker was verified live on 2026-10-06T23:00:32.830261+00:00. Its archived implementation matches current scientific source bytes. Results, independent every-probe replay and best-selection audit are pending. This source publication does not claim a completed comparison or improved animation quality.


## Completed matched result - 2026-10-06T23:37:01.592429+00:00

The completed comparison retains the same pinned start, all ninety continuous controls, **1707 native samples**, **1673 geometry times**, original acceptance gates, and eight-stage/64-probe ceilings. Best selection evaluates **512 neighbors** and retains **513 actual exports**. Every stage checks 64 candidates. The final result has **one stored motion violation**, zero contact failures and passing original reference bounds. It retains 43 absolute choices within the original 64-choice policy. Motion still fails, so no final geometry audit or appended clip is produced.

| Observed quantity | First improvement | Best checked improvement |
| --- | ---: | ---: |
| Actual neighbor probes | 81 | 512 |
| Final stored violations | 2 | 1 |
| Maximum normalized positive excess | 4.05884872442e-05 | 2.42571337646e-05 |
| Squared positive excess sum | 1.85728460064e-09 | 5.88408538476e-10 |

The starting maximum normalized excess is 4.64487206458e-05; the best result reduces it by **47.776530%**. These are constraint residuals, not ratings of animation realism. Different query counts prevent an equal-compute efficiency claim. The raw probe failure-count distribution is {1: 158, 2: 347, 5: 8}, including worse candidates; no failure was removed.

An independent consumer manually reconstructs every exported payload, fixed controls, native worlds, residuals and absolute choices with the legitimate original replay context. Original rate arrays and Float64 static references are recomputed and final reference bounds match. It imports none of the repair/search/storage/job/model/proxy implementations and never relabels a receipt. A second replay-bound consumer independently computes every merit, verifies every absolute single-neighbor transition, and checks that each stage selects the lowest eligible probed merit with stable ties. It also verifies identical pinned starts, controls, start GLB payloads and budget ceilings against the first-improvement study.

The **61 source tests** remain passed, with zero skips; no completed expensive study was rerun for this publication. Hosted CI success is not claimed. All raw results and older receipts remain immutable.

This is one generated cube-skin matched experiment. The finite prefix excludes some planned candidates, and the eight-stage limit does not prove infeasibility. A remaining motion violation prevents asset approval. Collision predicates, physical plausibility, production humanoids, action correctness, engine playback, animator ratings and cleanup time remain unverified. The next investigation should diagnose the remaining violation and sensitivity to candidate-prefix ordering under the existing limits. All fourteen release arrays remain empty and the full-project goal stays active.

Immutable ignored local receipts:

- Producer: `42ab33518863b202251311d87ac2d123231de93d9518bb668bdb6192bfbdc7fc`.
- Independent every-export replay: `842f6160cabdf4e1070e338a7e9aa3612c78320d9d2872d26487528e98fffdb5`.
- Independent best-selection and matched-start audit: `c2058b6986f0e581b36f76fdff7e6f10d889019ce3c3dcc7e92d15321138c930`.
