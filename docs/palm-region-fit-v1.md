# Palm-region fitting: development failures and step safeguarding

This experiment replaces the arbitrary same-vertex equality with explicit palm-region proximity, while retaining the original point-fit failures. It uses the previously observed first left-high-five seed, with both actors' reference finger postures already authored. It is neither a held-out test nor a generic scene-aware motion model.

The bind-mesh region consists of triangles entirely within 45 mm of the existing knuckle-derived palm center, inside the hand skin region, and within 60 degrees of its palm-side normal hint. These anatomical labels remain unreviewed. Each direction chooses three source vertices at least 6 mm apart and their closest points on the opposite palm region. Correspondences update between outer solves. Source and target proximity witnesses are checked separately, so projection onto a single target corner cannot be presented as distributed contact.

The objective fits a 1 mm separation, region normal and finger direction, plus small rotation edits. Full-mesh nearby/inside correspondences form 1 mm signed-clearance inequalities in each local SLSQP solve. Arm edit budgets and the 15-frame temporal envelope remain unchanged from the coupled-arm experiment. The numerical solver can fail; a frozen correspondence constraint is not a certificate for the actual deformed mesh.

The independent verifier reads the exported GLB mesh and animation, evaluates every declared patch vertex against the opposing patch, and finds realized triangle witnesses among vertices within 3 mm. Both sides need at least 25 square millimetres of spatial spread, opposing normals within 20 degrees, and full-body vertex penetration no greater than the existing 5 mm diagnostic. The triangle is a proximity-spread witness, not measured physical contact area or pressure. Edge-only intersections, self-collision, continuous time and anatomy remain outside this screen.

| Attempt | Initialization | Outer steps | Final selected-pair distance | Decoded event depth | Outcome |
|---|---|---:|---:|---:|---|
| v1 | Intersecting point-fit pose | 4 | 0.140 mm | 18.586 mm | Proximity witnesses pass; collision fails |
| v2 | Original separated pose | 8 | 7.071 mm | 21.483 mm | Proximity and collision fail |
| v3 | Original pose, nonlinear step check | 8 | 51.696 mm | 0 mm | Collision diagnostic passes; contact fails |
| v4 | Orientation initialization, nonlinear step check | 8 | 30.868 mm | 0 mm | Contact screen fails; normal and collision diagnostics pass |

The first attempt's four inner solvers all report a positive directional derivative failure. From the original pose, the first unconstrained approach can create previously absent collisions outside the frozen active set; later local constraints then struggle to escape. These are recorded failures, not demonstrations of impossibility.

The safeguarded version tests the full nonlinear bilateral mesh query at up to eight decreasing step fractions (1, 1/2, …, 1/128). A trial must not increase measured penetration beyond the current depth or a 1 micrometre numerical floor, and must not increase the current frozen objective. Otherwise it retains the current pose. All tested parameters, depths, objectives and acceptance decisions are saved. This does not establish collision-free motion between event frames or between line-search samples.

The v3 safeguard kept accepted event depth at zero and reduced the selected-pair gap from 213.578 to 51.696 mm, but it did not achieve contact. An independent rejected-trial audit (`reports/palm-region-obstruction-v1`) found 5.57 mm penetration at a thumb and the opposing index base. The original finger-direction mismatch was about 78.6 degrees; v3 still had about 59.9 degrees at step 7. The fourth attempt tests orientation initialization before approach, without changing the hand or contact thresholds.

Six focused tests pass (5.50 seconds): surface/orientation and inequality derivatives, declared-region correspondence membership and source spacing, analytic plane-patch proximity, rejection of point/line proximity as area coverage, and full-query step rejection/acceptance including retaining the input when every trial fails. No full suite or animator review is claimed.

All four completed exports passed actual Godot comparison on both input and candidate actors: 600 actor-frames per attempt, 77 bones per frame. Context outside the envelope, unedited locals, all local translations and native root/contact/heading arrays are preserved. `completion-verification.json` binds the artifact hashes and failed screen decisions. v1's verifier source was reconstructed from the one known boolean-reporting edit and matched exactly to the original recorded SHA; v2/v3/v4 retain the exact current verifier source. Source license files are included. No candidate is promoted to Studio defaults or a qualified high-five.

