# Full-vector constraints for penetrating partner surfaces

The coupled high-five fit now checks the full three-dimensional separation to a moving partner-surface point. This addresses the [measured frozen-direction failure](coupled-pair-reserve-v1.md): the old scalar projection could accept tangential movement even when actual penetration exceeded the per-time allowance. The source motion, original limits and final acceptance thresholds remain unchanged.

## Constraint and scope

Each retained penetrating witness has a point on a target triangle expressed by barycentric weights. The distance from the source vertex to this point is at least its distance to the nearest point on the target mesh. Bounding that full distance therefore conservatively bounds the penetration depth of that vertex, provided the target point remains on the mesh. Small numerical negative barycentric weights are projected to nonnegative weights and normalized; invalid bindings are rejected.

The new norm rows include both actors' movement, in a consistent A-then-B parameter order. Common translation cancels. The solver bounds the norm of the affine separation vector with a second-order cone. This is still a local approximation to nonlinear skeletal motion: neither the derivatives nor the affine norm certify the exported mesh. Outside witnesses keep their existing scalar gap rows; forcing an outside point to remain close to the surface would needlessly restrict safe separation.

The optional `--surface-norms` mode adds **2,415 penetrating-witness norm rows** to the existing 5,434 motion/edit rows, for 7,849 total norm rows. All 3,045 existing scalar witness rows remain. It uses the same 72 controls, 0.2-degree trust radius, measured motion-fitting reserves, original edit limits, source-relative motion caps and source-or-5-mm per-time penetration allowances as the matched preceding study. Final clearance still requires the separate 5 mm screen. Existing failed depths are not reclassified as acceptable animation.

## Solver, exported motion and engine

The conic solve reports Solved after 38 iterations and 2.32 seconds. The full step passes both actors' exported motion and original edit checks without backtracking. Independent finite-difference replay verifies 3,696 peak values across all 77 joints, six windows and 597 quarter-frame samples per actor; maximum replay discrepancy is 1.75e-13. Maximum original edits are 5.000050703 and 5.000050228 degrees, inside the pre-existing 0.0001-degree export allowance around the 5-degree limit.

Fresh Godot validation passes all **600 actor-frame observations**, with maximum position error below 4.16e-7 m. All four source/candidate clips preserve 77 bones, a skinned surface, their original duration and nonlooping import behavior. Separate checks preserve unedited keys/channels, root translations, authored fingers and contact/release samples. This is import evidence, not animator approval.

## Independent complete-skin replay of the retained constraints

The new verifier evaluates complete CPU-skinned meshes using `RigAsset.vertices`, independently of the fitter's selected-vertex skin evaluator. It reconstructs all 2,415 retained vectors, then checks two deterministic coupled perturbation directions per row: **4,830 directional comparisons**. Source-vector discrepancy is at most 8.89e-16 m; maximum derivative discrepancy is 8.49e-10 m/rad along the tested directions.

The exported retained-vector distances have no cap excess above the existing 1-micrometre comparison tolerance. Maximum excess is 0.368 micrometres. Nonlinear norm prediction error reaches 6.728 micrometres on other rows, while serialization contributes up to 0.038 micrometres; slack and independent validation remain necessary. These numbers do not establish a universal approximation-error bound.

A fresh signed-distance query revisits the earlier failing vertex B/14797 at frame 65.75. Its closest triangle remains 9426. Candidate penetration is **19.688042 mm**, below that time's **19.690034 mm** allowance; the previous scalar-only candidate reached 19.700544 mm. Its fixed-barycentric exported distance is 19.689903 mm, consistent with the intended conservative bound. This resolves that specific regression, not the remaining high-five penetration.

## Completed full sampled geometry result

The complete audit finishes all **57 quarter-frame times and 114 directional queries** across frames 63-77, considering all 18,056 vertices per actor with conservative broadphase filtering. Source queries are reused only with exact source identities, placements and sample-clock bindings.

| Measure | Source | Full-vector candidate |
| --- | ---: | ---: |
| Maximum partner penetration | 23.556264 mm | 23.023948 mm |
| Times exceeding the 5 mm screen | 25/57 | 24/57 |
| Per-time allowance excesses above the existing 1-micrometre tolerance | 0 | 0 |

The peak improves by **0.532316 mm**. Maximum numerical allowance excess is 0.179 micrometres. One already-clear time has a 48.614-micrometre depth increase, still inside its 5 mm allowance; no new time crosses that screen. Frame 69 becomes clear. Maximum floor depth does not increase. Event 75 remains unchanged at 21/17 regional vertices within 3 mm, 5.199358-degree opposing-normal error and 1.896658 mm penetration.

This is a validated local research step under the existing comparison policy. **The animation remains unapproved**: 24 sampled times still fail clearance, inherited full-clip floor defects remain, and the study does not certify continuous collision freedom, triangle intersections, self-collision, forces or naturalness. All fourteen release capabilities remain unapproved.

Fourteen of the 24 control knots reach the 0.2-degree step radius. The next experiment should apply a bounded sequence of relinearized proposals, with total edits and motion caps still referenced to the original clips, retained rejected trials, and complete exported geometry validation. Do not accumulate a fresh five-degree edit allowance per step or mistake a solved local conic problem for convergence of the full animation problem.

## Evidence, tests and reproduction

Local reports are `coupled-pair-surface-norms-v1`, `coupled-pair-surface-norms-review-v1`, `coupled-pair-surface-norms-engine-v1`, `coupled-pair-surface-norms-geometry-v1` and `coupled-pair-surface-norms-diagnostic-v1`, under ignored `reports/`. Input hashes, implementation snapshots, source/candidate clips and failed predecessors remain intact. Original linearization arrays match the retained calibration exactly; full-vector additions are saved and hashed separately.

**42 focused tests pass.** Five new model-free tests join Windows/Linux CI, covering both actor contributions, common translation, inside/outside selection, distance bounds and invalid or numerically rounded barycentric bindings. No model training, held-out generation, rendered review or human-quality approval is claimed. Reproduction requires the separately acquired licensed fixture, pinned solver and preceding local evidence. Use fresh output paths.

```powershell
.venv\Scripts\python.exe scripts/study_coupled_pair_proposal.py reports/paired-approach-witnesses-v1 reports/<new-study> --reserve reports/coupled-pair-reserve-v1 --surface-norms
.venv\Scripts\python.exe scripts/verify_coupled_surface_norms.py reports/<new-study> reports/paired-approach-witnesses-v1 reports/<new-vector-review>
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/<new-study> --output reports/<new-engine>
.venv\Scripts\python.exe scripts/audit_coupled_pair_geometry.py reports/<new-study> reports/paired-approach-witnesses-v1 reports/<new-engine> reports/<new-geometry>
.venv\Scripts\python.exe scripts/diagnose_coupled_pair_surface.py reports/<new-study> reports/paired-approach-witnesses-v1 reports/<new-diagnostic> --frame 65.75 --source 1 --vertex 14797
```
