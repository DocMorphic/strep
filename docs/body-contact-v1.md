# Whole-body clearance experiment

2026-09-25. The next stage adds bounded pelvis-height and torso edits around the existing hand/foot correction. It substantially reduces floor intersections, but getting-up clips still lose some plausible support contacts. This is an experimental kinematic authoring pass, not a physics or balance solver.

Open http://127.0.0.1:8768/studio and choose a **Body clearance** collection. **Version** switches between Raw generation, Hands/feet baseline and Body candidate at the same frame. Each selection loads a separate GLB and points to its own exports. **Ground detail** brings the camera closer to low poses. The inspector reports root-height edits, sampled skin depth and contact regressions for the selected version.

## What changed

The previous pass left knees approximately 4–6 cm below the floor during crawling, and torso skin approximately 9–16 cm below it during getting up. A first simple pelvis-lift prototype cleared the knees but moved nearly straight arms beyond their reach, lifting the hands. That prototype is retained in `reports/body-contact-prototype.json` and is not shipped as the candidate.

The final method starts with the unchanged v1 hand/foot correction, then:

1. Skips the body pass exactly when the limb baseline's maximum skin penetration is at most 1 cm. Already-clear poses are not needlessly edited.
2. Infers continuous hand/foot anchoring weights from baseline skin height: full weight below 1.2 cm, smoothly fading to zero at 8 cm. Targets follow the original moving end-effector tracks; this preserves existing sliding rather than pretending to solve it.
3. Raises penetrating hand/foot targets towards 2 mm clearance. Uses whole-body vertices outside these endpoint regions to determine a temporally smoothed pelvis-height correction, capped at 22 cm.
4. Applies up to 20 degrees of world-space Spine1 compensation to keep arm sockets reachable while the pelvis rises. This compensation is limited by available torso clearance; lying torsos cannot simply rotate back through the floor.
5. Re-solves arms and legs to the weighted targets with fixed bone lengths and baseline wrist/ankle orientations. Runs five fixed clearance iterations. Unreachable targets remain recorded errors.

Root XZ, heading, frame count, timing and predicted foot-contact labels are preserved. Root Y and torso/limb rotations can change, and the exported root track contains those actual changes. The stale model-derived `smooth_root_pos` auxiliary array is omitted when the body pass runs; the core motion arrays remain available. Finger articulation receives only numerical rotation normalization. No solver settings depend on action names.

The implementation is an analytic IK and filtered-clearance heuristic. It does not enforce anatomical joint limits, solve self-collision, simulate forces, infer ground-truth hand/knee supports, or solve objects/partners. It does not lock a drifting support point to one fixed world position. Clearing skin from a plane is insufficient evidence of believable weight bearing.

## Research basis

