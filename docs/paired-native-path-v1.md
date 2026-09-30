# Paired paths on native keyframes

The earlier time-indexed guide continued requesting wrist offsets after the
last editable key's influence had ended. `--native-clock` now plans on the
actual shared arm-key clock, with adjacent frozen keys as exact zero-control
endpoints. The authored window and protected contact stay unchanged.

`native_waypoint_clock.py` finds the contiguous editable support containing the
requested peak. It respects protected spans that split an edit window, rejects
missing support, and requires synchronized clocks across both three-joint arm
chains. Asynchronous arm clocks are explicitly unsupported by this experimental
planner; it does not silently resample them. The evidence loader independently
reconstructs the clock from the bound source clips and guards before baking.

The completed search uses nine native times from 1.4402683973312378 to
1.8411632776260376 seconds within the unchanged 1.408333-to-1.875-second window.
All six axis routes are connected. Xplus remains the lowest-cost route with
cost 9.069278. Its maximum guide rates are 0.798216 m/s and 299.330872 degrees/s
per swivel, within the unchanged 0.8 m/s and 300 degrees/s guide caps. Those
caps do not bound actual character joint motion.

## Decoded motion

| Metric | Previous path | Native-clock path |
|---|---:|---:|
| Actor A maximum sampled wrist-guide error | 22.857143 mm | 1.096393 mm |
| Actor B maximum sampled wrist-guide error | 22.857143 mm | 1.366099 mm |
| Actor A positional failures | 301 | 309 |
| Actor B positional failures | 194 | 172 |
| Actor A angular speed / acceleration failures | 64 / 39 | 64 / 39 |
| Actor B angular speed / acceleration failures | 69 / 38 | 61 / 39 |

Native-key wrist targets reconstruct within 3.291237e-8 m for A and
2.507310e-8 m for B in a separate decoded diagnostic. Remaining sampled target
error occurs between keys. Native clocks and frozen quaternion values compare
exactly, and protected/outside-window world-pose discrepancy is zero. Maximum
native rotation edits are 16.934896 and 17.029541 degrees, under the explicitly
declared experimental 45-degree budget.

The original-relative motion checks still fail. The largest measured positional
acceleration increases occur at the return boundary near 1.841667 seconds:
forearm acceleration is 117.258033 m/s^2 versus a source-bin cap of 6.866606 for
A, and 98.107199 versus 9.119739 for B. This identifies the next defect: the
selected path stops too abruptly. Matching wrist targets is not sufficient to
claim natural or acceptable motion. The next search must account for decoded
joint velocities and acceleration at transitions, including the frozen poses
outside the guide, rather than merely bounding guide-parameter speed.

Godot imports four source/candidate clips, verifying 444 sampled actor-frames
with 77 bones. Maximum position discrepancy is 5.366924e-7 m and basis-element
discrepancy is 6.851266e-7. Engine interoperability does not approve motion quality.

## Completed geometry audit

The full 148-time audit preserves the preceding path's collision result:
zero measured vertex penetration throughout the edited window, 15 remaining
failures in the untouched later cluster, and a full-clock peak of 21.433380 mm.
All 22 original first-cluster failures clear, with no introduced failing samples.
The audit performs 96 fresh directional mesh queries and reuses 100 samples
only after exact equality of both decoded actor world transforms and verified
geometry bindings. Maximum floor increase is zero.

These are sampled vertex-depth results, not a continuous-time or triangle-only
collision certificate. The rate failures prevent acceptance despite the much
smaller wrist-target errors. Both study workers are terminal, and no Studio
replacement or release approval follows.

| Temporal artifact | SHA-256 |
|---|---|
| Request | `332b9aa5f6ce72e9b2360d8f1ceda6c1ad744bc76f1d09778ce951bb1572312e` |
| Decoded tracks/rates | `31a463d22300598406e1e8870af30ede6e2fc46e6d4243e2679cd8c50f6bd9b0` |
| Local-clock geometry | `f567b10e4e68699dbd1ecdd1859c988126c64980973c9b02275517f641d6d53c` |
| Native engine verification | `14297f0a91c9230bbdfb335a172ecda80c7dbb33b8794b1d064d08999c7547f7` |

## Reproduction and tests

Local ignored character/evidence inputs and the existing runtime are required.
Preserve previous experiments and use fresh output directories.

```powershell
.venv/Scripts/python.exe -u scripts/plan_pair_waypoint_path.py reports/scene-pair-waypoint-path-motion-v1 reports/scene-pair-native-path-v1 --native-clock
.venv/Scripts/python.exe -u scripts/fit_pair_wrist_waypoint.py reports/scene-pair-wrist-waypoint-v1 reports/scene-pair-native-path-motion-v1 --path-plan reports/scene-pair-native-path-v1
```

The expanded focused suite passes 115 tests in development and minimal runtimes.
New checks cover native support boundaries, protected-span splitting, mismatched
clocks, no available support, independently reconstructed evidence clocks, and
actual GLB baking with exact frozen endpoints and retained shared samplers.

| Planner artifact | SHA-256 |
|---|---|
| Request | `a7496a164ac2bdd4679eb521d7fbda042127da26e180bb800ab9ddeb06a3ccc7` |
| Lattice | `be607899358ffc46c442905039776edeee02b98151c30ade2103af60b7cc4b94` |
| Routes | `fe490f8a1c0f409f5079980320027504df4fa4ce6dc713f96ca41d4d83f80ce7` |

See [the preceding time-indexed path](paired-waypoint-path-v1.md). No new model
or data was acquired and no training occurred. All 14 release capabilities
remain unapproved.
