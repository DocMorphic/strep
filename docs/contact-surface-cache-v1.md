# Exact skin-evaluation reuse experiment

The reference objective asks for the same posed skin vertices and analytic derivatives twice per evaluation: once for residuals and once for hard constraints. `CachedPatchFitter` is an experimental fixed-problem subclass that retains the last frame/parameter result. It copies its local-pose/spec inputs, copies the parameter key and exposes cached arrays as read-only. Rebuild the fitter if the rig or problem changes.

Two focused tests compare complete objective/gradient/constraint/Jacobian outputs bit-for-bit while changing frames, parameter values and neighbor/reference priors. They also verify that caller mutation cannot corrupt the cached pair or parameter key.

A paired benchmark evaluates 18 real prepared hold-pilot configurations, including frames with and without active contacts, with three timing repetitions and one numerical library thread. All output arrays are exactly equal. Median process CPU time is3.34375s uncached and1.671875s cached, a2.0x evaluation speedup. Another solver was active; process CPU timing reduces scheduling noise but is not an isolated full-fit measurement.

No production or live-worker code changed. No optimization was run by this benchmark and no quality threshold changed. A complete paired fit is still required before claiming end-to-end speedup or adopting the subclass in a default workflow. The ongoing uncached held-contact pilot remains the baseline.
