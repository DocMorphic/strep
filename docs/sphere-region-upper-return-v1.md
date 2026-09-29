# Upper-body return correction

A bounded post-release smoothing pass removes the measured whole-clip acceleration regression in the [coupled angular fit](sphere-region-coupled-angular-v1.md), while preserving its contact, geometry, hand-speed and angular comparisons. This is development evidence for one authored sphere interaction, not general motion or release approval.

## Method

Only frames 127–139 and the local rotations of Spine1, Spine2, Chest, Neck1, Neck2 and Head are edited. Frames 126 and 140 are locked. The other 167 native frames remain byte-exact. All other physical parameters, including root, arms, fingers and legs, remain exact to the input.

Each selected rotation moves toward the mean of its two original neighbours in local rotation-log coordinates. The single simultaneous pass uses weight `0.25 * 16*t²*(1-t)²`, with `t=(frame-126)/14`. The taper vanishes with zero slope at both endpoints. The source parameters are independently replayed before edits; source hashes and implementation snapshots are retained. No model, Studio default, contact target, acceptance tolerance or original edit limit changes.

## Measured result

The independent decoder samples the exported GLB at integer and quarter frames.

| Check | Result |
| --- | --- |
| Distributed grasp | 245/245 samples pass |
| Full geometry and original edit limits | 717/717 samples pass |
| Arm angular comparisons | 88/88 pass |
| Both hand release-speed comparisons | Pass, unchanged from input |
| Peak joint speed | 1.364917 m/s, unchanged; original comparison 1.409751 |
| Peak joint acceleration | 40.041065 → 38.009302 m/s²; original comparison 38.516182 |
| Minimum sampled floor / sphere clearance | 2.001973 / 2.069914 mm |
| Maximum joint rotation edit | 38.564717 degrees |
| Godot playback fidelity | 180 frames, 77 bones, maximum position error 0.311 micrometres |

All four speed/acceleration comparisons against the original baseline and immediate input pass, with a declared numerical allowance of 1e-7. Forty-eight focused tests pass, including endpoint taper, constant angular rate through rotation wrap, and isolated rotation-spike reduction tests.

Local evidence is under `reports/sphere-region-upper-return-v1`, `reports/sphere-region-upper-return-v1-audit`, `reports/sphere-region-upper-return-boundaries-v1`, and `reports/sphere-region-upper-return-engine-v1`. Candidate GLB SHA-256: `aa650e4a9199ab356f54015b5b346bdca4da80db102aae9a690fb841bb69b5da`. Generated artifacts and licensed character payloads are excluded from the public repository.

## Limits and next work

The sampled checks do not establish continuous triangle collision, self-collision, anatomy, balance, forces, naturalness or animator cleanup time. Developer review remains pending. The original fixed-point grasp condition is still unsolved; this result uses the separately authored region condition. The reserved held-out study remains unused, and all 14 release capabilities remain unapproved.

Next integrate explicit region bindings into the scene-authoring workflow and replicate on additional development actions, objects and rigs. Do not automatically apply this sphere-specific correction as a general solution.

## Reproduction

An existing provisioned workspace with the preceding local studies and licensed dependencies is required. Use fresh output directories.

```powershell
.venv\Scripts\python.exe scripts/upper_body_return.py reports/sphere-region-coupled-angular-v1 reports/new-upper-return --strength .25
.venv\Scripts\python.exe scripts/audit_region_grasp_track.py reports/sphere-region-track-v2 reports/new-upper-audit --approach-patch reports/sphere-region-approach-v1 --floor-patch reports/sphere-region-floor-v1 --release-patch reports/sphere-region-release-v1 --spatial-patch reports/sphere-region-spatial-v1 --coupled-patch reports/sphere-region-coupled-angular-v1 --upper-body-patch reports/new-upper-return
.venv\Scripts\python.exe scripts/audit_region_boundary_rates.py reports/new-upper-audit reports/new-upper-boundaries
```
