# Explicit joint-target tolerances

Status: the component and three-case real-motion trial are complete and independently verified. Two cases meet both target tolerances; one also meets this study's floor screen. This is not a production default or a quality approval.

The coordinated jump trial lowered its weighted objective and improved position while worsening orientation. That exposes a distinction between reducing a score and meeting the requested target. `scripts/rig_pose_tolerances.py` adds separate position and orientation inequalities over the existing coordinated temporal controls. It reuses the same world-joint derivatives and all inherited per-frame edit and neighbor-motion limits.

Position is measured as world-space Euclidean distance; orientation uses the relative rotation angle through the trace formula. The default tolerances are 5 mm and 5 degrees. Analytic derivatives include the contribution of each temporal control to the target frame. The scalar feasibility slack relaxes only the target inequalities during solving; edit and motion limits remain independent hard constraints. The objective minimizes the worst normalized target violation, aiming slightly inside the tolerances with a 0.01 dimensionless interior margin. The final geometric acceptance still checks actual distance and angle against the declared tolerances.

The stage retains the best target improvement that satisfies the hard motion limits. If a local solver exhausts its budget or returns an invalid endpoint, candidate segment steps are tested. An unmet request is returned as `target_tolerances_not_met`, with the candidate, measured residuals and solver status preserved. This is not a certificate of global infeasibility. Reaching a joint target is also not evidence of correct surface contact, floor clearance, collision avoidance, naturalness or action identity; those remain separate validation gates. The feasibility objective deliberately does not optimize the prior surface/support energy, so a subsequent quality stage must maintain reached targets while addressing those terms.

Fifteen focused tests passed in 6.49 seconds: eight new tolerance tests and seven existing coordinated-control tests. They check position/angle values against direct geometry, derivatives against finite differences, a reachable request with both tolerances met, exact fixed context, hard limits, explicit rejection of a far request without an infeasibility claim, and invalid tolerances. These synthetic tests are implementation evidence, not evidence of broad animation capability.

## Real-motion trial

The frozen protocol starts from the independently verified `coupled-pose-v1` candidates for jump-land, dance and get-up, all seed 502. It keeps the original targets, 31-frame edit envelope, ten-frame control spacing and hard motion/edit limits. The budget is 150 SLSQP iterations, with 5 mm/5 degree tolerances and the same 0.01 interior margin. This is posthoc development work, not held-out or equal-compute evaluation. Raw, coordinated and tolerance-stage files, source hashes, full optimizer traces, control bases and arrays are preserved in `reports/pose-tolerances-v1`.

| Action | Position, coupled → target stage | Orientation, coupled → target stage | Target-stage window floor | Result |
|---|---:|---:|---:|---|
| Jump and land | 5.701 → 4.975 mm | 10.185 → 4.975° | 3.238 mm | Target and numerical floor screens pass |
| Dance | 4.995 → 3.870 mm | 6.142 → 4.975° | 10.022 mm | Both target tolerances pass; floor fails |
| Get up | 68.747 → 6.580 mm | 14.834 → 6.581° | 90.207 mm | Targets and floor fail |

Jump and dance finish successfully in seven and four iterations. Getting up exhausts 150 iterations; its best motion-feasible candidate is retained with an explicit target failure, not an infeasibility certificate. Whole-clip floor maxima remain 7.634, 16.506 and 323.271 mm because defects outside the edit window are fixed. Dance and getting up also fail half-frame floor sampling.

The previous weighted quality energy changes from 5.415 to 6.947 for jump, 39.283 to 39.245 for dance, and 116599.459 to 116485.853 for getting up. Jump's increase demonstrates why target success alone is insufficient. Getting up worsens its window floor maximum from 89.245 to 90.207 mm despite its large target improvement. These tradeoffs are reported without threshold changes.

Independent verification reconstructs target acceptance, normalized target violation, source/warm-start hashes, fixed context, control subspace, hard edit/motion bounds, decoded poses, surface floor depth and previous quality energy. Six GLBs validate without errors or warnings; all 900 frames import in Godot, and all six served files match their hashes. Root-motion sidecars retain candidate GLB hashes. The three-stage browser comparison covers all actions, raw/coupled/candidate selections, dynamic frame limits, authored-frame seeking, playback and pause. Grey characters and target markers remain visible; browser error logs were empty. None of this supplies an animator rating.

The next quality stage should keep successful target tolerances enforced while improving surface/support quality. Failed requests need explicit rejection or a user-visible change in editing scope, not a hidden relaxation of limits. Whole-clip floor failures, action preservation, self/object/partner collision handling and held-out evaluation remain open requirements under the full-project goal.
