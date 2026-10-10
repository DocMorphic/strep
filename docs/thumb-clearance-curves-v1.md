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
