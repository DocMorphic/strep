# Full-duration regional contact transfer

The next development trial runs on the complete 180-frame motion behind the earlier five-frame box fixture. It preserves the original approach, grasp interval (frames 60–121), release, object keyframes, contact patches, anchors and tolerances. It applies the same declared +2-degree local wrist-X perturbation throughout the source and changes the target primitive to the earlier box dimensions. There is no repeated-frame padding or newly generated action. The original short crop differs by at most 1.79e-7 in rotation elements and 5.97e-8 m in positions because of reconstruction precision.

The fitter starts from this full perturbed source, not the corrected five-frame candidate. Its hard budgets are relative to that source, rather than the older sphere solver's cumulative reference. The recorded configuration is six stages of 100 iterations, a 3,600-second budget, balanced regional penalties, stage-wise witness refresh, full object-vertex coverage, per-vertex object multipliers, the earlier 0.05 mm clearance and 0.01 mm contact-gap solver margins, and sampled export-rate constraints with a 0.05% acceleration margin. All acceptance limits remain unchanged.

The prescribed box track has a conservative floor lower bound of -0.799555 mm. This bound does not prove actual penetration, but it does not certify the requested clearance. Actor-only fitting cannot fix the object trajectory. The fixture preserves and reports this condition; any later object-placement edit must be a separately named scene treatment.

## Exact sparse skin calculation

The optional `--skin-backend sparse` compiles fixed skin weights and inverse-bind points into a sparse linear map from joint affine transforms to vertices. Duplicate coefficients are summed and exactly zero coefficients omitted. All vertices and all nonzero influences remain. This avoids allocating the large frame-by-vertex-by-influence rotation tensor. The default backend remains `gather`.

On all 180 frames, 18,056 vertices and eight influence slots of the retained motion, maximum position discrepancy is 8.89e-16 m and maximum transform-gradient discrepancy is 7.11e-15. Five-frame chunked forward/backward timings were 2.179 s for gathering and 0.403 s for the sparse map; the full sparse batch took 0.330 s. These are local kernel measurements, not whole-solver speed or peak-memory claims. The running full fit was observed using approximately 1.5 GB RSS; this is an observation, not a measured peak.

The existing three-stage, 40-iteration short sphere repair reproduces every native array and the candidate GLB bit-for-bit with sparse skinning. It retains 34/34 contact, 17/17 geometry and original edit-bound passes. Actual Godot checks pass ten actor-frames across source/candidate exports and 77 joints, with maximum position discrepancy below 0.211 micrometres. The focused regression suite passes 72 tests; three new rate-audit tests and two process-identity tests pass separately (77 distinct tests total).

## Full-motion validation

The full fit is running; its contact, geometry, temporal and engine results are not yet known. A completion process is bound to the numerical worker's PID and creation time. It never retries fitting. Once that exact owner exits successfully, it will audit decoded quarter-frame geometry and original edit bounds, record per-joint rates, and import all source/candidate frames into Godot. Missing or failed fitting output remains a failure.

`audit_scene_joint_rates.py` reports each joint's peak and its sample location over the whole clip, approach, grasp, release, and two-frame neighborhoods around each contact boundary. Speed samples are located at edge midpoints and acceleration at stencil centers; overlapping windows are explicit. An unchanged global maximum cannot hide local increases in this report. These diagnostics do not create new acceptance thresholds or infer naturalness.

Evidence is retained in `reports/linear-skin-full-clip-v1.json`, `reports/region-sparse-sphere-regression-v1`, its adjacent audit, `reports/region-sparse-engine-v1`, and `reports/region-full-transfer-v1`. The latter contains the immutable authored fixture, full input, fitting protocol and implementation snapshots. No human, held-out, additional-action or release approval follows. All 14 release capabilities remain open.

Reproduce with `prepare_region_transfer_study.py` in a fresh report directory, then `fit_scene_regions.py` with the configuration above. The fixture builder requires the preceding local development assets. `verify_linear_skin_operator.py` independently compares a supplied native motion against gathered skinning; `audit_scene_region_fit.py` and `audit_scene_joint_rates.py` consume a completed fitting directory. Weights and generated artifacts remain excluded from Git.
