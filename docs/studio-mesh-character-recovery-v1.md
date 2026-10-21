# Continue an interrupted character correction

New Studio object-contact corrections use the recoverable native optimizer.
An interruption retains completed geometry frames and committed optimizer
stages. Continuing uses the same saved scene, bounds, targets, source clips and
processing limit. It does not extend a completed correction or apply newly
edited controls to an old job.

## Studio workflow

1. Save and measure the object-contact scene. Save the character editing bounds.
2. Under **Correct character contacts with objects**, choose the processing
   limit and submit the correction. Keep its correction job identifier.
3. Use **Refresh correction** to inspect that job. If it stopped or was deferred
   and its saved inputs still match, **Continue interrupted correction** becomes
   available. Wait for the previous worker to stop before continuing.
4. Continue creates a new guarded attempt. It preserves the previous attempt's
   logs, failures and resource observations. The saved processing limit applies
   to each attempt; the memory limits remain unchanged.
5. Once complete, compare the original and candidate and download the package.
   Original clips remain selected. Passing sampled checks is not animation,
   engine-import or release approval.

Old jobs without the explicit recoverable flag retain their original behavior.
They cannot acquire resumable optimizer state retroactively. Changing the saved
request or Python implementation requires a fresh correction; the earlier
artifacts remain available on disk.

## Implementation and evidence boundaries

`studio_mesh_character_recovery_job.py` owns per-attempt lifecycle and completed
package publication. Each continuation binds the previous attempt and current
progress receipt. Queue locking, process identities and the existing shared
worker lock prevent overlapping numerical attempts. Numerical imports and
checkpoint replay run inside the admitted worker, with BLAS limited to one
thread. Status and queue imports remain lightweight.

Source preparation compares the cloned package with the original saved scene
and rebuilds permissions from the unchanged request. The optimizer reuses its
native journal, source signature, bounds and current checkpoint. Preview and
ZIP assembly use fresh directories and publish a receipt only after complete
verification. A packaging interruption can reuse an already completed optimizer.
Abandoned directories stay on disk; the downloadable archive includes saved
source preparation, optimizer artifacts and the completed comparison previews.

Windows job roots use extended absolute paths so nested geometry records work
without changing system settings. Artifact paths must still stay inside the
saved job. Browser URLs and ZIP members remain relative and portable.

The resource policy remains 512 MiB maximum process-tree memory, a 600 MiB free
memory reserve, 15 seconds of stable admission, and the saved 900, 1800 or 3600
second execution budget. Recovery does not relax geometry acceptance or claim
continuous collision, dynamics, semantic correctness or animator approval.

## Validation scope

Lifecycle tests use a separately authored three-time geometry policy and one
correction iteration. The original source/contact clocks, native solver,
retained edit limits and actual GLB/preview/ZIP path remain in use. An injected
geometry interruption preserves its first complete frame; a later attempt
finishes the same saved job. An interrupted package assembly reuses the
completed optimizer, with a test that rejects any attempt to advance it again.
Both tests verify original source bytes, earlier guard records, preview asset
digests and every downloaded archive member. Synthetic per-attempt guard records
exercise serving; a real enclosing resource guard covers the numerical tests.

A separate 969-time, 16-iteration stress fixture remains unfinished. Its first
attempt exposed Windows path length; a subsequent attempt reached the
900-second guard at 900.594 seconds, with a peak process tree of 138,133,504
bytes. All 901 recorded resource observations replay. The original and one
eligible proposal each retained all 969 geometry frames, but the proposal's
outer optimizer stage was still uncommitted. Two preceding proposals were
rejected by native checks. No completed correction or package is claimed for
this stress case. Saved artifacts are copied and byte-verified outside pytest's
temporary cleanup area; their original absolute source bindings are preserved.

Set `STREP_RECOVERY_STRESS=1` to opt into the full-clock test cases, using the
resource supervisor. They are skipped in routine CI. The small lifecycle
fixture is not substituted into an existing saved job and supplies no evidence
for full-humanoid, partner, engine or animation-quality acceptance.

The final guarded run passes 69 tests, with two opt-in stress cases skipped.
It covers the new lifecycle and long-path boundaries, existing corrections and
previews, budgets, fresh-process worker thread limits and generated Studio
markup. Imported source stayed unchanged during the run. All 162 resource
observations replay; the peak process tree was 206,487,552 bytes. Node editor
checks also pass, including stale job/progress selection and preservation of
saved bounds despite subsequent editor changes.

Local evidence is under ignored `reports/studio-mesh-recovery-tests-v1` through
`-v5`. Initial path failures and the time-limited attempt remain retained.
The stress archive contains 9,993 byte-verified files. Browser rendering has
not been reviewed in this change; portable comparison behavior is checked
through its actual descriptor and served-file functions. These local results
do not imply completion of the hosted CI workflows.
