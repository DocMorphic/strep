# Coordinated temporal correction

Status: all three fits, independent checks and engine imports are complete. No candidate meets every target/floor screen or receives quality approval. The full-project goal remains active.

The previous bounded correction updates one frame at a time. Independent anchor diagnostics found that all three requested target poses fit within the edit box in isolation, but those poses violate limits against the current neighboring frames. This motivates changing several frames together while retaining the hard motion limits. It does not establish that a complete feasible animation exists.

`scripts/rig_coupled_pose.py` wraps the existing pose/trajectory fitter. It reuses the cubic control basis from `support_contact_v5.correction_basis` and multiplies it by the existing edit envelope. Controls operate around a retained trajectory. Per-frame component bounds contain possible spline overshoot; frames outside the envelope cannot change. Analytic inequalities jointly account for both sides of every root/edit-vector step and actual local rotation step. The original floor, support, height, prior, acceleration and authored-joint objectives remain intact, with each temporal term counted once.

The scalar objective is checked against an independently computed whole-trajectory energy. Its gradient combines the existing exact frame derivatives through the control basis. The solver retains the best objective-decreasing point that satisfies all hard inequalities. SLSQP can return infeasible trial endpoints; the final direction is backtracked and independently checked before any reduced step is retained. Neither solver success nor a feasible partial step implies target accuracy, floor clearance, convergence or animation quality. Position/orientation and surface/contact goals remain soft objectives in this experiment; their accuracy is screened separately.

## Frozen experiment

The sources are the three completed `pose-trajectory-v1` candidates: jump-land, dance and get-up, all seed 502. The original motions and authored targets are unchanged. Each candidate starts from its retained four-sweep coordinate fit, with the same 31-frame envelope, edit budgets, actual rotation-step allowance, target weights and unconfirmed support intervals. Cubic knots are spaced ten frames apart, with at most 60 SLSQP iterations. This is a warm-start development comparison, not an equal-compute baseline or held-out release test.

Reports preserve raw motion, the coordinate candidate, the coordinated candidate, original/warm/final parameter arrays, the control basis, source hashes, frozen implementations, optimizer trace and actual solver outcome. The independent verifier checks original and warm-start provenance, hard limits, exact fixed context, the fitted control subspace, independently recomputed objective values, all decoded poses and integer/half-frame floor depth. A finalizer waits for the specific observed process before running those checks, GLB validation, Godot import and served-file hash checks.

## Verification so far

Twenty-six focused tests passed in 20.52 seconds: seven coordinated-control tests and nineteen existing joint-target/trajectory tests. They include independent finite-difference derivatives, a real coordinated improvement, fixed context and hard bounds. One existing SciPy trial-clipping warning occurred. The first test invocation caught a NumPy integer passed to the existing strict cubic-basis API; the caller now uses native integers. A subsequent solve test caught the lack of feasible endpoint recovery; checked segment backtracking now retains a valid improving step. Initial failure logs remain available.

Production defaults and existing solvers are unchanged. All three runs used their full 60-iteration budgets and returned SLSQP status 9. Their endpoints required checked backtracking to retain feasible improvements. The saved final weighted energy decreases in all three cases, independently recomputed from original/warm/final arrays; no convergence or optimality is established.

## Results

| Action | Position, coordinate → coordinated | Orientation, coordinate → coordinated | Coordinated window floor | Whole-clip floor |
|---|---:|---:|---:|---:|
| Jump and land | 10.155 → 5.701 mm | 9.008 → 10.185° | 3.225 mm | 7.634 mm |
| Dance | 10.312 → 4.995 mm | 10.662 → 6.142° | 10.022 mm | 16.506 mm |
| Get up | 77.671 → 68.747 mm | 15.687 → 14.834° | 89.245 mm | 323.271 mm |

Dance passes the position screen alone; all three miss orientation. Jump and getting up also miss position. Dance and getting up fail floor screens, including half-frame samples. The large whole-clip getting-up failure is outside the unchanged edit window. Jump and getting up slightly worsen their window floor maxima relative to the coordinate result. No threshold is changed to accept these candidates.

Independent checks pass for original/warm-start hashes, unchanged source arrays, fitted control subspace, fixed context, hard edit/motion bounds, decoded poses and objective values. Six GLBs have zero validation errors/warnings. Godot imports all 900 sampled frames, with maximum joint position discrepancy 3.372e-7 m; all six served files match their hashes. The three coordinate GLBs are exact copies of the previously verified candidates. Root-motion sidecars are saved with the candidate GLB hashes.

The three-stage viewer defaults to coordinate versus coordinated output, with raw motion available separately. All actions, dynamic timeline limits, authored-frame controls and stage switching were checked in the browser. Grey characters and target markers remain visible; no browser errors were observed. These checks do not supply animator or semantic ratings.

The next experiment adds explicit position and orientation tolerances through a separate feasibility stage; it must report surface/support regressions rather than interpreting target accuracy as complete animation quality. See [target tolerances](pose-tolerances-v1.md).
