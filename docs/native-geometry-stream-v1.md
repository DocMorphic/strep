# Complete sampled scene geometry with streamed observations

The expanded humanoid study and its original-method replay both completed before
changing any producer source. Actual imported actor skin and saved/reloaded
native object Animation resources pass at all 2,201 original/key-union times.
The complete 18,056-vertex, 36,108-face mesh is retained; all 4,402 actor/object
observations pass. Maximum source-relative vertex error is 0.0950103 mm against
the original 0.1 mm limit. Default-import contact and object-pose failures remain
in the evidence. No partner or world plane is declared in this humanoid case.

The replay matches every skin/contact/object observation and all recorded
triangle reductions. It does not independently repeat geometry, containment,
partner or plane queries. This is sampled development evidence, without motion
semantics, human review, physics, GPU rendering or release approval.

The old dense worker was observed reserving 8.10 GB of private process memory.
Its complete triangle bounds/witness arrays alone represent 6,358,472,640
Float64 bytes. Removing times, triangles or precision would change the audit.
The scene workflow now writes those same complete arrays incrementally.

## Producer integration

`native_scene_geometry.evaluate` keeps its existing dense dictionary return by
default. The optional `observation_sink` receives the entire clock and each
complete lower-depth, upper-depth and three-coordinate witness array in the
same order. Query inputs, topology, clocks, contact targets, planes, precision,
containment/partner queries, reductions and decisions are unchanged.

`evaluate_to_archive` uses the [exact numeric writer](native-observation-archive-v1.md)
and returns the unchanged geometry report plus archive and receipt hashes.
The standalone geometry CLI, imported actor audit, combined native object audit,
two-grip object editor, native motion fitting and common scene placement use it.
Reports and method archives bind the new writer; combined evidence also binds
its full transport receipt. Replay verifies every receipt array before checking
the complete saved geometry reductions. Actor geometry files and their receipt
are rechecked before and after composition.

Only earlier numeric array values are released. Per-frame reports, imported
observations, mesh queries, compression buffers and small receipt metadata still
consume memory. The default whole-array limit remains 256 MiB; oversize or
failed writes preserve partial evidence and fail the producer. This is not a
measured total-process memory ceiling or a full-population memory benchmark.
Numerical failures still complete with false decisions rather than disappearing.

## Actual engine clock transport failure

The first actual two-rig procedural authoring job completed contacts, bounded
object editing, source/common assets and native object import. Actor import
then failed the existing strict clock check. For each actor, requested times
1/480 and 1/240 seconds returned eight double ULPs below their originals
(absolute shifts below 7e-18 seconds). Full-precision JSON output was already
enabled; the retained observations exposed decimal input transport loss.
The failed job, raw engine observations and clock diagnostic remain unchanged.

New actor and object requests carry a versioned, complete little-endian Float64
clock as hexadecimal bytes alongside the descriptive decimal times. Both engine
scripts sample the decoded binary clock. Python validates the exact entire
byte population; producer/replay receipts bind the shared decoder and its
executed copy. Existing clock and pose tolerances stay unchanged.
The implementation uses Godot's documented [hex decoding](https://docs.godotengine.org/en/stable/classes/class_string.html#class-string-method-hex-decode)
and [64-bit float decoding](https://docs.godotengine.org/en/stable/classes/class_packedbytearray.html#class-packedbytearray-method-decode-double).
This explicitly versioned byte layout must be checked against each target
engine; it is not a promise about every engine's generic byte representation.

## Historical replay

The retained humanoid dense study and replay use producer methods from commit
`9640b81d00938702e68b9c0a53e9d17832b3261d`. New code intentionally rejects those
old producers as changed-method evidence. Preserve the old records and replay
receipt; use the recorded Git revision in a separate checkout when rerunning
historical replay. Do not rewrite their hashes to admit them to the new method.
The completed expensive humanoid study is not rerun just to validate storage.

Ignored original evidence is under
`reports/native-object-expanded-engine-development-v1`, including `replay-v1`.
Current storage/workflow validation lives under
`reports/native-geometry-stream-validation-v1`. All frozen release gates,
held-out trials, source selections and quality/training/release approvals remain
unchanged. Realistic motion and broad action coverage still need separate
semantic, scene, rig-transfer and human cleanup evidence.

## Actual pipeline validation

The corrected actual Godot job uses two procedural articulated closed-cube rigs,
one sphere, two explicit grip correspondences and a declared plane at -2 m.
It is an integration case, not humanoid-quality or stance evidence. Eight
stages complete: source contacts, bounded object edit, source object asset,
common-clock preparation, object engine import, actor engine import, combined
geometry and replay. All 1,101 original/key-union times remain present. The
requested clock echoes are bit-exact for both actors; no tolerance is widened.

Original contacts fail, and the saved bounded object proposal passes. Native
object-resource observations pass while default imports fail. Complete combined
geometry includes 2,202 actor/object rows, 1,101 partner rows and 2,202 declared
plane rows. All sampled native conditions pass. Replay checks all 6,607 geometry
arrays and 1,065,768 logical bytes, plus complete actor/contact/object reductions.
No original source, source selection or quality/training/release flag changes.

Ignored actual evidence is `reports/native-scene-actual-canary-v1/job-v2`.
The initial failed `job`, its clock diagnostic and both source archives remain
retained. Prior local validation passed 68 initial transport/geometry checks,
206 integrated workflow checks and 96 targeted clock/engine checks. The final
post-repair suite passes all 335 cases in 821.10 seconds, with current source
hashes, terminal producer/replay receipts and unchanged original inputs bound
in the local validation record. These include dense/streamed report and byte
equality, released earlier frame arrays, expanded callback clocks, retained
geometry and partial-write failures, changed actor/combined receipts, forged
transport approval, malformed binary clocks and changed executed decoders.
