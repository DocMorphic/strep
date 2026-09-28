# Preserve reached targets during quality refinement

Status: complete as a development experiment, without promotion. Both eligible cases preserve their targets, but jump improves only marginally and dance does not improve. Getting up remains an explicitly rejected input because it did not reach the requested targets. The full-project goal remains active.

`TargetPreservingRefiner` minimizes the existing surface/support/trajectory objective over coordinated controls, while keeping the reached joint position and orientation inequalities active. It rejects inputs with unmet targets. A small normalized interior margin, at most 0.001 and no more than half the input's minimum margin, helps retain accuracy through export without changing the declared 5 mm/5 degree limits.

The original hard edit bounds, root/edit-vector step limits and actual rotation-step allowance remain unchanged. Additional guards use the actual full skin and recorded support vertex groups. Every editable integer frame may increase its floor penetration by at most one micrometre. Each requested support's position-error cap is its input error, with a 0.1 mm minimum radius for numerical conditioning; each consecutive support edge is capped by its input displacement, with a 0.01 mm minimum. These small allowances are recorded explicitly. Predicted supports remain unconfirmed; preserving their diagnostics does not make them physical annotations.

The floor inequality uses the lowest actual skin vertex at the current pose. Its derivative is piecewise smooth and the selected vertex can change. Support derivatives include both endpoints of each edge. SLSQP may fail or exhaust its budget; only a checked objective-decreasing feasible point can replace the input, with tested endpoint backtracking when necessary. Reached targets, score improvement and these guards still do not establish naturalness, contact semantics, anatomical validity or collision freedom.

## Experiment

The source is the independently verified `pose-tolerances-v1` study. Jump-land and dance, seed 502, are eligible. Get-up remains in the requested-case list with its rejection reason and source failures; it is not omitted to inflate success rates. The edit envelope, control spacing, targets, weights and hard limits are unchanged. The fixed budget is 40 SLSQP iterations per eligible case. This is posthoc development work, not held-out evaluation.

Raw, target-met and refined outputs are preserved with source hashes, original/warm/final arrays, the control basis, actual per-frame/support guard values, full optimizer trace and final solver outcome. Independent verification checks targets, fixed context, motion/edit limits, original and warm-start provenance, control subspace, full mesh floor guards, support position/edge caps and the original scalar quality objective. Half-frame floor regression is measured separately because the optimization guards apply at integer samples. Engine import and served-file hashes follow the independent geometry checks.

Eighteen focused tests passed in 10.49 seconds: three new refinement tests plus fifteen target-tolerance/coordinated-control tests. New coverage includes full-surface and coupled support derivatives against finite differences, direct skin-height checks, rejected unmet targets, and an actual improving refinement with reached targets, fixed context and all guards preserved. No existing solver was modified. The full canonical suite subsequently passed 460 tests in 135.83 seconds, with four existing Torch deprecation warnings and one existing SLSQP trial-clipping warning. Its log is `reports/target-refinement-v1/full-tests.log`.

Before final verification, the verifier was extended to measure decoded GLB integer-frame floor/support cap excesses separately from the float64 fitting arrays. No guard or acceptance tolerance was enlarged. The original verifier and amended version are both retained. The comparison viewer now includes raw, target-met and refined stages, plus a visible rejected get-up entry. Both actions, stage switching, authored frames, playback and grey character rendering were checked in the browser; no console errors were observed.

## Results and decision

| Requested action | Target error | Orientation error | Editable floor depth | Quality cost before → after |
|---|---:|---:|---:|---:|
| Jump-land | 4.97487 mm | 4.97539° | 3.23759 mm | 6.94704511 → 6.94700391 |
| Dance | 3.86989 mm | 4.97491° | 10.02163 mm | 39.24499978 → 39.24499978 |
| Get-up | Input rejected | Input rejected | Not refined | Not refined |

Both optimizations exhausted 40 iterations (SLSQP status 9). Jump's cost reduction is about 0.00059%; dance retained the input. These results do not demonstrate useful visible quality improvement. One of three requested cases meets the numerical target/floor screens. Dance still fails editable, whole-clip and half-frame floor screens; get-up still misses the input targets. No action is approved by an independent animator.

Source hashes, warm starts, control span, fixed context, motion bounds, targets, float64 floor/support guards and scalar energy were independently verified. Decoded GLB floor caps pass exactly. Decoded support caps show precision-scale excess: at most about 0.000017 mm for jump and 0.000050 mm for dance. These remain reported as exact-cap failures; no cap was silently enlarged. The largest jump half-frame floor increase is about 0.00000215 mm, and dance's is zero.

All four raw/candidate GLBs have zero validator errors or warnings. Actual Godot import checked 540 frames, with maximum position disagreement of 0.0000003372 m. Served raw/candidate file hashes pass. The target-met copies retain the verified upstream hashes. The viewer separates those structural checks from quality claims.

Do not promote this refiner as a default quality improvement. Integrate sparse joint-target editing as an explicit experimental operation with retained inputs and failed candidates, then address action/contact/dynamics failures and broader fixtures. Repeated tuning of this small pair cannot stand in for that work. See `interaction-physics-research-2026-09-27.md` for the next comparison directions.
