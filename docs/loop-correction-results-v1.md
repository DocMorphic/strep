# Deterministic run-loop correction — 2026-09-24

The session goal is complete: one implementation evaluated all five run seeds, preserving raw motion, exporting NPZ/BVH, and producing before/after previews. **Two of five seeds (22 and 55) pass every applicable loop screen and the defined regression checks.** All five pass the loop screens alone; three remain flagged for materially worse foot sliding. This is not full realism acceptance.

The current study is `reports/loop-correction-v1-reviewed/`. Open its `comparison.html` directly or through the project server at <http://127.0.0.1:8767/reports/loop-correction-v1-reviewed/comparison.html>. The earlier `loop-correction-v1` directory is an exploratory result with a weaker regression comparison; retain it as history, not the final result.

## Results

Seam values below are next-pose prediction RMS over all joints, comparing the **same selected source interval** before and after correction. They are not comparisons against the entire four-second recording. Foot speed is horizontal p95 during inherited model-predicted contacts, not an independent stance annotation.

| Seed | Cycle frames | Raw → corrected seam, cm | Selected raw → corrected foot speed, cm/s | Outcome |
| --- | ---: | ---: | ---: | --- |
| 11 | 24 | 6.68 → 1.63 | 12.93 → 32.30 | Sliding regression |
| 22 | 23 | 4.20 → 1.24 | 8.99 → 9.15 | Loop + regression checks pass |
| 33 | 24 | 4.91 → 1.72 | 12.24 → 35.06 | Sliding regression |
| 44 | 22 | 4.44 → 1.97 | 30.95 → 29.78 | Regression against full raw clip |
| 55 | 23 | 5.15 → 1.35 | 17.01 → 18.35 | Loop + regression checks pass |

Seed 44 illustrates why the full recording is also checked: its full-raw contact-speed p95 is 18.31 cm/s. Selecting a worse source crop must not conceal a regression. Full-raw p95 values for seeds 11, 22, 33, and 55 are respectively 14.12, 9.92, 14.61, and 19.55 cm/s.

## Fixed criteria

The existing provisional loop gates were not relaxed: next-pose RMS ≤2 cm; next-local-rotation RMS ≤5°; root-velocity gap ≤0.15 m/s; next-root-yaw error ≤2°; forward trajectory heading p95 ≤3°. Missing measures fail acceptance.

For each contact-speed reference, the allowed p95 is `reference + max(0.03 m/s, 25% of reference)`. A candidate must satisfy the strictest of three limits: selected source with its original labels, selected source with the fixed union contact mask used for correction, and the full source recording. Ground-depth increase is limited to 1 mm. These are explicit engineering regression tolerances, not validated perceptual realism thresholds. The broader rubric's independent stance-speed target remains 5 cm/s and has not been independently assessed here.

## Implementation and failure analysis

`scripts/correct_loops.py` searches matching gait phases and evaluates 128 candidates per seed. It extracts 18–40-frame cycles, aligns their net horizontal travel to +Z, and crossfades rotations along their shortest arcs over 6 or 8 frames. Forward kinematics preserves the SOMA77 skeleton's bone lengths. Contact labels are inherited and conservatively unioned during blending. A constant vertical offset of 0.13–0.92 cm removes joint-floor penetration; this does not establish mesh clearance.

Both aligned root motion and constant forward speed are evaluated under the same selection rule. The passing seeds retain varying root speed and blend during intervals without predicted foot contact. The three flagged winners use constant forward speed, which changes foot velocity in world space even outside the crossfade. Outside-blend p95 reaches 32.64, 35.06, and 21.68 cm/s for seeds 11, 33, and 44. This diagnoses a root/stance inconsistency; no foot-locking inverse kinematics is applied. All candidates and their failures remain available in each seed's `candidates.json`.

## Validation and files

- All 17 unit tests passed, including periodic-cycle preservation, accumulated root displacement, shortest-arc rotation blending, and conservative contact masks.
- An independent complete rerun produced exactly equal corrected arrays, candidate metrics, and winner selections for every seed. `reproducibility.json` records this same-machine result and verifies each raw NPZ against its original generation-time hash.
- All five BVH files were imported back through the pinned upstream converter. Frame counts, 30 fps, and loop gates were preserved; maximum full-joint error was below 0.0000045 m. Raw-source FK agreement was also verified.
- The comparison viewer was inspected at repeat boundaries for both passing seeds, and restart/playback was checked. This developer inspection is not blind animator approval.

Each `seed-N/` contains `corrected.npz`, `corrected.bvh`, `report.json`, `candidates.json`, `export-validation.json`, and four-cycle inspection artifacts. BVH does not store contact labels. The NPZ and inspection sidecars retain their predicted provenance. When repeating a single cycle, add `cycle_displacement_m` from `report.json` to each repetition's root position; resetting the root to the first frame would create a teleport. The four-cycle NPZ demonstrates accumulation.

The source checkpoint and vendor code remain unchanged. This correction stage needs no model inference or network. Its raw inputs came from the documented experimental original-precision streamed encoder; full 8B resident encoder equivalence remains untested.

## Reproduce

From `C:\wassup\strep`, choose new output directories; correction refuses to overwrite an existing study.

```powershell
.venv\Scripts\python.exe scripts\correct_loops.py --output reports\loop-correction-new
.venv\Scripts\python.exe scripts\export_loop_study.py reports\loop-correction-new
.venv\Scripts\python.exe scripts\correct_loops.py --output reports\loop-correction-repeat
.venv\Scripts\python.exe scripts\verify_loop_reproduction.py reports\loop-correction-new reports\loop-correction-repeat
.venv\Scripts\python.exe -m pytest tests -q
```

Implementation, configuration, acceptance-rubric, source-motion, and vendor revision hashes are recorded with the study. Repeatability is established for this machine and environment, not across platforms.

## Next milestone

Add stance-aware foot correction and compare all five seeds again against these frozen results. Independent stance annotation and animator review must check whether measured improvements look natural. Retargeting to CesiumMan and a chosen engine remain separate acceptance stages. Run-to-roll correction, calibrated box/partner contact, mesh collision checks, held-out actions and rigs, and cleanup-time measurements remain unfinished. No training is justified by this loop study alone.
