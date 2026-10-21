# Recovering imported-mesh geometry checks

The initial 47 recovery tests and 184 existing-pipeline regression checks pass.
An actual humanoid transport comparison is in progress; complete optimizer
recovery is still pending. No motion or release approval follows from this work.

The full humanoid correction trial stopped twice at its 900-second execution
limit while writing the first proposal's geometry observations. Its subsequent
3,600-second attempt completed six rejected proposals and stopped during the
seventh audit, with a 453.2 MiB peak process-tree footprint. A completed
original audit remained available, but the unfinished proposal had no geometry
decision. Increasing a processing budget does not make interrupted observations
complete. Future fitting attempts need to retain complete frames and resume the
same declared audit.

`scripts/native_mesh_geometry_journal.py` provides a separate journal for
`MeshPropScene`. It uses the original actor and prop triangles, native/frame
clock, query batch size, tolerances and geometry evaluator. It includes the
existing actor/primitive/plane/partner checks, actor/mesh-prop pairs, prop pairs,
prop/primitive pairs and prop/world planes. No contact or geometry condition is
removed to make a candidate pass.

## Checkpoint contract

- `prepare` binds the exact scene, policy, dependencies, implementation and
  numerical-library versions, snapshots the sources and records the complete
  required clock.
- `advance` takes an explicit checkpoint path and SHA-256 digest. It verifies
  the entire committed prefix before evaluating more original frames. Each
  complete frame receives an immutable receipt and checkpoint. A stopped or
  failed frame remains separate and is never counted as complete.
- `verify` checks the pinned prefix without new geometry queries. Even a
  complete prefix reports `sampled_conditions_pass=false` until finalization.
- `finalize` requires every original frame. It reconstructs the complete
  geometry report and retains measured failures. It can either create a
  combined observation archive or reference the existing frame archives with
  `--indexed-observations`.

The indexed form avoids copying every humanoid vertex array into a second
archive. Its index binds the original journal, checkpoint, request, clock and
ordered frame receipts. `iter_observations` verifies these bindings and reads
the original numeric arrays one at a time. A caller must consume the complete
iterator to claim a complete replay. This is a source-bound local transport;
it is not a standalone portable animation package.

The CLI commands are worker entry points. Run them through the existing
resource supervisor with an explicit policy, the shared worker lock and fresh
guard output for each attempt. The intended study policy remains a 512 MiB
process-tree cap, at least 600 MiB of available memory, 15 seconds of stable
admission and a bounded execution budget. A retry never overwrites its prior
guard record or abandoned frame. Direct calls from an already admitted worker
reuse only that thread's live verification lock.

## Validation scope

The tests compare complete reports and every saved array's shape, dtype
and bytes against the existing evaluator on generated geometry fixtures. They
exercise failed geometry, moving props, primitive/partner/plane populations,
query batch sizes, full native clocks, changed sources and checkpoint evidence,
partial finalization, indexed transport and CLI dispatch. A separate test kills
an interpreter without unwinding its archive context, then resumes and finalizes
in fresh processes while retaining the unfinished frame directory. All 47 pass
under the shared lock and existing resource supervisor: 151.657 seconds of
guarded execution, 187,080,704 bytes peak process-tree memory and 167 resource
observations independently replayed. Source bindings remained unchanged.
Evidence is retained under `reports/mesh-journal-tests-v2` in the recovery
checkout. The first run remains separately preserved: 46 passed and one test
incorrectly requested a single-time policy that omitted a required clip endpoint.
That test now verifies rejection; the evaluator's endpoint rule was not changed.

The separate 184-test regression run covers the default character fitter,
imported-mesh scene evaluation, existing native journal and observation archive,
Studio worker thread configuration, processing budgets and character correction
integration. It completes in 146.406 seconds of guarded execution with a
205,574,144-byte peak and 162 independently replayed resource observations.
Both new test files are included in the model-free CI inventory. Local evidence
is under `reports/mesh-journal-regressions-v1`; hosted CI remains separate.

A lightweight check has confirmed that the isolated recovery checkout shares
the live worker's lock: admission deferred with `owned_worker_busy`, with no
numerical import, worker start or journal creation. This proves exclusion only.

The existing Trimesh containment fallback can use process-local random state.
The journal preserves committed observations and checks the installed runtime;
it does not yet pin that fallback generator's state. Fixture equality must not
be generalized into bit-identical fresh reruns of ambiguous containment cases.
The geometry checks also do not certify continuous or self collision, physics,
engine playback, semantic correctness or animator quality.

## Integration still required

The character fitter accepts an opt-in `checkpoint_geometry=True` API
argument or `--checkpoint-geometry` worker flag. It checkpoints both original
and eligible proposal audits, retaining the existing complete geometry report
interface and decoded acceptance rules. Array observations use the indexed
transport. The default fitter and Studio still use the existing archive mode.
The source request binds the transport choice and journal implementation.
Neither path can restart an existing optimizer output directory.

The `resume_geometry` helper finishes a pinned interrupted audit against its
exact original scene and policy. It verifies the committed prefix, retains
abandoned frame/finalization directories, and publishes a complete report using
an atomic fresh hard link. It never writes an optimizer result, accepts a motion
or overwrites an already published geometry report. Its completion pointer
explicitly records `optimizer_completed=false`. A stop during final assembly or
publication can retry into a new assembly directory without re-querying
committed frames. Recovery from a missing initial checkpoint still requires a
fresh audit; incomplete preparation is not a completed prefix.

The passing tests include comparisons against archive mode for successful
contact correction and collision rejection, plus interrupted original geometry,
finalization and publication. Complete correction recovery must also preserve the
optimization state, original bounds and request/method pins; geometry frames
alone are insufficient to resume an interrupted correction.
Existing failed trials remain immutable and cannot be silently relabeled as
checkpoints produced by the new implementation. Retargeting, broad action
coverage, scene/partner workflows, style controls and the full release matrix
remain part of the project-wide goal.

## Next recovery boundary

Full optimizer recovery must commit a pinned request and original bounds,
current controls and decoded residuals, selected candidate, accepted geometry,
iteration/backtrack position, and the already computed solver direction before
expensive proposal geometry begins. A resumed attempt should finish the same
serialized proposal rather than recompute a potentially different solver step.
The geometry decision, probe history and next optimizer state need an atomic
commit boundary; a crash between their writes must not accept a probe twice or
skip an unchecked proposal. Completed contact/edit reports, exported asset
digests, failed attempts and frame receipts must remain bound to that state.

The required tests should interrupt original evaluation, proposal export,
proposal geometry, decision publication and accepted-step publication in fresh
processes. They must compare the complete decision sequence with uninterrupted
execution, reject changed inputs/methods/bounds, retain abandoned writes and
leave the original selected until a complete existing acceptance check passes.
This is an implementation plan, not a claim that optimizer recovery exists.
