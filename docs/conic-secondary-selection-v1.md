# Checked secondary motion proposals

Conic proposals now recompute all affine norm rows before selecting the
secondary minimum-movement result. An approximate solver status alone cannot
replace the primary minimax step. This affects the shared proposal solver for
arbitrary scene/action requests, not an action-specific motion rule.

The secondary result must remain in the original control/trust boxes, pass
every hard affine row and preserve the measured primary soft-row minimax error
within the existing 1e-9 tie allowance and an explicit floating-point comparison
reserve. The reported primary objective can itself understate its recomputed
error, so the tie bound uses the larger value. The comparison reserve is
`128 * (controls + 4) * float64_epsilon * max(1, abs(bound), abs(error))`.
It applies only to the proposal tie-break, is recorded in diagnostics and is
not a certified numerical-error bound or a relaxed decoded acceptance cap.

If the secondary result fails these checks, one stricter solve retries the
same model and bound. Each solve retains 100 iterations and a 30-second limit;
this adds at most one solve. Every retry receives the same complete checks.
If neither secondary result qualifies, the primary proposal is retained.
All attempts, statuses, measured errors, comparison reserves and selections
are recorded. Actual exports and complete scene checks remain the acceptance
authority; no solver status grants motion or release approval.

## Verification and retained failures

Eleven new tests cover misleading `Solved` and `AlmostSolved` statuses, soft-bound
overruns, hard-prefix violations, invalid/out-of-box points, successful retry,
reported-objective discrepancies, valid refinement, overflowed affine rows and
the explicit tie reserve. The final 14-module related check passes **229 tests**
in 54.31 seconds.
It includes real geometry/contact direction tests, surface restoration, partner
surface models, key/contact norms and full focused-inventory dispatch. Its guard
completes at 54.875 seconds execution and all 72 resource observations replay.
The complete source inventory now contains 478 Python modules and 42 Node
suites; the new module is also declared in the focused CI inventory.

An earlier check passed 65 focused tests but broader validation exposed an
unwanted movement component in an existing geometry/contact test. Two repair
attempts retained that regression (225 and 226 other checks passed). A separate
three-row diagnostic found the stricter secondary solve missed its proposal tie
bound by about 3.72e-13. The explicit comparison reserve fixes that regression;
the existing test and actual hard/decoded criteria are unchanged. All failed
logs and resource phases remain retained, rather than replaced by the final run.

## Development motion context

Before this code change, a one-micrometer inward **proposal** floor target
preserves all 2,017 sampled floor times at 4.998972 mm peak depth, while leaving
one intended and 24 serialized motion violations. The remaining intended row
is LeftArm angular acceleration over 2.158333, 2.166667 and 2.175 seconds, with
normalized excess 5.052974343474407e-9. Native failure groups are one position
speed, 21 position acceleration and two angular acceleration rows.

That study completes at 80.141 seconds / 97 observations. Fresh shared-arithmetic
reconstruction matches payloads, worlds, complete intended/native rows, original
caps/scales, controls/clocks and every full floor sample in 40.610 seconds /
58 observations. All four probe hashes are checked; other rays are not all
numerically replayed. The original 5 mm floor gate is unchanged. A targeted
twenty-times-overrun proposal margin worsens the full-step intended minimax error
and retains 19 intended / 50 native failures; it is a rejected alternative.

Checking the secondary result without retry initially falls back to the larger
primary step. Its full and half rays pass intended motion rows, but respectively
fail 153 and 44 floor times at 18.028396 and 7.075075 mm peak depth; they retain
16 and 21 native failures. An affine-valid step can still fail decoded geometry.
The worker completes at 44.703 seconds / 62 replayed observations. These raw
results remain available and do not establish feasibility or motion quality.

The checked retry version reruns the identical cached model without changing
caps, Jacobian, controls, source or geometry policy. The initial secondary is
rejected at 5.050773705981469e-9 affine soft excess versus a 1.000082382333489e-9
bound plus a recorded 1.904254531837069e-12 comparison reserve. The stricter retry
reports `InsufficientProgress` and is not selected. Full and half rays reproduce
the previous fallback exactly. Quarter and one-eighth rays respectively retain
zero and one intended violations, 35 and 32 native violations, and seven and
three failed floor times at 5.846453 and 5.217701 mm peak. All are rejected.
The study completes in 68.016 seconds / 85 replayed observations. These are
fresh complete probe audits, not separate numerical replays of every ray.

A separate captured-iterate diagnostic evaluates every original affine row on
the raw retry point. The retry returns the **identical** point and the same
5.050773705981469e-9 soft excess as the rejected initial secondary. It is not a
hidden feasible solution whose status alone prevented selection. The primary
control-step norm is 0.494326 versus 0.000355 for the secondary; that large
difference explains why preserving a valid small-movement refinement matters.
The diagnostic completes in 11.187 seconds / 29 replayed observations, archives
all three iterates and source bindings, and performs no motion export or mesh
check. Conditioning of the small-movement solve is the next measured question.

Ignored local evidence includes `reports/crawl-intended-restoration-v7`,
`reports/crawl-intended-restoration-replay-v7`, `reports/clearance-motion-failures-v1`,
`reports/crawl-intended-defect-margin-v1`, `reports/native-secondary-validation-v1`
through `v5`, `reports/native-secondary-diagnostic-v1`, `reports/native-secondary-iterate-v1` and
`reports/crawl-checked-secondary-v1` and `v4`. Source, assets, controls and full sampled
populations remain bound to their phases. No new model/training or reserved
held-out evaluation is performed. Live rendering, engine fidelity, dynamics,
semantics, independent review and cleanup evidence remain outstanding.
