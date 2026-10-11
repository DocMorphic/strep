# Source and transferred whole-mesh floor comparison

`scripts/rig_floor_comparison.py` evaluates two animated rigged GLBs at an explicit
shared clock and horizontal plane. It checks every mesh vertex and records the
deepest vertex, position and skin influences. It preserves both clips. The tool
accepts arbitrary clip pairs; the seven development cases below are a study
population, not a motion whitelist.

Twenty generated-fixture checks pass, including known plane crossings,
intermediate samples, mesh-node skin semantics, witnesses, changed floor height,
invalid clocks and unsigned-clock ordering. The completed test resource trace
replays 19 observations. The earlier 19-test method snapshot remains retained.

The actual study uses unchanged SOMA preview GLBs and independently replayed
Kenney transfers for seven seed-77 development motions. All 1,020 original 30 FPS
keys are sampled. Source geometry has 18,056 vertices; target geometry has 1,029.
The study evaluates 18,417,120 source and 1,049,580 target vertex positions.
The floor is explicitly Y=0 and the study tolerance is 5 mm. These assumptions
are not inferred from a real scene or promoted to release calibration gates.
All target peak depths match the earlier transferred-clip diagnostics within
1e-12 m. The production resource trace replays 39 observations.

| Motion | Source peak depth (mm) | Target peak depth (mm) | Source failed keys | Target failed keys |
| --- | ---: | ---: | ---: | ---: |
| Jump/land | 18.839 | 0 | 113 / 120 | 0 / 120 |
| Crawl | 89.508 | 263.015 | 120 / 120 | 120 / 120 |
| Dance | 14.428 | 0 | 100 / 150 | 0 / 150 |
| Wave | 11.617 | 0 | 120 / 120 | 0 / 120 |
| Kick | 8.867 | 49.728 | 36 / 120 | 14 / 120 |
| Get-up | 146.983 | 662.041 | 180 / 180 | 105 / 180 |
| Run/roll/stand | 70.498 | 978.276 | 47 / 210 | 27 / 210 |

All seven source meshes cross this declared floor beyond tolerance. Four target
motions have larger peak depth than their source. Across matched keys, both fail
at 244 times, source only at 572, target only at 22, and neither at 182.
Passing the target floor screen does not establish planted feet or motion quality.

The deepest crawl vertices are influenced by hand joints. The deepest source
get-up/run-roll vertices are on chest/shoulder regions, while target peaks are on
the head. Kick peaks are on a source toe and target foot. Source and target peak
times differ; maximum depths are not paired causal deltas. Differing body shapes
and the transfer profile also affect the comparison. The generation record lists
postprocessing as disabled; this does not by itself prove the origin of a defect.

No causal explanation, support intent, dynamics, action correctness, source FK
independence, engine playback, continuous-time clearance or human quality follows.
Clips and failed conditions remain unchanged. This is reused development data,
not held-out release evidence. Local records live under
`reports/kenney-source-target-floor-v1`; payloads are excluded from public Git.

Next, inspect reference alignment and body proportions, then define explicit
hand/knee/body support targets for the affected actions. Fit root and joint paths
under declared edit bounds and replay whole-body clearance alongside support,
transition and motion-preservation checks. A foot-only fix or constant lift does
not address the measured hand/head failures. See the preceding
[rig adaptation and seven-motion transfer](rig-scale-adaptation-v1.md).

For an explicit JSON array of times in seconds:

```powershell
python scripts/rig_floor_comparison.py source.glb target.glb --clock times.json --floor-y 0 --tolerance 0.005 --output reports/floor-comparison.json
```

The selected clips must use the supported rigid GLB representation; the tool
rejects clocks beyond either clip rather than extrapolating. The CLI uses the
shared local worker lock. Run through the guarded job workflow for resource
admission and archived resource evidence.

The [seven-action native export and encoding audit](kenney-native-export-v1.md) now carries these development clips through exact saved engine resources and game packaging, retaining floor, speed and skin-comparison failures. It also records the completed real correction/editor/export checks; successful checks do not approve these motions.
