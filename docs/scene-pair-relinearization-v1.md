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
