# Preserve the existing HiGHS scheduler during support repair

Hosted source checks fail the same four native support-feasibility tests on Ubuntu and Windows at commit 838fc79. Each shard passes 2,085 other checks. The affected LPs return SciPy status 4 / HiGHS `Not Set`; this is a runtime failure, not evidence that their constraints are infeasible.

Two fresh-process regressions reproduce every failure after an earlier default LP or an explicitly two-thread LP. The repair then asks HiGHS for one thread. HiGHS owns a process-global scheduler and reports conflicting thread settings after initialization; this behavior is described in the [upstream HiGHS discussion](https://github.com/ERGO-Code/HiGHS/issues/810). The pinned [SciPy 1.15.3 implementation](https://github.com/scipy/scipy/blob/v1.15.3/scipy/optimize/_linprog_highs.py) forwards extra options and maps an unset HiGHS status to status 4.

The repair now leaves the scheduler's thread count alone. It does not reset global state or call private scheduler APIs. The LP objective, constraint populations, bounds, 20-second time limits, 1e-9 feasibility tolerances, 1e-10 secondary-phase slack and serialized native acceptance rules stay unchanged. This does not promise single-thread execution; the existing process-tree/RAM guards remain responsible for resource limits.

The original reproduction fails both outer cases, each with the expected four inner failures, in 7.18 seconds. The corrected six-module suite passes 185 checks in 78.13 seconds, including both actual fresh-process regressions, feasible/conflicting LPs, serialized cleanup/plateau behavior, native support fixtures, coordinate/roundtrip behavior, protected inequalities and independent triangle LP comparisons. This verifies the fix locally; the complete hosted rerun is a separate result.

Both guarded attempts retain complete logs and source snapshots. Independent policy replay verifies all 13 original and 80 corrected resource observations. The successful guard exits 0 after 82.453 seconds, with 196,919,296 bytes sampled peak RSS. The original failure is not deleted or relabeled as a pass.

No motion, model weight, native contact tolerance, existing study output or release approval changes. Source-test module inventory remains 422 Python / 41 Node. Raw logs and reproduction files remain under ignored `reports/highs-scheduler-regression-v1/`.
