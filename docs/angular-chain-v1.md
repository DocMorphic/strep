# Bounded correction chain

`scripts/angular_chain.py` makes the existing angular correction studies reproducible as one bounded job. It accepts a declared list of completed contact-study exports and independently audited sources. This is a development CLI for those study artifacts; it is not yet a general character-file importer or an automatic Studio default.

Each case first verifies its completed files, source audit and original root/contact comparisons. A case with unresolved contact failures is retained as ineligible. A clip already passing the per-joint peak comparison is retained without running the solver. Otherwise, the runner selects the current largest angular excess using the existing branch-aware preparation, runs a bounded correction, and independently audits its exported motion before continuing from it.

The manifest fixes a maximum of eight correction blocks per case. Each block retains the existing solver's twelve-step limit, fixed proposal schedule, trust and pose bounds, and actual acceptance tolerances. An audit failure, no measurable decrease in total positive angular-excess score, or exhausted budget stops the case. A failed candidate cannot replace the last verified source. Partial results are explicitly marked; they are not passing exports. This score is a workflow progress measure, not a perceptual quality threshold.

The protocol pins every original source dependency and snapshots the transitive local Python imports plus the pinned Godot scripts. Existing output folders cannot be overwritten or silently resumed. The first preparation, `reports/angular-chain-development-v1`, caught a dependency-scanner bug when it attempted to parse a Godot script as Python. Its failure record is retained. The corrected preparation is `reports/angular-chain-development-v2`.

Reproduce into a new output directory:

```powershell
.\.venv\Scripts\python.exe scripts/angular_chain.py prepare reports/angular-chain-repeat --manifest benchmarks/angular-chain-development-v1.json
.\.venv\Scripts\python.exe scripts/angular_chain.py run reports/angular-chain-repeat
.\.venv\Scripts\python.exe scripts/verify_angular_chain.py reports/angular-chain-repeat reports/angular-chain-repeat-audit
```

The independent chain verifier checks the full declared population, case bindings, exact source-to-trial lineage and final selection. It performs fresh exported-motion and solver-projection audits for every completed block, and independently recomputes whether per-joint peaks remain above their references. A numerically passing label is invalid if unresolved peaks remain. Failed and ineligible cases stay in the report. Failed blocks are unapproved and do not become verified merely because their retention is correctly recorded.

The integration manifest deliberately contains five cases: the original dance rig01 source, original backpedaling sources on rig01 and rig03, the rig02 contact-failure source, and an already-passing dance output as a no-op control. This repeats known development inputs to test workflow integration. It does not create five new independent clips or provide held-out evidence.

Nine runner tests cover verified chaining, no-op and ineligible behavior, bounded attempts, audit errors, stale source artifacts, frozen-input failures and mixed-language snapshots. Four independent-verifier tests reject missing population entries, unverified final selections and false no-op passes, even when outer hashes are recomputed. Records: `reports/angular-chain-tests-v1.json` and `reports/angular-chain-verifier-tests-v1.json`.

The earlier motion limitations still apply: predicted contact labels are unconfirmed, tolerated penetration may remain, and reducing peak rotations does not necessarily improve rotation tails or perceived quality. No human rating, cleanup-time evidence, new training or release approval follows from successful workflow automation. Keep the project-wide goal and all incomplete release gates open.

The real integration run completed all five declared cases. Dance required two blocks; backpedaling on rig01 and rig03 each required three. The rig02 source was correctly excluded for its two unresolved contact-release comparisons, and the already-passing dance control launched no correction. The three final GLBs are byte-identical to their earlier manually chained results (`reports/angular-chain-reproduction-v1.json`). Eight blocks therefore demonstrate automation and reproducibility, not eight new motions.

The independent audit completed successfully at `reports/angular-chain-development-audit-v2/completion.json`: all five outcomes and all eight block lineages/exports passed their applicable checks. Numerical success covers three correction cases plus the no-op control; the fifth case remains contact-ineligible. This result does not remove the rig02 failure or any release gate.
