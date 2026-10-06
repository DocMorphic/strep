# Source-bound edit influence and crossing diagnostics

`scripts/native_edit_crossing_diagnostics.py` explains which permitted tracks could affect existing actor-pair triangle crossing records. It independently re-queries the actual saved anchor at every geometry time. This is a read-only authoring diagnostic; it grants no collision or motion-quality approval.

## Run and interpret

Use the [pinned stored-pair job request](native-stored-pair-job-v1.md) with the actual anchor clips and controls to inspect:

```powershell
python scripts/native_edit_crossing_diagnostics.py --request path/to/job.json --output reports/my-new-diagnostics
```

The output directory must be fresh. The optional `--maximum-records` defaults to 400000 and accepts 1–1000000. Exceeding it retains a failed job and never returns a successful truncated report. Inputs and archived implementation bytes remain bound; clips, permissions and acceptance limits are unchanged.

The command includes every actor pair, loaded triangle and original geometry time. It decodes the actual anchor through the source-bound job contract and repeats triangle queries at the original surface tolerance. Each record retains its geometry identity, left/right eligible track indices and one of three classes:

| Class | Meaning |
| --- | --- |
| `both_potentially_editable` | At least one permitted track could affect each triangle. |
| `one_potentially_editable` | Only one triangle has possible edit influence. |
| `both_structurally_fixed` | Neither triangle can move through the current edit tracks at that time. |

Influence follows every positive skin slot through the complete parent hierarchy; it does not select a dominant bone or discard small weights. Native scalar interpolation support, protected keys, boundary permissions and possible acknowledged storage adjustments determine time support. A zero derivative at one pose is not treated as proof of immutability. Potential influence is an overestimate: joint pivots, contact constraints, rate limits and edit bounds can still prevent separation. Fixed records cannot be repaired by these tracks, but this diagnostic does not automatically change or widen permissions.

Saved results include all samples/records, aggregate kinds/classes, every triangle recurrence and per-track node/descendant/control/key/vertex metadata. The scope is actor-pair surface crossings only. It does not establish containment, object/plane or self-collision checks, continuous motion, physics, engine playback or human quality. Zero crossing records do not approve an asset.

## Retained fixture result

At the [latest repaired fixture anchor](offline-stored-pair-study-v1.md), all 30432 records across 1673 geometry times are `both_potentially_editable`; none is wholly fixed. There are 98 unique actor/triangle/kind identities. Each actor currently permits one node6 rotation, affecting 24 of 152 vertices through nodes6/7/8, with all290 native keys editable. Original native motion/contact checks still pass. Geometry still fails at approximately 5.100709 mm penetration, and this diagnostic does not alter that result.

A separate consumer imports no new diagnostic/job/model/proxy. It reconstructs all hierarchy paths and positive skin influences, checks every record/class/eligible track and recurrence, and matches the previous complete actual-clip geometry report exactly. The producer repeats the existing crossing algorithm; the predicate itself is not independently reimplemented. These are generated cube-skin development fixtures, not production humanoid realism or partner-action approval.

## Sampler regression and next authoring gap

An initial test finds that casting a NumPy Float64 sample time to Python float changes a Float32 endpoint comparison at a positive subnormal time. The native sampler depends on key1 while the diagnostic incorrectly reports only key0. That version, failing test and exit1 are retained. After the worker exits, preserving the incoming scalar type fixes the mismatch. Ten diagnostic tests and twenty-nine existing job/model tests pass: 39 tests, zero skips. Tests include actual exported fixed vertices, frozen partners/protected endpoints, Float32 interpolation support, every positive eighth influence, complete crossing classification, fresh outputs and resource-failure preservation. CI includes the new suite; hosted CI success is not claimed.

Preparing a separate generated-fixture node7 permission experiment exposes a real editing limitation: node7 is a skin joint but has no animation channel in either the source or original reference. The existing editor correctly requires an existing LINEAR channel and rejects that preparation. Its failed driver, archived implementation and pinned input bindings remain retained; no enlarged correction job or model ran.

The joint has a static TRS rotation stored at greater precision than Float32. A new editable curve therefore cannot assume pose-byte identity. Next implement explicit preparation of a separate clip variant with added static rotation channels, measure actual storage/pose drift, preserve all original animations, and retain the original reference and rate/contact/geometry limits when binding the new edit epoch. Do not silently rebaseline those limits or enlarge a user's submitted permissions. More articulation freedom is a separate declared experiment, not a repaired version of the old request. Broad action/rig/object/partner, engine and developer/animator review requirements remain open; all fourteen release evidence arrays remain empty.

## Local receipt identities

Large observations, assets, failures and generated studies remain ignored by Git:

- `diagnostics`: `dbaccf6db57fb470bc27fcb5c4ec920ac012f9ad07e33fa7c290042c3badaf10`
- `replay`: `114231439b3d29cc35d5e9f73a61ebb40618286b5c88ffb3f55a7d34c4c3dd3d`
- `sampling_regression`: `7303708022675c4b84b95d063340a79de7c36768f846714a6ea7b8d783273c6c`
- `missing_channel`: `12702f6d0e8e3d105475b34360d391c9a7293c76035f1a7eca1428f5546ae5ee`
- `anchor`: `0ea0d4c809f61616408d1a402a4449fa6748461381ef896547d3b7a94887dce3`
