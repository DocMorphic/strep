# Faster exact support surface derivatives

The retained gesture fitter spends87% of its sampled objective-call time in `surface_jacobian` (0.148s of0.170s over12 profiled calls). The test rig has3273 vertices and27 parameters. This is an objective-call profile with other workers live, not an end-to-end inference benchmark.

The isolated `SparseSurfaceKernel` precomputes which skin vertices have any nonzero weight on descendants of each edited joint. It evaluates joint derivatives only there and leaves exact zeros elsewhere. It still computes every skin vertex and retains every floor/contact residual. Root influence weights are static and cached. No vertex sampling, approximate skinning, changed objective, or changed edit limit is used. Existing live fitters remain untouched.

`reports/sparse-support-surface-proof-v1.json` checks48 full positions/Jacobians/objectives across three rig proportions and the gesture, using zero, retained fitted and seeded random box-bounded parameters. All maximum differences are0.0. Objective-call median speedups are2.62,2.81,2.75,2.76. The full new source and dependent hashes are retained.

`reports/sparse-support-solver-proof-v1/completion.json` checks two fixed12-frame crops: gesture frames0–11 and backpedal frames14–25. Both use two sweeps,12 local optimizer evaluations, identical cropped context and original edit bounds. Dense and sparse runs have exactly identical parameters, solver records and convergence reports. Dense17.21/17.10s versus sparse7.65/7.59s, about2.25×. One SLSQP internal trial clipping warning was retained; neither implementation changes that behavior.

This establishes exactness on these numerical experiments and a useful local speedup. It does not establish full-clip convergence, runtime on another rig, animation quality, or a release gate. Use the new implementation in a separately frozen future study; do not replace source files inside running/queued experiments. Exec6204(surfaceproof) and69925(solverproof) finished exit0 and were consumed.
