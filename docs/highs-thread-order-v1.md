# Respecting the process-wide HiGHS scheduler

The seeded crawl correction and its complete replay remain separate from this runtime issue. Hosted regression found that an older vertical-root solve can return SciPy status 4, `HiGHS Status 0: Not Set`, before any candidate is exported when a different HiGHS solve has already initialized the process scheduler. This is not geometric infeasibility or animation-quality evidence.

## Evidence and earlier attempt

The orientation suite passes alone on both [Ubuntu and Windows](https://github.com/DocMorphic/strep/actions/runs/38660260914), while the broad Ubuntu shard reports Not Set. A local fresh-process probe starting a default SciPy LP before the orientation suite reproduces one failure and eight passes. Its 24.312-second guard and all 26 observations replay as failure. An actual project hull-then-one-thread LP reproducer also fails before correction; its 18.235-second/20-observation trace is retained.

The first attempted correction made implicit project LP starts explicitly one-threaded. An initial batch passed 212 checks but broke two existing support-API tests that intentionally inherit an external scheduler; that API change was reverted. The adjusted batch passed 214 checks in 61.35 seconds (79.032-second/80-observation guard). However, the larger [hosted shard at bb05f55](https://github.com/DocMorphic/strep/actions/runs/38661453545) still failed with the same Not Set status. Controlling some project initializers is insufficient when another component starts the scheduler first. Those passing focused checks do not close the broad failure.

## Shared-runtime correction

Project LP and MILP calls now inherit the existing HiGHS scheduler instead of trying to change its thread count. This extends the already-tested native-support behavior to geometry, root/grid, feasibility and restoration paths. It introduces no global reset, retry or alternate numerical model. Objectives, constraint matrices, bounds, tolerances and decoded acceptance are unchanged; the root-grid MILP keeps its existing 60-second limit.

Root reports now use `solver_threads: null` and `solver_thread_policy: inherit_process`; they no longer assert a thread count that cannot be guaranteed in a shared process. CPU thread count is inherited, while owned-process RAM, free-memory and elapsed-time guards continue to enforce the declared resource profile. The earlier root-only measurements retain their original archived implementation and metadata; they are not rewritten under the new policy.

The stronger regression starts a default or explicitly two-threaded external LP in a fresh child process, then runs project hull construction, the actual affine root-export test and an independent barycentric triangle witness. It checks public solver composition rather than assuming that a later caller can replace another caller's scheduler. The same fixed-choice focused workflow runs this regression on Ubuntu and Windows.

## Validation

All **229 combined checks pass in 161.58 seconds**, covering the default/two-thread scheduler cases, original root/affine exports, geometry, constraint/rate/grasp/inward/protected/support/triangle paths and selected-track correction/replay. The guard completes in 179.516 seconds with peak sampled RSS 725,880,832 bytes; all 179 resource observations replay. The CPU fixture guard estimates/caps process-tree RSS at 1 GiB, retains the additional 600 MiB free-RAM floor and 15-second admission stability, and hides CUDA devices. It imports the installed PyTorch runtime for small CPU fixtures; no model/checkpoint, inference or training is loaded. Other CPU/model resource profiles remain unchanged. Inventories validate at 511 Python/45 Node files and 75 Python/5 Node files in the focused suite; inventory validation is not execution of every listed test.

The [complete contact/rig regression at 7f2901e](https://github.com/DocMorphic/strep/actions/runs/38667441812) now passes all eight Ubuntu/Windows jobs, covering both contact/rig shards, lineage and game packages on each platform. This supplies the hosted compatibility confirmation missing from the earlier focused/local runs. The separate [model-free source workflow at 7f2901e](https://github.com/DocMorphic/strep/actions/runs/38667441732) also passes all twelve Ubuntu/Windows jobs; source tests do not establish animation quality or release readiness.

Evidence stays local under ignored `reports/native-polar-platform-diagnostics-v1`, `reports/native-polar-solver-order-v1`, `reports/native-highs-order-regression-before-v1`, `reports/native-highs-thread-validation-v1`, `reports/native-highs-thread-validation-v2` and `reports/native-shared-solver-and-track-validation-v1`. All fourteen release capability/calibration gates remain unapproved; the entire-project goal stays active.
