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

## Verification

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
