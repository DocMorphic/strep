# Compact surface guidance for native motion edits

The optional compact guide represents each observed triangle pair with one separation condition instead of nine vertex-pair conditions. This reduces the size of proposal guidance while retaining all six triangle vertices. Existing jobs, verifiers and acceptance limits remain unchanged.

For a fixed normal `n`, the condition `min(A @ n) - max(B @ n) >= clearance` is equivalent in real arithmetic to requiring that clearance for all nine vertex pairs. Both extrema are reevaluated when vertices move. Floating-point evaluation can differ slightly because the arithmetic order differs.

## Query and model behavior

`scripts/native_compact_surface_rows.py` queries every declared time, actor pair and triangle population using the existing crossing and containment procedures. Object, plane and penetrating-vertex witnesses retain their original forms. An insufficient row budget rejects the complete build; it never returns a truncated subset. The report records compact and expanded populations separately.

`scripts/native_compact_surface_model.py` appends the compact guides after every original native norm, retaining its caps and scales. Optional decoded anchoring checks that these arrays remain identical. The model supports central differences and bounded one-sided differences at control limits.

The minimum/maximum gap is nonsmooth. Its local finite differences are not equivalent to linearizing nine separate inequalities. Every proposal still needs independent export, decoding, original native checks and complete geometry evaluation. This optional model is not connected to existing Studio jobs and does not approve motion or release readiness.

## Software validation

The 24 new focused tests compare compact and expanded gaps on generated fixtures, including moved vertices that become new extrema. They also check complete populations, preserved object and plane witnesses, insufficient budgets, changed inputs, invalid settings, original native norms and decoded anchoring.

These tests establish the software behavior on small fixtures. The retained scene's full-clock compact guide, solver proposal and resulting geometry have not yet been evaluated with this implementation. Its previous geometry failure remains unresolved.
