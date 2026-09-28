# Per-frame collision limits inside the partner solver

Development investigation, 2026-09-28. The project-wide goal remains active and every release gate is open.

The completed projected partner trial repeated the same unsuccessful proposal three times. All24 backtracking trials reduced its worst sampled overlap, but increased overlap at other originally failing frames. The full step improved peak depth24.740→23.468mm while worsening frames67,73.5 and74 by up to1.364mm. The original acceptance rule correctly rejected it. The exact diagnosis and source-history hash are retained in `reports/frame-guarded-partner-diagnosis-v1.json`.

The new method moves those per-frame limits into the optimization. `frame_guarded_partner_step.py` solves a convex epigraph problem over the same120 timed arm controls and5,272 frozen surface rows. Each row retains its frame's allowance, `max(5mm, initial measured depth)`. Exact second-order cones bound control rotation vectors, adjacent rotation-vector edits and the proposal trust radius. Contact-event controls are fixed exactly. The objective reduces maximum predicted penetration, with a small control-step regularizer. There is no single elastic slack that can trade one frame's failure for another.

The frozen surface planes approximate the local geometry. They are not a collision certificate. `study_frame_guarded_partner.py` evaluates real whole-mesh geometry after every proposed fraction, testing the worst initial frames first. It rejects an attempt immediately after a violated cap, records all sampled failures, and does not claim to have checked unvisited frames. A candidate must pass all30 fitting times and improve the peak before export. The conditional export stage checks all299 integer/half-frame samples in both scenes, actual600 Godot actor-frames and preservation of the decoded event mesh. Further full-clock comparison against the initial edited scene is needed before any improvement claim beyond the fitting clock.

## Initial evidence

Seven focused tests pass: preventing the original cross-frame tradeoff, allowing jointly feasible improvement, exact event controls, rejecting invalid source allowances, hard adjacent-edit norms, hard rotation balls and immovable overlap. These are solver-component tests, not animation-quality evidence.

The first actual0.5-degree proposal solved in1.233 seconds. Predicted peak depth fell24.740→24.028mm, with zero predicted per-frame cap violation. Fresh geometry measured24.034mm at the peak, but frame67 worsened by17.687 micrometres. Half and one-eighth steps still worsened frame67 by4.438 and0.278 micrometres. All were rejected under the unchanged1nm comparison allowance for previously failing samples. This is evidence of a nonlinear error in an active frozen plane, not a reason to widen the geometry criterion.

The finite trial `reports/frame-guarded-partner-v1` completed all six predeclared attempts with no accepted candidate. Even the smallest0.125-degree, one-eighth attempt worsened frame67 by18.5 nanometres, exceeding the unchanged1nm allowance. No motion was exported from this rejected trial. Its request freezes source/proof hashes, implementation, process identity and iteration limits. Check its current pipeline and live process; do not infer termination from a quiet geometry query. Preserve all outputs, including a no-candidate outcome.

If the smaller trials fail for the same active-plane curvature, the next formulation should tighten proposal planes by a measured nonlinear buffer while leaving actual geometry acceptance unchanged. Record the buffer policy before rerunning, preserve the present trial, and do not repeat identical three-round proposals. Root and legs remain fixed in this arm-only experiment, so existing floor penetration cannot be repaired by this method. Partner interactions and broad supported quality remain unresolved.


## Buffered proposal follow-up

`reports/frame-guarded-partner-v2` freezes a measured proposal-only tightening rule: for each previously regressed frame, reserve1.5 times its largest recorded excess. V1 only exposed frame67 before early rejection, giving a26.531-micrometre buffer there. This changes the proposed direction, not the original geometric acceptance rule. The initial controls may violate the tighter proposal plane; the convex solver must find a feasible new candidate or return none. An impossible-buffer test verifies that no relaxed motion is returned.

Nine component tests pass in1.01 seconds. The first buffered proposal solves in1.287 seconds. Fresh mesh depth at frame67 is23.456824mm versus its23.465927mm original cap; frame66.5 measures24.046756mm versus24.740384mm. These early samples pass; remaining fitting samples and the complete exported clock still need verification. No broad collision solution or5mm clearance pass is claimed.

The live trial conditionally exports and runs the full independent geometry/engine audit if all30 fitting samples pass. A separate `verify_frame_guarded_partner.py` worker, in `reports/frame-guarded-partner-audit-v2`, waits for that exact process identity. It verifies source/assets, all engine actors, bounds and the full299-sample curves against the prior edited scene. It reports any regression outside the fitting clock and does not turn local acceptance into release approval. If no candidate is accepted, it records that outcome without inventing exports.

The parallel whole-support study has now completed19/24 cases (`whole-support-breadth-interim-v19`), including exhausted walking on rig01. That case lowers floor depth67.711→2.123mm and lowers P95 sliding, but raises right-foot peak speed0.0619→0.1902m/s and root peak acceleration2.132→2.531m/s². These tradeoffs remain visible; completing the computation is not passing quality. Completed input/candidate engine evidence now covers6,900 actor-frames.


Final update: the buffered candidate passed all 30 fitting samples at its full 0.5-degree proposal and exported successfully. Actual Godot import passed 600 raw/candidate actor-frames. Both the full geometry worker and separate comparator completed successfully; their terminal handles were consumed.

The independent comparison in `reports/frame-guarded-partner-audit-v2/summary.json` passes the unchanged per-sample collision caps at all 299 exported key/midpoint samples. Peak penetration fell from 24.740401 to 24.046751 mm. There are no newly failing samples and no worsened previously failing samples, including outside the fitting clock; no previously failing samples cleared the 5 mm threshold. The floor curve is unchanged. Event mesh displacement is below 24 nanometres for each actor. This verifies a bounded improvement over the prior edited scene, not a solved interaction: peak overlap still exceeds 5 mm, floor penetration still fails, and collision remains worse than the original raw scene's 21.622598 mm peak.
