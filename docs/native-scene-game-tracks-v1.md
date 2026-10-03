# Native root, contact and gameplay tracks

Completed native scenes can now produce a source-preserving game-track package
from Studio. This supports any supplied action: the asset/contact schema, rather
than an action-name list, determines what can be measured and exported.

The preceding scene job's clips, object trajectory, geometry queries, failures,
raw engine observations and original package remain immutable. This step reads
their complete audited clock and recorded imported transforms, adds explicit
track metadata, and tests a finite Godot event dispatcher. It does not regenerate
motion or rerun the expensive triangle/containment queries.

Existing clip-event sidecars are not automatically converted from their legacy
frame clocks. Scene gameplay markers are explicit new intent on the audited
scene clock; the original clip-event files remain in their source jobs.

## Studio workflow

Choose a complete scene in **Scene contacts & game assets**, then open **Root &
gameplay tracks** and use the selected scene. Choose an existing skin joint as
the root for each character. No default joint or anatomy interpretation is
inferred. Root names can differ between rigs; node indices refer to the exact
selected GLB and animation.

Add gameplay markers using an ID, name, actor and exact audited time. Timing
confirmation starts unchecked. Unconfirmed markers remain in the package but
do not dispatch. Markers at the same time remain distinct. A time outside the
audited clock is rejected, including decimal rounding or snapping to a nearby
native key. To use another time, declare it in the scene's geometry clock and
build a new scene job first.

Save the request for reproducibility, then build and show its results. Choosing
another scene cannot submit stale roots or markers. Root comparison and scene
failures remain visible; they do not replace the currently selected clips or
approve animation quality. The same loopback host/origin, JSON-size and single
offline-worker gates apply as for scene jobs.

An already-running Studio backend must be restarted after updating these routes.
An unavailable optional editor reports its load error without preventing the
remaining character editors from initializing. Offline bootstrap checks cover
this behavior; a live Studio restart/browser check was not performed here.

## Root reference contract

The `strep-native-scene-game-tracks-v1` request names every actor's root joint and
explicit marker intent. Each root is sampled at every original audited time.
Authored scene placement is included. Full 4×4 Float64 matrices are preserved;
no yaw filter, height removal, quaternion projection, downcast or resampling is
inferred. The selected root is compared with all corresponding recorded imported
joint matrices using the existing pose threshold. Failures remain measured
failures rather than missing files.

The reference delta convention is:

`delta(t) = inverse(world(0)) @ world(t)`

`world(0) @ delta(t)` reconstructs the recorded source root. Root JSON and NPZ
contain the complete world matrices and initial-local deltas. NPZ additionally
contains every imported root matrix. Float64 dtype, shape, population and bytes
are checked after serialization. Units are metres in glTF's Y-up frame.

**Motion stays embedded in the supplied character GLBs and native resources.**
These root tracks are references, not a second transform to apply to those same
clips. The package explicitly records `root_removed_from_character_clips=false`
and `root_application_mode=reference-only-motion-remains-embedded`. In-place
extraction, root decomposition and accumulated looping runtime playback remain
separate requirements. Between-reference-sample accuracy is not certified;
original interpolation is retained in the unchanged GLB.

## Contact and gameplay distinction

`contacts.json` preserves each complete vertex patch, reduction, actor,
object/world/partner target, interval and hard limit together with its recorded
imported contact measurement. A hold produces start/end intent boundaries; a
touch produces one boundary. Contact boundaries never dispatch automatically,
even when all sampled contact conditions pass. They do not prove physical grasp,
attachment, impact, action correctness or collision-free continuous motion.

These measurements describe the active scene proposal. Earlier source-contact
and default-import failures remain in the linked original scene job.

`events.json` contains those contact boundaries and the explicitly authored
gameplay markers. Only timing-confirmed gameplay intent can dispatch. The
original Float64 clock travels through the versioned little-endian binary clock
protocol. Integer sample indices address that clock; descriptive JSON decimal
times are not used to reconstruct engine timing.

