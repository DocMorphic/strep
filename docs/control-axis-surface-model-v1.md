# Triangle guidance that considers editable motion

The [complete-box diagnostic](native-affine-surface-box-conflict-v1.md) found individually unreachable fixed-direction rows in the last frozen model. Choosing the smallest current triangle overlap alone does not consider whether permitted control changes can improve that direction. `scripts/native_triangle_control_axis.py` adds an explicit alternative, and `scripts/native_control_axis_surface_model.py` builds a complete local model around it. Existing pose-only producers and original acceptance stay unchanged.

For each recorded triangle pair, retain both orientations of the finite original face/edge direction family and the original supplied baseline normal. For every direction, evaluate all **nine** vertex-pair gaps and all control derivatives. Maximize each scalar gap independently over the complete declared local delta box, then take the minimum of those maxima as its optimistic score. Choose the greatest score, breaking equal scores by the current minimum gap and retaining the baseline on an exact remaining tie.

This score is a mathematical upper bound on what simultaneous affine separation can achieve, because independent rows can require contradictory changes. Floating scores are used only for ranking; they are not outward or exact certificates. Native constraints are ignored during this ranking and remain hard conditions in the subsequent correction. A promising direction may still be impossible under them. Neither a positive nor negative optimistic score proves actual nonlinear mesh separation, full authored-range feasibility or animation quality.

## Complete model and audit boundaries

The new model rebuilds every original compact surface witness at its own stored-centered point. It verifies the expanded row budget before allocating derivatives and retains every original native three-vector norm, cap, scale and order. Every referenced skin vertex is differentiated on the same explicit continuous control stencils as those native norms. Symmetric stencils use the complete requested step wherever both samples fit; a recorded one-sided stencil points into the original authored box at a boundary. No control, small derivative or witness is silently removed. Resource overruns return failure instead of a partial model.

After ranking the directions, the model expands **all nine** scalar inequalities of every selected triangle block. Other plane, contained-vertex and object guidance retains its original normal, weights and identity. Vertex-position differences are projected onto the selected fixed normals; this is explicit and is not claimed bitwise identical to taking finite differences of scalar gaps. Original decoded key fidelity, contacts, edit/reference/rate limits and complete geometry audits remain authoritative.

Caller responsibilities remain explicit: build and verify the stored-centered problem against the original scene, reference and geometry contract; provide complete decoded anchor worlds and clocks; retain every generated failure; solve with original native conditions; export and audit every actual candidate. The model accepts a bounded original model point and an expanded enclosure of its local authored/trust intersection. It does not reuse the previous model's linearization as a new one or make a certificate over a different center.

```python
from native_stored_pair_model import centered_problem
from native_control_axis_surface_model import model

centered, decoded, binding = centered_problem(
    original_problem, controls, actor_files, guide_scene, guide_policy,
    guide_digest, source_policy=original_geometry_policy,
)
native, native_jac, guides, gaps, surface_jac, report, point_archive = model(
    centered, controls, guide_scene, guide_policy, guide_digest,
    original_trust, decoded_worlds=decoded,
    step=original_difference_step,
)
# Keep all original native/reference and complete stored-export geometry audits.
```

Thirty-two focused tests pass, zero skips, in **7.76 seconds**. An actual stored-scene fixture independently checks every native derivative against the existing full norm linearizer, every referenced-point column against its recorded continuous worlds, and every chosen-axis scalar column against direct full-gap differences. It also preserves every original norm/cap/scale and checks complete pair expansion, progress reporting, budgets and rejected anchor mismatches. Direction tests cover all vertices/pairs, the ninety-sixth control, both orientations, explicit baseline retention, immutable inputs and malformed or overflowing inputs. Both test files are included in the Linux/Windows source-check workflow; hosted CI success is not claimed.

A separately declared full ninety-control study starts from the [verified repaired wrist anchor](pair-hand-correction-study-v1.md), retaining the pinned original static/source/reference/rate/contact/edit/geometry contracts and requested fractions. It rebuilds a new model and audits every candidate; its driver and outputs remain ignored under `reports/`. At this source publication checkpoint, that worker is running. No complete-study improvement, collision solution or production selection is claimed. The original failed studies remain immutable. All fourteen release evidence arrays remain empty and the full-project goal stays active.
