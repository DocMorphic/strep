# Thumb clearance and exported curves

The contact-passing animation still fails full-body collision checks. This experiment isolates the complete surface neighborhood affected by three left-thumb joints on that same rig and sphere fixture. It does not approve the motion as physically correct or ready for release.

## Frozen acceptance

Keep the original 5-mm penetration limit, 5-mm grip-position limit, 15-degree normal-opposition limit, surface-side/reliability checks and relative-speed limits. The explicitly declared artist edit caps are 15/30/30 degrees for `LeftHandThumb1/2/3`; they are not anatomical limits. Other local transforms, translations, original finger key times, inherited arm channels and static mesh/skin payload stay unchanged.

The earlier four distal-only experiments remain rejected. Adding the thumb-base joint changes some grip vertices and normals, so those conditions become explicit solver constraints. All positive skin weights and ancestor dependencies select **1,179 complete incident triangles**, including their required vertices. Scoped workers forbid full posed-mesh queries.

## Pose pilot and first curve

At 2, 3 and 4 seconds, the new three-joint pilot passes **3/3** poses. Worst affected-surface penetration is approximately 4.999 mm. Independent primitive skin-matrix multiplication and library triangle-distance arithmetic replay the saved poses, grip normals and protected transforms. No motion between these poses is approved by that result.

An existing `TimedRotationEdit` export applies the middle pose's correction through the hold, with bounded ramps. It retains the original 180 keys on each edited finger channel and all inherited arm keys. Independent export reconstruction has zero quaternion difference. The original full contact clock passes with **zero lost conditions**: 11,590 normal correspondences and 16,960 velocity pairs replay. All **33,964** source-cap conditions across the 2,426-time full geometry clock also pass.

The exported first curve nevertheless fails the unchanged penetration limit:

| Affected-region result | Original contact-passing clip | First thumb curve |
| --- | ---: | ---: |
| Full-clock times failing | 2,007 / 2,426 | 450 / 2,426 |
| Hold times failing | 1,995 / 1,995 | 440 / 1,995 |
| Worst hold penetration | 8.672765 mm | 5.007019 mm |
| Worst full-clock penetration | 19.000018 mm | 18.267273 mm |

The curve repairs **1,557 sampled times** and loses **zero previously passing times** in this affected-region test. It remains rejected; the small hold residual is not rounded away.

## Independent geometry replay

Both original spheres and all 2,426 original geometry times are retained. Storage uses sixteen-time checkpoints, permitting continuation after a RAM stop without discarding the completed prefix. The interrupted unstreamed attempt and interrupted ninth streamed stage remain saved. RAM admission and reserve limits are unchanged.

The auditor checks every checkpoint hash, clock, static dependency selection and saved point. Independent primitive skin-matrix multiplication and manual triangle plane/edge projection replay **11,441,016 triangle/object queries** against the producer's library calculation. Maximum point, distance and upper-depth differences are respectively 6.66133814775094e-16, 1.77635683940025e-15 and 3.88578058618805e-16 m. The auditor completes in 37.969 execution seconds; all 41 resource observations independently replay.

Local immutable receipts:

- Producer: `reports/central-thumb-curve-v1/affected-geometry-v2/result.json`, SHA-256 `0bb8f392fd9a2db04c2549faeec3dee268d07297f92cf79709381b83fa83bb11`.
- Independent replay: `reports/central-hand-physical-v1/independent-thumb-curve-geometry-v2.json`; auditor SHA-256 `c2138a156f272792d1de7f6e58e0f2dbd12d668b4374fe123b59106400656ca4`.
- Contact replay: `reports/central-thumb-curve-v1/contact-clock-v1/independent-clock-audit-v1.json`.
- Source caps: `reports/central-hand-physical-v1/thumb-curve-clock-cap-audit-v1.json`.

This is an affected-surface diagnostic. Untouched body geometry, sphere-center containment, self collision, continuous time, whole-body dynamics, game-engine import and genuine human review remain outside its approval. The original full-body assessment still records 2,009 failing times and a 20.339273-mm peak. No new training or generation guidance follows from these tests.

