# Cylinder pose: inner accuracy and retained continuation

The 30-iteration inner solver limit is a measured source of linear-solve error. A more accurate continuation reduces the nonlinear objective further, but **all retained poses still fail the original contact checks**. Neither experiment changes a production clip or establishes infeasibility.

## Actual inner-system comparison

`scripts/probe_pose_inner_solve.py` starts at the best-cost pose from the [first full-residual search](cylinder-pose-full-residual-v1.md). It intercepts the first actual SciPy TRF inner call in its own process, compares iteration caps on the identical scaled and regularized operator/right-hand side, and returns the original 30-iteration answer unchanged. The function is restored in `finally`; no installed package file is edited. The SciPy source/version and all local methods/inputs are bound in the saved protocol.

The augmented system has **36,693 rows and 175 columns**. Only the iteration cap changes:

| Linear-system measurement | Cap 30 | Cap 175 |
| --- | ---: | ---: |
| Actual iterations | 30 | 107 |
| LSMR stop code | 7: iteration limit | 2: least-squares stopping criterion |
| Residual norm | 2.207123 | 0.582573 |
| Normal-equation residual norm | 0.153787 | 0.004689 |
| Solution norm | 6.404099 | 44.963461 |
| Solve and measurement time | 0.984 s | 3.360 s |

The 500-cap fallback is not run because the 175-cap solve meets its stopping criterion. The complete probe takes **6.906 seconds**. Independently rebuilding the scaled/regularized operator from the saved pose verifies both saved linear solutions and their residuals. The outer probe has only two function evaluations and returns its initial nonlinear cost unchanged. More accurate linear algebra is not itself a corrected pose.

## Continued nonlinear search

The full-residual driver now supports an explicit iteration cap and a hash-bound saved starting variant. It rejects a different source study, changed control budgets, modified inputs/method snapshots, or a seed pose failing edit bounds. The default inner cap remains 30. The continuation explicitly selects cap 175 and the first run's `best_cost` pose.

The continuation keeps the same source motion, geometry, patches, triangle selections, positive residual weights, physical edit budgets and independent final gates. It receives another 150 function evaluations and a 180-second guard. This is additional compute from a saved state, not a matched from-scratch ablation of the iteration cap.

It finishes at **150 evaluations / 112.563 seconds**, with peak observed process RSS **666,279,936 bytes**. Together, the two nonlinear runs use 300 evaluations and **216.298 seconds**; probe/verification time is additional. Termination is again the evaluation limit.

| Independent measurement | Continuation seed | Best cost / terminal | Smallest peak |
| --- | ---: | ---: | ---: |
| Object penetration | 10.564 mm | 10.265 mm | 9.812 mm |
| Left anchor error, 5 mm limit | 5.007 mm | 5.002 mm | 4.647 mm |
| Right anchor error, 5 mm limit | 5.624 mm | 5.586 mm | 14.949 mm |
| Left patch penetration | 4.285 mm | 4.091 mm | 4.128 mm |
| Right patch penetration | 6.880 mm | 6.619 mm | 6.281 mm |
| Weighted squared residual | 7.208021 | 6.725097 | 193.427554 |

Every retained variant passes its original edit bounds, and root XZ/foot labels are preserved. None passes both complete hand contacts. The smallest-peak variant trades away the right anchor and has much worse total cost; it is retained as a rejected trial, not called the best animation. The slight best-cost left-anchor excess also remains a failure.

Independent verification replays every serialized variant, source/continuation bindings, original limits, score selection and input/method hashes. The original study and its rejected outputs remain immutable.

## Convergence diagnosis and next decision

At the continuation's best-cost point, the half-squared-objective gradient infinity norm is **0.794008**, down from 9.074110, but still nonzero. The largest rotation-budget fraction is **96.837%**. These facts do not prove the requested pose impossible under the current limits.

A separate bounded-memory probe assembles the active-residual Jacobian for analysis. Of 175 columns, 121 have norm above 1e-12 at this pose. Their norms range from **0.007006 to 903.766**, a ratio of about **128,994**. With a declared relative singular-value cutoff of 1e-10, 91 singular directions are retained, with a retained ratio of about 3.50e9. These are local, active-set-dependent measurements; they do not establish permanently irrelevant joints or nonlinear infeasibility. Simple column normalization changes the retained rank, so its condition number alone is not an apples-to-apples improvement claim.

The next comparison should address local step conditioning and regularization under the existing limits, rather than assuming additional pose freedom is necessary or merely repeating the same iteration budget. Original contact/clearance acceptance must remain authoritative.

## Reproduction

With separately acquired assets and retained studies, use new output directories:

```powershell
.venv\Scripts\python.exe scripts/probe_pose_inner_solve.py reports/cylinder-pose-full-residual-v1 reports/<new-inner-probe>
.venv\Scripts\python.exe scripts/regional_pose_full_residual.py reports/cylinder-pose-bounded-v1 reports/<new-continuation> --warm-start reports/cylinder-pose-full-residual-v1 --lsmr-iterations 175
```

Eighteen targeted tests pass locally, covering Jacobian products, full-residual layout, warm-start binding and linear residual diagnostics. The three pure LSMR diagnostic tests join public Windows/Linux source CI. Raw evidence is retained under `reports/cylinder-inner-solve-v1`, `reports/cylinder-inner-solve-review-v1`, `reports/cylinder-pose-full-residual-v2`, and `reports/cylinder-pose-full-residual-review-v2`. There is no new engine, visual, temporal, dynamics, human-review or cleanup-time approval. All fourteen release capabilities remain unapproved.
