# Full-vector contact bounds in minimax proposals

Development component, 2026-10-18. The preceding sequential high-five trial
retained all three point contacts, then rejected later collision proposals
that lost them. Its scalar distance linearization permits sideways movement
outside a contact sphere even when the predicted distance row passes.

`minimax_step` now accepts optional complete `affine_vectors` (B by 3),
`affine_jacobian` (B by 3 by N), and positive `affine_radii` (B). All three
must be supplied together. Every vector receives a hard second-order cone:

```
norm(vector[b] + jacobian[b] @ delta) <= radius[b]
```

These cones have no peak-violation slack. Every original scalar row,
protected halfspace, original-relative control ball and trust bound remains
present. A fixed impossible cone returns no proposal; it is never silently
dropped. A local solver failure is not a proof of nonlinear infeasibility.
All affine data are owned copies, finite and bounded; shapes, complete
columns, up to 8,192 vectors and the original 64 MiB model budget are checked.

The solver searches inside each radius by a relative 1e-8 reserve. Returned
affine norms must pass the supplied radii exactly, with zero additional
physical tolerance. A test injects an apparent solved point only 1e-13
outside a radius and verifies rejection. The component does not infer units
or contact geometry: the caller must supply a consistent vector model.

Output trust checks now compare against the original caller bounds rather
than the solver's tighter internal search box. This avoids rejecting valid
points for rounding across an internal margin while keeping the original
trust bounds and control-vector balls exact. Nothing is clipped, and no
physical budget or tolerance is widened.

All **174 focused cases pass locally**, including the previous 157 and
17 new contact-cone cases. Tests reproduce scalar sideways drift, verify its
vector-constrained replacement, include both actors and the last contact,
retain fixed cones and original control balls, reject invalid/incomplete
inputs and enforce strict affine acceptance. Two earlier test runs remain
archived: they exposed an internal-box false rejection and an axis-aligned
degenerate scalar fixture. The final fixture tests sideways contact drift
away from that unrelated degenerate optimum.

Local source evidence: `reports/conic-affine-contact-tests-v3`.
Both hosted Tensor test groups include the new cases. Hosted results and the
same-state high-five comparison will be recorded after completion.

This is exact geometry for an affine approximation. Actual articulated
motion remains nonlinear, and full mesh, original/raw/saved motion,
serialization permissions, engine and human review gates remain mandatory.
The existing failed studies and qualified partial reference stay unchanged.
The entire-project goal remains active.
