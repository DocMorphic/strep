# Hand-aware screening of paired approach routes

The prior forearm-based path score missed thumb collisions between the final two
native animation keys. This experiment audits all six completed routes from
`reports/scene-pair-full-approach-path-v1`, preserving that planner's original
Xplus optimum. It does not retrain the model or change protected contact poses.

## Method

`waypoint_path_evidence.load_path` now permits an explicitly named route for
auditing. It still verifies all artifact/input/snapshot bindings, independently
replays every route, and checks the original declared optimum before returning
an alternative. Tests reject a forged optimum, a changed other-route score and
an unknown route. The historical plan remains immutable.

`screen_pair_hand_routes.py` bakes both complete GLBs for every replayed route,
decodes the original uniform clock, and measures original-relative positional
and world-angular motion limits. Native clocks and frozen quaternion keys are
checked exactly. The geometric screen includes every vertex with any positive
skin weight on the wrist or its descendants: 2,933 vertices per actor, including
blended seams. Each hand is tested against the other actor's full closed,
consistently wound 18,056-vertex mesh. Deepest-vertex IDs map back to the full
source mesh.

The final native edge is [2.041610718, 2.091722488) seconds. Seven original
120 Hz samples fall inside it, from 2.041666667 through 2.091666667 seconds.
Six routes and two directional queries per sample give 84 mesh queries.
The depth tolerance stays 5 mm. Ranking uses hand peak depth, failing sample
count, original proxy cost, then route name; ranking is not acceptance.

The Xplus GLBs have the same SHA-256 digests as the preceding full-body audit,
and this partial screen reproduces its 21.203789 mm thumb-depth peak. The other
routes do not inherit the earlier Xplus route's whole-clock geometry or engine
evidence.

This is a final-edge, hand-source vertex test. It neither establishes clearance
of the rest of the body or timeline nor detects every triangle-only or
continuous-time intersection. Full decoded motion, full-body geometry and
engine checks on the same candidate remain necessary before publication.

## Reproduction

Local ignored source assets and bound prior studies are required. Use a fresh
output directory and keep the old evidence immutable.

```powershell
.venv/Scripts/python.exe -u scripts/screen_pair_hand_routes.py reports/scene-pair-full-approach-path-v1 reports/scene-pair-hand-routes-v1
```

The public source checks now install pinned Trimesh, Rtree and threadpoolctl
alongside NumPy/SciPy/pytest. The new surface tests use real closed-mesh distance
queries and verify blended skin selection, palette-to-node mapping, stable
source vertex IDs, closed-target rejection and malformed subsets. No checkpoint
or character payload is needed for those tests. The legacy full-pipeline
geometry comparison still imports Torch and remains outside this minimal suite.

Validation: 153 focused tests pass in both the development and minimal runtimes.
The complete declared public suite passes 613 Python tests plus all eight Node
editor test files locally, with offline Hugging Face/Transformers flags. Adding
Trimesh activated a previously skipped continuation reconstruction test; its
missing threadpoolctl dependency was added, and that test passes too. This
source coverage does not establish visual animation quality or engine import
of the new candidates.

See [the preceding full-approach study](paired-full-approach-v1.md).


## Completed comparison

| Route | Final-edge hand peak (mm) | Failing samples / 7 | Positional violations A / B |
|---|---:|---:|---:|
| Xminus | 19.929572 | 4 | 329 / 245 |
| Xplus | 21.203789 | 5 | 348 / 372 |
| Yminus | 20.828581 | 6 | 485 / 525 |
| Yplus | 21.324793 | 6 | 925 / 525 |
| Zminus | 8.490147 | 4 | 734 / 599 |
| Zplus | 20.629024 | 6 | 484 / 459 |

Every route also has angular speed and acceleration violations for both actors. None passes the hand screen; no motion is accepted for publication. Zminus is the best of these six at 8.490147 mm, but four sampled times still exceed 5 mm. It does not inherit the Xplus full-body result of five failures in 148 times.

The six routes are one forearm-proxy optimum per fixed axis, not an exhaustive hand-aware search. These failures do not prove the permitted control domain infeasible. Next put between-key hand geometry into candidate generation: search terminal-edge offsets and elbow angles beyond those six winners, retaining the native edit, guide-rate and original-relative motion bounds. Any promising route must then pass its own full-body/full-clock audit. Merely projecting toward the best still-colliding route is not a clearance method.

The worker completed successfully. Native clocks and frozen quaternion keys remain exact for all 12 GLBs. No engine audit, Studio replacement, human approval, training or new model/data acquisition occurred. All 14 release capabilities remain unapproved.

| Artifact | SHA-256 |
|---|---|
| Request | `26501c6f0dc0bbda73e6a16be2b105082ca34b36b184a6eefa7165e5c48ac936` |
| Route results | `af3c37bfc8095d714b5261d40bf3d56b0833dc686d183c8b217287f2138b2bc6` |
| Best hand route geometry (Zminus) | `4e660e8b3e3b543a23c1f01e1b40126dea0a7b215af6b071d1f482e1f6078a9c` |
