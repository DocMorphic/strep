# Exact norm budgets and wider surface-path correction

The original pose solver used a component box inscribed in each joint's allowed rotation ball. `bounded_pose_ball_ik.py` now refines that feasible initializer using the complete norm-constrained search space, without increasing the declared limits. A finite, feasible improvement is accepted only if it preserves already matched targets; otherwise the initializer remains the result.

The ten-actor study at `reports/bounded-wrist-pose-v2` completes with **9/10** strict matches, using the same 0.5 mm position and 0.5° orientation tolerances. Seed 2089 actor A improves to 0.08075 mm position error and 4.46163° orientation error. Its four edited joints reach the existing 15°, 25°, 35° and 30° caps. The remaining orientation failure is retained. These limits are edit budgets, not anatomical limits, and local optimizer failure does not prove global infeasibility.

No v2 timed export or scene-quality approval follows from the pose study. The earlier bounded-wrist v1 timed exports continue their own independent geometry audit. The completed native full-body/posture audit is summarized separately in `reports/paired-pose-posture-summary-v2`; all whole-motion collision/floor screens still fail.

`bounded_path_trajectory.py` applies full norm constraints to timed controls. Its nonnegative interpolation basis keeps integer-frame corrections inside the declared balls; a separate constraint limits adjacent correction-vector changes. Independent decoded fractional checks remain necessary. The first wider-window surface trial uses this module and retains the prior guard against actual mesh-depth regressions at fitting samples.

Four focused tests pass: the exact norm pose solver reaches a rotation excluded by the old box, retains a genuinely out-of-budget target as unmatched, checks norm-constraint derivatives and diagonal overruns, and distinguishes allowed total rotation from excessive temporal correction speed. These tests do not certify whole-motion quality.
