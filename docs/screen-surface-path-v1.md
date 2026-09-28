# Matched screen-preserving path experiment

This development comparison addresses the rejected proposals recorded in `docs/bounded-path-guard-diagnostic-v1.md`. It keeps the first declared seed (1301), source body motion, separately authored finger layer, v2 event initializer, five-control basis, fitting frames, three outer iterations, 60 inner iterations, trust region, eight backtracking trials and exact edit limits from the strict wider-path experiment. It does not select a new seed or change a final quality threshold.

The new step-selection rule checks actual surface queries at the fixed fitting samples. Samples already within the existing 5 mm collision screen must stay within it; already-failing samples cannot worsen, and neither can the overall peak or fitting objective. The actual event palm regions must retain three nearby points in both directions, a realized source/target triangle area of at least 25 mm² within 3 mm, and opposing normals within 20°. The original strict experiment remains intact. An accepted optimization step can still be a failing animation.

The other implementation change is an analytic skin Jacobian at exact integer frames. Fractional samples retain the original export-compatible interpolation and finite differences. `reports/fast-path-skin-v1` compares both actors, two parameter settings, nine frames and 96 skin vertices: 36 comparisons. Maximum position disagreement is 4.44e-16 m and maximum Jacobian-element disagreement is 4.77e-10. The median active-integer local benchmark is 11.16× faster over three repeats on the busy laptop. This is not an end-to-end solver speedup. Request, source implementations, results and completion evidence are retained; the benchmark exited successfully.

`run_screen_surface_path.py` freezes its inputs and implementation before waiting for the exact original completion/audit owner. It starts from the same original initializer, not the best rejected proposal. `refine_screen_path.py` records every attempted step and its contact/selection checks. The full existing completion adapter will separately reconstruct and export raw/candidate clips, verify edit budgets at integer/half frames, compare actual Godot imports, and audit all 299 integer/half samples per scene. Root, torso, legs and known floor failures remain unchanged by this arm-only method.

Nine focused selection tests pass, including rejected collision/energy regressions, loss of contact area or opposing orientation, invalid data and incomplete directions. Python compilation passes for the new runner/refiner/adapters. These are implementation checks. The queued experiment and its final exported motion are not yet validated; all release gates remain open.


## Solver finished; full exported comparison pending

The three fixed iterations finished at 2026-09-27T21:25:34 UTC. Each iteration accepted one safeguarded step. Sparse fitting-sample peak penetration fell from 23.465927 to 22.233281, 20.960328 and 20.913885 mm. It still exceeds the collision screen. Inner SLSQP solves reported positive directional derivatives; accepted backtracked candidates, rather than optimizer success flags, determine the recorded updates. Internal trial clipping warnings were retained.

The exact completion worker is now auditing both full 299-sample clocks and the actual exported assets. `compare_partner_paths.py` will verify matched initial parameters and fixed settings, source/engine hashes, all 299 samples, and any new or worsened failures outside the fitting samples. Six focused population/geometry tests pass; the completed strict audit also loads successfully. The queued comparison is tracked by `reports/partner-path-comparison-wait-v1`; no final full-path improvement is claimed yet.


## Full exported result: improvement is small and introduces an unsampled failure

Both full audits and the matched comparison are now complete. `reports/partner-path-comparison-v1` verifies the same raw assets, initialization, fixed settings, all 299 samples per variant, source/implementation hashes, and both actual engine populations. The revised export independently passes its edit/preservation bounds and 600 Godot actor-frame checks. Structural validity does not approve the interaction.

| Variant | Maximum body penetration | Peak frame | Samples over 5 mm | Maximum floor penetration |
|---|---:|---:|---:|---:|
| Raw pair | 21.6226 mm | 67 | 9 | 11.9591 mm |
| Strict retained initializer | 24.7404 mm | 66.5 | 14 | 11.9591 mm |
| Screen-preserving candidate | 23.9373 mm | 66.5 | 14 | 11.9591 mm |

The full-clock peak reduction is only 0.8031 mm, much smaller than the sparse fitting result suggested. Frame 69.5 newly crosses the existing 5 mm screen; it was absent from the fitting clock. Six sampled frames worsen numerically, with maximum increase 0.9328 mm (changes that remain under the screen are permitted by the selection policy). Event-point gap improves from 22.6281 to 19.4978 mm, while opposing-normal error increases from 5.1917 to 12.0063 degrees, still within the existing 20-degree event screen. Every variant still fails full-clip collision and floor acceptance.

A future trial must include the observed half-frame peak and new failure in its fitting/selection clock, and still run the complete independent audit afterward. This is a development-informed refinement, never held-out validation. More iterations on the same sparse clock would not establish protection between those samples. The current candidate is retained as a failed interaction; no scene, human, physics or release approval is claimed.
