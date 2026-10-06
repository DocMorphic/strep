# Fixed affine surface guidance within a control box

`scripts/native_affine_surface_box_conflict.py` diagnoses whether an individual supplied surface row can meet its clearance anywhere inside a declared delta box. This explains a limitation of local collision guidance without changing motion limits, running another solver or approving an animation.

For a row `gap + coefficients · delta >= clearance`, each scalar term reaches its maximum at the upper endpoint for a positive coefficient and the lower endpoint for a negative coefficient. These choices give the exact maximum over the entire box. If even that maximum remains below clearance, the row is unreachable within that box, including every subset imposed by native motion constraints. Its positive deficit divided by the declared scale is a lower bound on worst affine surface excess.

The helper scans **every original row**, using outward Float64 arithmetic for upper bounds and `Fraction.from_float` for its selected exact witness. Multiplication and addition are each rounded upwards; zero products are handled exactly. Uncertain or positive overflowing bounds cannot issue a conflict certificate. Exact rational numerators and denominators preserve cancellation, subnormals and large results without a tolerance-based infeasibility decision. Complete canonical CSR inputs, box endpoints, clearance and scale are bound by a digest; CSR and CSC inputs normalize to canonical row order.

`diagnose` returns the complete upper-bound array and a report. `verify_witness` rebinds all inputs and recomputes only the selected exact witness. It deliberately does not independently verify the aggregate screening count. Callers must establish that the declared box encloses every permitted local step; an arbitrary smaller box cannot certify the caller's complete search domain.

```python
import numpy as np
from scipy import sparse
from native_affine_surface_box_conflict import diagnose, verify_witness

# Complete original populations; delta endpoints belong to this model point.
upper_bounds, report = diagnose(
    gaps, surface_jacobian, delta_lower, delta_upper,
    clearance=original_clearance, scale=original_scale,
)
if report['witness'] is not None:
    check = verify_witness(
        report, gaps, surface_jacobian, delta_lower, delta_upper,
        clearance=original_clearance, scale=original_scale,
    )
```

This is a certificate about the **fixed affine target**. Surface normals and support witnesses are local guidance, not necessary conditions for all nonlinear ways to separate meshes. Other axes, relinearized geometry, a different path or further admissible motion may remove actual collisions. The diagnostic does not prove nonlinear geometry or full authored control-range infeasibility. Conversely, finding no conflicting individual row does not prove simultaneous feasibility: different rows can require incompatible changes. No native feasibility, geometry, engine, motion quality or release approval is issued.

## Frozen ninety-control study

The [completed wrist correction](pair-hand-correction-study-v1.md) preserves a fully replayed model with **90 controls**, **276815 scalar surface rows**, all **30450 native norms** and the original bounds. This diagnostic reuses that immutable model at its original point. Its independently checked reduction proof box encloses the actual authored/trust intersection, including the roundoff reserve. Using the larger box makes an individual conflict certificate conservative with respect to the original solver domain.

The complete scan certifies **33095** individual rows as unreachable at zero clearance in this box. The strongest reported witness is original scalar row **262675**, block **31654**, scalar **5** of its nine-row triangle-support block. It occurs at **1.1145833134651184 s**, between A triangle87 (vertices58/60/56) and B triangle94 (vertices62/61/60), on the original fixed world normal `[0.007729836283257821, -0.0021110246653841314, 0.9999678960876175]`.

Its exact maximum gap is

```text
-5193520598597563671270356072695 / 649037107316853453566312041152512 metres
```

That is about **-8.001885470105 mm**, implying an affine excess lower bound of **1.600377094021** at the original 5 mm normalization scale. Native conditions were ignored in maximizing the row; adding them cannot make that maximum larger. This does not locate the constrained minimax optimum or certify an 8 mm nonlinear penetration.

The separately replayed motion-feasible repair anchor lies inside this old model box, with maximum control difference about **0.0025**. The diagnostic remains attached to the original linearization. It supplies no derivative or infeasibility certificate for a new model centered on that anchor, whose trust box can extend beyond the old one. No original study, limit, control, candidate or source asset changes; no model rebuilding, solve, export or geometry rerun occurs.

An independent consumer imports no diagnostic, reduction, solver, job or model implementation. A separate row-batched calculation reproduces **every original upper bound** exactly, then exact rational arithmetic verifies the maximum of **all 33095 reported conflicting rows**. The complete input digest, selected rational maximum/deficit/normalized lower bound, maximizing endpoint and original triangle-block binding match. Both producer and consumer exit zero, retaining the original pinned study and repaired-anchor receipts unchanged. This independent check certifies the stated local affine conflicts; it does not recompute nonlinear collision predicates.

Thirty-eight focused tests pass, with zero skips. They compare outward bounds against independent exact arithmetic and exhaustive small-box corners, exercise late rows/the ninety-sixth control, mixed signs, collapsed boxes, clearance equality, incompatible joint conditions, rebinding/tampering, subnormals and positive/negative overflow. The test file is included in the Linux/Windows source-check workflow. Hosted CI success is not claimed.

The result directs the next experiment toward explicitly revised separation guidance at the retained motion-feasible anchor, followed by every original native/reference/geometry check. It does not justify relaxing constraints or bypassing failed collisions. These cube-skin development fixtures provide no production humanoid realism or human cleanup evidence; all fourteen release evidence arrays remain empty and the full-project goal stays active.

Immutable ignored local result identities:

- Complete frozen-model diagnostic: `99333bb0122f96df55592dbf77cc0f75ce1af608b9059fdc2d952881ded04f7c`.
- Independent complete bound scan and all-conflict exact proof: `b72d04b29543cd1c46f7386ac246cd002ca49c1a995bc5c0b425a8e48e91b3d7`.
