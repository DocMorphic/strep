# Bounded temporal joint-target correction

Status: all three fits and independent export checks complete; none passes the complete numerical screen. The full-project goal remains active. This extends the existing mesh/support trajectory solver, rather than using independent frame-by-frame IK.

`PoseTrajectoryFitter` adds sparse world-joint positions and orientations to `TrajectoryFitter`. World position and orientation derivatives are analytic and checked against independent finite differences. Existing mesh-floor, foot-height, support position/velocity, motion-acceleration and edit-prior terms remain active. Existing hard root translation, joint rotation, edit-step and actual adjacent-rotation limits are unchanged. Goals must lie in editable frames, refer to a skin bone below the editable root, and carry finite coordinates, proper orientation, positive weights and provenance. Duplicate frame/node goals are rejected.

The3selected inputs are jump-land, dance and get-up offsetseed502 from `pose-response-v1`, chosen because their measured absolute targets failed. Selection is posthoc development work, not held-out release testing. The original clips, target NPZs and hashes are preserved. No checkpoint, inference or training changes occur.

Each edit spans31frames centered on the authored target, with a smooth envelope and the first/last two window samples fixed. Every world pose outside the editable window is copied exactly from the original. The initial root limits are4cmhorizontal/12cmvertical, edited joints use25degree budgets for the target chain and existing leg limits for support. Root-edit steps are limited to1.5cm, rotation-edit steps5degrees, and actual adjacent rotation may increase by at most0.5degrees relative to the source. The inherited component bounds conservatively fit inside those norm budgets.

The pose objective uses positionweight60 and orientationweight0.5. Each case gets4alternating sweeps and at most30function evaluations per coordinate solve. These budgets are recorded before fitting. A fixed computation budget is not proof of convergence or optimality. Contact/floor/goal accuracy remain soft objectives; infeasible and insufficiently optimized results are retained without approval.

The source's foot/toe predictions draft unconfirmed support intervals and surface vertices; no human support annotation is inferred. The target foot is excluded from pins when it is deliberately being repositioned. Other supports remain explicit in each request. Foot-height targets are zero-clamped source clearances, not a flight or planted-contact classifier. Skin clearance covers the actual eight-weight mesh, not only skeleton joints. Uneditable source-floor failures remain in the final clip and its measurements.

Nineteen focused tests passed in18.41seconds:10newjoint-goal tests and9existingtrajectorytests. One SLSQP internal-trial clipping warning occurred; accepted outputs were separately checked against hard bounds. No inherited production solver code was changed.

A finalizer observed the fit process finish successfully, then independently checked source hashes, exact outside-window world poses, unedited local chains, hard edit/step limits, all decoded poses, full-mesh integer and half-frame floors, target residuals and predicted-support diagnostics. All invariants passed. Six GLBs validate with zero errors and warnings; Godot imported all 900 sampled frames, and all six served files match their saved hashes. The grey-character comparison is available at `reports/pose-trajectory-v1/viewer.html`. All three actions, dynamic timelines and authored-frame controls were exercised; playback advanced, characters and markers remained visible, and browser error logs were empty. These are UI checks, not animator review.

Development screens are5mmposition,5degreesorientation and10mmfloor. They are reported separately from invariants and do not constitute physical, semantic, anatomical or animator approval. Do not add this correction as a production default until actual results and action preservation are reviewed.

Before the independent verifier's first execution, its flag list was corrected to include half-frame floor failures at the same 10 mm threshold. The original verifier measured those samples but only flagged integer-frame depth. The frozen fit, thresholds and raw measurements are unchanged. The original verifier snapshot is retained; save the executed verifier with final evidence. Finite half-frame sampling still does not certify collision freedom continuously between samples.

## Measured results

| Action | Target position, original → candidate | Orientation, original → candidate | Window floor, original → candidate | Whole-clip floor |
|---|---:|---:|---:|---:|
| Jump and land | 41.643 → 10.155 mm | 6.746 → 9.008° | 6.534 → 3.164 mm | 7.634 mm |
| Dance | 33.579 → 10.312 mm | 12.249 → 10.662° | 11.933 → 10.634 mm | 16.506 mm |
| Get up | 80.650 → 77.671 mm | 15.863 → 15.687° | 90.954 → 89.205 mm | 323.271 mm |

All three miss position and orientation screens. Dance and getting up also fail floor screens at integer and half frames. Whole-clip maxima remain unchanged because failures outside the edit window are deliberately preserved. All four sweeps were used; none meets the small-update stopping rule. There are 25, 53 and 93 solver updates reporting non-success respectively. Accepted updates preserve the hard bounds and do not increase the local objective, but those facts do not establish convergence, naturalness or usable target accuracy.

No candidate is promoted or installed as a production default. [Posthoc anchor diagnostics](pose-target-diagnostic-v1.md) find that the same targets can fit within the edit box when neighboring frames are ignored, but those probes violate temporal limits. This motivates coordinated changes across multiple frames while retaining contact and orientation constraints. Existing spline-based native correction code should be evaluated for reuse before introducing another solver. Full source-floor correction, self/object/partner collisions and action preservation remain separate requirements.