Next: fit a curve from multiple contact-constrained poses, replay its complete clocks, then address the remaining full-body approach/departure failures. Preserve every rejected curve. The same full-project goal still includes broad actions, objects, partners, rig transfer, editing, style, transitions, engine checks and human cleanup evidence.

## Six-pose refinement

A fresh, separately retained pilot fits 2, 2.5, 3, 3.5, 4 and 4.0333333015441895 seconds. The optimizer's additional clearance margin increases from 1 to **10 micrometres**, based on the first curve's measured interpolation residual. Acceptance stays exactly 5 mm; edit caps and all original grip/surface conditions stay unchanged. Minimax slack cannot relax acceptance. All **6/6** poses independently replay and pass, each at approximately 4.990 mm affected-surface penetration.

The second export uses the six fitted rotation vectors as interior knots through the existing timed-rotation API. Original 180-key clocks and native SLERP remain; no keys are added. All other channels, original binary prefix and static scene/mesh/skin data stay exact. The independent quaternion reconstruction error is zero. The complete original contact clock passes with zero lost conditions; all 11,590 normal correspondences, 16,960 velocity pairs and **33,964** source-cap conditions replay.

| Affected-region result | First curve | Six-pose curve |
| --- | ---: | ---: |
| Full-clock times failing | 450 / 2,426 | **10 / 2,426** |
| Hold times failing | 440 / 1,995 | **0 / 1,995** |
| Worst hold penetration | 5.007019 mm | **4.998037 mm** |
| Worst full-clock penetration | 18.267273 mm | 18.262187 mm |
| Original failing times repaired | 1,557 | **1,997** |
| Previously passing times lost | 0 | **0** |

The complete affected-region hold now passes. The full-clock curve remains **rejected**: ten approach/departure times exceed the same 5-mm limit, between 1.9833333333333334 and 4.058333396911621 seconds. Passing this finite hold subset does not certify untouched body surfaces, sphere-center containment, continuous collision or full-scene consistency.

All 11,441,016 original/candidate triangle/object queries independently replay. Maximum skin-point, nearest-distance and upper-depth reconstruction differences are 4.9960036108132e-16, 1.77635683940025e-15 and 3.88578058618805e-16 m. Production completes in 47.875 execution seconds, and independent replay in 41.312 seconds. All 50 producer and 44 auditor resource observations independently replay. Sixteen-time checkpoints and the original 1,024-MiB-plus-600-MiB resource policy remain; the fresh producer allows 160 new chunks per invocation without increasing its per-chunk population.

Local immutable receipts:

- Producer: `reports/central-thumb-curve-v2/affected-geometry-v2/result.json`, SHA-256 `547107866b3eefcbbf2d2010a222438c710f0f352eb16abd3da1528bc9b2fa2e`.
- Independent replay: `reports/central-hand-physical-v1/independent-thumb-curve2-geometry-v2.json`; auditor SHA-256 `125e50c5bc380004e11e7a13b3b8c73e1064a87f752e369d5ce92e4dd3f6808e`.
- Contact replay: `reports/central-thumb-curve-v2/contact-clock-v1/independent-clock-audit-v1.json`; contact result SHA-256 `b5d93005967f6a53a11d1e5f90b2f433b57d5b621a95f9a2e285b28b5c58d22d`.
- Source caps: `reports/central-hand-physical-v1/thumb-curve-clock-cap-audit-v2.json`.

Next: independently finish the original full-body geometry audit, inventory the second curve's remaining entry/exit failures and test bounded corrections that preserve the verified hold. No force, engine, genuine human, guidance or release approval is inferred. The full-project goal remains active.

## Local comparison package

`reports/thumb-curve-review-v1/offline.html` packages the exact contact-passing arm correction and six-pose thumb curve, original sphere tracks, fifteen bound inputs and saved contact/cap/geometry receipts. The grey SOMA character retains all eight skin weights. Both source licenses remain embedded. No character/model payload is published to GitHub.

