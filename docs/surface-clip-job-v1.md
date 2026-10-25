# Resumable surface correction jobs

`scripts/surface_clip_job.py` turns the native surface-clip component into a
prepared, resumable correction job. It copies the source and initial candidate,
records the clip/solver configuration, and binds the script implementation and
Python/numerical-library versions. Subsequent edits to the external source file
do not silently change a prepared job. Changed copied inputs, implementation or
runtime require a new job; the old artifacts remain available.

The incoming key must pass its decoded check before it can be frozen. The worker
then advances overlapping three-key windows (two for a two-key clip), tries the
current, held and extrapolated correction seeds, and solves with the existing
feasibility helper. Explicit budgets limit epochs, iterations, working-floor
growth and added sample times. The optimizer supports at most 64 active interior
samples; the complete declared clock still decides acceptance. Reaching that
working-set limit does not waive failing samples.

The current v2 request protocol preserves the initial and final keys by default.
The final key is checked before correction; incompatible protected-end contacts
stop the attempt with `invalid_preserved_end`. A preserved end receives fixed
solver bounds and is omitted from exported edits. Every candidate and resumed
checkpoint is checked against the initial clip's exact protected channel values.
Protecting endpoint values does not prove that velocity, acceleration or other
transition properties remain compatible.

To permit changing the ending, configuration must contain both
`"end_policy": "edit"` and `"acknowledge_changed_end": true`. Its result explicitly
requires transition review. The default is `"end_policy": "preserve"` with a false
acknowledgment. Earlier v1 requests allowed end edits implicitly; they retain their
original files and require their recorded implementation. They are not silently
reinterpreted as v2 jobs.

Every exported window is decoded and checked before it advances the accepted
checkpoint. Rejected candidates, optimizer records and interrupted attempts stay
in separate attempt directories. Only the last accepted clip is selected by the
checkpoint. Continuation checks the request and receipt chain, hashes its clips
and reports, and freshly audits the entire accepted prefix. An interruption
before checkpoint publication can leave an orphan candidate; it is preserved,
and continuation recomputes from the last committed checkpoint. A complete run
requires a final full-clip decoded audit.

The job can stop between windows on its soft time or window budget. The outer
resource guard can also stop a running optimizer; the next attempt restarts that
unfinished window. Optimizer records are diagnostic snapshots, not a claim of
resuming SciPy's internal state. A shared worker lock serializes numerical jobs.

## Command interface

Use the project's numerical Python environment. A configuration JSON supplies
`clip` (the explicit `SurfaceClip` constructor options) and `solver` with integer
`epochs`, `iterations_per_epoch`, `floor_batch_size`, and
`maximum_new_samples_per_epoch` budgets. There is no automatic joint-name or
contact inference in this command.

```text
python scripts/surface_clip_job.py prepare --folder reports/my-correction --source source.glb --initial seed.glb --config config.json
python scripts/surface_clip_job.py run --folder reports/my-correction --maximum-windows 10 --soft-seconds 240
```

Repeating `run` continues the same prepared job. Each run has its own resource
trace and each worker attempt retains its result. `complete_numerical_candidate`
is the narrow floor/contact/correction-bound result; it does not approve scene
collisions, engine playback, physical plausibility or human motion quality.
The CLI does not start a preview server. Studio integration remains pending.

The process exit code is 0 for a completed guarded worker, 2 for deferred
admission and 1 for a failed worker/guard. A completed worker can still report an
unresolved motion window; inspect the attempt result rather than interpreting
process completion as an animation pass. Inputs retain the surface component's
shared LINEAR native-clock and world Y=0 floor requirements.

## Original v1 verification

Twenty lifecycle tests pass, covering full-clip and budgeted continuation, a real
contact solve, rejected and invalid-incoming candidates, selected non-default
animation and two-key clips, input copies, changed input/runtime/implementation
and receipt rejection, path boundaries, and actual process exits immediately
before and after checkpoint publication. Both exit cases produce the same final
clip as uninterrupted work and preserve the interrupted attempt files.

Three CLI status cases and a real subprocess that defers behind the occupied
worker lock also pass: 24 distinct passing cases in total. The subprocess case
uses an explicitly bounded in-project temporary directory so it also works when
pytest's default temporary root is outside the checkout. Both CI inventories
include this module (652 full and 201 focused Python test files).

The initial longer synthetic fixture run was stopped by the operator; the next
run reached its 300-second time guard. Both traces and partial evidence remain
under `reports/surface-clip-job-tests-v1` and `v2`. The final full lifecycle run
uses a five-key fixture with three overlapping windows and a 600-second outer
test guard; its 20 cases pass in 455.37 seconds. The CLI-only follow-ups are `v4`
and `v5`. The numerical and checkpoint implementation is unchanged after the
full lifecycle run; only CLI exit propagation changed, with separate checks.
Publication checks compare the archived source hashes and unchanged function
ASTs. The three successful test traces replay 523 resource observations, with
maximum sampled worker-tree memory 196,825,088 bytes.

`reports/surface-clip-job-getup-v1` exercises two separate guarded CLI runs on
the existing corrected KayKit get-up, retaining the original transfer as the
edit basis. Both one-window runs checkpoint successfully. The decoded accepted
prefix grows from three keys / 81 samples to four keys / 121 samples; continuation
first rechecks the earlier prefix. Both windows pass their 81-sample checks.
Their resource traces replay 57 observations, with peak worker-tree memory
132,567,040 bytes. Request, input and receipt hashes verify independently.

This last check validates real-asset job continuation, not a fresh get-up solve
or whole-clip processing by the new coordinator. It does not replace the earlier
complete get-up/engine evidence or resolve its ordinary-import clock failure.
The previously corrected source clip and the review packet remain unchanged.

## Endpoint protection verification

The v2 protocol adds fourteen boundary cases to the 87 clip/job/export/solver
regressions: all 101 pass in 584.85 seconds under the existing RAM guard. Tests
cover an actual interior contact repair with a nonzero initial ending preserved
exactly, a protected-end conflict without an accepted checkpoint, the same
endpoint repaired after explicit edit acknowledgment, a fully fixed two-key clip
with an unresolved interior contact, exact decoded boundary-value rejection, and
invalid policy requests. Existing continuation, actual process-exit and changed
input/receipt cases also pass with the new default.

A final reporting-only change makes `transition_review_required` true even when
the endpoint poses are protected, because adjacent edits can change velocity.
Its targeted real-solve test passes separately. Archived source hashes and AST
comparison verify that this follow-up changed no numerical or checkpoint logic.
Both inventories include the new boundary module (653 full and 202 focused
Python test files).

The real KayKit check in `reports/surface-clip-boundaries-getup-v1` processes the
final window at keys 177-179 of the already corrected get-up. Only key 178 is
exported as editable. Key 0, the incoming key 177 and the final key 179 retain
identical decoded channel bytes. All 81 window samples pass, with zero floor
penetration and maximum contact error 19.776323 mm under the unchanged 20-mm
limit. This is a final-window export check on an existing candidate, not new
generation, a full-clip rerun, an engine test or motion-quality approval.

Studio integration remains the next product step. The adapter must carry the
explicit endpoint policy and preserve the existing scene/engine gates; it must
not translate broader object/partner or moving-target constraints into this
static flat-floor model by dropping unsupported requirements.
