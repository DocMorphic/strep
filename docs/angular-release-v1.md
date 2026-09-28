# Per-joint angular correction development study

The earlier root repair introduced a right-toe rotation spike that a whole-body maximum hid. The new protocol measures every edited joint at every adjacent frame edge and targets the largest excess over that joint's raw/prior peak. It preserves root, contacts, floor, edit bounds, already-passing releases and all original aggregate comparisons. This is a new development comparison, not a revision of old results or a physiological speed limit.

For proper rotations, the Frobenius norm of the matrix difference divided by sqrt(2) equals2sin(theta/2), where theta is the relative rotation angle. The implementation uses this monotonic norm in conic proposals; actual exported local angles decide the independent audit. SciPy's official [rotation-vector documentation](https://scipy.github.io/devdocs/reference/generated/scipy.spatial.transform.Rotation.as_rotvec.html) documents radians and angle-vector magnitude; the matrix-chord identity and derivative are separately tested in this project. Existing local-rotation/right-Jacobian code was inspected and reused in the new isolated helper. No active study dependency changed.

Each joint's reference is max(raw global peak, prior global peak)+1e-5degrees. Its per-edge safety bound is max(source edge, reference). Existing excesses may improve but cannot grow, and already-passing joints cannot cross their reference. No limit is inferred from agility/strength or presented as animator approval. The target is selected before optimization; a six-frame neighborhood may change. Root coordinates and the protected joint stay eliminated.

The fixed budget is12accepted steps, at most9proposals per step, and8safeguard fractions per proposal. Trusts0.01/0.001/0.0001 accommodate the measured1.55degree regression but remain subject to unchanged absolute and adjacent edit limits. Prediction margins only tighten proposed constraints. AlmostSolved remains optimizer metadata; serialized feasibility, geometry and objective reduction govern acceptance.

Three focused tests pass, including noncommuting rotations, chord/angle equivalence through pi, full objective/constraint derivatives and a spike hidden by another joint's larger motion. The real-character preflight has126variables and51,045constraints. Its largest directional discrepancy is2.36e-6, below the frozen2e-4threshold; original-margin identity error is1.67e-16. See reports/angular-release-tests-v1.json and reports/angular-release-rig03-v1/derivative-proof.json.

The first trial accepts four steps. The selected RightToeBase step32 falls from11.237850 to9.164529degrees/frame, below9.687237. Its global peak moves to the unchanged step75 at9.523382 and now passes its joint comparison. The independent audit verifies all14combined preservation checks, all16original aggregate comparisons,144untouched decoded frames, exact repaired-root matrices and450Godot actor-frame checks. Candidate SHA25620b493d7871c429930da9c9f4c96e0e64f4dba659eaf16bd8cbb22205b82be10. LeftLeg and LeftFoot peak comparisons still fail; all failures remain reported.

Evidence: reports/angular-release-rig03-audit-v1/completion.json. No animator ratings, cleanup-time evidence, held-out generalization, physics validation or production approval follows from this numerical improvement. Angular acceleration, rotation tails, intentional motion and other joints/actions still need evaluation.


The second frozen trial (LeftLeg step108) makes no accepted change. Most AlmostSolved proposals exceed their trust box by1.5e-12 to2.6e-11 and are discarded before actual evaluation. The sole qualifying proposal fails the unchanged serialized constraints. This is retained as a failed method result, not presented as a proven physical conflict or global infeasibility.

A separate projected variant clips each finite Solved/AlmostSolved proposal into the intersection of the same trust box and original absolute-coordinate bounds, retaining raw deltas and projection distances. It does not alter acceptance tolerances. Two focused projection tests pass; a fresh real-mesh proof passes. `verify_projected_angular.py` independently reconstructs every projection before accepting the decoded audit.

Source chaining is also tightened: once a source has an angular audit, every added angular preservation guard must pass before it can seed another trial. A failed target may continue, but a failed preservation guard may not. Two tests exercise missing/false guards. Older frozen study implementations and output decisions remain preserved.


The projected trial clears LeftLeg step108 from8.905816 to8.474804degrees/frame in one accepted step, below8.733907. Its independent audit reconstructs the4.6078e-12coordinate projection exactly and passes all14preservation checks, all16original comparisons and450engine actor-frame checks. LeftFoot remains above its joint reference.

A measured tradeoff remains: integer-frame penetration rises from zero to1.505661mm, within the unchanged5mmguard. The worst half-frame penetration remains2.591363mm. Passing a frozen tolerance does not mean geometry is unchanged or perfect; both clock populations stay in the report. This trial is retained, not promoted to product default or human-approved motion.


## Final audited development result

The final projected follow-up clears LeftFoot step13 from12.669854 to11.843089degrees/frame in one accepted step. The remaining foot peak moves to step102 at12.235221, below its12.638320reference. All eight edited-joint peak comparisons, all14preservation checks and all16original aggregate comparisons now pass. Root matrices remain exact; each latest block preserves144unselected frames and verifies450nativeGodot actor-frames. Independent projection reconstruction checks the1.6921e-10maximum clipping adjustment. Final candidate:da456c243e6dc2d2efd1e21ed52a6bd7188ec54f9a46268e1f52c158f3b069b4.

This does not establish complete angular quality. A separate fresh audit still finds95th-percentile increases versus raw/prior: LeftLeg+0.033680, RightLeg+0.149519, RightToeBase+0.227609degrees/frame. There is no calibrated perceptual threshold for these differences. Peak constraints can redistribute motion without improving every tail statistic; ratings and cleanup evidence must assess usefulness. The integer/half-frame penetration tradeoff above also remains.

Final evidence: reports/angular-release-summary-v1.json, reports/projected-angular-release-rig03-audit-v2/completion.json and reports/angular-final-joint-dynamics-rig03-v1.json. Seven focused tests across angular derivatives, box projection and source-audit chaining pass. All release gates remain open; no checkpoint, UI or product default changed.

Next evaluate this method on another eligible action/rig and preserve the full declared population, rather than repeatedly optimizing this one clip against additional after-the-fact metrics. Existing release-restore-v1(backpedal) and block-release-dance-v3(grapevine) are potential inspected development replications; their older audit schemas and missing root-cap fields must be explicitly adapted and verified, not bypassed. They are not held-out data.
