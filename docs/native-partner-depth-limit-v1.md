# Source-bound partner depth floors

The scene's actual 5 mm depth floors conflict jointly inside the current local affine correction box. A four-witness weighted certificate proves this with exact rational arithmetic, without any native/contact norms. This identifies a local correction limitation rather than another solver convergence failure. It does not prove that the nonlinear motion or broader authoring problem is infeasible.

## Guidance from the original geometry policy

`scripts/native_partner_depth_limit.py` reads the penetration limit through the existing source-bound geometry policy validator. It checks source bytes and requires every witness time to belong to the complete policy clock. Each existing partner containment witness receives the hard scalar condition `gap + J delta >= -penetration_limit`. There is no soft-penalty coefficient on these rows.

Unlike the previous gap-change guards, these conditions permit a shallow witness to deepen within the original limit. They require an already failing witness to improve to that limit. The original native norms, caps/scales, reference, contacts and geometry acceptance remain unchanged. Certified surface reduction still represents every original soft scalar condition. Fixed-normal/barycentric depth floors are local guidance; they do not certify nonlinear depth, prevent new crossings or grant asset acceptance.

## Complete retained experiment

The experiment reuses byte-exact independently replayed model arrays, thirty controls, nine original source-rate arrays, source-scale storage and seven fixed one-neighbour component corrections. Both actors retain the original five rotation-control knots at node 6, 5 degree track envelopes and 30 mm cumulative joint bounds. The local trust is 0.02. All 1,707 native times, 1,673 geometry times, original reference/contacts and original geometry policy remain.

The complete model contains 29,290 original native norms, 1,167 active native cones, 277,385 soft scalar surface conditions represented by 118,367 equivalent rows, and all 2,840 hard partner depth floors. Clarabel 0.11.1 returns `PrimalInfeasible` after 18 iterations. It produces no direction, so no candidate is exported and no new full geometry audit is claimed. The anchor retains its earlier geometry failure.

Independent replay finds 102 anchor depth-floor failures, with maximum deficit approximately 0.195942 mm. Exact rational whole-box bounds find no individually impossible witness. That does not establish joint feasibility: different witnesses may require incompatible controls.

## Joint contradiction independent of native limits

A separate CPU diagnostic removes native/contact norms only to identify the conflict. It exports no asset and changes no acceptance criteria. The full 2,840 depth-floor feasibility LP returns infeasible. A second LP finds nonnegative weights; those numerical weights become inputs to an exact rational check on the original represented gaps, depth limit, derivative coefficients and enclosing proof box.

For nonnegative weights `w`, every feasible step must satisfy `sum(w J) delta >= sum(w (-gap-limit))`. The maximum left-hand side over a box is the sum of each coefficient times its upper endpoint when nonnegative, or its lower endpoint otherwise. The certificate's required change exceeds that exact maximum.

| Scalar row | Time (s) | Anchor gap (mm) | Weight |
| --- | ---: | ---: | ---: |
| 172065 | 0.7927083522081375 | -5.193908260058278 | 0.4590296298463774 |
| 172066 | 0.7927083522081375 | -5.19387624803147 | 0.47209515950719644 |
| 172247 | 0.79375 | -5.128304950667378 | 0.06547649034352147 |
| 172248 | 0.79375 | -5.128297330857179 | 0.00339872030290439 |

These four witnesses require a weighted gap change approximately 0.189375 mm. The maximum permitted by the enclosing box is approximately 0.042128 mm, leaving an exact contradiction margin approximately 0.147247 mm. Another consumer imports no solver and independently reconstructs the weighted sparse coefficients and exact box maximum. Its rational numerator and denominator match the diagnostic certificate. All 2,840 witness ids and nonnegative weights are checked.

The box encloses the actual local trust region with the previous recorded arithmetic padding. Thus the contradiction applies to the represented local floor model. It uses no native/contact norm and does not depend on a numerical solver status alone. It does not apply globally to nonlinear geometry, wider controls, other rigs/actions, a recentered model or new authoring permissions.

## Validation and next work

All 85 focused tests pass with zero skips, including seventeen new source-policy/clock, hard penalty isolation, unchanged native-prefix, reachable shallow decrease, fixed deep conflict and malformed-input cases. CI adds only the new suite; hosted CI is not asserted green. The complete-model consumer binds the earlier independent thirty-column derivative replay by exact array bytes and unchanged methods, verifies every guard reference and all 159,018 exact surface implications, and validates the original policy limits/clock/planes. Geometry predicates are not independently recomputed.

The next experiment should use depth-focused feasibility restoration under the original hard native constraints, retaining every intermediate failure and rebuilding local geometry guidance after meaningful moves. Requiring all depth floors to pass in a single step from this anchor cannot work in this model. Only a candidate passing the unchanged complete decoded geometry checks can be accepted; this result grants no relaxation of those checks.

This generated fixture study establishes no production humanoid quality, physics, rendering/GPU, engine integration, new model sampling/training or human-review evidence. Raw arrays, payloads, drivers and method archives stay local and excluded from Git. All fourteen release evidence arrays remain empty and the broad full-project goal remains active.


All four CPU drivers exit zero with worker locks free and original/current/archive method and input bytes preserved.

| Local receipt | SHA256 |
| --- | --- |
| `reports/partner-depth-limit-probe-v1/result.json` | `52bc8c3d234849fa51e948254596cb6daeee61ac0eb364ae5d888f3d9eea91f7` |
| `reports/partner-depth-limit-independent-v1/result.json` | `b79746c4c5d1f0d9c616fe7f40bc44189bb3669b597f403c920eba40ff60f22a` |
| `reports/partner-depth-limit-feasibility-v1/result.json` | `f030ee66818d0ce22344420514d8ae22b164a8bb939b782a2813207091d18d48` |
| `reports/partner-depth-limit-certificate-v1/result.json` | `d425bdeb63ff938c7bd4f9be774d0ed63c95fec604fe3990c685ce8f7aae0e37` |
