# Component correction with separate clear-sample guards

The [clear-component capture](clear-component-guards-v1.md) supplies complete derivative coverage for the 98 originally positive component samples and the previously missing shifted support peak. A new solver version, `native_material_component_guarded_support_step.py`, now keeps those positive rows hard alongside the existing full-mesh guards. The earlier solver and scientific archives stay unchanged.

## Local model and coverage

Require a separately typed `ComponentSeparationGuards` argument with complete ordered source pairs, group identities, time/axis/margin metadata and an explicit component-only coverage report. Reject missing, overlapping or mislabelled rows, wrong source IDs, mismatched control columns or a claimed full-mesh/continuous partition. Auxiliary rows have no objective slack or extra objective weight. Each row enters the conic directly and is checked again at every point in the strict 81-fraction retreat.

Original native norms, control/trust boxes, parameter equations, starting containment and legacy triangle-deficit ceilings stay hard in the represented local model. Preserve solver statuses and distinguish full-mesh from component-only guard reports in every result. Strict local checks still do not establish nonlinear or stored-output nonregression.

The experiment retains all original 90 controls, 30,450 native norm rows, 1,707 native samples and 1,673 geometry samples. Reuse the independently replayed same-point ten-frame native/material/full-mesh model and the 107-time component model at the verified 54-choice anchor; no fresh derivative observations are generated for this trial. Add one complete 64-row objective group at 0.8947917073965073 s, where the preceding failed export's support peak shifted. Its gap derivatives explicitly project fresh component point-derivative columns onto the fixed axis; existing finite-gap derivative rows remain byte-exact.

The combined model has 2,196 material rows and eleven complete component groups with 704 ordered vertex-pair rows. The original 3,132 full-mesh hard guards retain the complete 519,840 triangle/time-pair partition at ten times. Another 6,272 separately typed auxiliary rows cover every one of the 98 originally positive component samples. Eleven full-mesh query times measure the changed exports, but the added query time is not relabelled as a new full-mesh guard partition.

## Actual stored results

Three new 101-variable conics use original norms, event-preserved parameter equations and uniform-increment equations respectively. All return `Solved`. Their strict retreat fractions are 0.9999980926513672, 0.9999999995343387 and 0.9999999999708962. From each candidate, export the original requested full/half/quarter/eighth fractions and audit both stored actor files under the original 54-choice storage policy. Save every payload, decoded norm/vector/world observation, guide query and failure.

| Parameter family | Stored motion failures: full / half / quarter / eighth | Centered proxy failures | Actual full-mesh guard failures | Actual component guard failures |
| --- | --- | --- | --- | --- |
| Original controls | 12 / 7 / 5 / 1 | 7 / 0 / 0 / 0 | 4 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Event preserved | 18 / 2 / 6 / 6 | 4 / 0 / 0 / 0 | 6 / 0 / 0 / 0 | 8 / 0 / 0 / 0 |
| Uniform increment | 1 / 5 / 4 / 3 | 1 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

Every represented affine full-mesh and auxiliary guard passes for all twelve exported fractions. Actual event full fails eight component rows, illustrating that the additional affine rows also require actual checks. Original full and uniform full each fail one original contact row; every reference and control/trust check passes. The centered proxy passing at smaller steps does not isolate pure storage rounding in their failed actual native vectors.

Only uniform half, quarter and eighth pass both actual legacy-triangle and containment ceilings along with every actual full-mesh and auxiliary guard. Those three still fail five, four and three original motion rows. Every export improves its measured eleven-group deficit sum from 0.15344238576232624 m, but all twelve retain 188 proper crossing records over the eleven full query frames. This count is explicitly checked by record kind; it is not an assumed interpretation of an aggregate score.

No export passes all declared actual eligibility checks. Consequently no changed candidate is selected for a new full 1,673-sample scene scan, and no scan is inferred from sparse query success. The original already-failed anchor remains the selected source. The earlier 32 failed late-recovery component rows are not accepted merely because a solver returned a local candidate.

## Verification and next decision

Thirty-two new solver tests pass without skips. They cover hard auxiliary conic rows without slack, every-row retreat, independent full-mesh restrictions, original caps and parameter equations, preserved solver statuses, nonpassing anchors, mutation isolation and complete source/time/axis/descriptor validation. Existing bound solver implementations are not edited.

A separate original-context reader reconstructs the eleven-group model, the added peak's fresh derivative projection, original event/uniform equations, all three complete conics and strict retreat prefixes. It decodes all twelve actual exports and reproduces the complete native/contact/reference checks, every full-mesh and auxiliary guard, material ceilings, all eleven-frame mesh queries and the absence of an eligible selection. The two prior complete derivative readers and 9,120 exact rational affine coordinate bounds remain bound. Skinning and geometry predicates are shared; no optimum, nonlinear enclosure, independent collision arithmetic or global infeasibility is claimed.

Next trace all failed original motion-row identities and complete saved vector defects, especially the three uniform candidates that pass actual material/guard checks. Only then choose bounded fixed-control storage correction or an updated response model from the measured error. A successful storage correction must still recheck every actual guard and the unchanged full original scene; it cannot promote this failed trial. Do not loosen the original caps or discard source faces to obtain a pass.

The saved-data trace is complete for all twelve exports and all 30,450 vector rows, retaining entire before/predicted/actual vector populations and original caps/scales. It binds the previously independently reconstructed original norm identities. The three actual-material-passing uniform candidates fail angular acceleration only: half fails A node 7 at 1.175 s, B node 6 at 0.9666666667 s and B nodes 6/7/8 at 1.1833333333 s; quarter fails A node 8 at 1.05 s, A nodes 6/7 at 1.125 s and A node 7 at 1.175 s; eighth fails A node 8 at 1.0583333333 s, A node 7 at 1.0666666667 s and B node 7 at 1.125 s. These are exact fixture source-node identities, not production anatomy. Their affine norm rows pass, and their centered scalar proxies pass. The complete stored vector defect still combines nonlinear response and storage effects. The eighth is a concrete candidate for a bounded fixed-control storage experiment; three localized failures do not guarantee that the search will succeed.

Raw outputs stay under ignored `reports/`. All fourteen release evidence arrays remain empty and the full-project goal stays active. No arbitrary-action, production anatomy/rig, engine import, animator review, cleanup-time or release approval follows from this experiment.
