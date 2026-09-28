# Running pace controls — v1

Completed 2026-09-25. Viewer: http://127.0.0.1:8767/reports/pace-controls-v1/viewer.html

Uniform asset retiming adds 2.4, 3.0 and 3.6 m/s to the screened arm/lean styles. Speed and cadence move together; every pose key and stride length is preserved. This is a deterministic authoring control, not new model inference or an independently adjustable cadence control.

## Results

48 existing periodic-control takes (arms 10/20/30/45 degrees, lean 0/10/20 degrees, seeds 11/22/55/101) produce 144 exports. All four seeds were already observed before this study.

| Speed | Passes | Review flags |
| --- | --- | --- |
| 2.4 m/s | 48/48 | None |
| 3.0 m/s | 48/48 | None |
| 3.6 m/s | 24/48 | Seeds 11 and 22, all 12 styles: root velocity seam |

The 3.6 m/s root-velocity gaps are 0.170 and 0.177 m/s for seeds 11 and 22, exceeding the unchanged 0.15 m/s threshold. Faster timing amplifies inherited velocity discontinuities. Failures remain accessible and explicitly flagged in the viewer, recipes and packs. Passing these provisional engineering checks does not establish realism.

Across all exports, measured cadence ranges from 126.6 to 229.3 steps/min. Stride length differs from the original by less than 5e-16 m. Requested forward speed is verified within 1e-5 m/s from decoded output timing and travel. All GLB pose accessors are exactly unchanged.

Foot geometry uses the actual SOMA mesh and all eight skin influences. The contact proxy selects foot-dominated vertices with more than 99% combined foot/toe weights, within 5 mm of the lowest foot surface and 3 cm of the floor. A vertex must persist in that patch across adjacent predicted-contact frames. Its horizontal speed is measured with cycle displacement at the wrap. Sliding p95 spans 2.04–4.85 cm/s; maximum penetration spans 2.33–4.65 mm. All pass the provisional 5 cm/s sliding, 2 cm/s regression and 1 cm penetration thresholds. Rolling feet, sample weighting and incorrect model contact labels can bias this measure; there are no independent stance annotations or full-body/object collision checks.

## Outputs

Every take has a four-cycle GLB with a terminal pose, BVH, NPZ, timing JSON, root-motion JSON, predicted-contact interval JSON, recipe, evidence and a ZIP with the mesh license. NPZ must be consumed with its timing sidecar; it no longer implies 30 fps. BVH Frame Time retains twelve decimal places. Root motion is the SOMA Hips world transform in meters, Y up, +Z forward, with xyzw quaternions; target-engine ground-root extraction remains unspecified. Contact intervals are half-open seconds, aligned to frame segments, and mark clipping at the start/end. They are predictions, not independently confirmed foot strikes.

The viewer shows original and chosen pace against the same clock, holding the shorter clip's last pose. Preview speed affects only viewing. Recipes include quality flags and leave capability mapping null. It uses the actual grey SOMA body and preserves the earlier final-frame visibility fix.

## Validation

- 144 GLBs: zero validator errors or warnings (`export-validation.json`).
- 144 ZIPs: integrity, every member hash, license and root/contact timelines verified (`pack-validation.json`).
- GLB output pose keys equal source keys; original source hashes verified.
- Every BVH reimport matches source joints within 1.56e-6 m; timing differs by less than 1e-5 s.
- All 52 project tests pass (`python -m pytest tests -q`), with four upstream Torch deprecation warnings. An initial unscoped pytest invocation collected historical snapshots and vendor tests and failed collection; using the project test directory avoids those unrelated copies.
- Viewer JavaScript parses; browser checks cover pace/style selection, visible failure warnings, recipe export, playback, and clicking the final-frame character without disappearance.

## Reproduce

Run from the project root using the existing environment and preserved `reports/periodic-controls-v1` sources:

```powershell
.venv\Scripts\python.exe scripts/run_pace_controls.py --output reports/pace-controls-repeat
.venv\Scripts\python.exe scripts/build_pace_viewer.py --output reports/pace-controls-repeat
node scripts/validate_pace_exports.mjs reports/pace-controls-repeat
.venv\Scripts\python.exe -m pytest tests -q
```

The runner refuses to overwrite an output directory and records implementation hashes before export. See `benchmarks/pace-controls-v1.json` for the frozen protocol and `reports/pace-controls-v1/summary.json` for all measurements.

## Next milestone

Add acceleration/deceleration and turning, evaluate transition continuity and foot placement, and validate a selected engine's root-motion convention. Independent cadence at fixed speed needs stride and foot-placement changes. Only then calibrate game-stat mappings against measured movement and human review. No stamina, strength, agility, naturalness, dynamic balance or engine-import validation is claimed here.
