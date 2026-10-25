# Ground-contact cleanup in Studio

Character Studio now mounts the resumable SurfaceClip correction workflow beside
the existing scene editors. It edits a selected saved rig clip, preserves the
original, and exposes accepted and rejected candidates for comparison. It does
not generate a new action or establish motion realism.

## Use

1. Select a saved character result and version in Character Studio. Open
   **Ground-contact cleanup**, then **Use selected character clip**.
2. Choose editable rotation joints and per-joint angular limits. Set root-motion,
   floor-depth, contact-error and per-key correction-change limits. Currently the
   clip needs one animation and compatible shared LINEAR tracks.
3. For floor-only correction, leave contacts empty. For a static point target,
   select exactly one mesh vertex in Mesh contacts, enter its target XYZ in clip
   coordinates and its closed time interval, then add it. Each selected point is
   bound to a mesh node, primitive and vertex. A multi-vertex selection is rejected.
4. The starting pose stays fixed and must already pass. The ending pose is also
   fixed by default. Allowing it to change requires the explicit acknowledgment.
   Preserved poses still require transition/velocity review after adjacent edits.
5. Choose an attempt budget and submit. **Refresh jobs**, select the saved job,
   then **Inspect selected job**. A checkpointed or resource-interrupted attempt
   can continue from its verified saved inputs and constraints. Changing the
   request requires a new job. Source/runtime changes can prevent continuation.
6. Inspect the original, last accepted clip and any rejected candidate using the
   comparison link. Downloads are verified against saved hashes. A partially
   processed clip includes unprocessed motion beyond the reported checked prefix.

The UI is delivered with the generated Studio bundle. A running older server
needs a normal restart to load the new Python routes; this development turn did
not start or restart a server.

## Boundaries and evidence

The ground plane is Y=0. Contacts are static point targets in clip coordinates.
Object geometry, moving targets, partner contact, self-intersection, dynamics,
engine playback and motion quality are separate checks. Existing scene tools
remain necessary for those constraints. This adapter never converts a broader
scene request into a floor-only job by discarding its requirements.

The sampling population now includes the exact start and end of each contact
phase, including off-grid instantaneous contacts. The declared sample budget
reserves space for these boundaries and rejects oversized requests without
dropping samples. This remains sampled validation, not a continuous guarantee.

Transport requires the local Studio origin and bounded JSON. A per-job queue
lock and the existing global numerical-worker lock prevent concurrent writes.
Workers run under RAM/time admission and execution guards. Accepted checkpoints,
failed attempts and rejected candidates remain on disk. Publication requires a
completed guarded attempt and its resource replay; artifact hashes are checked
again before download. A failed/interrupted attempt may be resumable without
publishing incomplete files.

Automated checks exercise the actual server dispatch without opening a socket,
the editor with a DOM fixture, and real core export/continuation with a synthetic
rig and explicitly substituted source resolver. These are integration checks,
not a live rendered-browser test, a production-asset study or animator approval.
Local test receipts are retained under `reports/studio-surface-clip-tests-v1/`.

Across the initial run and targeted follow-up, all 76 distinct Python checks
pass. The initial run retained one Windows path-length failure; shortening the
fixture's in-project store resolved it. The follow-up passes all 33 adapter and
contact-clock checks, including actual exported-clip continuation. Four Node
suites pass for the editor, comparison controls and existing preview behavior.
Both CI inventories include the new tests (655 full / 204 focused Python files).

An additional actual hidden supervisor/worker launch deliberately uses a missing
source. Queue exclusion, guarded failure, resource-trace replay, non-retryable
error reporting and withholding downloads all pass. This tests the real failure
path; successful production-asset launch and rendered browser behavior remain
unverified here. Its receipts are in `reports/studio-surface-clip-launch-v1/`;
the combined binding/replay verifier is in
`reports/studio-surface-clip-verification-v1/`.

The existing get-up review remains separate. Its ordinary-import endpoint clock
failure and missing human quality/cleanup evidence are not waived by this work.
