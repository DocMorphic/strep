# Conic proposals for root and foot release correction

Development evidence, 2026-09-28. This changes the deterministic correction method, not the Kimodo checkpoint. All original decoded acceptance limits remain unchanged. None of these trials establishes animator quality or release readiness.

The previous linearized squared-speed constraints admitted directions that violated the actual speed norm near zero. The new proposal retains affine velocity, acceleration and edit vectors in second-order cones. Serialized skin measurements still determine whether a proposed change is accepted. Floor, hover, support speed, foot/root acceleration, edit bounds, protected tracks and import checks remain separate guards.

Clarabel 0.11.1 is separately vendored with its license and verified wheel/file hashes. Each experiment freezes sources, parameters, selected frames, proposal budgets and implementation snapshots. Actual-mesh proofs reproduce the original normalized constraints to about 1e-16 and check smooth vector derivatives. `AlmostSolved` is retained as the optimizer's status; it is permission to evaluate a proposal, not evidence of animation quality.

## Root result

| Trial on rig 02, root center 77 | Target acceleration (m/s²) | Original limit | Result |
|---|---:|---:|---|
| Previous linear descent | 12.222871 | 11.673293 | No accepted step |
| Unbuffered conic descent | 12.184141 | 11.673293 | Five accepted steps; target still fails |
| Buffered conic descent | 11.453698 | 11.673293 | Two accepted steps; target passes |

The buffered proposal subtracts a small margin from movable *predicted* speed and acceleration caps. It never increases actual acceptance limits. The independent audit confirms that rig 02's earlier repaired spike also remains within its original comparison. Both root-repaired rigs now pass that comparison. Rig 02's overall root maximum is 11.673058 m/s²; rig 03's is 12.147652 m/s². These are comparison results, not universal physiological limits.

Evidence: `reports/conic-root-descent-audit-v1`, `reports/conic-root-rejection-diagnostic-v1.json`, and `reports/buffered-conic-root-audit-v1`. Each completed trial includes 450 native Godot actor-frame checks and fresh decoded geometry/dynamics audits.

## Foot results and buffer fallback

The first foot method eliminates root coordinates and protects the audited repaired root. It selects the largest remaining release excess using the existing deterministic selector.

- Rig 02, Left release 32: 12 accepted iterations reduce the selected objective from 4.630047 to 0.393509. The measured release peak remains 52.858166 versus a 52.230863 m/s² limit. Other failures remain in the report.
- Rig 03, Left release 129: the extra proposal margin makes all three trust-region subproblems report `PrimalInfeasible`. No animation change is accepted. This is not evidence that the original motion constraints are globally infeasible.
- A fixed two-scale diagnostic finds that one tenth of the extra proposal margin permits a full step that passes the original serialized guards. With no extra margin, most tested fractions fail those same guards.

`study_scheduled_conic_foot.py` therefore freezes a fallback order: scales 1, 0.1, 0, each at trusts 1e-4, 1e-5, 1e-6; at most nine proposals per iteration and eight safeguard fractions per proposal. It stops on the first accepted step, with at most 12 accepted iterations. The independent history reconstruction binds the chosen buffers and fractions.

On rig 03, this reduces release 129 to 22.555402 versus the unchanged 22.708076 m/s² limit in three accepted steps. The independent audit verifies all 12 preservation checks, exact repaired-root matrices, 142 untouched decoded frames, and 450 engine actor-frames. Two other release failures remain. Rig 02's scheduled trial targets its now-largest remaining release and retains its bounded result for the same independent audit.

`study_conic_release_sequence.py` permits at most three further automatically selected blocks per rig. Every block must have a fresh independent audit. The sequence stops if total original release excess fails to decrease, guards fail, the original comparisons pass, or the block budget is reached. It never promotes a clip to release quality.

## Validation and remaining work

Five cone/buffer tests and four schedule/reconstruction tests pass. The tests check vector signs, scaling, actual constraint correspondence, bounded fallback and rejection of infeasible motion despite a zero proposal buffer. Real-mesh proofs and independent exported-file audits supplement them. See `reports/conic-buffer-tests-v1.json` and `reports/conic-buffer-schedule-tests-v1.json`.

The broader floor-support study is 15/24 completed action/rig cases. Rig 03 kneel/rise improves typical predicted support speed but worsens the right-foot maximum from 0.130157 to 0.528501 m/s. That regression is retained in `reports/whole-support-breadth-interim-v15`; the current correction is not an accepted general solution. Object/partner geometry, intentional contact semantics, per-joint tails, held-out motions, independent animator ratings and cleanup time still need their own evidence.


## Bounded continuation results and remaining joint spikes

The two three-block-budget sequences each stop after two blocks, because the second block makes no accepted progress. Rig 03 clears Left release32 to51.780265 versus52.047914m/s², leaving only Right86 at34.263886 versus34.192145m/s². Rig 02 clears Left32, leaving Left74 at42.799312 versus42.722809m/s² and Right19 at14.880144 versus14.337625m/s². Every completed block passes the12corrected-root preservation guards; failed releases remain failures.

A fresh per-joint audit (`reports/conic-release-joint-dynamics-v1.json`) exposes limitations hidden by the global rotation peak. Rig02's right-leg maximum is0.769441degrees/frame above the raw/prior maximum, already present in its held source. Rig03's right-toe maximum is11.237850degrees/frame, versus9.687227 in the prior correction and9.523382 in the held source. The original global check does not protect every joint. These are diagnostic differences, with no post-hoc threshold or animator judgement. Any further quality claim must address them.

The rig03 stalled proposal violates adjacent-edit bounds as well as some tiny support/acceleration margins. A read-only replay labels the constraints in `reports/conic-foot-stall-labels-rig03-v1.json`. A further fixed diagnostic adds1e-6 or1e-7radians to the extra *prediction margin* for movable adjacent joint-edit vectors. The1e-6 margin gives a proposed step passing the unchanged actual guards; the1e-7 variant does not. Root variables are eliminated, so the added movable-vector margin applies to joint angles. A separately frozen two-rig trial tests this hypothesis; no existing tolerance is widened.

The stage-by-stage rotation audit (`reports/conic-root-chain-joint-dynamics-rig03-v1.json`) locates rig03’s right-toe peak increase in the earlier SLSQP root repair, before the conic foot trials. The conic follow-ups preserve that peak; they do not resolve it. A future per-joint-aware correction must address this measured regression without sacrificing the repaired root/contact constraints.


## Final audited result of this development pass

`reports/conic-release-summary-v1.json` binds the final exported clips and independent audits. With the adjacent-edit proposal margin, rig03 clears Right86 to33.807655 versus34.192145m/s² in one accepted step. All16original comparisons, all12corrected-root preservation checks and450native engine actor-frame checks pass. Candidate SHA256:80cab681e5fc02e0256b3456dd9c5a548e1fb65f10948be47d2170c61e75b935. The separate toe-rotation regression remains an unresolved quality issue.

Rig02 accepts12steps and improves Right19 from14.880144 to14.637920m/s², still above14.337625. Left74 remains42.799312 versus42.722809. All12preservation checks and450engine actor-frame checks pass, while both original release comparisons correctly fail. Candidate SHA256:fc9b257695dd5915c6596d59fa661406900eb7c2eea0e01554915e1d9d17a059. This is useful progress, not approval.

Next work must account for per-joint motion quality alongside aggregate root/contact improvements, continue the declared breadth population, and assess transfer to uninspected actions. Do not spend an unlimited trial budget silently tuning one example or reinterpret numerical passes as human realism ratings.
