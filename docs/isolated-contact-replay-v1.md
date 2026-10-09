# Complete contact replay in separate processes

The complete frozen-source independent V8 replay now passes. Both recorded retained windows, 75–77 and 117–119, reconstruct without changing any numerical auditor or tolerance. V8 stage 2 is the latest verified retained contact state. This is verification of incremental corrections, not approval of the animation: complete physical and keyed passes remain **0/62**, and thirteen of twenty-one contact windows remain unattempted.

## Why process isolation was needed

The previous admitted replay ran every auditor through `runpy` in one Python process. It completed stage 1's local reconstruction—74 window records, 222 native poses, eight accepted steps and 96 proposal archive files—then the available-RAM guard stopped its owned process tree. Its sampled peak was 1,954,787,328 bytes; free RAM reached 572,342,272 bytes, below the unchanged 629,145,600-byte floor. All 92 resource observations independently replay. The complete replay and V8 adoption were still pending at that point.

Those auditors retain large proposal and geometry populations in their module namespaces. The new `scripts/isolated_python_replay.py` runs each complete auditor in a fresh Python process, waits for its actual exit and releases that process before starting the next phase. It does not divide the population into favorable subsets, substitute newer proposal-array transport into the archived math, change metrics or lower admission estimates. Other applications affect laptop headroom, so one successful run does not prove a general memory or speed improvement.

## Frozen numerical methods and evidence

The six local/interval/summary scripts are byte-identical copies of the prepared frozen auditors, placed in new report directories. The copied batch verifier changes exactly two report-path literals to read the new directories and save a new result. Its checks are unchanged. All original source bindings are retained, along with the copies, launcher and owned-process cleanup helper: **1,335 bound source files**, including the original 1,318-module snapshot. The frozen `strep` and eight required numerical modules are preloaded from that snapshot in every fresh child. This experiment uses the cached isolated Python 3.10 environment without Torch.

The runner requires a fresh execution folder and rejects existing phase outputs. It verifies complete source bindings before and after every child, requires all declared outputs and pins their hashes. Later phases cannot silently change earlier completed reports. A nonzero exit, missing output, changed binding or timeout prevents publication of a complete result. Timeout/exception handling stops the owned child tree and lets its `Popen` owner reap the parent. The runner accepts trusted local Python replay scripts; it is not an upload sandbox or a numerical auditor itself. Its false quality/release fields remain explicit.

**13 focused tests pass in 11.12 seconds**, covering actual fresh process IDs and frozen imports, independent module state, child reaping, timeout/descendant termination, existing-output preservation, incomplete/nonzero phases and source/output tampering. The complete model-free inventory is now 421 Python test modules and 41 Node suites; previous coverage is retained.

## Actual native replay

The first isolated admission attempt defers without a child after 60.703 seconds; all 61 resource observations independently replay. The second admits after 35.391 seconds, including the required three-second stable interval, and completes all seven phases with exit zero. All seven child processes have exited and been reaped. The guard finishes in **129.735 seconds**, with a **1,976,754,176-byte** sampled peak and **126 independently replayed resource observations**. The unchanged full-audit profile remains 2 GiB plus 600 MiB admission, 600 MiB available-RAM floor, 7 GiB process-tree cap and 1,800-second execution limit.

| Stage | Local windows / native poses | Accepted steps | Margin attempts | Correction proposals | Proposal archive files |
| --- | --- | --- | --- | --- | --- |
| 75–77 | 74 / 222 | 8 | 8 | 16 | 96 |
| 117–119 | 4 / 12 | 1 | 4 | 0 | 12 |

Both stage interval auditors independently reconstruct the complete 62-key interval plus exterior frames 59 and 122, complete native eight-weight skinning, source/reference/root/rig rows and physical audits. The batch verifier checks the ancestral chain, window selection, all **22,720 original rows per stage**, zero original passing loss, zero protected failed-row regression and exact preservation of earlier edited poses. The recorded penetration reductions in [V8's native study](contact-interval-batch-v3.md) are now independently verified.

The worst remaining penetration is still **24.831 mm at frame 71**. Normal and object checks fail at all 62 keys, point checks at 27, and reference-position checks at nine. The second window's `linear_start_unavailable` remains a search failure, not proof of nonlinear infeasibility. No between-key/full-clip, import, semantic, effort, human-review or cleanup approval is inferred. All fourteen release capabilities remain unapproved, and the full-project goal stays active.

Local immutable evidence remains under ignored `reports/box-lift-interval-batch-v8/`, including the interrupted one-process attempt, both isolated admission attempts, source copies, seven phase logs and complete outputs. No credentials, weights, third-party assets or raw studies are published.

| Final artifact | SHA-256 |
| --- | --- |
| Isolated replay protocol | `bb26e020799935e5b8860d84ec44d2e737caca017a5a58d53c577360d3708b51` |
| Isolated execution result | `fa9d89c469602a07b017ba31a6acd09562d4b23d0d9a98267cc568a2f5c47d80` |
| Independent complete batch replay | `31d3c4f0a2934b5b08324d2f124683f00ee00e3f5dd52412678bcbb10842f2d9` |
| Final guard protocol | `496da281b4fe3261faef64ddf4cacbbd823e2873b5471084d21ce3fa715fb1a9` |
| Final resource trace | `d5ba19bc17ea900b4376858e925a8452a17f3087e5c33d46c8fce8a7ca486aa7` |

The predeclared alternative proposal-solver native diagnostic is attempted next under the unchanged 2 GiB plus 600 MiB fit profile and fifteen-second stable admission. It defers without a child after **60.688 seconds**; all **61** resource observations independently replay. Its deliberately fixed V7 input preserves the earlier comparison plan even though V8 is now verified. No new conic fit, improvement or adoption is claimed.

Continue that diagnostic when admitted, remaining contact coverage, explicit load/effort authoring and broader actions, rigs, editing, style, transitions and engine validation. The developer review packet still needs actual ratings and cleanup trials. The running Studio backend is not restarted and live delivery is unverified.
