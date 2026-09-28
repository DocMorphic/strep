# Wider running styles with periodic upper-body correction

The 45-degree arm range now passes the existing motion screens at torso angles 0, 10 and 20 degrees on seeds 11, 22, 55 and a newly generated seed 101. The updated viewer provides six arm ranges, four takes and a before-smoothing comparison. Ranges 60/70 remain experimental because some takes still fail. No quality threshold was relaxed.

Viewer: http://127.0.0.1:8767/reports/periodic-controls-v1/viewer.html

## Method and evaluation

Wider swings amplify an inherited upper-body boundary discontinuity. The editor applies two circular rotation averages with weights 1/4, 1/2, 1/4 to the Spine1 subtree in world space, projecting each result to a proper rotation. It reconstructs local rotations, then solves torso lean and arm range. The root, legs and contact labels remain unchanged. Arm ranges below 45 use the identical v1 algorithm.

Development used previously observed seeds 11/22/55. The algorithm, targets, thresholds and fresh seed 101 were frozen before generating the new take. Test collection subsequently caught one missing dictionary-closing brace in diagnostic code; that syntax repair was recorded before held-out editor evaluation, with original and amended freeze records retained. The filter and target-fitting mathematics did not change. The measurement runner was recorded before evaluating the new take. This is one held-out seed, not broad generalization evidence.

The new raw take used the unchanged checkpoint and byte-identical cached neutral-prompt embedding. Generation took approximately eight seconds. Its raw loop needed cleanup; the existing loop/stance pipeline produced an accepted source. Both raw and corrected outputs remain in `holdout/`.

## Results

Across 18 target pairs × four seeds:

- V1 passes 51/72 takes; the periodic editor passes 60/72. Nine take failures become passes; no previously passing take becomes a failure.
- Twelve target pairs pass all four seeds: arms 10/20/30/45, each with lean 0/10/20.
- At 45° arms / 20° lean, the old failing seed 55 improves from 21.29 to 19.66 mm next-pose prediction RMS against the unchanged 20 mm screen. The new seed improves from 19.07 to 17.90 mm. These small numerical margins do not certify visual polish.
- Every target is measured after filtering and composition. Every edited result repeats exactly. Root/lower-body arrays and contact labels remain unchanged.
- The frozen whole-body cyclic peak-speed/acceleration regression screen passes. A separate post-hoc upper-body audit examines every joint across the whole cycle: maximum per-joint peak ratios are 1.000016 for speed and 1.000074 for acceleration, including float/export noise. This supplemental audit is separate from the frozen release rule; it is not a force or dynamics simulation.
- All 148 GLBs (72 edited, 72 previous-editor comparisons, four neutral) validate with zero errors and warnings. GLB and BVH joint positions are checked after export.
- All 44 repository tests pass; four upstream Torch deprecation warnings remain.

The UI exposes experimental variants for inspection but disables screened recipes for any pair failing a tested seed. Recipes record filter application order and exact source hashes. Agility/strength/stamina mapping, human naturalness, collisions, surface contacts and engine import remain unvalidated.

## Reproduction and artifacts

The protocol is `benchmarks/periodic-controls-v1.json`. The report directory contains `summary.json`, both freeze records, `evaluation-freeze.json`, `export-validation.json`, `upper-body-audit.json`, the new take's provenance/logs and every per-take export/evidence record. Historical studies are preserved.

On this prepared machine, reproduce into a fresh folder directly under `reports/`:

```powershell
.venv\Scripts\python.exe scripts/reproduce_periodic_controls.py --output reports/periodic-controls-repeat
.venv\Scripts\python.exe -m pytest tests -q
```

Replaying seed 101 is a reproduction, not another unseen evaluation. Next useful work is varied running speed and cadence with contact checks, then acceleration/turning tasks before proposing a game-stat mapping. The remaining 60/70-degree failures and naturalness review should stay visible.
