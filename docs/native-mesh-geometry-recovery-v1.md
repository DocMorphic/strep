# Recovering imported-mesh geometry checks

The initial 47 recovery tests and 184 existing-pipeline regression checks pass.
The actual humanoid transport comparison also passes after a real execution-limit
interruption and fresh-process resume. No motion or release approval follows
from this work.

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

## Actual humanoid interruption and comparison

The experiment re-evaluates the original fixed-panel humanoid diagnostic with
the exact existing scene, full 2,017-time policy and geometry implementation.
The first process saves four complete samples; a fresh process resumes. That
attempt reaches its unchanged 900-second execution guard after sample 1,740.
Its incomplete frame remains separate. Another fresh process verifies the saved
prefix and completes all 2,017 samples. No sample or tolerance is removed.

A separately admitted comparison assembles indexed observations and checks the
entire report against the previously completed original audit. All report fields
match, and all 4,035 numeric arrays have the same names, shapes, dtypes and bytes.
The original source/report/archive bindings remain unchanged. The earlier audit
contains 4,282 failed condition identities and 42,666 surface records; recovery
retains those failures and does not approve the motion.

Evidence is under `reports/humanoid-mesh-journal-v1` in the recovery checkout:
`comparison.json`, the original reference digests, pinned checkpoints, abandoned
frame, per-attempt guards and independent resource replays. The four attempts
replay 23, 903, 243 and 277 resource observations respectively. This proves
transport and recovery for this original humanoid audit, not a completed
humanoid correction, general deterministic containment, engine success or
animator quality. This study makes no whole-job speed claim.

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

## Optimizer recovery and remaining integration

The separate [optimizer recovery worker](native-mesh-optimizer-recovery-v1.md)
now commits a pinned request and original bounds,
current controls and decoded residuals, selected candidate, accepted geometry,
iteration/backtrack position, and the already computed solver direction before
expensive proposal geometry begins. It resumes the same committed direction,
retains abandoned exports and assemblies, and commits decoded decisions exactly
once. Completed contact/edit reports, exported asset digests, failed attempts
and frame receipts remain bound to that state.

Its generated-fixture tests compare the complete decision sequence and candidate
bytes with uninterrupted execution, reject changed evidence and verify
fresh-process recovery after hard exits during original/proposal geometry.
The original remains selected. The existing `fit` entry point remains a
fresh-output API; the new recovery API is separate. Studio lifecycle and package
recovery, full humanoid optimizer measurements and collision guidance remain
unfinished. Neither recovery component satisfies the full release contract.
