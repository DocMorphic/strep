# Bounded actor anchor placement

The preceding rotation-only high-five screen found no candidate that passed
geometry at both known failing times. `scripts/native_anchor_placement.py`
adds an explicit world translation after a bounded pivot rotation, permitting
contact-anchor registration as a distinct placement experiment.

This changes actor placement, not the local animation. It is a newly authored
world-space contract; it cannot claim the original world-placement bounds still
hold. Fixed world targets remain fixed, actor-attached targets follow the
changed actor, and object tracks, source clips, contact intervals, clock and
geometry thresholds remain unchanged.

## Contract and verification

`apply(original, angles_degrees, translations_world_m, permission)` requires
angles, translations and permissions for every original actor. The `pivot`
permission retains the previous primitive's unit world axis, pivot and per-actor
angle/origin bounds. The outer `actors` permission adds a Euclidean
`maximum_translation_m` and an independent `maximum_origin_displacement_m`
measured from the original origin after both operations. Vector components,
angles and limits must be finite numbers; missing or undeclared actors/fields
reject. An actor can be fixed by zero bounds. All-zero operations preserve the
complete original placement, including quaternion signs.

For a world point `v`, pivot rotation `R` around `c`, and post-rotation world
translation `s`, the explicit transform is `R v + c - R c + s`. The translation
is not rotated again. Its norm and the final origin displacement are checked
separately. Neither bounds every joint or establishes support/contact validity.

`stage` validates pinned source contacts, geometry policy and actor assets,
then writes a fresh variant outside immutable source-result populations.
`verify` reconstructs the authored variant from the original amendment, replays
the unchanged geometry clock, checks the complete source/method archive and
rejects semantic changes even if an outer artifact checksum was updated. It
does not rewrite or copy the animation payload. No placement pass approves
collision, physics, native bounds, engine import or human quality.

The source suite has 24 tests. It checks composition along three pivot axes,
actual synthetic skinned vertices at several times, exact local curve retention,
zero-change identity, independent translation/final-origin bounds, invalid
permissions and receipt/archive/target/threshold tampering. Its isolated local
run passes in 11.63 s. The guard completes in 28.468 s at 114,900,992 sampled
bytes with 30 observations independently replayed. These are primitive checks,
not evidence about the real high-five's geometry.

## Declared development screen

`reports/high-five-anchor-screen-v1/` uses the sealed actual mixed-root CPU
surface capture, receipt
`0f0bd10afb84e859b3e1f3cee010cde38d3b1b763aabb92f61251e07114c96a9`.
It tests 18 predeclared combinations: each actor's yaw in {-10, 0, +10} degrees,
with target-point gap 0 or 20 mm along world Z. Rotation is around [0,1.5,0]
and retains the original 10-degree/100-mm pivot-origin limits. Post-rotation
translations are limited to 75 mm and final actor-origin displacement to 150 mm.
Those are explicit new placement permissions, not relaxed collision thresholds.

The two measured hand points at the 2 s contact are registered around a common
center at world X/Z zero and the higher of their two original heights. Thus
neither actor is lowered. A goes to center minus half the gap along Z; B to
center plus half the gap. The fixed world target remains [0,1.5,0], and all three
original 30-mm point-error limits remain unchanged. A zero/20-mm proxy-point gap
does not establish physical palm touch, orientation or believable reaction.

Every contact-passing proposal receives fresh complete-surface geometry queries
at indices 579 and 1016 (1.1395833333 s and 2 s). The surface positions are rigid
counterfactual transforms of the sealed observed vertices, not new engine
observations. This is a development screen at two known failures. Full-clock
geometry, support, native reference bounds and engine playback remain separate.
The original stays selected until broader checks justify a candidate.

## Completed screen and replay

All 18 proposals pass the original point-contact checks; none passes geometry
at both queried times. No candidate is selected. The nominal best is A +10
degrees, B -10 degrees, with a 20-mm point gap. Its two fixed-world-target
errors are 10.750386 mm and its inter-actor point error is 20 mm, all within
the original 30-mm limits. Final actor-origin displacements are 66.493033 and
91.687623 mm, within the explicitly amended 150-mm bound.

| Counterfactual | Early maximum depth, mm | Contact maximum depth, mm | Early/contact surface records |
| --- | ---: | ---: | ---: |
| Original placement, prior pinned queries | 21.138522 | 10.549988 | 301 / 754 |
| Zero yaw, zero gap, registered points | 20.741802 | 18.703156 | 545 / 801 |
| Best screened placement, +10/-10 degrees, 20-mm gap | 1.584968 | 13.303428 | 36 / 834 |

Even the best's early sample has proper surface crossings; a sub-5-mm maximum
vertex depth alone cannot pass the declared geometry policy. Its contact-time
depth is worse than the original. These counts are triangle-pair records, not
distinct independent anatomical collisions.

The screen completes in 468.547 s at 460,324,864 sampled process-tree bytes;
458 resource observations and its terminal state replay. The source geometry
thresholds, curves, capture and original failures remain unchanged. Result
SHA-256: `c6a502067caa0a3901c78e08af1d0b7304c56eba853308d9a1c631402e72217c`.

An independent sin/cos implementation replays all 18 placement transforms,
translations, original point-target errors and summary reductions. It checks
every case's source/method/artifact bindings and the complete observation
archive receipts. Maximum point replay error is zero for this finite study.
The geometry observation archives in this object-free scene contain the query
clock; archive verification is not an independent collision-predicate rerun.
The replay completes in 34.796 s at 232,181,760 sampled bytes, with 36 resource
observations independently replayed. Result SHA-256:
`46bfc05b360584cd09ba7f7fa4dbff2cd6795da0eca339cfa9e47bd0a7539caa`.

As a diagnostic, original skin weights label each recorded crossing triangle
by its largest aggregate joint influence. The selected contact vertices are
dominated by `RightHandIndex1`, which is not a complete palm frame. For the best
proposal, the early sample's 36 proper crossings involve hand/forearm versus
pinky labels. At 2 s, large groups involve ring/middle/index/pinky labels; the
deepest A vertex is dominated by `RightHandPinky2` (13.303428 mm). These are
skin-weight labels, not independent anatomical annotations or new geometry
queries. They motivate palm-orientation and finger-pose corrections while
retaining complete-surface checks, rather than approving a point match.

The 24 source tests also pass on Ubuntu (1.39 s) and Windows (6.25 s) in
[hosted run 38965864726](https://github.com/DocMorphic/strep/actions/runs/38965864726).
Inventories are 545 Python/45 Node suites and contact subset 109/five; those
counts do not assert a complete inventory run. Full-clock geometry, updated
support/native bounds, engine playback and human cleanup remain unresolved.
