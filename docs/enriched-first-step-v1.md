# First enriched-path iteration remains rejected

The still-running enriched partner trial has completed its first outer iteration. Its 60-iteration inner solve reached the iteration limit without success. It retained 23.4786 mm of elastic restoration slack, and the relaxed constraint minimum was negative. That slack is an optimizer aid, not an allowed collision in the exported animation.

All eight backtracking proposals improved the internal objective and met the event-region/orientation checks, but each worsened at least one already-failing sample. The unchanged acceptance rule therefore rejected all eight, preserving the original accepted controls. `reports/enriched-first-step-diagnostic-v1` captures the exact history bytes and every regressed frame using the same 1e-9 non-regression tolerance as the guard. This is an intermediate result; the frozen three-iteration trial continues.

The solver currently relaxes every surface constraint with one shared allowance. A shallower failing frame can worsen within that allowance while the maximum penetration or total objective improves. This is a plausible mismatch with the downstream per-frame guard, not a proved cause of the observed failure: the inner solve also failed to converge.

A subsequent experiment should test restoration allowances tied to each frame's existing depth/screen budget, while preserving the final acceptance screen, edit limits and full exported audit. Geometry is nonlinear, so aligning the linearized allowance with the guard cannot guarantee an accepted step. Do not relax the final collision threshold or present a lower internal objective as repaired interaction motion.
