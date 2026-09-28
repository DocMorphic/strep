# Knee contact across neighboring frames

The static pose experiment showed that explicit knee and foot patches can meet the existing floor/contact screens within declared pose budgets. It did not establish a usable animation. The next comparison applies each solved pose to its full source clip with a local edit envelope.

`pose_edit_window.py` adds the center pose's local rotation changes and world-root displacement to the body-clearance animation. A quintic envelope spans a 31-frame neighborhood with two unchanged outer samples. The source is preserved exactly outside the active window before export. A focused test verifies center matching, correct root displacement beneath a rotated parent and unchanged outer poses.

All eight full clips retain the ordered posture proxy and reach their center-frame contact targets. Every candidate reintroduces floor penetration: 7.19–39.93 mm, measured on all skin vertices at keys and quarter frames. All 1,440 candidate Godot frames import correctly. The blend is therefore retained as a failed development comparison, not adopted.

`audit_knee_window_bounds.py` separates source and candidate limits inside and outside the edit window. Most global step warnings already exist in the body-clearance source. For example, final-frame seed 1301 already has a 17.073 mm root-edit step at frame 142, outside the window around frame 62. Its local window remains below the 15 mm step limit. Do not attribute an unchanged outer failure to the new edit.

The first hard temporal pilot uses the first declared case, rather than selecting an easier result. It updates 27 interior frames with all-vertex keyframe floor constraints, the same center-frame contact target, pose budgets and limits relative to both neighboring edits. Outer body motion remains fixed. The original contact contract is a single frame; no sustained knee support interval is claimed.

An initial preflight stopped before optimization because the legacy solver's conservative angle/sqrt3 component box excluded a RightShin rotation of 28.962 degrees that meets the declared 35-degree norm limit. The failed preflight and source code are preserved. The temporal solver now uses the actual Euclidean joint-angle and horizontal-root constraints. This expands the internal parameter subset without increasing the declared budgets. Independent decoded edit checks remain required. Two focused objective/constraint derivative and norm-budget tests pass.

The pilot permits four coordinate sweeps with 80 SLSQP iterations per frame. It retains all solver outcomes and accepts only successful updates that satisfy nonlinear constraints; no successful convergence of the whole trajectory is implied by reaching the sweep cap. Final evaluation includes dense interpolation, unchanged outer motion, source-relative edit budgets and center contact. Human review and the full release goal remain open.


## Completed hard temporal pilot

All 108 updates across four sweeps were accepted, and the resulting 180-frame GLB passes actual Godot import. The independently decoded audit samples all keys and eighth frames (1,433 samples). Maximum floor depth is 4.990 mm, center-frame knee errors are 14.16 and 3.65 mm, and pose and neighboring edit budgets pass inside the window. The standing–kneeling–standing proxy is preserved. The three global root-edit step failures at frames 39, 142 and 143 already existed in the body-clearance input outside the window.

The candidate is not promoted. Right-knee patch peak speed rises from 0.350 to 1.178 m/s, with the new peak at frame 49.125 near the correction boundary. Passing geometric and edit limits did not establish smooth motion. Four sweeps are a bounded experiment, not proof of convergence. Contact remains a single-frame target, not an interval support contract.

The next controlled ablation should center pose and temporal priors on the already body-corrected input, with hard constraints and solver budget unchanged. The current objective instead penalizes edits relative to the limb-only source, so it can pull neighboring poses away from the desired input. Retain this as a testable explanation, not a confirmed cause or guaranteed fix. Current results and detailed tracks are in `reports/knee-contact-temporal-audit-v1`.


## Reference-preserving objective

The matched ablation is complete. Both versions use exactly identical initial, body, limb and envelope arrays, source/spec hashes, hard constraints, pose budgets and four-sweep/80-iteration limits. The new reference trajectory was independently reconstructed from saved body transforms. Three focused tests establish zero-reference equivalence, objective derivatives and identical hard constraints, plus explicit-reference validation.

Right-knee peak speed falls from 1.178108 to 0.542870 m/s, moving from boundary frame 49.125 to frame 62.125. Its source peak is 0.350198 m/s. Left-knee peak is 0.882880 versus source 0.881782 m/s, both at frame 56. Floor depth remains 4.990 mm across 1,433 samples; center left/right knee error is 14.59/2.81 mm. Pose and window step budgets, posture order and all 180 Godot frames pass. Existing outer source failures keep the global step gate false. All 108 updates were accepted, without a convergence or naturalness claim.

The result supports preserving the body reference as a promising objective change on this clip. It does not establish sustained support or generalization. The unchanged method is now evaluating the remaining seven cases in the original development cohort; the completed pilot is reused. No release/default promotion. See `reports/knee-contact-reference-comparison-v1` and `reports/knee-contact-reference-population-v1`.


## Full reference-method cohort completed

All eight declared cases complete with no filtered failures. Each passes its center contact, 1,433 decoded floor samples, pose and local edit budgets, posture-order proxy and 180 actual Godot frames. The global step gate passes only 2/8; the other failures share identities with the input, and no new step-failure identity appears. All8 increase at least one patch-speed peak. Four seeds under two ending-guide conditions are paired development data, not eight independent or held-out examples. No default/release promotion. Full comparisons are in `reports/knee-contact-reference-population-summary-v1`. The explicit one-second hold pilot is the next quality experiment.
