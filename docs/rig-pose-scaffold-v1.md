# Rig-proportion reference proposals

Captured joint positions cannot simply be scaled onto a character with different
proportions. The [preceding study](pose-length-preflight-v1.md) excluded all 2,422
such targets under fixed bone translations. `scripts/rig_pose_scaffold.py` instead
uses captured edge directions as preferences and constructs new joint points
through the target rig's forward kinematics.

Each mapped joint fits all its nearest mapped children together. Unit directions
prevent longer branches from dominating this local fit. A proper rigid rotation
preserves target branch angles and lengths even if the reference requests
incompatible angles. Rank-one branches use minimum swing; an underdetermined
zero-rank objective retains orientation. Leaves favor their original world
orientation within the same source-relative cap. Unmapped helper transforms and
all local translations stay fixed. Every edited local rotation has an explicit
norm cap, including after an ancestor changes.

These are pose proposals. A local branch fit does not minimize all downstream
errors jointly, and source-relative caps can prevent the preferred direction.
Individual edges may worsen. Framewise fitting can also introduce discontinuity
near changing branch rank or opposing directions. Quaternion sign continuity in
the study's glTF export prevents representation flips; it does not smooth physical
rotation changes or validate joint speed. No anatomical joint-limit model,
support inference, surface correction or temporal optimizer is introduced.
The study retains every neighboring-key local rotation speed, compares its
maximum and 95th percentile with the original, and identifies the worst node
and time interval. These are diagnostics without a calibrated acceptance gate.

The [frozen protocol](../benchmarks/cmu-rig-scaffold-v1.json) uses both complete
captured clips at 120 Hz and the unchanged target/profile, with all 19 mapped
rotations capped at 25 degrees. The study preserves every proposal and checks
every target vertex at every native key, original versus proposed directional
errors, root/local/length preservation and glTF roundtrip. Original clips and
animations remain intact. Explicit support goals must be authored separately;
unknown captured contacts are not a proof of no contact.

The prepared source checks deferred after the unchanged 600-second admission
window: no numerical worker started. All 594 recorded resource observations
replay with matching archived bindings; admission still requires 2,776,629,248
bytes of available RAM for 15 stable seconds. Syntax parsing succeeds for the
module, its 17 planned regression cases, and both private study runners. The
source-test inventory now contains 456 Python modules and 42 Node suites; this
count does not imply execution.

Subsequent [source-only GitHub CPU validation](contact-audit-compatibility-v1.md)
passes all 172 focused checks on both Windows and Linux, including the 17 scaffold
cases and 48 earlier bounded-fitting regressions. This verifies the synthetic
proposal behavior and permits the prepared captured study to proceed after local
resource admission. It does not change the earlier local deferral or establish
its resource safety. The complete captured comparison remains pending; no
captured proposal has yet been produced or approved.

Captured references retain their [existing evaluation
rights and training exclusion](cmu-ground-reference-v1.md). Native-key screens
do not establish between-key geometry, forces, engine import, semantics or human
quality. All project release requirements remain unchanged.
