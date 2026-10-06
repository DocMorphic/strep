# Offline stored-pair correction jobs

`scripts/native_stored_pair_job.py` provides a reproducible command for the [stored-centered backend](reusable-stored-pair-model-v1.md). It builds one complete bounded correction model, exports each requested step fraction, and records actual native, original-reference and complete sampled geometry checks. Original clips stay selected; proposals receive no automatic quality or release approval.

## Run a job

Use the existing project Python environment with its CPU numerical dependencies installed:

```powershell
python scripts/native_stored_pair_job.py --request path/to/job.json --output reports/my-new-job
```

The output directory must be fresh. This command does not acquire a model or character, train, generate new motion, render a preview, or import into an engine. Input files and dependencies must already be available locally. The public repository is a development source snapshot, not a bundled offline installer.

## Request contract

The top-level JSON fields are:

| Field | Required value |
| --- | --- |
| `schema` | `strep-native-stored-pair-job-v1` |
| `source_scene` | Pinned source scene JSON |
| `reference_scene` | Pinned original reference scene JSON |
| `edit_request` | Pinned source-bound boundary edit request |
| `storage_policy` | Pinned source-bound storage adjustment policy |
| `geometry_policy` | Pinned original source-bound geometry policy |
| `source_rate_caps` | Pinned original rate-caps NPZ |
| `anchor` | Controls, explicit storage corrections and actual exported edited-actor clips |
| `settings` | Trust, finite-difference step, resource limits and requested fractions |

Each pinned file is an object with `path` and `sha256`. Relative paths resolve against the submitted job JSON directory. An anchor has `controls` as a pinned NPZ, `array` naming its numeric control array, `corrections` containing explicit storage adjustments, and `actor_files` mapping every edited actor ID to its pinned GLB. An unedited participant keeps actual source playback rather than inheriting altered reference worlds.

Settings can use:

```json
{
  "trust": 0.02,
  "difference_step": 0.001,
  "maximum_rows": 400000,
  "maximum_nonzeros": 60000000,
  "fractions": [1.0, 0.5, 0.25, 0.125]
}
```

Trust is bounded to 0.000001–0.02, finite-difference step to 0.000001–0.01, rows to 400000 and nonzeros to 60000000. Choose one to eight strictly descending, unique fractions between 0.0001 and 1.0. Booleans are not numeric settings. Unsupported fields and mismatched pinned bytes are rejected.

Original rate caps must contain the uniform sample clock and all four metric arrays for every edited actor. Each supplied actor's arrays must exactly recompute from its pinned reference motion at the existing 120 Hz clock and 0.00001 tolerance. Changing and rehashing a caps file therefore cannot silently relax motion limits. Source-bound permissions, track clocks, anchor payloads and original reference movement budgets remain enforced.

## Saved evidence

A successful computational job records input snapshots and hashes, archived implementation files, the anchor, complete model matrices, guard and reduction records, solver status, and every exported fraction. Each fraction has actual exported GLBs, decoded observations, original-reference track/displacement bounds, and a full geometry observation archive, including when its native checks fail.

`numerical_conditions_pass` is the conjunction of actual native checks, cumulative original-reference bounds and sampled geometry checks. Solver convergence and smooth predictions alone do not establish it. `original_selected` stays true, every proposal's `retained` stays false, and quality/release approval stays false. If no solver direction is available, the completed computational job can contain zero proposals; inspect the recorded solver status. Algorithm failures preserve a failure record and traceback once computation starts. Existing job directories are never overwritten.

The job records original paths and resolves guide assets against the local machine. Its snapshots support audit; they are not a self-contained portable asset package. Geometry archives validate saved observations but do not constitute independent geometric predicate recomputation, continuous collision detection, self-collision or physical realism evidence.

## Validation and remaining work

Thirteen job tests and thirty-three existing stored-model/proxy tests pass: **46 passed, zero skips**. The new tests run an actual complete CPU model, solver, export and geometry audit on a generated two-actor cube fixture. They verify unchanged source files, snapshot hashes, frozen playback, strict numerical acceptance, fresh-output requirements, malformed requests, changed inputs, and rehashed weakened caps. CI includes the new job suite; hosted CI results are separate from this local test result.

This publication does not rerun the larger retained fixture study or claim production humanoid quality. The previous repaired anchor still fails full geometry at roughly 5.117411 mm penetration. Next work is to apply the command to that saved anchor, independently replay all proposals, and continue correction while preserving failures. Broad action/rig/object/partner testing, engine validation and developer/animator review remain required by the active project-wide goal. All fourteen release evidence arrays remain empty.


The first complete retained job execution and its independent model/storage replays are documented in [Complete offline stored-pair job study](offline-stored-pair-study-v1.md). All raw fractions receive full geometry audits; the repaired candidate passes original motion/contact/reference checks but remains geometry-failed and unapproved.
