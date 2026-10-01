# Full joint-angle constraints for paired contact fitting

The earlier hand-plane fitter used an inscribed box for each rotation vector.
Its components were limited to the allowed angle divided by sqrt(3). That
guarantees the angle limit, but excludes axis-aligned rotations between 57.735%
and 100% of the same budget. Saturated component bounds motivated testing the
complete rotation ball, not increasing the allowed angle.

## Matched experiment

Two SLSQP trials start from the same shared-marker clips and zero controls.
They retain the same target, plane, selected surface, native-key envelope,
original-reference budgets and residual objective. Each actor gets at most
80 optimizer iterations. The control trial uses the old component-box domain;
the other constrains the Euclidean norm of each joint's normalized control
vector to one. Coordinate bounds of [-1, 1] merely enclose these balls.

Both use the full joint radius as their variable scale. Multiplying the small
control regularizer by sqrt(3) retains the earlier physical objective exactly.
The earlier least-squares-box trial remains evidence, but it is a different
optimizer and cannot alone isolate the effect of constraint shape. Iteration
limits match between the new trials; function evaluation counts can differ.

The joint-margin Jacobian is analytic. The residual cost uses central numerical
differences and a fixed scale from the initial cost. Every optimizer callback
and terminal proposal is replayed after any required inward projection. Only
the best feasible replay is retained. Numerical solver tolerance never enlarges
the joint-angle budget. Original per-joint angle checks are repeated on the
actual exported rotation keys.

Each result independently decodes both GLBs, retains native clocks and unedited
channels, checks outside-window motion, scores the original authored contact
screen and original motion caps, and audits all partner triangles and both
vertex-depth directions at the contact pose. No optimizer status or contact
marker score approves geometry, motion quality or Studio promotion.

## Completed comparison

All four actor fits exhaust 80 iterations. No convergence or infeasibility proof
is claimed. Both trials independently preserve original edit budgets, native
channel clocks, unchanged channels and outside-window poses. Both pass the
original authored contact screen and fail the selected-region plane screen.

| Measurement | Matched box trial | Joint-ball trial |
| --- | ---: | ---: |
| Actor A fit cost | 1,132.420387 | 594.784451 |
| Actor B fit cost | 1,056.998330 | 605.006244 |
| Marker gap | 1.095241 mm | 1.068067 mm |
| Anchor error, A / B | 0.038418 / 0.060200 mm | 0.036878 / 0.042444 mm |
| Normal error, A / B | 18.793106 / 19.014337 degrees | 16.713587 / 16.876708 degrees |
| Vertices beyond plane, A / B | 239 / 217 | 183 / 188 |
| Maximum plane excess, A / B | 7.718447 / 7.627849 mm | 5.667512 / 5.740572 mm |
| Contact-pose proper crossings | 214 | 220 |
| Maximum full-vertex penetration | 11.963172 mm | 10.212648 mm |

The ball result reduces maximum depth by 1.750523 mm but adds six proper
triangle pair crossings at the contact pose. The earlier, different
least-squares-box optimizer had 204 crossings and 11.688520 mm depth. Neither
the plane residual nor any one aggregate metric establishes geometric quality.

All four original motion-cap groups fail in both new trials. Ball-trial failures
are 253 position-speed, 133 position-acceleration, 633 angular-speed and 184
angular-acceleration rows. Largest excesses are 0.095166 m/s, 6.366837 m/s^2,
0.751081 rad/s and 170.530655 rad/s^2. Corresponding box counts are 376, 142, 866
and 197; their largest excesses are 0.113984 m/s, 5.098540 m/s^2, 0.738178 rad/s
and 168.193997 rad/s^2. Fewer failing rows can coexist with a worse maximum.

The ball result reaches within 1% of the original angle budgets at the thumb,
index, ring and pinky bases and the second pinky joint for both actors. This is
not proof that those budgets make the requested pose impossible. The finite
fit has not converged and the plane is only a conservative surrogate.

## Decision and provenance

Retain full joint-vector constraints as a valid way to express the existing
budgets. Do not select either candidate or claim a physical-contact solution.
The next correction should use the actual intersecting triangle surfaces and
contact constraints together, updating partner geometry after pose changes.
Do not keep using decreases in the fixed-plane objective as a substitute for
collision improvement, or increase edit budgets just to obtain a pass. Full
approach/departure fitting still requires a valid contact pose and the original
motion checks.

The comparison verifies that both requests have identical original inputs,
archived implementation, target, selected surface, edit limits and iteration
budgets. It permits only run timestamp and optimizer/constraint label to differ.
Both studies bind 3,241 inputs, 75 archived methods and eight output files;
all hashes were rechecked. Ball and box residual-call counts were
10,732 / 10,734 and 10,728 / 10,729 respectively.

- Ball result SHA-256: `42b57b5c919694e77ad7d38f2bf4007720369a2aed2ec89d0a7bf6672e4f5be6`.
- Box result SHA-256: `5d461409c9d4e566d87ab990960d090f486ffad0cefd1b138f6c0dbab33a1967`.
- Matched comparison SHA-256: `d969b6dd93cd31e9883592fceba5610b94f0b45a5f7e603745d0063d5b1182ee`.

All 1,005 model-free source tests pass. No training, held-out evaluation, full
interval geometry audit, engine import or browser validation occurred. Raw
results remain under ignored `reports/`. All fourteen release capabilities
remain unapproved; no candidate is promoted into Studio.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_contact_plane_pose.py reports/shared-palm-meeting-v1 reports/<fresh-ball-output> --optimizer slsqp_ball
.venv/Scripts/python.exe scripts/study_contact_plane_pose.py reports/shared-palm-meeting-v1 reports/<fresh-box-output> --optimizer slsqp_box
.venv/Scripts/python.exe scripts/compare_contact_plane_constraints.py reports/<fresh-box-output> reports/<fresh-ball-output> reports/<fresh-comparison>
```

Run one heavy study at a time. The hash-bound local rigs and prior studies are
required and excluded from Git. Seven new model-free tests cover an axis-aligned
solution excluded by the box, independent joint-ball projection, the analytic
constraint Jacobian, inward numerical replay, invalid inputs, residual-population
changes, and feasible best-result retention after an iteration limit.