The next solver work must address finger posture/orientation and temporal contact while preserving full-surface checks. A lower point distance, solver convergence or engine import alone is insufficient.


The orientation-initialized v4 has now completed and been independently exported/audited. It retains zero measured vertex penetration at frame 75 but fails the contact-area screen while the opposing-normal screen passes. Its 30.868 mm figure is the maximum of the selected solver correspondence distances; the independent verifier evaluates all region vertices and does not equate this scalar with usable contact. Across four attempts, 2,400 actual Godot actor-frame samples pass; all four interactions remain unqualified. No whole-window collision run is inferred from these failed event screens.

Eight safeguarded outer steps are a fixed development budget, not a convergence or infeasibility certificate. Further work should inspect solver convergence, finger posture/orientation and temporal approach, then freeze the method before evaluating unseen partner cases.


## Fixed continuation comparison and approach failures

The v4 parameters are the identical starting pose for two eight-step continuations. V5 retains 24 arm parameters; v6 adds 19 bounded finger joints per actor (138 parameters total), initially zero. Source, arm budgets, envelope, contact objective, safeguard and common implementation hashes match. This is an equal iteration budget, not an equal runtime or optimizer-difficulty comparison. The existing anatomical limitations remain. All 138 orientation/contact/clearance derivatives and exact zero-finger pose preservation pass focused tests.

| Continuation | Selected-pair gap at event | Decoded event depth | Distributed contact | Peak depth in five approach samples |
|---|---:|---:|---|---:|
| V4 starting candidate | 30.868 mm | 0 mm | Fail | 19.685 mm |
| V5: eight more arm steps | 3.246 mm | 0 mm | Fail | 21.187 mm |
| V6: eight steps with fingers | 3.847 mm | 0 mm | Fail | 21.189 mm |

Both continuations pass opposing-normal and event penetration diagnostics but fail the unchanged contact-area screen. Arms alone improve more on the final selected-pair maximum gap; this does not establish a general ranking or physical success. All eight arm inner solves succeed; finger inner solves 1 and 6 report failure and remain preserved. V6's maximum additional finger edit is 10.033 degrees under the original per-joint correction budgets. Root/body/translations and the unchanged context remain independently verified. Both exports pass 600 actual Godot actor-frames each. The comparison is `reports/palm-region-continuation-comparison.json`; its `max_joint_step_degrees` means change between **optimizer iterations**, not adjacent animation frames. Actual adjacent animation edits remain bounded by 5 degrees and checked in export preservation evidence.

`audit_palm_approach.py` independently samples decoded GLBs. The completed narrow audits for v4/v5/v6 use frames 74, 74.5, 75, 75.5 and 76, input and candidate, with bilateral bounded mesh queries. Every input sample measures zero vertex penetration. Every candidate exceeds 5 mm at 74 and 74.5, with its worst sample at 74.5. The event itself remains zero. This proves the single-event correction can create approach collisions; it does not estimate an unmeasured full-window maximum. No candidate is promoted. `reports/palm-approach-comparison.json` binds all three summaries and sample populations.

The new audit passes an analytic moving-cube test: integer frames are clear while the half-frame sample penetrates by 400 mm. A second test verifies clipped window boundaries and rejects invalid sampling settings. Ten focused tests passed across the region, fingers, safeguard, independent geometry and temporal sampling groups (eight in 18.77 seconds, two in 4.58 seconds); no full-suite claim.

The grey-character comparison is `reports/palm-continuation-review-v3/viewer.html`. It retains the same frame when switching between original input, starting candidate and both continuations, supports half-frame scrubbing, verifies GLB hashes, and includes full-finger camera bounds. Earlier v1/v2 viewer builds are retained. This is a development review, not an independent animator rating.

Next: build a bounded trajectory correction that checks the approach/release samples as well as the event, retain unsuccessful candidates, and evaluate the complete declared window before broadening to unseen partner cases. Do not relax contact or collision tolerances to turn these outcomes into passes.
