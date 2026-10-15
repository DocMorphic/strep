# Bounded native skin-floor workspace

Native interval floor evaluation now bounds its largest gathered skin-matrix tensor to 64 MiB. It retains every original triangle-referenced vertex, skin influence, plane and geometry time. The original floor limits, row order, source-rate caps and acceptance decisions remain unchanged. This is a memory-allocation change, not temporal or spatial decimation.

Previously each call gathered 32 frames of Float64 3-by-4 transforms for every used vertex and influence. The real SOMA high-five asset has 18,056 vertices and eight influence slots, giving a 443,744,256-byte gather. The new planner uses four complete frames for this asset, giving a 55,468,032-byte gather. If even one complete vertex population exceeds the workspace, evaluation also tiles vertices. It rejects an insufficient budget for one complete vertex rather than dropping influences.

Each tile reduces full plane distances. Strictly better minima replace earlier minima, preserving the first original vertex on ties just like a single `argmin`. Output plane/time order, witness IDs and penetration addition remain unchanged. The 64 MiB limit covers the gathered matrix tensor, not the complete process: source models, worlds, archives and other arrays still require admission and supervision. External RAM changes can still stop a worker.

All **50 targeted checks pass in 160.57 seconds**, including new tile-budget checks, complete time/vertex coverage, first-witness ties, loaded unnormalized weights, exact agreement with the old full calculation and actual native-export floor replay, plus selected-track, contact-completion and interval-workflow regressions. The guard completes in 176.813 seconds with peak sampled process-tree RSS 149,569,536 bytes; all 176 observations replay under the 512 MiB CPU profile and unchanged additional 600 MiB free-memory floor.

## Measured motivation and retained failures

The separate high-five hand experiment predeclares a contact-only bounded pose solve and three symmetric quintic native-control windows with half-widths 0.2, 0.5 and 1 second. It edits only A's right shoulder/arm/forearm/hand, at 10-degree per-track bounds and 50-mm maximum joint displacement, with a 0.5-mm search reserve inside the original 30-mm contact limit. Root, original source-rate arrays and other actor bytes stay fixed. Proposal guidance omits floor cones; every returned curve is still checked against the original actor-A floor policy. Pair crossing/containment, anatomy and legacy orientation constraints are not certified by this experiment.

The pose solve reports success after nine iterations. The first exported 0.2-second curve meets all three point conditions, with a 29.500011-mm hand gap, but **15 original rate failures and 2,017 failed actor-A floor times** keep it rejected. No floor condition worsens and root error is zero. Meeting this old 30-mm point tolerance does not establish a physically convincing high-five or a release-level contact pass.

The first worker stops during the second curve when external available RAM falls below the unchanged 600 MiB floor. Its peak sampled process-tree RSS is 753,618,944 bytes, below its 768 MiB cap; the recorded stop reason is `available_ram_guard`. All 159 observations replay. Its completed first case, partial second case and unstarted third case remain intact. The memory change above is being checked against its saved exact arrays before any continuation reuses results. No new pose solve or undeclared replacement windows are planned.

The full two-actor Studio/Godot study separately defers after its 600.281-second admission window, without starting a worker. All 596 admission observations replay. Its existing 2 GiB estimate plus 600 MiB reserve remains intact; no engine, scene ZIP or game package result is claimed from that deferral. Records remain local under ignored `reports/native-high-five-hand-seeds-v1`, `reports/native-floor-tiles-validation-v1` and `reports/high-five-studio-weight-export-v1`.

All release capabilities and calibration gates remain unapproved. The broader goal still requires useful motion, complete interactions, actual engine validation and genuine review.
