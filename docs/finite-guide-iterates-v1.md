# Inspecting stalled motion-solver iterates

The [material-witness experiment](material-witness-guides-v1.md) discarded two solver outputs because their status was `InsufficientProgress`. That status establishes neither an optimal solution nor infeasibility. Clarabel's [official Python interface](https://clarabel.org/stable/python/getting_started_py/) exposes the returned primal point through `solution.x` and lists the distinct termination statuses. Strep now has a separate explicit diagnostic path to inspect that point without changing the original solver or its status.

```python
from native_finite_guide_iterate import assess

step, report = assess(native_rows, native_jacobian, guide_residual,
    guide_jacobian, controls, lower, upper, trust,
    solver_status=str(solution.status), solver_point=solution.x,
    parameter_rows=original_parameter_rows)
```

The caller must bind the returned point to the unchanged conic model and solver provenance. Its entries are the normalized controls followed by every guide slack. The function does not solve, infer infeasibility, change a solver status, select an asset or authorize a storage repair. The existing solver API retains its original behavior.

`Solved`, `AlmostSolved`, `InsufficientProgress`, `MaxIterations` and `MaxTime` can supply diagnostic iterates. Other statuses, including infeasibility certificates and numerical errors, reject before using a point as motion. Missing, incorrectly sized and nonfinite points are retained as rejections.

Every original norm, column, cap, scale, control/trust bound and homogeneous parameter row remains present. The raw point's complete norm, parameter and guide-slack residuals are recorded. A 1e-9 proposal tolerance applies to the raw box/slacks and parameter equations only. The existing explicit 81-fraction ray prefix must find a nonzero represented step passing every original affine norm and box with zero acceptance excess. The resulting step must also satisfy the parameter rows and strictly reduce the complete squared negative guide residual. A candidate still requires actual stored-motion, contact, reference and scene checks; none of these proposal tolerances replaces an export limit.

## Generated-fixture comparison

83 focused local tests pass with zero skips: 43 new iterate cases, 15 existing hinge-solver cases and 25 existing ray/recovery cases. They cover all allowed/rejected statuses, incomplete/nonfinite points, coupled norm rows and scales, original bounds, slack inequalities, parameter preservation, nonimproving directions, stationary points and invalid complete models. Hosted CI success remains unverified.

The comparison reuses the authenticated material model from the separately completed full replay: 90 controls, 30,450 norms, 1,707 native samples, 1,673 geometry times, 964 material rows and all 180 same-point complete stencils. It claims zero fresh derivatives. All three unchanged solver calls reproduce their previous result records and steps exactly. A local function copy substitutes only a capture facade in its private globals; the original function bytecode, settings and returned solution/status remain unchanged, and no shared solver module is mutated. Complete conic matrices, right-hand sides, quadratic objective, cones, settings and returned primal/dual/slack arrays are retained locally.

The original-norm and event-preserving raw iterates each violate one affine norm. Strict retreat selects fraction 0.99993896484375 of each raw direction. The uniform iterate already passes the affine norms, but its guide loss rises from 7.11975335625 to 7.12175252059; it rejects as `NoStrictGuideImprovement`.

| Family | Solver status | Stored-motion failures at fractions 1, 1/2, 1/4, 1/8 | Contact failures | Seven-frame depth, mm |
| --- | --- | --- | --- | --- |
| Original norms | InsufficientProgress | 23 / 5 / 3 / 0 | 1 / 0 / 0 / 0 | 5.327623027 / 5.216070268 / 5.159551924 / 5.131091191 |
| Event-preserving | AlmostSolved | 15 / 8 / 8 / 4 | 0 / 0 / 0 / 0 | 5.244799322 / 5.219763571 / 5.161567728 / 5.132031935 |
| Uniform increment | InsufficientProgress | No improving diagnostic step | No exports | No exports |

All eight exports pass reference/control/trust bounds. Only the original-norm 1/8 export passes all stored scalar/vector motion and contact conditions. It reduces aggregate guide loss and seven-frame crossing records from 106 to 104, but worsens maximum sampled depth from 5.102497259 mm to 5.131091191 mm. Its full original scene scan covers all 1,673 geometry times and rejects: 28,876 proper-crossing records, 27 vertex-over-tolerance incidences and 1,527 failed sample checks. This is evidence of a motion-feasible proposal from a stalled solver, not a usable collision-free interaction.

Two producer/report-writing failures remain retained. The continuation binds their artifacts, reuses all three completed solver captures and eight completed exports, and finishes the full scene scan. It does not rerun those solver/export stages or overwrite the failed runs.

The separate consumer reconstructs the original context and 53 absolute storage choices, all 18 event and 72 uniform parameter rows, complete conic matrices/cones/settings, every raw and strict-ray diagnostic, and all eight actual exports including every native condition and seven-frame geometry query. The complete derivatives and witness populations are authenticated from the prior replay, rather than recomputed. Geometry predicates are shared, and the full-scene archive receives transport validation rather than independent collision arithmetic or optimizer proof.

The next solver change should optimize worst containment depth separately from aggregate crossing guidance. The present loss can trade a smaller aggregate deficit against a deeper local overlap. Keep all original motion conditions and guide populations, and measure actual geometry before considering any proposal useful. Do not run additional storage repairs solely to promote the seven rejected motion proposals.

Original assets remain selected, all fourteen release evidence arrays remain empty, and the full-project goal stays active. These fixture results establish no arbitrary-action semantics, production anatomy, engine, continuous physics, animator-review or cleanup-time approval. Source is published; local generated evidence stays under ignored `reports/`.
