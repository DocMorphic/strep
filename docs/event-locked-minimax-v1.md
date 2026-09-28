# Joint clearance correction with a fixed contact pose

The component sweep found no useful blend of the existing arm correction. A later single-witness approach probe preserved contact but moved penetration to another region. This study therefore considers all retained near-surface vertices and fitting times together.

`event_locked_minimax.py` solves a scaled minimax subproblem: reduce the maximum predicted vertex penetration, with a small squared control-step penalty. Surface distances are linearized at the current geometry. Original joint rotation balls, adjacent-frame edit limits and a separate norm ball on each control-joint step remain explicit constraints. The event's middle knots are locked exactly. Variables are scaled by the trust radius and distances by5 mm; the epigraph is not a permission to relax final quality thresholds.

Five focused tests pass: balancing conflicting witnesses, analytic-versus-numeric derivatives, unchanged event controls, a true joint-norm trust region and preservation of original hard limits. Evidence: `reports/event-locked-minimax-tests-v1.json`.

## Frozen development protocol

`study_event_locked_minimax.py` retains the existing30 fitting times, starting controls, authored fingers and original hard edit budgets. Initial correspondence records are reused only after their projected depths reproduce retained full-mesh results within1e-8 m. Subsequent rounds rebuild correspondence records from actual skinned geometry.

At most three rounds are allowed, with one-degree and then half-degree trust radii if the first attempt fails. Each solved proposal must preserve the whole event skin exactly, satisfy all hard edits and pass fresh full-mesh queries at every declared time. The worst sampled depth must decrease by more than1 micrometre to retain a development step. All source/target vertices within the retained contact margin contribute to the subproblem; fresh queries can discover new violations.

This is a different experimental objective from the earlier contact-objective restoration study. The local progress criterion is a decreasing global peak, not a guarantee that every frame improves relative to raw. Every per-frame raw-cap regression and every5 mm failure remains reported. No intermediate step is promoted to product output or declared physically valid.

## Initial numerical result

The first subproblem includes5,112 surface constraints. It converged in45 iterations,3.69 seconds, with minimum normalized slack about-3.95e-12 and a one-degree maximum control-joint step. It predicted peak depth24.422624→22.936829 mm. Fresh geometry measured22.845584 mm, retaining the first local step. Thirteen of30 samples still exceed5 mm, and the peak remains worse than raw21.622598 mm. `reports/event-locked-minimax-round1-audit-v1.json` independently recomputes the saved geometry maximum, decision, exact event-control lock, original control balls and adjacent edit limits, retaining every surface file hash. The remaining rounds and full exported evaluation are still running or queued.

The second one-degree step also converged and passed fresh geometry, with peak22.744015 mm versus its22.628787 mm prediction. The fixed final round is now running. This remains a local development improvement from the previous corrected clip, not a raw-baseline or quality pass.

The exact-owner continuation in `reports/event-locked-minimax-validation-v1` waits for study completion. If no step is retained, it exports nothing. Otherwise it uses a separate, hash-bound data adapter and the unchanged full exporter to retain raw and candidate assets, check integer/half-frame edit limits, test600 actual Godot actor-frames and audit299 samples per scene. It additionally compares the decoded event skin with the original candidate within1 micrometre. Queued checks remain unverified until they run. Triangle, self-collision, continuous-time, anatomy and human review remain separate requirements; all release gates are open.


## Fixed study complete

All three rounds finished. Fresh peaks24.422624→22.845584→22.744015→22.592042mm; final13/30 samples still exceed5mm and raw peak remains21.622598mm. Round3 took73 iterations, retained hard slack.358641, and exactly locked event controls. `reports/event-locked-minimax-final-audit-v1.json` independently checks all90 retained surface records, solver hashes, step radii and event coordinates. No extra rounds. Full600-pose/299-sample export validation is still running. Study exec21738 terminal0 consumed.

## Full export finished

The conditional exporter completed600 actual engine actor-frames and299 geometry samples for each of raw and candidate. Both decoded event skins match the previous candidate exactly(0.0m error). `reports/event-locked-minimax-export-audit-v1` independently checks completion/asset/engine/provenance links and recomputes both full curves. Raw peak21.622598mm(9failedsamples), previous24.422622mm(14), minimax22.592020mm(13). Minimax improves peak1.830602mm over previous but is0.969423mm worse than raw;12 sample depths increase over previous. No newly failing samples versus previous. Floor11.959117mm unchanged. Both5mm screens fail; no quality selection. Terminal75554 consumed.

Audit-script integration fixes: integer-bounds reports expose `passed` at top level; conditional export completion is owned by the wrapper, while inner progress remains at geometry299. The independent verifier initially rejected these format assumptions, then was corrected to check the actual wrapper completion and concrete artifacts. Export itself did not fail or rerun.