The packaged `runtime/godot_scene_game_events.gd` helper validates event identity,
clock indices, order, intent kind and Boolean confirmation. Forward advancement
dispatches each eligible event crossed in `(previous, current]`. A new cursor
includes time zero. Skipped samples preserve every crossed event; repeated
identical times dispatch nothing twice. Rewind and out-of-range/nonfinite
advancement are rejected without changing the cursor. An explicit `reset()`
starts a new traversal. Automatic looping, reverse dispatch and silent preview
seeks are not implied by this finite helper.

The implementation uses Godot's documented [RefCounted helper type](https://docs.godotengine.org/en/stable/classes/class_refcounted.html),
[JSON parsing and full-precision serialization](https://docs.godotengine.org/en/stable/classes/class_json.html),
and the existing binary [Float64 clock](native-geometry-stream-v1.md).

## Packaging and evidence

The original ZIP entries remain byte-for-byte unchanged. Its manifest is retained
as `source-package.json`; a new manifest binds the original assets plus root,
contact and event sidecars, request and runtime helper bytes. ZIP contents are
streamed, read back and hashed without selecting a smaller population. The source
package and completed scene result are pinned throughout. Fresh jobs snapshot
the complete method population; repeated dispatch against completed/failed jobs
does not alter their evidence. Modified inputs, sidecars, runtime receipts or
executed scripts block serving. Rewritten artifact hashes cannot turn contact
intent into confirmed gameplay or change the original marker choices.

This is development asset transport and finite event-helper evidence. Actual
animation/runtime integration, in-place root extraction, physics, human semantic
review, cleanup-time evaluation, engine integration on diverse rigs and release
approval remain open. All original evaluation/release gates remain unchanged.

## 2026-10-03 development validation

The final combined suite passes all 100 Python cases in 494.85 seconds. These
cover root reconstruction and exact array transport, preserved numerical
failures, strict root/marker choices, original package byte equality, retained
execution failures, source/sidecar/method tampering, forged confirmation with
updated receipts, offline handler gates and preservation of the Studio build.
Initial targeted runs passed 18 root/intent checks, 31 mocked game-wrapper checks
and 22 root/build checks. New root/gameplay and existing scene, mesh-contact and
native-support editor workflows pass under offline Node DOM checks. No live
Studio HTTP or browser/GPU verification is claimed.

The final additional root suite passes 19 cases in 6.68 seconds, including another
selected skin joint, rotated actor placement and reordered actor choices. After
adding optional-editor load isolation, both scene editor Node workflows, existing
mesh-contact playback and all four rebuilt desktop checks pass again.

The final actual canary reads the completed two-rig procedural scene at all
1,101 original audited times. Every selected root compares with the recorded
imported engine joint transforms. Root NPZ arrays survive a complete dtype,
shape, population and byte readback. Declared contact intent and the original
scene failures are preserved. Six authored markers include one unconfirmed
marker; five confirmed markers dispatch, including two distinct actor markers
at the same instant. Actual Godot 4.7.2 traces match exactly for whole-clip,
every-sample, skipped-sample and repeated-seek traversal.

The actual helper also rejects negative, over-duration, positive backward,
NaN and infinite clock advancement without moving the cursor. Six malformed
configurations reject: duplicate IDs, out-of-range indices, Boolean indices,
truncated binary clocks, non-Boolean confirmation and contact auto-dispatch.
The packaged runtime helper/clock bytes match the executed scripts. The original
ZIP entries remain byte-for-byte identical, and every extracted package receipt
and offered download passes verification. Original scene, engine observations,
package, completion and status hashes remain unchanged. No motion generation,
geometry requery or source selection change occurs.

Ignored evidence is `reports/native-scene-game-jobs/procedural-canary-v2` and
`reports/native-scene-game-validation-v2/checks.json`; the earlier completed
canary remains intact. This fixture uses articulated closed cubes and a sphere,
not a human-quality animation benchmark. Numerical/export/event-helper success
does not approve the animation, physics or full game runtime. Prior commit
`3aec272` passed all four GitHub CI jobs. Release capability evidence, held-out
trials and frozen acceptance gates are unchanged.
