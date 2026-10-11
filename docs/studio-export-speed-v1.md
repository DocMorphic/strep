# Current joint-speed limits in Studio exports

A staged speed-limited correction now produces a
`strep-studio-native-scene-v2` draft with explicit `rotation_speed_limits`.
Limits identify the actor, original glTF joint index and maximum degrees per
second. A zero limit stays zero. A later correction replaces matching current
limits and preserves other current actor/joint limits. Duplicate entries reject.
The older v1 draft has no current export-speed obligation; retained correction
history remains a separate record of what each earlier correction requested.

The scene editor displays current limits and saves them with the draft. Removing
a limit is an explicit action; removing an actor with active limits is blocked
until those limits are removed. Contact-patch revisions preserve the current
limits. An object edit changes the bound scene digest but keeps the selected
limits unchanged. Source and recipe checks reject missing, changed, unknown or
invalid limits before publishing a job. The v2 authoring recipe records a separate
source-bound rotation-speed policy.

After the actor producer saves its native Animation resources, the speed audit
loads an exact snapshot of each selected exported `.res` file. It does not
regenerate a replacement animation. Resource structure, original key times,
source/method/engine hashes, joint-parent mapping and actual engine observations
are checked. Fresh replay recomputes each selected interval's local rotation speed
from saved engine matrices and compares every saved numerical array. Studio's
completion reader also requires the audit's source resources to be the exact
actor resources being exported.

The overall scene decision includes both the imported pose and speed decisions.
A speed failure remains a completed measured failure with downloadable assets;
it does not become a successful animation, change the selected original or gain
quality approval. Scene and game ZIPs retain the unchanged current limits,
rebound portable scene digest, measurements and replay record. Game packaging
preserves the scene's failure decision. Nested read-only verification reuses only
the owning thread's live worker lock; independent jobs still cannot acquire it.

## Verification

The dedicated [hosted workflow](https://github.com/DocMorphic/strep/actions/runs/38164023442)
uses checksum-pinned official Godot 4.7.2, generated rigs and offline numerical
dependencies. At `48bd31d`, both Windows and Linux pass **182 Python checks**
and both editor suites, without skips or failures (43.04 seconds on Linux,
237.18 seconds on Windows). Seven Python cases execute the actual
engine: five standalone speed cases and two full scene-to-game export cases.
The remaining cases cover source policies, frozen inputs, receipts, revisions,
orchestration and worker contention; mocked cases do not establish engine behavior.
The retained artifacts and a local passive certificate bind 68 committed source
files and 17,470 expanded files, including the exact exported resources and both
ZIPs. Numerical replay runs on each hosted runner; the certificate only checks
saved transport bytes and source identity.

The [focused compatibility run](https://github.com/DocMorphic/strep/actions/runs/38164023332)
at the same commit passes all six jobs: 451 contact/rig, 34 correction-history and
32 game-package Python checks on each OS, plus editor checks. All **517 checks
per OS** pass without skips or failures. This regression population overlaps the
dedicated export workflow; the two counts are not a count of distinct checks.

The complete export fixture explicitly declares a floor and samples geometry at
0, 1 and 2 seconds. Speed capture separately retains all five original fractional
rotation keys, making four measured intervals. It does not infer a geometry pass
from an empty geometry policy.

| Current limit (degrees/s) | Observed peak (degrees/s) | Scene conditions | Game package conditions |
| --- | ---: | --- | --- |
| 200 | 147.286246 | Pass selected conditions | Pass selected conditions |
| 100 | 147.286246 | Fail authored speed | Fail authored speed |

Both cases confirm that the packaged animation's SHA equals the audited resource
SHA, that the policy binds the relocated scene JSON, and that changing the final
resource invalidates both scene and game evidence. Empty contact/event tracks
are supported. The actual event-helper audit now creates isolated valid rejection
fixtures instead of indexing a missing event or adding events to the export.

The first integration run at `2d7510d` retains three failures per OS: an invalid
contact-revision fixture, an outdated result-reader method population on Linux,
and missing launcher companion executables on Windows. The following run at
`dc18d55` exposes relative-path and undeclared-geometry fixture errors. The
`77cc172` run is cancelled after inspection identifies the empty-event audit bug;
its retained actual engine log is separate from the final successful evidence.
No thresholds were loosened to obtain a fixture pass.

## Scope

These are selected native-key interval-average principal rotation speeds, with
zero allowance added to the authored maximum. They do not certify instantaneous
between-key speeds, rotation winding, unselected joints, continuous collisions,
rendering, physics or human motion quality. The complete fixtures add actual
imported skin/pose, declared sampled floor geometry, root-track export and finite
event-helper checks. They do not establish arbitrary-action, partner/object,
anatomical or style-calibration acceptance. The broader project release goal,
held-out evaluation and developer review remain open; the model is unchanged.
Fresh numerical replay requires the producer's bound method version and engine;
portable ZIP contents alone are not an independent full-system certificate.
