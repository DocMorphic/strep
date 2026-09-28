# Authored intent and exported dynamics

The audit covers every completed contact, joint and posture edit present in Studio at preparation: 15 jobs (10 contact, 2 joint, 3 posture), including rejected jobs and repeated development runs. All 15 were measured successfully. This is an integration study, not 15 independent held-out motions or a quality pass.

`scripts/audit_authoring_intent.py` freezes the population, input/result/recipe hashes and transitive local Python implementation. It checks exact GLB lineage, matching clock, topology, skin and geometry, then decodes both complete clips. It measures each skin joint's peak and P95 local rotation step, mapped-root acceleration, saved world-space mesh contact targets, sparse world-joint targets and timed local finger intent. Finger intent is reconstructed independently with quaternion interpolation. Original recipes and results are not modified. Failure rows remain in the denominator.

Evidence lives in `reports/authoring-intent-audit-v1/`: request, one detailed JSON per job, implementation snapshot and completion. Four tests passed in 3.73 seconds: changed-source rejection, world-target errors, independent attack/hold/release interpolation and shortest rotation across the 180-degree boundary. No new engine import or human evaluation was performed.

## Findings

| Edit | Fresh observation | Implication |
| --- | --- | --- |
| Head clearance, `20260926-195612-5047106e` | Target error 171.973 → 13.747 mm; peak root acceleration 3.987 → 13.446 m/s². Historical status is provisional pass. | Meeting the old contact screen does not establish acceptable dynamics. Preserve the explicit head target in any further correction. |
| Right-hand target, `20260927-043725-43fc4d62` | Position error 20.000 → 4.975 mm, orientation error 0 → 0.756 degrees; inherited heel error 23.720 → 24.113 mm. | Keep its rejected status. A successful hand adjustment does not fix the inherited support failure. |
| Left-hand target, `20260927-044311-aab345bc` | Position error 20.000 → 4.972 mm, orientation error approximately 0 → 0.670 degrees; heel error 23.720 → 24.394 mm. | Same separation of achieved intent and unresolved support. |
| Three finger-posture jobs | Maximum error from independently reconstructed intended rotation ≤ 0.000003156 degrees; unedited local matrix error ≤ 7.18e-8; frozen world matrix error ≤ 5.35e-7. | Increased finger rotation speed can be the requested edit. Restoring the input's angular peak would erase intent. Anatomy and grasp quality are still unreviewed. |

The measurements are integer-frame observations. They do not certify continuous collision, force balance, semantic correctness, naturalness or physiological capability. There are no invented angular or acceleration pass thresholds. The old statuses are retained as history, not re-approved. The research angular chain currently lacks a generic adapter that protects arbitrary authored head/hand/finger constraints, so these jobs are not automatically submitted to it.

## Next integration

Build an adapter around an exact selected edited GLB. Carry the original target definitions and achieved target errors into explicit preservation constraints, together with existing root/contact/floor and edit budgets. Sparse world position/orientation targets, local timed finger poses and mesh patch targets need distinct treatment. Independently inspect a proposed export against all these constraints before presenting it as a usable corrected version. Retain the original and every rejected candidate. Do not apply an input angular ceiling indiscriminately to requested pose changes.

## Parallel contact continuation

`edit-buffer-conic-foot-rig02-v2` continued the prior solver with the unchanged 12-step budget, trust region, safeguard and tolerances. All derivative/conic preflight checks passed; its first proposal was rejected, so it ended with zero accepted steps. The output remains byte-identical to v1 (`fc9b257695dd5915c6596d59fa661406900eb7c2eea0e01554915e1d9d17a059`). The fresh `edit-buffer-conic-foot-rig02-audit-v2` verifies root preservation, strict geometry/edit constraints and 450 engine actor-frames, but both original foot release comparisons still fail. This is recorded stagnation, not proof of infeasibility or a successful correction.

Runtime snapshot v53 verifies the original four worker identities and all frozen/current implementation hashes. Whole-support remains 16 complete, 1 running, 7 pending; partner correction remains at iteration 2 with 24.740384 mm overlap. CPU time continues to advance. Studio is unchanged. All project release gates remain open under the same active project-wide goal.
