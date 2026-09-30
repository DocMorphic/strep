# Cylinder pose: simultaneous collisions and nonregression

Both comparisons finish **without an accepted step**. They preserve the previous rejected pose byte-for-byte. They explain why the strict restoration policy stalls, but do not solve cylinder grasping or establish infeasibility.

## Fixed condition and acceptance

The input is the selected frame-96 pose from the [bounded feasibility experiment](cylinder-pose-phase-one-v1.md). Original source-relative rotation/root budgets, actor, cylinder, contact windows, patches, guide anchors, triangle selections and contact tolerances are unchanged. Smooth bounded rotation coordinates keep every trial inside its rotation budgets.

The diagnostic exposes **36,518 individual residual rows**: all skin-floor values, all skin-object values, all authored patch-clearance values and every regional contact condition. Some patch vertices also appear in whole-skin object checks. A step must lower the maximum positive violation without introducing or increasing any other positive residual. It must pass that rule both in the continuous solver representation and after the independent float32 pose reconstruction. These are deliberately strict restoration safeguards, not new product quality thresholds. Original pose acceptance remains separate and unchanged.

No trial replaces a Studio clip. If all probes fail, the original pose file is copied exactly. The method is a separate diagnostic, not an enabled production correction.

## Near-tied active-row model

`scripts/regional_pose_bundle.py` includes near-tied extrema and individual contact constraints in a small local linear model. A minimax LP proposes a normalized step. Ten nonlinear backtracking probes check the complete residual vector. Regressing omitted rows can enter the next local model; the initial policy permits four such rounds, 128 active rows and five accepted steps, within a 180-second/memory guard.

The matched run completes in **6.328 seconds**, with peak observed process RSS **617,758,720 bytes**. Its models grow from **34 to 52 to 68 to 85 rows**. All **40 trials** are rejected. The first full step lowers the worst normalized violation from 23.039575 to 22.091606, but creates 11 newly failing rows and worsens 129 already-failed rows. Even the last 1/512 step worsens 104 failed rows.

Independent replay distinguishes two causes. At that last probe, seven regressions are on rows already in the model and 97 are omitted. The local model predicts essentially zero regression on its selected rows, while nonlinear evaluation increases one by 1.292e-5 normalized units. More collision samples alone cannot resolve these tangent-step regressions.

## All-failing-row inward model

The second mode includes every failed row, every row within 0.1 normalized units of its boundary, and the required contact/extremum rows. It requests common inward improvement on each failed row rather than leaving some exactly at their current ceilings. `scripts/inward_feasibility_step.py` maximizes that common improvement with the same coordinate trust bounds; passing constraints receive no relaxation. A secondary LP minimizes the largest normalized displacement while preserving the primary improvement to its declared numerical reserve.

This is a different linear model and row-selection policy, not an iteration-only retry or a one-factor ablation. The original nonlinear/serialized acceptance policy is identical. The active-row resource cap is 4,096.

The run completes in **61.781 seconds**, with peak observed process RSS **624,148,480 bytes**. It evaluates models of **1,982 and 1,992 rows**, followed by **20 nonlinear trials**. Both models find a positive common inward direction. Two trials pass all continuous nonregression checks, but fail after float32 reconstruction. They are the same coordinates reached in the two rounds, not two independent improvements.

For those trials, 11 serialized rows worsen. The largest increase is **6.558524e-6 mm (6.559 nanometres)** at object vertex 3550, repeated in its hand-patch row. The original penetration remains approximately **21.040 mm**, and both hand contacts remain invalid. Thus the safeguard is reacting to representation-level changes while the substantive failure is still centimetres large. Neither this rounding effect nor the local LP result proves the original task infeasible.

All 40 first-run and 20 second-run trials replay independently, including edit-bound checks. The inward model's full set of 1,992 differentiated rows passes a directional finite-difference check. Both final pose hashes equal the input pose hash. All failures, coordinates, protocols, snapshots and checks remain saved.

## Decision and reproducibility

Do not spend another run merely increasing the cut or iteration budget. Strict per-vertex monotonicity is a poor primary search rule for this failed pose: nonlinear tangent steps regress, and sufficiently small continuous improvements reach float32 reconstruction differences. The next useful comparison should separate exploratory feasibility search from candidate promotion, represent simultaneous clearance residuals directly, and continue to require the original independent contact/geometry thresholds for any passing result. It must not turn a smaller residual or optimizer convergence into quality approval.

With the separately acquired assets and retained bounded study:

```powershell
.venv\Scripts\python.exe scripts/regional_pose_bundle.py reports/cylinder-pose-bounded-v1 reports/<new-bundle-study>
.venv\Scripts\python.exe scripts/regional_pose_bundle.py reports/cylinder-pose-bounded-v1 reports/<new-inward-study> --model all_failed_inward
```

The source includes active-row and LP regression tests. Eight pure NumPy/SciPy inward-step tests are included in public Windows/Linux CI. Asset-dependent tests also cover equivalence between the full vector and the original maximum-based constraints, bounded seed reconstruction, tied-row descent, and rejection of a per-vertex tradeoff hidden by a better maximum.

Local evidence stays in `reports/cylinder-pose-bundle-v1`, `reports/cylinder-pose-inward-v1` and `reports/cylinder-pose-bundle-review-v1`. The repository publishes methodology and concise results; generated pose/character payloads remain excluded. No held-out prompt/seed is consumed, no checkpoint changes, no new engine or human-review evidence is claimed, and all fourteen release capabilities remain unapproved.
