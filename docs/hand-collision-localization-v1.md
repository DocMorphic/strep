# Remaining hand collisions and native event support

Verified at 2026-10-07T02:07:52.779470+00:00.

The [passing-motion half-step](ray-half-storage-result-v1.md) still fails geometry. All **30431** archived intersection records involve the two left-hand skins: 30430 proper crossings and one unresolved boundary/near contact. Each side has positive skin influence from node 8, with editable arm, forearm and wrist ancestors at every affected native sample. The distant box passes all 1673 geometry samples. This rules out missing structural edit coverage as the explanation; it does not prove reachable separation.

A separate consumer reconstructs every classification and recurrence. All **104 proper crossings** at five explicit diagnostic times receive exact rational interior witnesses for the decoded represented coordinates: `0`, `0.26875`, `0.34375`, `0.5000000149011612`, and `1.2000000476837158` seconds. These witnesses prove those intersections; they do not certify every predicate or continuous motion.

`scripts/rigid_rotation_halfspace_screen.py` encloses point-versus-oriented-plane residuals under independent rigid rotations about fixed pivots, using exact rational arithmetic and checked outward square roots. At the depth peak, both directions stay behind all twelve reference hand planes under the declared wrist-only hypothesis and rational radian bound `0.0872664625997165` (approximately five degrees). Arm/forearm transforms and pivots are fixed in that hypothesis. **This is a halfspace result, not a certificate of actual mesh containment, quantized animation validity or infeasibility of the full 90-control edit.**

Allowing arm/forearm/wrist pose changes at that one frame gives a different result: a relaxed 18-control pose has zero complete partner triangle intersections and zero partner vertex depth, with both object depth queries zero. Upper-arm changes are about **0.514 degrees**; maximum joint displacement is **5.919 mm**, within the original five-degree/30-mm pose budgets. Independent hierarchy construction agrees within 1e-12, saved skin vertices reproduce exactly, and exact arithmetic proves strict separation of all 64 represented hand vertex pairs on the saved axis. The original geometric routines are also independently re-queried, not independently reimplemented. The requested strict 100-micrometre proposal is short by **2.676e-15 m** and its failure remains recorded. This pose relaxes curve timing, source rates and contact constraints; it is not an admissible animation.

| Native pose-guidance trial | Source failures | Contact failures | Reference bounds | Peak-frame depth (mm) |
| --- | ---: | ---: | --- | ---: |
| Minimum hat update | 16 | 1 | Pass | 4.934173969 |
| Constant before contact | 16 | 1 | Pass | 4.931394590 |

Both trials use the original 90-control curve family and 45 absolute one-neighbor storage choices. Only the first two control knots change; all reference, source-rate, contact and geometry limits remain. The source failures are linear/angular acceleration rows. Both clips have 20 intersection records at the original depth-peak frame and worse depth there than the 4.802282354-mm anchor peak. Nominal component clipping to the original 0.02 local trust produces **3.469e-18** positive strict step excess after floating addition/subtraction. That defect is retained, not treated as passing. Every actual payload, native world, residual, failure group and original reference bound is independently replayed. Both trials are rejected, with no full geometry audit, appended promotion or engine import.

`scripts/native_key_control_support.py` samples the complete editable-key basis using actual native LINEAR clock arithmetic. At the touch event, the ideal authored-knot basis is `[0,0,1,0,0]`, but the native preceding-knot coefficient is **0.010204016249468813**, about **1.0204%**, for all six edited tracks. A zero authored event-knot contribution therefore does not imply zero native interpolation influence. For rotations this describes key-parameter support, not a linear SLERP pose response or proof of the whole contact-error cause.

**53 tests pass**, zero skips, covering exact outward root bounds, sampled rigid residual enclosure, malformed/tampered certificates, actual native versus authored knot support, translation response, rotation leakage and input preservation. Both suites are registered in Linux/Windows source checks; workflow YAML parses, hosted success remains unverified. Completed expensive studies were not rerun for publication.

A genuine next Job binds the repaired motion-feasible anchor and is independently replayed, with every non-anchor field unchanged. The next correction should use actual native key support and coupled source-rate/contact constraints when lifting pose guidance, with representable steps that satisfy the original trust exactly. Pose reach alone does not justify wider permissions or looser acceptance. This remains one generated cube-skin scene; original assets stay selected, every candidate is unapproved and all fourteen release arrays remain empty.

Ignored immutable result SHA256 values:

- localization: `3348f343c0efb7fb5f855aab54e4629fbae75b141b0b8f7711f0742361f0d223`
- localization_replay: `c9235c7936c56cbef64a72fc1dcc967841d7ab59ed4f139f534dbd9677e6a782`
- anchor: `47db45493f3203da4aff74e74d2bfad253408a204a3db947b97519d7c6863230`
- pose: `a2ebd65435f8ec58c83edc87015093cc34662cbb5d5c57bc11595c81fcf7a847`
- pose_replay: `792afae11831dad713a03c7403858c0db2769f1fd6061b0b7b5d531e3564fc55`
- lifts: `5ba65eecef07b6d25e9ae463a1d3febb2d844ecc0ea380f70474c505ad92a014`
- lifts_replay: `a760827638e0e8c56f1008e456d3f47cf75954efdc8f5c80d7e9ffb63265ecd3`
