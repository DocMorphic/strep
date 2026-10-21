# KayKit getting up sequence correction

This development study extends the bounded static pose experiment to all 180
native keys of the generated KayKit Skeleton Minion getting-up clip. It fits
explicit contact phases and neighboring correction bounds. A completed fitting
run is not evidence that the resulting animation passes those bounds; decoded
geometry and actual engine observations determine the measured outcome.

## Contact and correction method

The study retains all 22 model-predicted Foot and ToeBase intervals, including
single-key intervals. Three additional hand intervals are a geometric draft:
source wrist height at or below 60 mm for three consecutive keys starts an
interval at the first of those keys; height above 100 mm ends it. This proposes
left-hand support at keys 0–107 and right-hand support at 0–41 and 68–124.
Height alone does not establish stationary contact or action semantics.

For each phase, vertices with at least 65 percent direct weight on its mapped
joint form the candidate region. The vertex with lowest mean original height
over that phase supplies one fixed material point. Its median original position,
projected to floor height zero, supplies the target. These targets are derived
from the defective transfer and require review; they are not mocap ground truth.

The fitter evaluates all 4,858 mesh vertices. Eighteen mapped local rotations
may change by 45 degrees, except the head at 60 degrees. Pelvis translation is
bounded to 150 mm horizontally and 0–750 mm vertically. Acceptance retains a
5 mm floor penetration limit and 20 mm point-target error. Fitting reserves
1 mm inside each limit. The smooth floor approximation includes every vertex
and has at most 0.25 mm downward bias in exact arithmetic. Full decoded vertex
checks remain authoritative.

One forward and one backward coordinate sweep update each key while neighboring
corrections remain fixed. Neighbor bounds are 25 mm root displacement and
5 degrees of rotation-vector difference. These bound the correction parameters,
not total animation speed. Each update retains the best observed constraint
violation and then objective value; an optimizer failure is preserved. A later
neighbor update can invalidate an earlier pair, so complete final checks are
necessary. The static frame-40 proposal seeds the first sweep; it is not assumed
feasible at other frames.

## Complete sequence outcome

The compact run completes all 360 pose updates and exports all 180 native keys.
The candidate fails the declared numerical constraints and is not selected.
Across 1,053 decoded samples, 696 exceed the floor limit, 714 exceed the contact
limit and 51 exceed the root displacement limits. Rotation edit limits pass,
but 11 adjacent root correction steps and 21 adjacent rotation correction steps
fail their bounds. Maximum floor penetration is 226.831742 mm; maximum proposed
point-contact error is 235.053603 mm. Maximum adjacent correction steps are
124.466240 mm and 19.319876 degrees. Export roundtrip vertex error is only
1.432e-7 m, so these large defects already exist in the fitted proposal.

The candidate SHA-256 is
`4369018917d3c84f3604f40b2a0780538fba7238227312a7f22c1a0ca45165f5`.
The decoded audit SHA-256 is
`ad3a23cc841bf292d599b2efd079714a95ded79cb319538217733e4d89bb4fff`.

## Verification method

The candidate replaces only mapped rotation channels and pelvis translations.
Original native clock values, mesh, skin and original binary bytes remain
unchanged. The audit includes native keys, their midpoints, a uniform 120 Hz
clock and the exact endpoint. Contact intervals include their native endpoints;
single-key intervals are instantaneous.

Independent replay reconstructs phase membership, selected material points,
targets, clock population, saved edits and complete skin geometry. The actual
Godot check uses the existing native-authoring resource path. It checks imported
pose and skin agreement and remeasures floor and contact errors. It does not
establish ordinary playback, physics, GPU skinning or usable motion.

Independent replay verifies all 1,053 samples and the 25 phases. Its separate
skin arithmetic agrees within 8.969e-16 m. Actual Godot 4.7.2 authoring-resource
capture passes pose and skin agreement, with maximum skin error 0.034011 mm,
and reproduces exactly the same 696 floor and 714 contact failures. Thus engine
agreement confirms the defective proposal rather than approving it. The maximum
native-key local angular-speed diagnostic rises from 451.701101 degrees/second
in the original to 575.776194 in the proposal. No rate approval follows.

The independent replay result SHA-256 is
`bbcc0b58a9d254a79cdc2cf213ff6434cbf34646a34d27573f4e5bb8558f80e1`.
All three resource traces replay, covering 1,214 recorded observations. Peak
observed worker-tree memory across these runs is 375,160,832 bytes. The existing
600 MiB free-memory stop threshold remains unchanged.

The initial dense constraint run was deliberately stopped after 12 updates
because of its measured cost. Its inputs, checkpoint, stop evidence and failed
exit remain in `reports/kaykit-getup-sequence-v1`. The compact floor version is
recorded separately in `reports/kaykit-getup-sequence-v2`; independent replay
belongs to `reports/kaykit-getup-sequence-replay-v1`.

Twenty-one focused tests pass: ten cover complete constraint derivatives,
neighbor bounds and invalid inputs; eleven cover floor approximation bias,
tied-height derivatives, compact constraints and lazy derivative caching.
Both CI inventories include these test files. This is not a full-suite CI claim.

## Next experiment

Before another full sequence fit, check feasibility at the starting pose and
each proposed hand release or arrival. Compare the retained dense first-pose
checkpoint with the compact run, and inspect whether the projected targets
are compatible with the character geometry. Preserve the current target set
as a failed baseline. A revised proposal must explicitly identify changed
targets or phases rather than silently removing difficult contacts. Then solve
coupled neighboring keys with all pair constraints active together; repeat the
complete decoded and engine checks before considering a candidate for review.

Self-collision, anatomical support, balance, semantic correctness and animator
cleanup remain separate requirements. The project-wide release goal remains
active across all action families.
