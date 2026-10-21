# Replaying combined engine evidence

`verify_native_object_scene_engine.py` checks a completed combined native scene
audit without regenerating animation, executing Godot or repeating the expensive
triangle geometry queries. It checks evidence consistency; it does not approve
motion quality or establish independent animator review.

```powershell
python scripts/verify_native_object_scene_engine.py contacts.json reports/objects-common/common-policy.json reports/actors-engine reports/objects-engine reports/combined-engine reports/combined-verification
```

Use the unchanged producers from the [combined engine workflow](native-object-scene-engine-v1.md)
and a fresh verification directory. Verification shares the worker lock and
must wait for the study worker to finish. Initial producer/receipt checks run
before creating the output; later failures retain a failed pipeline record.
Original producers, assets, methods and reports are never rewritten.

The verifier revalidates terminal producers, source/policy hashes, actual engine
requests and outputs, native Animation resources, actor snapshots and archived
implementations. It reconstructs every imported actor vertex at every engine
time, rederives each source-relative maximum skin error, and compares every
saved error value exactly. Both default-import and native-authoring object
observations are used to replay all contact measurements and source-relative
object pose errors. Every contact report and array must match, including
correct raw-weight metadata. A failed default import stays a failed comparison.

Geometry verification covers the complete declared policy clock, topology,
actor/object, partner and plane populations. For each actor/object observation,
all triangle lower/upper bounds and witnesses must be finite and have the
original face count. Maximum depths, peak faces, witnesses and sampled decision
reductions must agree. Recorded containment distances must agree with their
status; partner containment availability/depth summaries and plane summaries
must agree with their saved decisions. Missing populations, extra arrays and
inconsistent decisions fail verification. An explicit geometry policy can have
fewer times than the engine contact clock; its original times are preserved and
must all occur in the engine observations. Common-clock preparation includes
all original and stored-key times in the geometry policy itself.

The current reducer also requires the versioned, complete self-surface reports
for every actor. It checks topology, pair counts, retained proper/ambiguous
records, degeneracy and containment eligibility. Recorded self-surface failures
remain failed samples even when all object, partner and plane checks pass.
A verified failure is valid evidence, not a successful animation.

Center containment uses the retained signed-distance, ray and winding consensus.
A zero signed distance can erase the unsigned magnitude in the pinned
nearest-normal implementation; center records do not retain that separate
observation. Such records may therefore remain near-surface or unresolved, but
cannot establish inside/outside status or pass clearance. Partner records retain
the unsigned observation. An eligible target can still have unresolved query
points; their identities and diagnostic states must agree, and the unavailable
query cannot publish a depth reduction. These checks do not repeat geometry
queries or turn an uncertain measurement into a pass.

The actor-only verifier now archives and binds this shared reducer alongside its
own implementation. The general scene verifier already freezes this dependency.
The facing-only integration fixture moves its unused stationary triangle away
from the animated square's end pose; production collision policies are unchanged.

All 127 focused tests and 10 subtests pass in 659.99 seconds under the 512 MiB worker cap; all 677 resource observations replay. Coverage includes combined, actor-only and general scene replay, retained self-surface failures, malformed evidence, containment consensus and uncertainty, shared-reducer mutation, the facing-only integration job, Studio diagnostic reporting and source-suite partitioning. Engine execution is mocked in these fixtures; this is not rendered, physical, animator or release approval. The same correction policies remain in force.

These are saved geometry reductions, not independent reruns of depth queries,
containment distances, partner crossings or plane measurements. Matching files
and replay are not cryptographic proof against coordinated fabrication of all
inputs. Real geometry evidence remains the source-bound producer's actual
queries. A consistent recorded numerical failure can verify successfully;
`recorded_sampled_conditions_pass` preserves its original pass/fail result.

The separate result records source/producer receipts, archived method hashes,
the verifier's own copied implementation and the reduction scope. Inputs and
methods are revalidated after replay. It retains the source selection and leaves
quality, training, release, GPU, physics and real-time playback approval false.

Unit fixtures use small closed meshes and explicitly mocked engine execution.
They exercise exact replay, immutable inputs, retained default failures, altered
observations even with updated receipts, incomplete populations, source binding,
partner/plane decisions, explicit clock preservation and retained geometry
failure. These tests do not count as actual Godot execution or human feedback.
The expanded real 2,201-time humanoid study and its full original-method replay
have since completed. Every skin/contact/object observation and all 4,402 saved
actor/object geometry reductions match. New producers additionally stream and
verify exact archive receipts; see [producer integration and historical replay](native-geometry-stream-v1.md).

Local validation covers 29 replay cases, 20 combined producer cases and 22
geometry cases. The initial combined run records 69 passes and two existing
wrapper failures caused by contention with the active production study lock.
Those two synthetic tests now use their own fixture lock directory, preserving
production locking, and both pass on targeted rerun. The original failed
transcript is retained. No expensive humanoid study was restarted for tests.
Hosted CI for the preceding combined-engine commit passes all four Windows and
Linux jobs. Its Windows source job took 13 minutes 50 seconds; the source-check
budget is extended to 30 minutes to include replay coverage without dropping
checks. The adapter job's budget is unchanged.
