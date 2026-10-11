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
its resource safety.

The complete captured comparison subsequently runs after 15 stable seconds of
sufficient RAM. It processes every one of the 2,422 original keys and 2,492,238
target vertex positions, retaining both original clips and all proposals.

| Measurement | Crawl, 1,524 keys | Get-up, 898 keys |
|---|---:|---:|
| Original / proposed keys failing 5-mm floor screen | 1,480 / 1,435 | 446 / 443 |
| Original / proposed maximum floor depth | 0.649773 / 0.672831 m | 0.367568 / 0.308403 m |
| Newly failing / newly passing floor keys | 8 / 53 | 4 / 7 |
| Original / proposed mean mapped-edge direction error | 8.837 / 7.766 degrees | 10.665 / 10.422 degrees |
| Individual direction edges worsened | 6,266 | 3,102 |

Both complete clips still fail. Small mean direction improvements do not solve
support, and crawl peak penetration worsens. Maximum local edits remain within
the declared 25-degree caps up to floating-point precision. Maximum role-edge
length change is `8.882e-16 m`; maximum pelvis-position change is `4.441e-16 m`.
All translations and unedited local transforms are retained. Appended glTF
animations preserve the original library and payload; native-key roundtrip
vertex errors stay below `2.807e-7 m`. Root tracks and unknown-contact records
are saved alongside the complete pose arrays and per-frame reports.

Recorded local rotation speeds also expose unresolved discontinuities. Crawl
original/proposed maxima are approximately 21,596 / 21,592 degrees per second;
get-up maxima are 4,978 / 3,686 degrees per second. No speed gate is calibrated
or claimed passed. A separate full-mesh/rate replay and raw captured-relative
rotation comparison are prepared to investigate these observations. Their
results are pending; no particular capture failure mechanism is inferred.
Its first guard defers after the unchanged 600-second admission window without
starting a replay worker. All 594 observations of that deferral independently
replay with matching archived bindings. No separate skin/rate/source-relative
verification is claimed from the stopped admission attempt.

Execution completes in 41.078 seconds with 169,725,952-byte sampled process-tree
peak RSS. All 551 resource observations replay under the unchanged policy.
This includes a 514.219-second admission wait and does not remove the earlier
source-check deferral. Original and proposed failures remain local, with
originals selected and no quality or training approval.

Captured references retain their [existing evaluation
rights and training exclusion](cmu-ground-reference-v1.md). Native-key screens
do not establish between-key geometry, forces, engine import, semantics or human
quality. All project release requirements remain unchanged.
