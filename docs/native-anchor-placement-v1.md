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
