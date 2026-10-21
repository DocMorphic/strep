# Reproducible containment diagnostics

The v1 diagnostic could change its answer for identical geometry. A retained
transition candidate reproduced this at frame 515, time 0.393750011920929 s:
actor A vertex 57 was resolved on one evaluation and unresolved on replay.
Controlling only Trimesh's random fallback across 32 seeds produced 12 resolved
and 20 unresolved reports. The original reports and draws remain preserved;
no seed was selected to obtain acceptance.

## Versioned measurement

`strep-containment-consensus-v2` uses the triangle ray intersector with three
fixed, non-axis-aligned directions, each cast forward and backward. All six
hit-count parities must agree. A disagreement, including a zero-hit ray paired
with an odd-hit ray, remains unresolved. There is no random retry or majority
vote. The six integer counts and explicit resolution state accompany retained
unresolved partner observations and primitive-center queries.

The signed-distance calculation keeps Trimesh's nearest-triangle normal branch.
Its off-triangle branch is bound to the same deterministic ray diagnostic on
that query's mesh instance; it cannot invoke the random fallback indirectly.
An unresolved ray's Boolean placeholder is false, but the explicit resolution
mask prevents that placeholder from becoming an outside decision. Complete
solid-angle winding still has to agree with the signed distance and ray result.
Near-surface queries remain non-passing under their original tolerance.

The independent engine-evidence reducer checks all six saved count parities,
the resolution flag, the ray Boolean, unsigned distance and final state. It
rejects missing, contradictory or relabelled evidence. This replays recorded
measurements; it does not independently recast imported-engine rays or prove
their geometric truth.

## Scope and historical results

Each direction pair is processed separately, preserving the existing bound of
at most 64 simultaneous rays for 32 query points. All original target faces
remain eligible for intersection; the winding calculation still streams the
complete face population. Existing source-vertex screening, tolerances, edit
permissions, contact limits and resource guards are unchanged.

Six agreeing floating-point parity counts are a reproducible diagnostic, not
an exact solid-membership proof. Degenerate or self-intersecting surfaces,
near-surface queries and conflicting winding/sign evidence still prevent
acceptance. Self-surface checks, complete motion clocks, engine playback and
human review remain separate requirements.

The old 602-of-2,017-frame humanoid journal retains its v1 measurement and source
hashes. It is incomplete and cannot be resumed with v2 producer hashes or mixed
with new observations. Preserve it as historical evidence; fresh v2 validation
must establish its own complete population. Older archived v1 outputs remain
available with their original implementation snapshots and recorded failures.

## Completed source and complete-clock checks

The initial guarded source run passes 126 tests in 261.22 seconds; all 286
resource observations replay. The retained failing frame is byte-identical
across query batches 1, 2, 32 and 1, with random generation forbidden. Vertex
57 remains unresolved, with forward/backward counts `[2,1]`, `[1,1]` and
`[1,2]`. Thus reproducibility does not turn the disputed contact into a pass.

The final integration run passes 211 tests in 465.64 seconds; all 490 resource
observations replay. It covers scene geometry, actor and general engine
evidence replay, journal-to-engine completion, and native/mesh geometry
journal recovery. The 12,426-byte generated witness is retained in
`tests/fixtures/containment-ray-ambiguity.json`; it contains no downloaded
character data. Existing first-run test functions and production sources
remain unchanged; the later run additionally covers that permanent witness.

Two fresh evaluations of all 1,673 declared times of the saved transition
candidate completed in 216.18 and 217.34 seconds. Their complete JSON reports
and observation archives are byte-identical, with random generation forbidden
and original inputs unchanged. All 470 resource observations replay. Both
evaluations retain failed sampled geometry; this establishes reproducibility,
not motion acceptance. The old candidate and old observations remain intact.

The [focused containment run](https://github.com/DocMorphic/strep/actions/runs/39603350403)
at `33aaacc` passes 34 tests on Ubuntu (0.87 s) and Windows
(1.22 s). The
[Studio correction run](https://github.com/DocMorphic/strep/actions/runs/39603357934)
at the same source passes all 25 tests on Windows (1,498.27 s) and Ubuntu
(2,113.12 s). Both job conclusions are successful; exact metadata and logs
are retained under `reports/deterministic-containment-v2-publication-v1/hosted`.
The separate
[direct correction run](https://github.com/DocMorphic/strep/actions/runs/39603353868)
at `33aaacc` also passes all 22 tests on Ubuntu (2,764.81 s) and Windows
(3,067.73 s). All three focused runs are complete and successful, totaling
81 source tests per operating system. Their metadata and full job logs are
retained in the same local evidence folder. These suites can be
selected in focused both-OS CI with a 60-minute limit because the retained
setup alone took over 14 minutes locally and later tests replay full clips.
Other focused CI jobs retain 15 minutes. Local numerical studies retain the
512-MiB process-tree cap, 600-MiB free-memory reserve and 900-second guard.

These results establish source-level checks and a reproducible retained
failure, not realistic motion, a completed transition workflow, real engine
playback or release approval. Raw local evidence remains under ignored
`reports/deterministic-containment-v2-tests-v1`,
`reports/deterministic-containment-v2-integration-v1` and
`reports/deterministic-transition-replay-v2`.
