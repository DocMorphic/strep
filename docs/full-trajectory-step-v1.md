# Complete timeline correction trial

The [complete sampled component model](full-component-trajectory-v1.md) now has a distinct correction solver. Its first trial reduces the measured timeline-wide deficit, but every actual candidate fails at least one original condition. No animation is selected or approved.

## Solver and preserved conditions

`native_component_trajectory_step.py` accepts the separately typed large trajectory model and separately bounded legacy material rows. It minimizes the normalized trapezoidal integral of each sample's worst complete vertex-pair deficit. All pairs at all supplied required times are retained. Every initially positive component pair row stays hard, with no objective slack.

Preserve original native scalar/vector norms and cap/scale arrays, cumulative control and trust bounds, optional original parameter equalities, full-mesh separation guards and starting legacy containment/triangle ceilings. The legacy material population keeps its 4,096-row limit. Explicit complete-model row/nonzero and conic-row budgets reject an oversized population; no subset is passed to the solver. A strict 81-fraction schedule checks every represented hard row and requires actual numeric movement plus integral improvement. Returned solver statuses remain unchanged; even a strict local candidate is provisional.

All 47 focused tests pass without skips, including a complete trajectory beyond 4,096 rows, original-clock objective weights, all positive rows without epigraph slack, independent mesh/native/control/equality/legacy constraints, late-sample retreat, source population validation, callback isolation and status-preserving invalid-iterate rejection. Registered source CI has not been independently confirmed successful on GitHub.

## Same-point model and fresh mesh coverage

Reuse the independently verified 180 stencils at the authenticated 56-choice anchor: 90 controls, 30,450 native norm rows, 1,707 native clocks, 1,673 original geometry times and 107,072 complete component rows. All 99 positive samples contribute 6,336 hard pair rows. No old-pose derivative or new stencil is used.

At all eleven prior guide times, query the complete original skin meshes and construct every current legacy witness: 1,692 crossing corner rows and 18 contained-vertex rows, totaling 1,710. Their frozen-axis columns explicitly project the verified full-skin point derivatives. They are not relabelled as a reused old finite-gap model.

Build a fresh full-mesh affine partition over all 571,824 original triangle/time pairs: 571,232 are disjoint throughout the represented control box, 404 receive all nine positive pair rows, and 188 remain unresolved. This gives 3,636 hard guard rows. Component coverage over the full timeline and full-mesh coverage at eleven times retain separate labels; no between-sample or nonlinear certificate is inferred.

## Three solves and actual exported motion

| Variant | Returned status | Strict ray result | Stored motion failures: full / half / quarter / eighth |
| --- | --- | --- | --- |
| Original norms | AlmostSolved | Fraction 0.99951171875, prefix 31 | 9 / 2 / 0 / 1 |
| Preserve event key | AlmostSolved | Fraction 0.9990234375, prefix 32 | 10 / 1 / 2 / 2 |
| Uniform control increment | InsufficientProgress | All 81 fractions fail integral improvement | No candidate exports |

Each conic has 1,763 variables and keeps every original-clock objective weight, hard row and parameter condition. The uniform result is a rejected nonoptimal iterate, not a proof of infeasibility.

All eight exports improve the actual complete-clock deficit integral. All original references and cumulative edit/trust bounds pass. Actual full-mesh guard failures are 5/0/0/0 and 5/0/0/0; actual positive-component failures are 0/0/0/0 and 2/0/0/0. Affine guards pass for all eight. Their eleven complete mesh queries still contain 188 proper crossing records each.

The original-norm quarter passes all stored motion and both actual guard populations. Its complete-clock deficit integral decreases from 0.016120351839208256 to 0.01607581509410981 m s. It nevertheless exceeds the original material containment ceiling by 23.6227469998 nm and the legacy triangle ceiling by 84.5913968144 nm. All eight exports violate a legacy triangle ceiling. These small failures remain visible and rejected; no tolerance is loosened. No export qualifies for a full original scene scan.

## Independent replay and endpoint defects

A separate original-context reader reconstructs every new witness and projected column; the complete mesh-pair partition and every guard; 10,032 affine coordinate bounds with exact rational arithmetic; all three full conic matrices, weights, equalities and retained statuses; every strict ray prefix; and every actual stored export's native/contact/reference, material, 107,072 component observations and full-guide queries. It confirms the absent selection without calling the trajectory solver/model, material, guard, Job or centering producer APIs. Skin/native/geometry primitives remain shared, so this does not establish independently implemented collision arithmetic or solver optimality.

Retain complete saved error arrays for all eight exports: every 30,450 native vector row and every 1,710 material row. There are 27 failed native and 25 failed material row observations across those exports. The motion-passing quarter has three material failures, all passing in the affine prediction. The diagnosis retains their full original source descriptors and prediction errors. It also records the uniform variant's complete 81-fraction non-improvement. This requires no new motion, derivative or geometry query and cannot attribute errors exclusively to Float32 rounding.

Next assess material-aware bounded storage correction or empirical safety constraints from these authenticated complete endpoint defects. Preserve every original gate and recheck the actual exported motion, all clear samples, all material ceilings and the full original scene. Observed endpoint error is not a nonlinear guarantee. Preserve the original failed source and earlier lower-depth branch.

All fourteen release evidence arrays remain empty. This fixture adds no action-semantic, production rig, engine-import, animator or cleanup-time evidence. The full-project goal stays active.
