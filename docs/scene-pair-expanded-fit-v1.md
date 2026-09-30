# Expanded edit window: no accepted export

Follow-up: [export rounding diagnosis and proposal margins](scene-pair-export-reserve-v1.md) explain these failed attempts and describe a new full-step candidate under validation. The original five failed outputs remain unchanged.

The earlier edit window removes the demonstrated fixed-collision obstruction, but does not produce an accepted correction. All five exported fractions fail both positional and angular motion screens. No candidate replaces the current Studio comparison, and no release capability is approved.

## Reproducible experiment

The prepared request retains the same source actors, placements, selected joints, 5-degree edit budget and protected contact at 2.091722595 seconds. Its window is 1.408333333 to 2.591722595 seconds, with five knots and 72 controls. This changes the motion-cap population; results are not a matched comparison against the narrower request.

Run with the locally prepared, licensed inputs:

```powershell
.venv\Scripts\python.exe scripts/study_scene_pair_fit.py reports/paired-edit-jobs/expanded-window-v1 reports/scene-pair-expanded-fit-v1 --geometry-donor reports/scene-pair-fit-v2 --angular
```

The output must be fresh. This completed output is retained locally and must not be overwritten. The public repository contains the implementation and methodology, not the licensed inputs or generated clips.

Source geometry contains 148 times: 126 exact observations reused and 22 newly queried. Reuse requires identical actor bytes, placement, timestamp, extraction function and dependency snapshots, with verified input and sample hashes. Sample indices alone are remapped. Raw donor and fresh rows remain separate, with per-row provenance. Neither candidate geometry nor constraints are reused.

Across the full population, 21 samples are fixed and none fails the 5 mm screen. This rules out the earlier obstruction, not other feasibility limits.

## Results

The solver reports Solved after 45 iterations and 18.39 seconds. It includes 4,287 surface rows and 32,271 solver norm rows, passes its affine hard checks, and predicts a peak decrease from 22.568796 to 22.554817 mm. This is a prediction, not measured candidate geometry. The saved linearization has 28,752 norm rows before the solver adds its additional cones.

| Export fraction | Positional-rate failures | Angular-rate exceedances |
| --- | ---: | ---: |
| 1 | 2 | 7 |
| 1/2 | 3 | 3 |
| 1/4 | 1 | 4 |
| 1/8 | 3 | 5 |
| 1/16 | 6 | 2 |

Counts combine both actors. The angular checks compare all joints in the actual exported motion against original span maxima, using separate 1e-5 rad/s and rad/s² tolerances. Positional checks retain their existing tolerance. None passes both guards, so the runner correctly skips candidate full-mesh queries and selects no output. Smaller fractions do not monotonically improve the exported checks. These failures do not establish perceptual unnaturalness, and no tolerance has been relaxed to admit a result.

The generic study runner now supports optional angular constraints and exported angular checks. Production jobs retain their previous default; this experiment does not claim an independently replayed angular publication gate. Before publishing any future candidate, that gate needs independent validation.

Local evidence is preserved under `reports/scene-pair-expanded-fit-v1`, including request and method hashes, raw and merged source geometry, reuse provenance, solver output, feasibility audit, derivative proof and all five export reviews. Twelve source-reuse tests cover identity, exact timing, provenance, remapping and tampered evidence; existing runner and angular-constraint tests also pass. The next diagnostic should distinguish serialization and nonlinear rate changes from the affine prediction before another expensive geometry pass. No held-out action or human rating was used.
