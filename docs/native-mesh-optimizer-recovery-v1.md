# Recovering the bounded character optimizer

Worker implementation validated on generated rig fixtures; not yet connected
to Studio. The original
source, fixed targets, native editing bounds, floor guards and full geometry
acceptance remain unchanged. This component adds recovery, not collision guidance
or animation-quality approval.

`scripts/native_mesh_character_recovery.py` exposes `prepare`, `advance`,
`verify` and `finish` worker APIs. They must run through the existing resource
supervisor and shared worker lock. `prepare` requires a fresh output directory;
each subsequent call takes a checkpoint path and its SHA-256 digest. An advance
requires the current committed optimizer checkpoint, preventing rollback over
later decisions. Read-only verification can inspect an older pinned state.

## Saved state and publication

The request binds the original scene, permissions, policy, complete source
snapshots, method closure, numerical runtime, solver implementation, native
clocks, initial controls and original bounds. Resuming reconstructs the original
problem and compares that signature; it cannot rebase on a previously modified
character or change the processing request.

The optimizer commits explicit stages: original preparation, geometry,
initialization, direction, serialized proposal, decoded decision and completion.
Checkpoint state retains the current controls and residuals, decoded world
transforms, original and current geometry, selected diagnostic candidate,
iteration/backtrack position, history and complete decisions. The computed
direction is saved before a proposal is exported. A resumed committed direction
is used exactly; the solver is not rerun for that stage.

Geometry uses the existing full-frame journal. Its request and genesis are
pinned by the optimizer before expensive queries start. Resuming verifies the
completed prefix and continues the same full clock. Complete geometry is
assembled from those frames into a fresh directory before the optimizer stage
can commit. An abandoned assembly is retained and never trusted merely because
it contains a result file. Already committed complete geometry cannot be rolled
back to a partial prefix.

After full geometry validation, a file seal records the authoritative frame
archives, receipts, checkpoint chain, request and input/method snapshots. The
optimizer checkpoint binds that seal. Later stages verify the exact saved file
bytes instead of repeatedly decompressing the same numeric observations.
An unfinished journal still undergoes the journal's full prefix verification.
This avoids redundant decoding while retaining the already validated evidence;
it does not replace the initial complete geometry check.

The decision and next optimizer state commit separately from incomplete work.
Every state extends a pinned checkpoint chain; prior artifact hashes, decisions
and history cannot disappear or change. A crash after writing a decision but
before publishing the new checkpoint retries that same decision, without
duplicating it. Atomic fresh-file publication protects final decisions and
results. Incomplete exports, direction writes, checkpoint writes and geometry
assemblies remain in their unique directories and do not count as committed.

## Validation and limits

The implementation keeps the existing bounded proposal and decoded acceptance
algorithm. It still rejects new failed geometry conditions or any worsened
geometry metric, even when the hand is closer to its target. It never edits
props, loosens contact tolerances, changes the clock, grants engine or human
approval, or automatically selects a diagnostic candidate for the user.

All 21 distinct test cases are covered by passing guarded runs. They compare
complete accepted/rejected probe sequences and candidate GLB bytes with the
existing optimizer, including a collision-obstructed case. They cover
interruption before each stage's publication, preserved solver directions,
changed source/checkpoint rejection, rollback rejection, abandoned-assembly
handling, and hard process exits during original and proposal geometry followed
by fresh-process recovery. A separate partial-export test leaves an actor GLB
without its scene manifest, then confirms that the orphan remains unchanged
while the same committed direction is retried in a fresh directory.

The initial run has 19 passing cases and one incorrect fixture assumption:
the test expected the first proposal to reach geometry, but the native source
checks rejected it earlier. The corrected test advances to an eligible proposal
and compares the preceding decisions with uninterrupted execution. No solver,
bound or acceptance rule changed. Targeted runs pass the corrected hard-exit
case, its original-geometry counterpart and the added export case. Final
assertions compare the baseline sequence rather than requiring a particular
number of rejected proposals; those changed cases pass again.

The implementation is byte-identical across all test epochs; the other original
test functions are unchanged. Evidence is retained in
`reports/mesh-optimizer-recovery-tests-v1`, `-v2`, `-v3` and
`reports/mesh-optimizer-recovery-publication-v1`. All 661, 104 and 76 recorded
resource observations replay, including the initial failed test run. The largest
observed process tree is 222,248,960 bytes under the unchanged 512 MiB cap and
600 MiB available-memory reserve. The complete test file is in the model-free
CI inventory; local results do not assert hosted CI completion.

These are generated single-character fixtures, not full humanoid optimizer or
partner-scene release evidence. The separate real humanoid experiment verifies
complete geometry-audit recovery only. No new accepted full humanoid correction,
motion-quality, engine or release result is claimed here.

Further work includes Studio job lifecycle integration and measuring recovery
overhead on full humanoid correction. Per-frame verification reads saved arrays
and can be expensive; completion and exactness matter before any performance
claim. The existing containment fallback's process-local random-state limitation
also remains. Broader actions, objects, partners, rigs, engine imports and human
cleanup evidence stay required by the project-wide release contract.

## Studio integration work

The current `studio_mesh_character_job.execute` always copies a fresh source,
calls the legacy fresh-output fitter, builds previews and writes one package.
`launch` and `review` assume one supervisor and `guard/` record. Reusing that
function over an interrupted folder would overwrite or collide with evidence;
adding a Continue button alone is insufficient.

The integration must retain legacy queued requests and introduce an explicit
recoverable request mode for new jobs. Continue must bind the existing request
digest and current optimizer checkpoint, reject a live owner or another active
worker, and create a fresh attempt directory with its own guard, supervisor
identity, failure and replay. Changed editor controls cannot alter a saved job.
The request's existing processing budget and memory policy remain authoritative.

Source preparation needs a verified completed snapshot and exact original
permissions before optimizer preparation. A retry must reuse those inputs,
retaining any abandoned preparation directory. A completed optimizer must also
survive an interruption during previews or package assembly: use a fresh
assembly directory, verify its contents and publish a complete package receipt.
Never expose an incomplete archive as a finished result or discard earlier
attempts. Preserve the current portable original/candidate previews and original
selection behavior.

Route and editor tests must cover current-job exclusion, stale request or
checkpoint rejection, immutable processing budgets, deferred and interrupted
attempts, completed optimizer plus interrupted packaging, legacy jobs, and
successful preview/download verification. Numerical work and checkpoint replay
remain inside the admitted worker; status and queue imports stay lightweight.
