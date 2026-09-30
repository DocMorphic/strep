# Continuing a paired correction with refreshed geometry

The peak diagnostic showed different depths for affine witnesses, decoded retained witnesses and fresh mesh queries. The next implementation supports another coupled step from the previously accepted cumulative controls, recalculating nearest triangles, barycentric points and normals on the current poses.

`scene_pair_relinearization.py` preserves the original motion policies while evaluating angular vectors and derivatives at nonzero controls. Derivative validation perturbs those current controls rather than returning to zero. An infeasible iterate is reported against the original angular caps; it never becomes the new reference motion.

The refresh validates complete sample populations and replaces witness geometry while retaining each time's original depth ceiling. Original surface rows remain alongside refreshed rows. Native edit budgets, contact-key protections, original motion bins and empirical proposal margins remain in force. The solver's trust radius applies to an increment; trial exports use the previous cumulative controls plus a scaled increment.

The driver queries both mesh directions at each changed sample. It may reuse original geometry only when both complete world-transform arrays exactly match the source at that sample. Refreshed witnesses are measured on continuous model poses; decoded exports are independently checked afterward. This is not evidence of continuous collision avoidance between samples.

## Run

```powershell
.venv/Scripts/python.exe scripts/study_scene_pair_relinearization.py reports/scene-pair-refined-reserve-completed-v1 reports/scene-pair-relinearized-v1
```

The input is the completed refined reserve study, including its bound selected trial and margins. A fresh output directory retains input identities, method snapshots, cumulative controls, refreshed samples, derivative proofs, linearization, solver result and all decoded trial failures. No older result is overwritten.

Every decoded trial checks original positional and angular motion limits, native edit budget, frozen keys, protected poses, original surface bounds and refreshed planes. A preliminary pass still requires fresh full-timeline decoded geometry, independent replay and engine validation before publication. The driver cannot publish or confer quality approval.

## Validation and current state

Twenty-five focused tests pass across relinearization, angular constraints and scene problems. They cover unequal actor control counts, nonzero-pose angular derivatives, original cap preservation, retention of previous surface constraints and rejection of changed, duplicate, rejected or malformed starting trials. The real-character run has started; numerical and decoded outcomes remain pending. All release capabilities remain unapproved.

## Independent continuation replay

After the worker completes, run:

```powershell
.venv/Scripts/python.exe scripts/verify_scene_pair_continuation.py reports/scene-pair-relinearized-v1 reports/scene-pair-relinearized-replay-v1
```

The evidence loader verifies the completed request, solver, matrix, refreshed sample index and files, input bindings, implementation snapshots, trial records and actual clip hashes. It also checks that each trial uses `previous cumulative controls + fraction * increment`, with distinct finite fractions and matching ordered actors. Failed animation trials remain valid evidence to replay; they are not converted into passing trials.

The replay reconstructs every attempted GLB and checks the saved preservation, native edit and retained-surface reports. It independently counts every joint's positional rate stencils in the original bins and uses scalar quaternion composition for angular rates. It recomputes the preliminary classification and fails if it differs from the recorded result. Even a preliminary pass still requires the full decoded mesh and engine checks described above.

Thirty-two focused tests pass across continuation evidence binding, existing real-GLB replay and scalar angular replay. The new continuation replay command has not yet run on the real study because that study is still refreshing geometry. This testing does not establish a passing continuation animation. The preceding implementation commit `4dc0dee` passed hosted Windows/Linux checks.

The continuation replay now also has a native-GLB integration fixture. Two actors use refined curves, nonzero starting controls and a nonzero increment; the actual replay reconstructs both encoded exports, checks all 2,872 positional observations and independently replays angular rates. The deliberately failing trial retains its failures and cannot become a preliminary pass or publication approval. Prepared-input loading is isolated with a fixture and skin points are synthetic, so this is not a real-character collision audit. The complete focused suite passes 33 tests in the development runtime. The minimal CI environment passes 17 evidence tests and skips the one integration fixture requiring optional Trimesh. Commit `1df39b4` passed hosted Windows/Linux checks. The real-character producer and its subsequent replay remain pending.

## Previous-correction identity and full validation

Replay now additionally binds the parent's completed result and selected trial, requiring the starting cumulative controls to exactly match that accepted correction. The native-GLB fixture exercises this check too. It prevents a self-consistent continuation record from silently starting at another pose curve.

`audit_scene_pair_continuation.py` accepts a completed study, its independent replay, a fresh output directory and `--trial INDEX`. Only an index passing both recorded and independently recomputed preliminary checks is eligible. It reconstructs the exact clips, runs native Godot import, then queries both complete decoded meshes across the unchanged local sample clock. It retains the original per-time depth caps and floor checks. Local acceptance requires at least one micrometre of peak improvement **over the selected previous correction**, whose full geometry file and clock are hash-checked; beating only the raw source is insufficient.