The self-contained file is 10,570,060 bytes, SHA-256 `e2bf0fa8f19b51e3819839f62f9dc612865b8f8e8b8ffbdfbb278292eddcbe62`. All saved/embedded payload bindings and JavaScript syntax checks pass; seven local modules and nine saved payloads require no network fetch. The interface explicitly distinguishes the passing thumb-region hold from the remaining ten entry/exit failures. Developer observations require a real user entry and remain separate from animator ratings or cleanup tests.

Browser rendering and interactions remain unverified. The prior browser security rejection of local file URLs is respected; no new browser/server workaround is attempted. Packaging is not human review or physical approval.

## Entry/exit wrist pose pilot

The fresh one-phase full-body baseline replay defers after **600.125 admission seconds**, without starting a child. All **595** resource observations replay. Its required available RAM remains 2,776,629,248 bytes; the existing Studio and other applications are left running. This is a resource deferral, not a numerical geometry result.

A smaller, separate pilot tests the two wrist channels at 1.9833333492279053 and 4.05 seconds, outside the verified hold. It retains the original raw-motion **45-degree artist caps** for each wrist and exact other local transforms/translations. All positive skin weights and descendant dependencies select **5,920 vertices and 11,784 complete incident triangles**. Both original spheres are tested; no full posed-body query is used.

Both poses pass, with worst affected-surface penetration **4.493073 mm** and **4.950000 mm** against the original 5-mm acceptance limit. The producer's manual plane/edge distances and the independent library calculation replay all **94,272 triangle/object queries**. Maximum primitive-skin point and nearest-distance differences are 4.44089209850063e-16 and 1.77635683940025e-15 m. Both producer and auditor resource records replay. These are two isolated pose results, not an accepted curve or whole-body result.

Local producer result: `reports/central-hand-physical-v1/entry-exit-wrist-pilot-v1/result.json`, SHA-256 `02548aeec4957fdd2605764119a9fa7c11a309bb28873b9558af51756a3bbd6a`. Independent replay: `reports/central-hand-physical-v1/independent-entry-exit-wrist-v1.json`.

A native-key curve trial is now declared with the complete successful hold protected. Two setup failures remain retained before numerical curve fitting: an incorrect asset-path accessor and the editor's requirement for matching candidate/reference key clocks. The corrected wrist channels have 315 keys; the raw reference has 180. A fresh trial explicitly saves a separate raw-reference derivative sampled onto the wrist clocks using the original decoder and float32 export. That derivative supplies the editor's matching-clock contract only. It does not replace the raw model asset; final source-cap acceptance still requires replay against the true original raw motion. Quantized interpolation, complete collision clocks and abrupt wrist motion remain pending. No guidance or release approval follows.

The aligned-reference curve attempt subsequently stops at its unchanged **900-second execution guard** (recorded 900.375 seconds). All **830** resource observations replay; the measured process-tree peak is 763,600,896 bytes. Only its declared plan, derivative reference and iteration log remain: **no final observations, candidate export or numerical result exists**. Iteration logs are not accepted motion evidence or an infeasibility certificate. The two original setup failures also retain independently checked resource records.

A separately prepared, unrun trial uses geodesic extrapolation from the two independently passing poses and saves each iterate. Before retrying it, a fresh complete two-hand diagnostic is submitted on the retained six-pose thumb curve: both spheres, all 2,426 original geometry times and all 11,784 incident wrist-descendant triangles. Actual edits remain the three thumb channels. The verified thumb-only hold and the broader hand population are distinct; complete-hand and full-body results remain pending. The resource profiles, thresholds and raw assets stay unchanged.

## Complete hands remain rejected

