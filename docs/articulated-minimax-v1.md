# Bounded articulated tracks and complete minimax proposals

Development components, 2026-10-18. These author controls and propose a local
step; they do not approve motion or narrow the whole-project release goal.

`scripts/articulated_track.py` applies explicit local rotation-vector edits and
optional root translations to a complete supplied clip. Rig joint indices,
rotation budgets, temporal basis and protected frames come from the caller.
There is no action-name, humanoid-joint-name or anatomical mapping whitelist.
The source rotations are owned copies and must already be consistent with SO3.
The module does not repair a rig, infer joint limits or evaluate forward kinematics.

Rotations use matrix exponentials, preserving the rotation representation.
Every unselected local joint stays unchanged, and protected frames have exact
zero temporal support. Per-frame vector norms are checked before applying an
edit; excessive controls reject without clipping or normalization. A convex
temporal basis makes bounded knot-vector controls sufficient for complete
per-frame bounds. The explicit complete frame assessment stays available.
Actual serialized geometry, kinematics, motion and author limits still require
independent checks. The normalized control assessment does not approve them.

The initial implementation supports 3–300 frames, 1–256 source joints,
1–16 selected joints and 1–8 temporal columns. Rotation budgets are positive
and at most 90 degrees; root translation is explicitly bounded up to 22 cm.
These are component capacities and author permissions, not measured human
abilities or new release thresholds. With root editing disabled, no hidden
root variables are created.

`scripts/conic_pose_minimax.py` retains every supplied signed physical row and
all normalized three-vector control balls. It minimizes the largest linearized
violation, with a small movement cost, instead of summing collision errors.
Two characters' controls can appear in the same rows. It uses the existing
pinned Clarabel backend, explicit trust bounds and a declared search reserve
strictly inside author budgets. Solver tolerances never replace strict physical
or saved-file gates, and controls are never clipped after solving.

A solver result is a proposal. Closest-feature changes, nonlinear FK, geometric
sign classification and serialization can invalidate a linear prediction.
Complete nonlinear and raw/saved checks remain mandatory. Uneditable failed
rows stay visible; a failed local model is not proof that an action is impossible.

The first source suite passes **139 cases**, including the previous 111.
New checks cover exact zero/frozen/unselected behavior, full control Jacobians,
true angle norms and SO3, complete temporal bounds, source ownership, invalid
permissions and explicit disabled root controls. Solver cases verify competing
contact rows, a mean-error tradeoff rejected by minimax, actual vector balls,
nonzero original-relative controls, both actors and a hidden last-row violation.
Malformed or over-budget inputs reject before solving.

Local evidence: `reports/articulated-minimax-tests-v1`. These checks are
engineering evidence; the next study must use the original real clips and
retain all failed constraints, exported artifacts and independent observations.