This audit remains separate from publication and release approval. The live study has not yet produced a candidate for it. Thirty-four focused evidence/geometry tests pass in the minimal environment, with one optional native-GLB integration skip; all 23 evidence tests, including that integration, pass in the development environment. Tests cover parent identity, prior-correction regression, original depth/floor ceilings, missing replay bindings and false preliminary-pass claims. The actual full decoded geometry and engine command remain unexecuted pending an eligible candidate.

## Windows write failure and recovered result

The first refresh stopped with `PermissionError: WinError 5` while atomically replacing `progress.json`. Its process exited with code 1 after saving 121 sample files. The old request, method snapshots, samples, progress file and pending temporary JSON remain unchanged; a separate failure observation records the terminal exit.

`strep.save` now retries only Windows access/sharing/lock denial codes 5, 32 and 33, for at most six replacement attempts and 1.55 seconds of total backoff. The previous valid JSON remains visible until replacement succeeds. Other errors fail immediately; permanent denial remains an error and retains the pending JSON. This does not make multiple writers to the same destination safe.

The worker accepts `--reuse-current` only into a fresh output. Recovery binds the same parent, cumulative controls and source inputs; verifies the previous snapshots and unchanged geometry extraction block; and independently reconstructs saved surface witness positions, triangle membership, normals and signed gaps. The contiguous recovered sample population is explicitly recorded. This is verified reuse of recorded signed-distance results, not a second independent signed-distance query of the recovered population.

```powershell
.venv/Scripts/python.exe scripts/study_scene_pair_relinearization.py reports/scene-pair-refined-reserve-completed-v1 reports/scene-pair-relinearized-v2 --reuse-current reports/scene-pair-relinearized-v1
```

The recovered worker completed all 148 times: 121 saved samples recovered, 21 source-identical times reused in total, and 36 new directional queries. Its 8,557 surface rows and 35,778 norm rows produced an `AlmostSolved` incremental proposal that passes the explicit numerical hard checks. Predicted peak decreases from 22.522268 to 22.333486 mm; these are local-model predictions, not a decoded mesh result.

The full increment fails four positional observations, three angular observations and retained/refreshed surface limits after export. Fractions 0.5, 0.25, 0.125 and 0.0625 each have zero decoded positional/angular failures and pass the original surface and refreshed-plane checks. Every attempted export is retained. Independent continuation replay and fresh full decoded geometry remain required before selecting a local correction; no animation has been approved by this study yet.

Twenty-seven focused retry/recovery/relinearization tests pass. The complete minimal source-check suite passes **465 tests with five optional skips**. This includes transient and permanent write denials, preserved previous JSON, changed source/control/clock rejection, saved-witness reconstruction and unchanged extraction semantics. No active worker source was modified.

The independent real-character replay has now completed: ten exact GLB reconstructions and 225,610 positional observations, with matching scalar angular results and all five original classifications preserved. Trial 1 (half the increment) is undergoing the fresh decoded geometry audit in `reports/scene-pair-relinearized-geometry-v2`. Godot has already checked four clips / 444 frames / 77 bones per clip; maximum position error is 5.366925e-7 m and maximum basis-element error is 6.851267e-7. Full-mesh depth, floor regression and improvement over the previous correction remain pending. No new Studio publication or release approval follows the engine result alone.

## Packaging an audited continuation

`assemble_scene_pair_continuation.py` prepares a completed, locally accepted continuation for the standard Studio replay/publication path. It requires the completed geometry result, corresponding independent replay, exact clip identities and reconciled full-sample geometry. A failed or unfinished audit cannot produce a completed package. A byte-identical prepared-request alias can be supplied with `--prepared` for a separate comparison that preserves existing history.

The normal replay matrix remains the parent's original zero-control matrix, used to check source skin witnesses. The actual nonzero tangent matrix is copied separately to `proposal-linearization.npz` with a bound hash. The saved solver remains an increment from the explicitly recorded cumulative base; exported trial controls are never rebased. The package retains all attempts and marks preliminarily passing alternatives without a full audit as `full_geometry_not_evaluated`. Even the selected local improvement retains `quality_approved: false`.

Thirty-six focused assembly/geometry tests pass, including exact artifact copying, separate matrix identities, cumulative-control preservation and rejection of incomplete, rejected, changed or inconsistent audit evidence. Artifact fixtures isolate the already separately tested replay gate; these tests do not replace running the full real-character package and standard Studio replay after the live audit finishes. The preceding recovery commit `12fd301` passed hosted Windows/Linux checks.
