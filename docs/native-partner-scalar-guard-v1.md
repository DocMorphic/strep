# Scalar encoding of hard partner guidance

The same complete partner guards now converge when encoded directly as hard scalar inequalities. Both solver phases return `Solved`, but the final control step is effectively zero. This improves numerical convergence without producing a useful motion correction or geometry acceptance.

## Equivalent local conditions

`scripts/native_partner_scalar_guard.py` retains the previous complete witness validation and certified soft surface reduction. Every `penetrating-vertex` guard is encoded directly as `J delta >= 0`, with no coefficient for the soft surface penalty. That penalty cannot buy a guard violation. These are the same affine gap-change conditions as the norm-based experiment, whose equivalence throughout the local proof box was independently checked.

Every original native vector norm remains hard, with its original cap and scale. Passing fixed norms and conservatively whole-box-passing norms use the existing omission rules. Partner guards introduce no artificial second-order cones. All surface conditions remain represented, including every triangle's nine vertex-pair conditions and every singleton witness. Original decoded native and complete geometry checks remain authoritative.

Settings remain Clarabel 0.11.1, one solver thread, 100 iterations, a 30 second limit per solve and `1e-9` feasibility/gap tolerances. The secondary phase minimizes the normalized control step within `1e-9` of the primary soft optimum. Reported numerical excesses do not widen asset acceptance limits.

## Complete sealed scene comparison

The experiment reuses the exact previously independently replayed model bytes rather than recomputing derivatives. It retains thirty controls, nine byte-exact source-rate arrays, original reference/contacts, source-scale storage and seven fixed one-neighbour component corrections. All 1,707 native times, 1,673 geometry times and original geometry policies remain.

| Population | Count |
| --- | ---: |
| Original native norms | 29,290 |
| Active original native cones | 1,167 |
| Hard partner scalar guards | 2,840 |
| Complete scalar surface conditions | 277,385 |
| Equivalent encoded soft surface rows | 118,367 |

The norm-based guard experiment stopped with `InsufficientProgress` after 28 iterations. The scalar encoding reaches `Solved` after 37 primary iterations, and the minimum-norm phase also returns `Solved`. Its soft optimum is approximately 2.13385429427; the original zero-step soft excess is approximately 2.13385429427. The final maximum control step is approximately `5.26e-10`, with predicted native excess approximately `-2.24e-6` and normalized partner guard deficit approximately `1.47e-12`. There is no meaningful motion or surface improvement.

The returned step and its 0.5, 0.25 and 0.125 fractions are freshly exported and independently decoded. Every fraction has zero stored native, unrounded native and contact failures, and passes cumulative original-reference bounds. Both actor files at every fraction are byte-identical to the starting clips: Float32 storage erases the tiny continuous step.

All four complete geometry audits fail with the same maximum vertex depth approximately 5.195942 mm against 5 mm, 30,505 triangle records, 102 contained vertices and 1,594 failed samples. No candidate is selected or approved. Solver convergence grants no asset acceptance. Local fixed-normal/barycentric guidance does not establish nonlinear penetration nonregression or prevent new crossings.

## Validation and remaining scope

All 68 focused tests pass with zero skips, including fifteen new matrix/penalty isolation, native-prefix, fixed-conflict, equivalent no-guard, one-sided and malformed-input cases. CI adds only the new suite; hosted CI is not asserted green. Existing producers and Studio jobs remain unchanged.

The next experiment must address the guidance: requiring every existing penetration witness to avoid any decrease gives no useful motion correction in this retained solve. This does not prove global motion infeasibility. A test against the actual authored depth floor can distinguish an overrestrictive local guard from insufficient correction freedom, while retaining the original complete decoded acceptance checks.

The broader release goal remains open. This retained scene uses generated fixtures and local CPU software checks. It establishes no production humanoid quality, physics, rendering/GPU, new model sampling/training or human review. Raw studies, payloads and method archives remain local and excluded from Git. All fourteen release evidence arrays remain empty.


Independent replay imports neither the new scalar solver nor the guard/reduction solver modules. It binds the prior complete thirty-column derivative replay by byte-identical model arrays and unchanged method hashes, verifies all guard equivalences and all 159,018 direct surface implications with exact rational arithmetic, and reevaluates every proposal affine residual. All four stored payloads, complete native worlds/conditions, scalar gaps, reference displacement/rotation bounds and geometry clock/limits/observation transport replay. Geometry predicates are not independently recomputed. Both CPU drivers exit zero with worker locks free and original/current/archive methods preserved.

| Local receipt | SHA256 |
| --- | --- |
| `reports/partner-scalar-guard-probe-v1/result.json` | `95e1ec3993cf0ff482bb061587e811a91b68049d5b1fb5d5fbe24191a03fb811` |
| `reports/partner-scalar-guard-independent-v1/result.json` | `e8993a27c94c5d272788fe62ff6623d0259ce5b25f5831294e3b6239c9873f93` |
