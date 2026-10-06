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
