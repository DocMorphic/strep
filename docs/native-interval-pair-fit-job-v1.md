# Reusable paired native contact/surface fitting

`scripts/native_interval_pair_fit_job.py` turns the source-zero paired fitting
experiment into a recipe-driven offline command. It uses supplied native rigs,
contacts, geometry and explicit edit permissions. It does not generate prompts,
select an animation or grant motion-quality approval. It is a backend component;
Studio integration and full release validation remain pending.

Run through an owned resource-guarded worker in the pinned CPU environment:

```text
python scripts/native_interval_pair_fit_job.py recipe.json fresh-output
```

The recipe uses schema `strep-native-interval-pair-fit-v1` and contains:

- `contacts` and `geometry`: each a relative or absolute `path` and exact
  lowercase `sha256` for an original source declaration.
- `actors`: exactly the two original actor IDs. Each has pinned `request` and
  zero `controls` files, plus a contiguous list of existing `active_keys`.
- `surface_samples`: sorted unique indices in the original geometry clock.
  Surface derivatives must use exact existing quaternion keys.
- `surface_seed`: an explicit integer seed for source mesh queries. The job
  saves the before/after query states and restores the caller's generator state.
- `trust`, `difference_step`, `contact_reserve_m` and `maximum_nonzeros`:
  explicit bounded proposal settings. The complete combined sparse model must
  fit its budget; no rows or columns are truncated.

Source hashes, actor IDs and zero seeds are validated before fitting. Output
must be fresh and separate from immutable input results. Actor IDs cannot
escape the output directory. Source rigs, poses, original rate caps, root and
boundary contracts remain bound through the existing interval model. New edit
permissions must be declared in the actor requests; they are not inferred from
an action name.

All original native and floor-protection rows remain hard. The contact reserve
tightens only authored **position** norms; relative-speed norms retain their
own units and caps. Fixed surface guides are proposal objectives. If no source
surface witnesses exist, the job runs a contact-only proposal and does not
infer geometry clearance.

The job saves its source arrays, layouts, original caps/scales, complete affine
system/Jacobian, surface rows, query states, solver output and implementation
snapshot. A returned solver direction is saved **before** the full hard-row
postcheck, so a rejected iterate remains diagnosable. Only a passing affine
proposal is exported. Actual coupled contacts are then measured on the export;
full decoded native/floor/mesh validation remains a separate required stage.
Every output keeps `original_selected=true` and quality/release approval false.

Fifteen source tests exercise hash and zero-epoch rejection, actor-path safety,
bounded settings, contact row units, complete original native-cap retention,
unchanged source files, query-generator restoration, rejection of a forced
infeasible iterate even with a `Solved` label, and a forced feasible export
remaining unselected pending independent validation. Solver injection in the
last two cases tests the caller's gate, not numerical solver capability; the
separate full job case uses the actual solver.

All 15 pass locally in 73.06 seconds. The guarded run completes in 89.375
seconds including admission, peaks at 155,557,888 process-tree bytes, and
independently replays all 90 recorded resource observations. The guard stays at
512 MiB for these small fixtures, plus the unchanged 600-MiB free-memory floor.
Larger paired matrix studies retain the 1-GiB profile. These source tests do not
establish animation quality, engine playback, held-out coverage or human review.

The next development case adds explicitly selected finger controls to the
existing high-five source. The source inspection finds all 24 finger joints per
actor have compatible LINEAR tracks on the original wrist clock. Complete world
rate caps and scales replay exactly against the original saved baseline at the
same uniform clock and bins. Local finger motion and world-joint motion are
measured separately; local near-static tracks do not imply zero world-rate
headroom. No source bounds or model weights are changed by this inspection.
