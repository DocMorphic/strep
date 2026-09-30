# Moving-partner constraints across the high-five approach

The next correction now has a measured full-approach witness set and a tested model for moving both partner surfaces. This work **does not generate a new animation**. It prepares the coupled fit needed after the [guarded temporal candidate](paired-guarded-temporal-v1.md) improved motion but regressed penetration.

## Why the interval expands

The retained full-clip audit places the first pair's major partner failures in two groups: frames 65.5–69 and 72.5–74.5, dominated by left forearm and hand vertices. Restricting the next correction to the four recent regressions would leave the earlier group untouched. Floor failures also exist elsewhere and cannot be fixed by arm controls alone.

The new query uses the unchanged guarded candidate, seed 1301, and both original scene placements. It covers **57 quarter-frame times from 63 through 77**, including both approach collision groups, the fixed contact and the beginning of release. There are **114 directional queries**, each filtering all 18,056 source vertices before bounded signed-distance queries against the complete closed partner mesh.

**25 of 57 times fail the existing 5 mm screen.** Maximum measured penetration is **23.556264 mm at frame 66.75**. The older half-frame population did not include that time. The temporal correction changed only keys 74 and 76, so this earlier peak is an inherited defect, not a newly introduced edit. The largest floor depth in this interval is 5.004118 mm at its beginning; full-clip floor failures remain separately recorded.

## Surface witnesses that move with both actors

The completed extraction retains **3,045 witnesses**, at most 64 per direction and time. Selection takes the deepest points and then nearby outside points within a 5 mm band. Every record includes the source vertex, target triangle vertices, barycentric location, reference outward direction and signed gap. The complete query summaries retain the depth and failure counts independently of this bounded fitting subset.

The local gap is the source point minus a barycentric point on the moving partner triangle, projected onto the reference outward direction. Its Jacobian contains both actors' contributions. Treating the partner triangle as fixed would omit the second contribution and give a wrong correction when both characters move. Common translation of both actors must leave the gap unchanged.

These are local surface approximations: directions and barycentric bindings are frozen at the reference pair. They require refreshing after steps and an independent complete-skin audit of any exported candidate. They are not global collision certificates, and a selected subset cannot replace the full query.

## Approach controls and verified derivatives

`ApproachActor` uses the left shoulder, arm, forearm and hand for each actor. Three internal control knots at frames 66, 70 and 74, bounded by zero additional controls at keys 63 and 75, give **36 parameters per actor, 72 total**. The native edited keys would be 64–74. The retained contact key 75 and release correction at 76 stay fixed. Original-reference rotation vectors remain available so the forthcoming solver can enforce the same total edit budgets.

This module is a parameterization and derivative evaluator, **not an enforcing solver**. The next fit must impose rotation and motion limits and verify the resulting exported channels. At nominal frame 63, float32 glTF key timing can already enter a tiny fraction of the following edge; the stored boundary key itself is unchanged. Tests distinguish stored-key preservation from sampling on an ideal frame clock.

The skin evaluator carries all eight skin influences and bounds temporary allocations to 128 selected rows per batch. Its actual-mesh skin agreement is within 8.89e-16 m. Zero controls reproduce the current candidate's world transforms within 1.34e-15.

At frames **66 and 66.75**, three deep witnesses in each direction are checked on the real characters: **12 local directional derivative checks**. The assembled two-actor Jacobian is compared both with direct perturbation of the moving-triangle gap and with fresh signed-distance queries against the perturbed full partner mesh. Maximum discrepancy is 2.20e-10 for the plane calculation and 1.83e-10 for the signed-distance calculation, in metres per radian along the tested control directions. Both actors have nonzero contributions. These local checks do not prove derivatives are valid after a large step or a closest-feature change.

Twenty-seven focused model-free tests pass. Added cases cover common-translation invariance, both actor derivatives, invalid triangle bindings, contact/release key preservation, batched skin weighting and derivative evaluation across a batch boundary. The new tests join Windows/Linux CI. There are **zero new engine observations**, since this work produces no changed GLB.

## Evidence and next step

The completed extraction is `reports/paired-approach-witnesses-v1`. Actual-mesh derivative checks are `reports/paired-approach-derivatives-v2` at frame 66 and `paired-approach-derivatives-v3` at frame 66.75. Earlier checks remain preserved. All workers are terminal. Inputs, original geometry evidence, per-frame records and implementation snapshots are hash-bound. The current extraction runner additionally checks the audited adapter's identities; those bindings were verified against the retained run without repeating its expensive mesh queries.

Next assemble a joint proposal using these moving surfaces, native edit-vector limits and the measured motion caps. Preserve the current event and release, then validate all affected quarter frames and the complete exported clip. A local improvement must not hide the other approach group, create new collisions, or be represented as solving the full action while the floor failures remain. All fourteen release capabilities remain unapproved; no new model, motion or human-quality approval is claimed here.

```powershell
.venv\Scripts\python.exe scripts/build_guarded_pair_witnesses.py reports/<new-witnesses>
.venv\Scripts\python.exe scripts/verify_paired_approach_basis.py reports/<new-witnesses> reports/<new-derivative-review> --frame 66.75
.venv\Scripts\python.exe -m pytest tests/test_paired_surface_witness.py tests/test_paired_approach_basis.py tests/test_paired_guarded_temporal.py tests/test_paired_temporal_neighbor.py tests/test_paired_stage_rates.py tests/test_scene_joint_rates.py -q
```

Reproduction requires the retained licensed fixture and prior proof files. Use fresh output paths. Generated meshes, witness payloads, caches and motion assets remain excluded from the public repository.
