# Moving-surface distance constraints

The static witness trial rejected one candidate and then stopped because a refreshed plane falsely excluded the original pose. This experiment retains source vertex identities but recomputes the closest target triangle, barycentric coordinates, normal and signed distance at every control evaluation. Only seven selected vertices are queried initially; the existing5,272 core rows and motion objective stay unchanged. Proximity query batches remain at most32 points. All control limits, frame caps and physical acceptance checks stay fixed.

`dynamic_contact_witness.py` differentiates the skinned source vertex and the current barycentric target point along the current distance normal. Closest-feature ties remain nonsmooth; this is not a general smoothness guarantee. Eight geometric tests cover independent finite differences of translated/rotated closed surfaces, both query directions, cache changes and malformed identities. Together with witness-selection and scaled-solver regressions,25 tests pass in4.50 seconds.

`reports/dynamic-witness-proof-v1` verifies the real120-control fixture at the original initializer and both rejected candidates. Seven distinct vertices across five times receive six fixed random directions and one largest-Jacobian coordinate, at three step sizes. All21 predeclared decisive checks (step1e-5) pass; maximum scaled error is6.5362e-9. Seven comparisons against retained actual distances agree within3.435e-16 m. All seven dynamic constraints permit the original initializer. The problematic frame74.5 vertex actually penetrates20.447437 mm, below its21.006530 mm cap; the static plane had predicted21.591152 mm. Initial evaluation of all seven rows took1.11–1.34 seconds locally. This is directional verification of selected contacts, not a full Jacobian proof or a motion-quality result.

The frozen `reports/dynamic-witness-cuts-v1/request.json` permits three correction rounds,60 inner iterations per round, original initialization and five-degree neighborhood. It begins with all seven verified identities, adds every newly violating identity after fresh full30-time geometry, and stops if there are no new identities or any true constraint excludes the seed. Each solved proposal is preserved. Added inequalities never change the motion objective's weights.

The trial is complete with no accepted step. `reports/dynamic-witness-validation-v1` records `exported:false`; no new engine or whole-clip export audit ran. Accepted steps would still require decoded edit limits,600 Godot actor-frames and299 samples per pair over the whole clip. Every release gate remains open; root/leg/floor repair, continuous-time collision and independent animator quality are not established here.

All three rounds reached their60-iteration limit; none claims solver convergence. `reports/dynamic-witness-comparison-v1.json` binds all candidates, witnesses and full30-time geometry, recomputes every guard, confirms the original parameters were retained, and verifies the skipped export.

| Round | Dynamic rows | Solve seconds | Peak penetration (mm) | Failing-frame regression |
|---|---:|---:|---:|---|
| 1 | 7 | 132.501 | 24.423714 | frame73.5 +0.034084 mm; frame74.5 +0.029383 mm |
| 2 | 9 | 171.053 | 24.667873 | frame74 +0.144517 mm |
| 3 | 10 | 244.093 | 24.732655 | frame74 +0.551337 mm |

The original peak is24.740384 mm. Passing-frame screens, peak/objective nonregression, event area/normals and hard edit checks pass in all rounds. Failure at other already-penetrating samples still rejects every proposal. Frame75 worsens in round3 but remains below the passing-frame5 mm screen; it is retained in the curves and is not labelled a guard failure.

A direct final-pose requery in `reports/dynamic-witness-coverage-v1.json` confirms that all10 constrained vertices meet their original caps. Three unconstrained nearby vertices at frame74 violate the cap. Their original depths were only0.873–1.113 mm below it. This distinguishes missing vertex coverage from the earlier stale-plane problem: true distances fixed the false seed infeasibility, but selecting only previously violating vertices did not bound the neighbouring surface.

`reports/dynamic-witness-seed-band-v1.json` retrospectively evaluates broader initial-pose selections. Bands0.5/1/2/5 mm below each unchanged cap select29/53/113/396 vertices and cover5/10/13/13 of the13 identities discovered in the trial. A2 mm band spans15 fitting times. This is a development diagnostic, not a conservative bound on moving surfaces or proof that a new solve will pass. The [separate expanded-band experiment](seeded-dynamic-witness-v1.md) now passes its preflight and is running with frozen selection and finite budget. It preserves the original objective and limits, and must still evaluate all fitting times and eventual whole-clip exports independently.
