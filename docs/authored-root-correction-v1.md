# Root correction with authored-target preservation

The new adapter produces experimental root-translation corrections for real Studio contact edits. It retains all rotation channels and unrelated animation channels exactly, including finger poses. Seven of ten contact jobs produce a lower-acceleration-energy candidate that passes the declared exported preservation checks. Two have no useful improvement and one reaches the solver iteration limit. Five joint/posture jobs retain their fixed body/root unchanged. All 15 original outcomes, failures and repeated development jobs remain in the population.

This is one component of the general editing workflow. It is not a complete pose/interaction correction system, a quality approval, or a new held-out study. No UI or server behavior changed.

## Method and evidence

`scripts/authored_root_correction.py` prepares and runs a frozen study from the prior authored-intent intake. It changes only the sampled root-translation channel. World displacement at keys and midpoints accounts for the animated root parent and exact float32 key clock; skin influence weights propagate displacement to actual vertices. Convex constraints preserve achieved contact positions and within-interval movement, sampled vertex floor depth, original root edit budgets, a 10 mm additional correction radius, and the first/last two samples. Per-sample root acceleration cannot increase in the proposal. The objective reduces squared root acceleration with a small displacement regularizer.

The predeclared export allowances are 1 micrometre in position, 2 micrometres for differences of root edits, and 0.0036 m/s² in root acceleration (four position-error contributions at 30 fps). These are numerical serialization allowances, not realism thresholds or changed earlier-study tolerances. Final exported rotations must remain unchanged; lower objective and all declared guards are required before selecting a candidate. Four fractions are available; all seven selected candidates use the full proposal. Solver status alone does not select a candidate.

`scripts/verify_authored_root_correction.py` separately decodes selected GLBs, recomputes target/floor/root checks without solver matrices, verifies channels, and runs real Godot imports. All seven candidates pass that limited audit. All 15 selected outcomes import with 1,451 actor-frames reproduced. Original rejected statuses are retained. Seven tests pass: four affine/export/scope tests and three independent-audit tests, including a translated clip that breaks authored targets and a changed rotation channel.

Artifacts:

- `reports/authored-root-correction-v1`: frozen inputs, transitive implementation snapshot, all proposals/exports/checks and selection records.
- `reports/authored-root-correction-audit-v1`: separate geometry/target audit, Godot records, verifier/test snapshot and test results.
- `reports/authored-root-correction-audit-v1/patch-dynamics.json`: additional whole-clip patch-acceleration measurements, outside the root-only acceptance rule.

## Results and remaining tradeoffs

| Job suffix | Root peak before → after (m/s²) | Result |
| --- | --- | --- |
| 195412-bf0e8a1d | No useful change | Original retained |
| 195612-5047106e | 13.446 → 10.284 | Head target and sampled floor preserved; still above original unedited root peak 3.987 |
| 195952-76bed1e3 | No proposal | Solver reached 150 iterations; failure retained |
| 202244-c3c3bb14 | 17.679 → 16.264 | Existing floor failure remains, approximately 9.958 mm |
| 205132-5726f4ae | No useful change | Original retained |
| 210755-7717c78e | 22.845 → 18.737 | Foot-patch acceleration peaks increase by as much as 7.148 m/s² |
| 224112-ad9494b0 | 1.695 → 1.596 | Right forefoot peak increases by 0.227–0.239 m/s² |
| 224245-27ed02e6 | 19.363 → 16.435 | Existing floor failure remains, approximately 7.012 mm |
| 224821-4b3059cc | 1.695 → 1.596 | Repeated development case; same forefoot tradeoff |
| 225025-7cb4f8f4 | 23.051 → 17.402 | Existing floor failure remains, approximately 6.344 mm |

Root smoothing can improve root acceleration while worsening a foot patch's acceleration. Three selected cases exhibit this limitation; two are repeated instances of the same case. No candidate is promoted as release-ready. The next solver revision must explicitly preserve relevant patch dynamics across the whole clip and contact boundaries while preserving the same authored targets. Keep this complete root-only study unchanged as the comparison. Full pose correction, arbitrary joint-target integration, scene/partner constraints, animator review and broad release validation remain open.

## Concurrent studies

Whole-support now has 17 of 24 completed cases; the independently captured report is `whole-support-breadth-interim-v17`. The original partner solver completed its three planned iterations without reducing its recorded 24.740384 mm peak overlap. Its queued validator has exported and imported 600 actor-frames and is evaluating the full 299-sample raw/candidate geometry. The comparison waits on that exact validator. Runtime v54 verifies the remaining live owners and unchanged dependencies. None of these results completes the project-wide goal.
