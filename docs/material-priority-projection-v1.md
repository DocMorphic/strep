# Strict projection of secondary material guidance

The [peak-priority study](material-peak-priority-v1.md) reduced measured depth but retained first-phase proposals after every secondary step exceeded its strict depth ceiling. `scripts/native_material_priority_projection.py` projects an explicit secondary target around the already verified first-phase step. The ceiling and every original motion limit stay unchanged.

```python
from native_material_priority_projection import project

step, report = project(native_rows, native_jacobian,
    complete_gaps_m, complete_gap_jacobian_m, complete_witnesses,
    controls, lower, upper, trust,
    verified_first_step, rejected_secondary_step,
    parameter_rows=original_parameter_rows)
```

Caller authentication still binds the original model, complete indexed witness population and both proposal steps. The baseline must strictly pass every original affine norm, absolute control/trust bound and all parameter equations. The target must remain within the original proposal box. The projected correction minimizes distance to that target with all original native cones, parameter equations and every contained-vertex depth inequality hard.

The correction is expressed about the first-phase candidate, while bounds remain those of the **original** absolute trust/control box. A correction can span the full original box; no smaller trust box is introduced around the baseline. Only exactly fixed passing native rows omit conic encoding, and every row remains in final represented checks. All material rows remain in the complete guide-loss check, although the projection objective is control distance rather than a new guide-loss solve.

Finite solver output keeps its original termination status. Infeasibility/numerical-error statuses and invalid points reject. The explicit 81-fraction retreat interpolates toward the verified first-phase step, not toward the original pose. Each probe records all original norms/bounds, parameter residuals, material peak depth and complete guide deficit. A nonzero change must pass every original norm and the existing depth ceiling with zero excess and strictly improve the complete guide loss. The 1e-9 parameter/proposal-box tolerance does not replace actual export limits. No optimality, signed-distance, collision or quality claim follows from a returned step.

101 focused local tests pass with zero skips: 29 new projection cases, 29 existing peak cases and 43 existing iterate cases. They cover depth priority, complete coupled norms/scales, full absolute trust range, parameter locks, model-capture isolation, invalid baselines/targets, certificate/point rejection and preflight validation. The new suite is registered once in Linux/Windows CI; hosted success remains unverified.

## Same-point measurement

The fixture authenticates the previous full peak replay and reuses all 180 complete same-point stencils; zero fresh derivatives are claimed. All 90 controls, 30,450 original norms, 1,707 native samples, 1,673 geometry times, 964 material rows and 18 event/72 uniform parameter rows remain. Original solver/runtime dependencies stay unchanged, and neither earlier study is modified or rerun.

| Variant | Solver status | Retained interpolation | Complete guide deficit before → after | Result |
| --- | --- | --- | --- | --- |
| Original norms | AlmostSolved | 1 | 311.613685924 → 294.431606372 | Strict affine projection; exports fail stored motion |
| Event-preserving | InsufficientProgress | 2^-20 | 310.282926787 → 310.282926462 | Strict but very small affine improvement; exports fail stored motion |
| Uniform increment | NumericalError | None | 258.546650629 → no candidate | Numerical-error output rejected |

The original projection stays below its unchanged 4.673499617 mm material ceiling; the event projection equals its unchanged 4.679387563 mm ceiling. Those are fixed-witness affine quantities, not actual nearest-surface depth guarantees.

| Family | Stored-motion failures at fractions 1, 1/2, 1/4, 1/8 | Continuous motion failures | Contact failures |
| --- | --- | --- | --- |
| Original norms | 12 / 5 / 2 / 7 | 8 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Event-preserving | 4 / 4 / 1 / 6 | 5 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

All eight exports pass original contact/reference/control/trust checks, but none passes every stored scalar/vector motion condition. All differ in bytes from their same-fraction first-phase exports, including the very small event projection. No full scene scan is selected; the previous motion-passing first-phase export remains the better demonstrated candidate. The original full projection's seven-frame depth is 4.665329557 mm versus the first-phase 4.663817166 mm, and its crossing records rise from 102 to 104. Lower affine guide loss still does not prove improved actual geometry.

A separate original-context reader reconstructs all three complete anchored conic matrices/objectives/inequalities, the 53 storage choices, all event/uniform equations, every baseline/target and strict interpolation-prefix check, and every actual export including all native conditions and seven-frame geometry queries. Shared collision predicates are not independent geometry arithmetic; existing complete derivatives/witnesses are authenticated from the prior replay rather than recomputed. No optimizer proof is claimed.

Next, address the continuous/stored-motion discrepancies and choose crossing proposals using actual geometry. Preserve the complete original conditions; do not promote these geometrically worse or motion-rejected clips through further storage repair alone. The uniform numerical error is not an infeasibility certificate.

Raw evidence remains immutable under ignored `reports/`. Original assets remain selected, all fourteen release evidence arrays remain empty and the full-project goal stays active. There is no production-anatomy, arbitrary-action, engine, continuous-physics, animator-review or cleanup-time approval.
