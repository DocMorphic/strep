# Interrupted character correction status

Studio's character correction worker now records its process ID and OS creation
time, bound to the exact prepared-job hash. The server separately records the
launched process handle. Different receipt filenames avoid a server/worker
startup write race. Direct CLI workers register while holding the existing
per-job lock; completed jobs do not overwrite their execution identity.

Review and job listing observe these receipts without changing `pipeline.json`,
raw probes, partial assets or the original selection. For active jobs:

- A live process with the same birth identity retains the recorded active state.
- A missing, exited, zombie or replaced process projects a failed review, with
  no downloads or staging approval.
- Missing execution identity on a legacy processing job, malformed or changed
  identities, conflicting launch/execution identities and denied process access
  project an unverified state. These do not prove the worker exited.
- A prepared job without a launch identity can still be waiting to start.
- A terminal pipeline receipt takes precedence, including a completion written
  while the process is being queried. Normal completed-result validation remains
  required before downloads become available.

Partial numerical evidence stays available locally for diagnosis. A projected
failure does not manufacture a terminal computation receipt, enable automatic
retry, accept a partial clip or change any native/geometry/quality gates. The
process check observes the recorded owner, not every possible descendant or
external worker. It is not a guarantee that a live process is making progress.

This addresses the stale outer processing state exposed by the
[actual crawl attempt](native-component-receipts-v1.md). That historical job's
explicit supervisor-stop reconciliation remains separate and immutable. This
change covers character correction jobs, not every other Studio job family.

`tests/test_studio_native_fit_activity.py` exercises identity binding, PID reuse,
permission denial, invalid saved metadata, startup registration, terminal races,
offline server dispatch and a real child-process exit. It observes failure while
the original raw pipeline still says processing and checks that all saved bytes
remain identical. These are lifecycle checks; no new motion, model inference,
production pose/geometry validation, engine playback or human quality evaluation
follows from these lifecycle cases.

All 108 related local tests pass together, covering 27 initial lifecycle cases,
the existing native Studio workers and 21 mixed/edge-control cases. The run
completes at 415.875 seconds execution; all 426 resource observations replay.
After adding bounds/error handling for oversized saved identity numbers, all
29 lifecycle cases pass on final source, including the two new regressions;
all 28 resource observations replay. This is 110 distinct passing cases across
the two runs, not a final repeat of the entire compatibility group. Inventory
is 475 Python modules / 42 Node suites. Local records remain under
`reports/native-fit-activity-checks-v1` and `reports/native-fit-activity-checks-v2`.

Source and offline handler tests do not verify the currently running browser or
restart an existing Studio server. The new behavior applies when the updated
server/worker source is launched.
