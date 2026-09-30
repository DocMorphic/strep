# Cylinder pose: iterative versus dense trust-region steps

The matched comparison does **not** solve the grasp. Both methods retain failing hand contacts and roughly 10.28 mm of object penetration at their best-cost points. The dense SVD variant remains a diagnostic option; the production/default path is unchanged.

## Controlled comparison

Both runs start from the exact same `best_cost` pose in `reports/cylinder-pose-full-residual-v2`. Inputs, method snapshots, weights, source-relative rotation/root limits, patches, guide anchors, selected triangles, evaluation limit and resource limits are identical. Their protocols differ only in timestamp, linear-solver choice and whether an LSMR cap applies.

The control uses the established matrix-free TRF/LSMR path with inner cap 175. The comparison uses SciPy's dense `tr_solver='exact'` path, which computes an SVD-based step for the current linearized trust-region problem. “Exact” is SciPy's solver name; it does not mean an exact nonlinear solution or an accepted animation.

`TorchJacobianOperator.to_dense()` builds the **36,518 × 175** derivative table one column at a time. A preallocation check limits the table to 128 MiB; this case needs **51,125,200 bytes**. Existing time/process-memory/available-memory guards are checked between derivative products. Both runs permit 150 function evaluations and a 180-second solve guard, and run sequentially to avoid competing for local resources.

The independent dense/operator comparison at the shared seed has maximum forward-product error **2.843e-14** and transpose-product error **1.333e-15**. Thus the comparison changes the step calculation, not the residual derivatives or acceptance thresholds.

## Observed results

| Measurement | Shared seed | Iterative control | Dense SVD |
| --- | ---: | ---: | ---: |
| Best weighted squared residual | 6.725097 | 6.708462 | 6.698109 |
| Best-cost object penetration | 10.265 mm | 10.280 mm | 10.289 mm |
| Best-cost left anchor error, 5 mm limit | 5.002 mm | 5.003 mm | 5.003 mm |
| Best-cost right anchor error, 5 mm limit | 5.586 mm | 5.585 mm | 5.587 mm |
| Best-cost left patch penetration | 4.091 mm | 4.095 mm | 4.093 mm |
| Best-cost right patch penetration | 6.619 mm | 6.617 mm | 6.618 mm |
| Function evaluations | — | 150 | 76 |
| Constructed Jacobians | — | 120 | 53 |
| Total recorded time, including final audit | — | 69.203 s | 181.656 s |
| Peak observed process RSS | — | 664,424,448 bytes | 905,015,296 bytes |
| Termination | — | Evaluation limit | Time guard |

These are identical budget ceilings, not identical consumed compute: the control reaches its evaluation cap first, while the dense variant reaches its time guard first. The slight dense cost reduction does not improve the physical quality screens. Its smallest-peak diagnostic reaches 10.116 mm penetration but has a 6.680 mm right anchor error; it also fails. No result is promoted based on the average cost, one improved maximum or solver status.

All six retained variants independently replay their original edit bounds, serialized pose arrays, source/root-XZ/foot-label preservation, scores and selection rules. Every complete hand-contact check still fails. Input and frozen method hashes are verified, and the shared starting pose is identical. The time-interrupted dense output is preserved with that explicit status; it is not described as converged.

## Decision

This comparison does not justify replacing the default solver or simply spending another larger whole-body budget on the same formulation. It also does not prove infeasibility. The next diagnostic should isolate the authored hand-shape/contact geometry under the original finger budgets and guide binding, then use existing bounded wrist projection only for a demonstrated local hand placement. That can distinguish a hand-placement/shape problem from a coupled whole-body search problem.

Existing [finger-shape and placement research](grasp-shape-search-v1.md) and [bounded wrist projection](bounded-wrist-pose-v2.md) provide implementation precedent, not a result on this cylinder fixture. Finite-cylinder orientation matters: the sphere study's axial-twist symmetry must not be assumed for a cylinder. Any changed binding or contact condition must remain a separately labelled experiment, with original failures retained and anatomical/human review still pending.

## Reproduction and validation

With the separately acquired assets and retained studies, use fresh directories:

```powershell
.venv\Scripts\python.exe scripts/regional_pose_full_residual.py reports/cylinder-pose-bounded-v1 reports/<new-lsmr-comparison> --warm-start reports/cylinder-pose-full-residual-v2 --lsmr-iterations 175 --linear-solver lsmr
.venv\Scripts\python.exe scripts/regional_pose_full_residual.py reports/cylinder-pose-bounded-v1 reports/<new-dense-comparison> --warm-start reports/cylinder-pose-full-residual-v2 --linear-solver exact
```

Twenty-one focused tests pass, including analytic dense-column agreement, both SciPy solver interfaces, preallocation rejection, interruption between columns, warm-start binding and residual layout. Public source CI remains separate from these Torch/asset-dependent checks. Evidence is retained under `reports/cylinder-trust-comparison-v1-lsmr`, `reports/cylinder-trust-comparison-v1-exact` and `reports/cylinder-trust-comparison-review-v1`. No new clip, engine, temporal, dynamics, human-review or cleanup-time approval follows; all fourteen release capabilities remain open.
