# Serialization-aware motion proposal headroom

The previous mesh-cut repair's second direction failed actual motion limits at
all eight backoffs and all 256 exact ray fractions. This study diagnoses that
mismatch before changing the proposal. Actual motion, palm, edit, witness and
mesh acceptance thresholds remain unchanged.

## Error decomposition

The saved second Jacobian and exact seed are bound to the completed mesh-cut
study. Each backoff is reproduced and evaluated in four forms:

1. The saved affine prediction centered on the serialized seed.
2. The unrounded nonlinear animation.
3. The unrounded nonlinear change, added to the serialized seed.
4. The actual serialized animation.

The third form removes the constant seed rounding offset. Its difference from
the affine prediction measures local nonlinear error; its difference from the
actual serialized animation measures the change in serialization error.
Every original motion row is checked. Failing rows carry joint, time interval,
units, original cap, seed headroom and both error magnitudes. No diagnostic
result can approve or publish an animation.

The full step has five failing affine rows, five failing recentered nonlinear
rows and seven failing serialized rows. The seven smaller backoffs have no
failing affine or recentered nonlinear rows, yet fail respectively 2, 2, 3, 4,
2, 1 and 3 serialized rows. No new failure is attributable solely to nonlinear
curvature in these eight samples. This finding concerns this direction and
these samples, not all possible controls or serialization error bounds.

Most smaller-step failures are finger angular acceleration at 1.483333333 to
1.5 seconds. For A's thumb at fraction 1/16, the serialization-change vector
error is 7.363056e-5 rad/s^2, while the nonlinear vector error is 2.405418e-12
rad/s^2. A's index has only 4.404208e-7 rad/s^2 headroom at the seed; changing
rounding error can overwhelm that margin even on a tiny step.

All 2,873 bound inputs, 68 archived methods and three outputs were rehashed.
Diagnostic `reports/coupled-mesh-motion-probe-v1` binds:

- Result: `267b33e0e0aadbf3d2be9bdba6e8259df9da3432b40583bb695f6b0940cbe42b`.
- Request: `a27ff575b7c4c2c88b6899e6745db51714ca8c81cbe051a965aa3bf33ac3d268`.
- Decomposition: `90fbc332a053073ee406999f392d1235078be5ae741cd360b4181cbcd2e3d79b`.

## Bounded headroom proposal

For each row that fails after serialization in the diagnostic, the proposal
reserves twice the largest observed sum of nonlinear and serialization-change
vector errors, plus 1e-9 times that row's normalization scale. This is an
empirical target on the proposal only, not a certified error bound. It neither
raises original caps nor asserts that unseen rows or directions are safe.

The same saved Jacobian and exact seed produce one new direction at trust
radius 0.001. Only the proposal's vector caps are reduced. Original geometry
witness reserves, objective ceiling, scalar constraints and control bounds
remain in place. A 256-point serialized replay uses the original untightened
acceptance caps. A changed selected output would still require the complete
53-time mesh guard and independent export checks.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-probe> --mesh-ray-study reports/coupled-mesh-cuts-v1 --probe-motion
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-headroom> --mesh-ray-study reports/coupled-mesh-cuts-v1 --motion-headroom-study reports/coupled-mesh-motion-probe-v1
```

The bound studies and assets are required locally and remain excluded from Git.
Ten new model-free tests distinguish nonlinear from serialization error, remove
constant seed offsets, reject changed references and invalid diagnostics, and
verify that proposal tightening does not change actual replay caps.


## Completed headroom outcome

The revised conic proposal reports `AlmostSolved` and supplies a direction.
**202 of 256** exact replay fractions preserve all original motion, palm, arm
and finger edit constraints, versus zero on the preceding unreserved direction
from the same saved seed/Jacobian. The best admissible fraction is 255/256.

Its worst normalized violation falls from 0.009095176 to 0.000233171, a **97.44%**
reduction relative to the starting state for this experiment. The fixed-axis
objective increases from 3.388868 to 3.553050 mm, still below the unchanged donor
ceiling of 3.580942 mm. This is a constraint tradeoff, not an animator-quality
score or a physical penetration-depth improvement measurement.

All original hard motion/palm/arm constraints and 3,610 finger edit rows pass at
this internal state. There remain **251 old signed-witness failures** and
**21 new projection-row failures**, with maximum excesses about 3.973987 and
4.663423 micrometres respectively. These are proxy constraint excesses; the
candidate is still rejected. Selected output GLBs remain byte-identical to the
donors, and no new mesh guard or Studio promotion occurs.

The ten new tests and full minimal suite pass: **980 tests**. All 2,945 bound
inputs, 69 archived/current methods and nine output files were rehashed.
Study `reports/coupled-motion-headroom-v1` binds:

- Result: `1fb9bb4a6a64ecf68f3ccc30a180b8309186aca0788d81c967d88d37d0e17195`.
- Request: `c70c321b109defa00f404a7dd10728c96929b51ae59d282fefef1b2315c33142`.
- Iteration summary: `c69504bb2679e2634910e96faf08843e30632956b04b101a50f73bb93516388f`.
- Final constraints: `7f4f84c3013f428788bbdbec7bb7267926bb7ecc0e019750a45d8e51b27af77a`.

Next relinearize at this exact improved state, preserving the original reference,
frozen mesh cuts and actual limits. Carry the observed-error reserve as a
proposal heuristic, recheck all rows after serialization, and refresh the error
model if newly affected rows fail. Full geometry remains mandatory before any
changed clip can be selected. No training, held-out use or release approval.
