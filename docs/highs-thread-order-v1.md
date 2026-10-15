# HiGHS initialization order in geometry and correction workflows

The seeded crawl correction and its complete replay remain unchanged. A separate hosted regression exposed a solver-runtime problem in the older vertical-root test: an earlier default HiGHS solve initializes a process-wide scheduler, then the explicit one-thread root solve returns SciPy status 4, `HiGHS Status 0: Not Set`, before any candidate is exported. This is not a geometric infeasibility or a motion-quality failure.

## Reproduction and scope

The orientation suite passes alone on both [Ubuntu and Windows](https://github.com/DocMorphic/strep/actions/runs/38660260914), while the broad [Ubuntu shard with diagnostics](https://github.com/DocMorphic/strep/actions/runs/38660109300) reports the runtime status above. A local fresh-process probe reproduces the failure by starting a default SciPy LP before running the unchanged orientation suite: one failure, eight passes, and no exported polar proposal. Its 24.312-second guard and all 26 resource observations replay as a failure, not success.

The project-level reproducer uses `convex_colliders.direction_hull` first, then requests a one-thread LP in the same fresh process. It fails before the change with the same status 4/Not Set result. Its 18.235-second guard and all 20 observations replay as a failure. Thus the behavior is reproducible with actual project geometry code, without relying on test ordering in the full shard.

## Correction

Convex hull construction and the other previously implicit LP entry points in constraint restoration, contact-rate feasibility, grasp steps, inward steps, protected inequality steps and triangle verification now request one HiGHS thread explicitly. The vertical-root LP, Float32 root-grid MILP and existing explicitly single-threaded paths keep their original settings. Objectives, matrices, bounds, tolerances and complete decoded acceptance remain unchanged. No scheduler reset, hidden fallback or acceptance waiver is introduced.

`native_support_feasibility` is an intentional exception: its existing public contract supports a scheduler already started by a default or explicitly two-threaded external solve. It continues to inherit that scheduler. An initial attempt to force that API to one thread passed 212 checks but failed its two existing mixed-scheduler tests; that change was reverted byte-for-byte before publication. The failed batch is retained with its 87.157-second/88-observation resource trace. This exception is preserved rather than weakening the tests or resetting another caller's runtime.

The new fresh-process regression checks actual hull construction, a later one-thread solve and an independent barycentric triangle witness. It belongs to the full and focused source inventories. The fixed-choice focused workflow can run it on Ubuntu and Windows. Arbitrary third-party scheduler configuration is not globally overwritten; correction jobs should continue using their owned worker processes and declared resource limits.

## Validation

All **214 affected checks pass in 61.35 seconds**, after actual hull construction initializes the scheduler before the full batch. They exercise geometry, original affine/root export, constraint restoration, contact-rate/grasp/inward/protected steps, native support compatibility, triangle checks and the new ordering reproducer. The guard completes in 79.032 seconds, peak sampled process-tree RSS 709,140,480 bytes, with all 80 resource observations replayed. The source inventories validate at 510 Python/45 Node files and 74 Python/5 Node files in the focused suite; this is not execution of every inventory entry.

Because these checks import the installed PyTorch runtime for small CPU fixtures, the guard explicitly estimates/caps process-tree RSS at 1 GiB, retains the additional 600 MiB free-RAM floor and 15-second admission stability, and hides CUDA devices. No model or checkpoint is loaded and no GPU/inference/training job is run. Other CPU/model resource profiles remain unchanged. The wider seeded crawl trial and complete replay precede this separate LP-initialization correction; their original archived inputs, implementations and failures stay intact, and no expensive animation study is repeated for these LP option changes.

Evidence stays local under ignored `reports/native-polar-platform-diagnostics-v1`, `reports/native-polar-solver-order-v1`, `reports/native-highs-order-regression-before-v1`, `reports/native-highs-thread-validation-v1` and `reports/native-highs-thread-validation-v2`. Hosted complete regression success must still be checked after the fix. All fourteen release capability/calibration gates stay unapproved; the full-project goal remains active.