The complete two-hand population exposes failures outside the corrected thumb neighborhood. Both the original contact-passing clip and the six-pose thumb curve fail **2,009/2,426 sampled times**, including **every one of the 1,995 hold times**. Worst hold penetration decreases from 8.672765 to **7.796010 mm**, still above the unchanged 5-mm limit. Worst full-clock penetration stays **20.339273 mm**. Complete-hand times repaired: **zero**; passing times lost: zero. The earlier 1,997 repaired times describe only the thumb's affected region and must not be presented as complete-hand or full-body repairs.

The first strict replay fails on a saved library-distance disagreement. At 1.9083333015441895 seconds, face 33366 is outside the 0.25-m sphere: library distance 0.2778976129554197 m versus manual distance 0.2778976125343279 m. An 80-digit Decimal calculation agrees with the manual value; a separate SVD calculation matches that reference within 5.551115123125783e-17 m. The 4.21091828e-10-m disagreement is preserved, not hidden by increasing the 2e-12-m replay tolerance. Its diagnostic, probe and resource records remain separate from full-clock evidence.

A fresh producer uses vectorized triangle-plane/cross-barycentric and clamped-edge distances; a separate auditor uses an SVD orthonormal-plane/barycentric calculation and independent primitive skin matrices. Both original spheres, all 2,426 times, all **11,784 complete hand triangles** and every checkpoint are retained. Strict replay completes all **114,351,936 triangle/object queries**. Maximum point, distance and depth differences are 6.661338147750939e-16, 2.6645352591003757e-15 and 4.996003610813204e-16 m. All remain below the original tolerance. Production and replay take 191.594 and 314.219 execution seconds; all 182 and 295 resource observations replay under unchanged profiles.

The unchanged-face diagnostic excludes **10,605 hand triangles / 5,353 vertices** from every possible rotation of thumb nodes 16/17/18 while the mesh, skin, hierarchy, object tracks and all other local transforms stay fixed. Their source/candidate coordinates are exactly equal. Even after subtracting the original floating reserve and 2e-12-m replay allowance, the worst fixed-face depth at each hold time is **7.777564–7.796010 mm**. Every hold sample still fails. Face **15676** is the deepest fixed face at all 1,995 hold times; its three vertices are each fully weighted to **`LeftHandMiddle4` (node 28)**. This is a sampled necessary-condition exclusion of thumb-only repair under those fixed permissions, not general anatomical or physical infeasibility.

Local immutable evidence:

- Stable producer: `reports/central-thumb-curve-v2/complete-hand-geometry-v2/result.json`, SHA-256 `3861424ac2c69c11a8773ffe154acc4ba2c3ea4dd4f0d8f2f14b43169db2ff84`.
- Strict replay: `reports/central-hand-physical-v1/independent-complete-hand-geometry-v2.json`; auditor SHA-256 `3cd16a82bfbdd6bcf97b46fb3fbd551dba21f2dcc2f3e928b0167778b6e560bb`.
- Fixed-face witness: `reports/central-hand-physical-v1/unchanged-hand-face-witness-v1.json`, SHA-256 `c217d61b9c5273cbbc7d517db2495b4814135819900b77caeb8f456544dd5dc5`.
- Preserved discrepancy: `reports/central-hand-physical-v1/nearest-distance-disagreement-v1.json`; high-precision comparison: `reports/central-hand-physical-v1/svd-distance-probe-v1.json`.

Next: inventory all remaining violating hand faces and declare the smallest useful additional finger permissions, then repeat grip preservation, complete-hand clocks and source-cap checks. Do not retry thumb-only correction as a whole-hand solution. Preserve the passing thumb-region result and every rejected broader result. Full-body/containment, continuous-time, dynamics, engine, human, guidance and release approval remain outstanding under the same full-project goal.


## Subsequent complete-hand hold repair (2026-10-10)

The [middle/ring correction](middle-ring-clearance-curves-v1.md) adds six explicit distal finger permissions after the thumb-only rejection. Complete hands now pass all 1,995 hold times, with zero grip regressions and all raw-reference caps passing. Independent full-clock replay retains twelve approach/departure failures. This successor does not alter the earlier observations or approve full-body physics, engine behavior or human quality.
