# Reusable surface-pose feasibility proposals

`scripts/surface_pose_feasibility.py` exposes
`propose(window, initial, max_iterations=...)` for existing `CoupledPoseWindow`
and `SampledPoseWindow` objects. The caller initializes floor working sets and
supplies the original constraints and explicit fitting reserves. The helper
uses a constant-zero SLSQP objective to seek a feasible correction without
pulling it toward a separate fidelity target.

The input is copied, fixed parameters stay fixed, and the iteration budget must
be explicit. Bounds and floor working rows must stay frozen during the solve.
Invalid parameters, mismatched derivatives, changing constraint populations and
nonfinite results are rejected. Complete floor rows rank candidate iterates,
including vertices omitted from optimizer rows. A better intermediate candidate
is retained when the solver's final point regresses. An already feasible input
is returned unchanged; an entirely fixed but infeasible input remains a failure.

The returned metadata separates the solver's status from the independently
computed fitting-constraint result. Derivative consistency allows floating-point
roundoff; the final fitting-gap comparison and box/fixed checks remain strict.
The helper does not alter targets, caps or reserves. It does not grow working
sets during the optimizer invocation or export animation. Callers must still
check the complete requested sample clock, decoded animation, preserved keys and
engine behavior, under the existing resource guard. Modeled fitting samples are
not a continuous collision certificate. Quality and release flags stay false.

Twenty direct tests pass, covering real native rotation interpolation, incoming
pose preservation, repair checked against original step bounds, hidden floor
failures, misleading success flags, a regressing final iterate, frozen-row/bound
mutations, malformed derivatives and outputs, and explicit iteration limits.
Both source-test inventories include the helper tests: 650 full and 199 focused
Python test files. This is source-level coverage; Studio does not automatically
select this new helper yet.

## Continued get-up evidence

The earlier experiment driver in `reports/kaykit-getup-rolling-v7` continues
from the 95-pose checkpoint using the feasibility objective and 0.5-mm internal
geometric fitting buffers. It accepts all 45 attempted windows before its soft
time checkpoint: finalized through key 138, validated lookahead key 139,
140 of 180 poses. All 5,533 prefix samples pass the unchanged original limits.
Maximum floor depth is 4.740287 mm, contact error 19.867673 mm, root correction
step 24.997139 mm and rotation correction step 4.999863 degrees. Candidate
SHA-256:
`125f55cff0d6778c27cb69ab93649f6ab0927ec75ad393939ce080cb787f6d4b`.

`reports/kaykit-getup-rolling-engine-v7` checks the independently reconstructed
clock in fourteen Godot batches, totaling 5,560 observations. Every prefix
pose/skin/floor/contact check passes, with maximum skin disagreement 0.031912 mm.
This evidence belongs to the experiment driver; the new reusable helper has its
separate 20-test coverage above. The next continuation is prepared to exercise
the helper directly, retaining full decoded-window and prefix checks.

The continuation's 13 export checks and the helper's 20 tests pass. Three
resource traces replay across 835 observations, with peak worker-tree memory
322,383,872 bytes. Hash bindings and unchanged release requirements are checked
in `reports/surface-pose-feasibility-publication-v1/summary.json`.

The complete clip, ordinary playback, physics, GPU skinning, continuous geometry
and human motion-quality approval remain unfinished. Preserve all earlier
failed attempts. The next continuation starts at key 138; published release
requirements and the broad action scope are unchanged.
