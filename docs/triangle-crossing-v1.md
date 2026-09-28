# Triangle crossings supplement vertex penetration

The previous partner audit tests every skin vertex against the other closed mesh. Two surfaces can cross between vertices while all vertices remain outside. The new independent `triangle_crossing.py` diagnostic closes part of that measurement gap; it does not replace containment/depth checks or correct animation.

The implementation uses triangle-plane distances and overlapping intervals along the planes' intersection line. This geometric construction is described in [Möller's triangle intersection paper](https://fileadmin.cs.lth.se/cs/Personal/Tomas_Akenine-Moller/code/tritri_tam.pdf). The NumPy implementation is original; no upstream source code was copied. A spatial index streams overlapping triangle bounding boxes, without a dense all-pairs matrix or a candidate limit. Distances use a declared 1e-8 metre tolerance. Transverse interior crossings, near/boundary contacts, near-parallel/coplanar overlap and degenerate inputs remain separate outcomes. Floating-point tolerances are not exact geometric predicates.

Ten focused tests pass. They cover analytically known intersections, separation, coplanar and boundary cases, input validation, winding/actor-order/rigid-transform/scale invariance, and indexed-versus-exhaustive candidate comparisons. Crossed closed boxes produce proper crossings while both vertex tests return zero penetration. A nested box instead needs the vertex test: its surfaces do not cross. Evidence: `reports/triangle-crossing-tests-v1.json`.

## Fixed decoded character samples

`audit_triangle_scene.py` binds exported scene and character hashes, decodes animation and applies the scene transforms. The current adapter explicitly requires two actors with one triangle primitive each. It checks frames0,66.5,67,75 for both raw and candidate clips, without changing either clip or the running optimizer. All8 samples completed in `reports/triangle-scene-v1`; no degenerate faces were found.

| Frame | Raw intersecting triangle pairs | Candidate intersecting triangle pairs |
|---|---:|---:|
|0|0|0|
|66.5|583|158|
|67|275|172|
|75|0|42|

These are mesh-triangle pair counts, not penetration depth, unique collision events, area, force or animation quality. At66.5 the candidate has fewer intersecting triangle pairs even though its deepest vertex penetration is worse. Event-region proximity also coexists with42 crossings at75. Do not convert these counts into a realism score or reinterpret intended tolerance-level contact as a new release failure without a frozen policy.

`verify_triangle_scene.py` independently solves for a common point strictly inside both triangles, using linear constraints on barycentric weights rather than plane-intersection intervals. All1,230 reported crossings have positive interior weights above1e-8 and normalized equality residuals at most1e-8. Every witness is retained in `reports/triangle-scene-proof-v1`. This verifies the reported positives; it does not prove the absence of false negatives.

## Full-clock follow-up

`reports/triangle-scene-full-v1` completed all 299 integer/half-frame samples of each clip, 598 samples total. The exact-owner checker in `reports/triangle-scene-full-check-v1` confirmed every one of the 6,680 reported proper crossings with independent barycentric witnesses and compared the same decoded clocks against the retained vertex-depth curves.

Raw motion has crossings at 10 sample times, including frame68.5 below the 5 mm depth screen; the candidate has crossings at 16 sample times, including frames69.5 and75 below that screen. None occurs where vertex depth is at or below1e-8 m. Thus this clip does not demonstrate a crossing entirely missed by vertex containment; the crossed-box regression establishes that separate capability. These are complementary measurements, with no new quality threshold introduced after seeing the result.

Self-collision, arbitrary multi-primitive scene adapters, continuous-time intersections, exact degeneracy handling and animator judgment remain separate gaps. All release gates remain open.