[Kovar, Schreiner and Gleicher's Footskate Cleanup](https://research.cs.wisc.edu/graphics/Gallery/kovar.vol/Cleanup/) discusses root adjustment, near-straight-limb knee popping, and blending corrections across contact boundaries. Their method permits small leg-length changes. This experiment retains rigid bone lengths and reports reach failures instead; it is not a reproduction of that paper.

[Gleicher's comparison of constraint-based motion editing](https://graphics.cs.wisc.edu/Papers/2001/Gle01/) describes per-frame inverse kinematics plus filtering as one family of editing methods. The current implementation is a limited test of that family, with actual skin collision measurement and explicit regression gates. Existing [NVIDIA motion metrics](https://research.nvidia.com/labs/sil/projects/kimodo/docs/benchmark/metrics.html) remain useful for joint/foot diagnostics; this study adds skin and body-support measurements.

## Evaluation and honest failures

Development used only crawl, get-up and run/roll/stand seed 11. The frozen implementation was then evaluated on the remaining earlier clips, including seeds 22 and 55 and the existing shrug/balance examples. These were previously inspected in other studies, so they are regression cases rather than a blind dataset.

Seven new seed-77 takes were generated after `benchmarks/body-contact-v1-freeze.json`. They use the same exact verified text feature tensors, encoder revisions and unchanged Kimodo checkpoint, with new motion inference. Reuse provenance, full prompts, model settings and timing remain in `reports/action-jobs/body-holdout-seed77`. No model training, new dataset acquisition or paid service occurred.

Reserved-seed results demonstrate both progress and limits:

- Crawl: limb-baseline skin depth 6.11 cm becomes 0.90 mm at stored frames; halfway samples reach 0.98 mm. Root lift peaks at 6.31 cm. No current regression flags.
- Get-up: 14.70 cm becomes 0.79 mm, but torso, head, knee and elbow contact-patch gaps/sliding remain flagged. Root lift peaks at 14.90 cm. This is not a solved or accepted get-up animation.
- Run/roll/stand: 7.05 cm becomes zero at stored frames; halfway samples reach 1.29 mm. Root lift peaks at 7.25 cm. No current regression flags.

The reserved seed passes the current numerical screen on six of seven clips. All remain semantically unreviewed and have no animator approval or engine-import certification.

Each candidate is compared both with raw motion and with the limb-only baseline, so new regressions cannot be hidden behind an improvement over poor raw motion. The existing pose-change, added-speed, skin-depth and fixed hand/foot-patch gates are retained. Additional low/slow torso/head/knee/elbow patches are drawn from the limb baseline and tested for p95 gap growth over 2 cm or horizontal speed growth over 5 cm/s. Knee/elbow masks cover dominant-bone skin within 13 cm of the corresponding bind joint. These are conservative geometric candidates, not independently labeled support events; a flagged original patch may cease to be the actual contacting patch.

Floor tests cover every skin vertex and all eight weights at 30 fps keys and at halfway poses using shortest-rotation interpolation, giving 60 Hz sampling. Halfway measurements use reconstructed source poses, not an independent continuous collision detector. Root midpoint interpolation is linear. GLB keyframes are independently decoded and checked against the candidate; skin-depth errors are recorded. Clearance between all samples is not guaranteed.

Independent action ratings, manual correction time, physical stability, final game-engine import and external-rig transfer remain unmeasured. Failed candidates are preserved and visibly flagged. Automatic application to new user requests remains disabled.

## Reproduce and verify

From `C:/wassup/strep`, use fresh output folders:

```powershell
.venv\Scripts\python.exe scripts/run_body_contact.py reports/action-coverage-v1 reports/action-jobs/20260925-165323-a7448117 reports/action-jobs/20260925-184620-15dd1b9d reports/action-jobs/floor-holdout-seed55 --output reports/body-contact-repeat
.venv\Scripts\python.exe scripts/run_body_contact.py reports/action-jobs/body-holdout-seed77 --output reports/body-contact-holdout-repeat
.venv\Scripts\python.exe scripts/verify_body_study.py reports/body-contact-repeat reports/body-contact-holdout-repeat
node scripts/validate_body_exports.mjs reports/body-contact-repeat
node scripts/validate_body_exports.mjs reports/body-contact-holdout-repeat
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe scripts/build_desktop.py
```

Body corrections are executed twice and compared exactly in each export run. Both new versions receive GLB/BVH/NPZ exports, root tracks, predicted contacts and provenance. Candidate ZIPs include actual body motion and measurements. Raw copies retain original hashes. Existing v1 baselines are independently checked array-for-array; the new-seed limb baselines are recomputed for verification.

The verification finalizer removes an ambiguous inherited raw hash field from early candidate evidence and labels exact no-op body stages correctly, then updates package hashes. These are metadata-only fixes; the frozen solver and evaluation thresholds did not change after seed-77 results. The raw hashes remain explicitly under `raw_trial`.

The project test suite contains 77 passing tests. New tests check rigid bone lengths, root XZ, end-effector orientation, source immutability, exact no-op behavior, valid halfway rotations, and detection of unsupported global lifting.

Next work should constrain the get-up contact sequence across the torso, elbows and knees and reduce sharp correction changes, rather than relaxing these failure thresholds. The three-version comparison and retained failures are the review surface for that work.

## Final per-clip measurements

Across all 30 clips, 24 pass the numerical gates and six remain flagged (four get-ups and two crawls). The body stage changes 12 clips and leaves 18 limb baselines exactly unchanged. All 60 new candidate/baseline GLBs and seven newly generated raw GLBs validate with zero errors/warnings.

| Clip | Limb depth (cm) | Body depth (cm) | Halfway depth (cm) | Root lift (cm) | Screen |
|---|---:|---:|---:|---:|---|
| jump-land-seed-11 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| jump-land-seed-22 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| crawl-seed-11 | 4.60 | 0.07 | 0.08 | 4.80 | flagged |
| crawl-seed-22 | 3.62 | 0.08 | 0.07 | 3.82 | numerical pass |
| dance-seed-11 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| dance-seed-22 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| wave-seed-11 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| wave-seed-22 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| kick-seed-11 | 0.00 | 0.00 | 0.07 | 0.00 | numerical pass |
| kick-seed-22 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| get-up-seed-11 | 12.62 | 0.06 | 0.23 | 12.82 | flagged |
| get-up-seed-22 | 8.99 | 0.00 | 0.00 | 9.19 | flagged |
| run-roll-stand-seed-11 | 1.89 | 0.00 | 0.26 | 1.27 | numerical pass |
| run-roll-stand-seed-22 | 2.04 | 0.00 | 0.20 | 2.24 | numerical pass |
| custom-motion-seed-33 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| custom-motion-seed-44 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| jump-land-seed-55 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| crawl-seed-55 | 5.01 | 0.04 | 0.06 | 5.49 | flagged |
| dance-seed-55 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| wave-seed-55 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| kick-seed-55 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| get-up-seed-55 | 16.34 | 0.08 | 0.05 | 16.54 | flagged |
| run-roll-stand-seed-55 | 1.03 | 0.00 | 0.22 | 1.23 | numerical pass |
| jump-land-seed-77 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| crawl-seed-77 | 6.11 | 0.09 | 0.10 | 6.31 | numerical pass |
| dance-seed-77 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| wave-seed-77 | 0.00 | 0.00 | 0.00 | 0.00 | numerical pass |
| kick-seed-77 | 0.00 | 0.00 | 0.32 | 0.00 | numerical pass |
| get-up-seed-77 | 14.70 | 0.08 | 0.06 | 14.90 | flagged |
| run-roll-stand-seed-77 | 7.05 | 0.00 | 0.13 | 7.25 | numerical pass |
