# Floor-contact correction milestone

2026-09-25. This is a completed implementation/evaluation milestone, not a claim that floor interaction or realistic animation is solved.

The studio at http://127.0.0.1:8768/studio now provides two floor-cleanup collections. Choose an animation and switch **Version** between **Raw generation** and **Corrected · experimental**. Playback time, camera and selected frame are preserved when switching. The inspector reports both whole-skin depths, current numerical flags, and the deepest frame for the displayed version. Each version links to its own actual animation files.

## Result

23 corrected clips cover jumping/landing, crawling, dancing/turning, waving, kicking, getting up, running/rolling/standing, shrugging and balancing. These are evaluation examples, not an allowed-action list. 14/23 pass the provisional numerical correction screen; 9/23 remain flagged. All 7 new seed-55 clips were generated locally with the unchanged checkpoint; 4/7 pass that screen. No training, checkpoint changes or new dataset acquisition occurred.

Hands clear the sampled floor in the reserved-seed crawl/get-up/roll clips, but knees, torso and other regions remain problematic. Reserved-seed whole-body penetration changes from 13.71 to 5.01 cm for crawling, 16.50 to 16.34 cm for getting up, and 5.24 to 1.03 cm for run/roll/stand. Hand patch gaps or sliding also regress in several examples. These are retained failures, not accepted game-ready clips.

## Diagnosis and sources

The old whole-surface audit correctly found finger penetrations of up to 14 cm. Checking source joints at the deepest frames confirmed fingers extending below wrists near the floor. The pinned upstream `SOMASkeleton30.to_SOMASkeleton77` expands the reduced skeleton using `relaxed_hands_rest_pose`, copying only the reduced joint rotations into that pose. This helps explain why prompt generation alone does not guarantee detailed finger contact; it does not prove all collisions are caused by skeleton expansion. Deep torso and knee collisions also exist.

Primary references inspected:

- [NVIDIA constraint documentation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/constraints.html): reduced SOMA constraint representation and smooth post-processing. Our implementation is separate from NVIDIA's C++ correction module.
- [NVIDIA benchmark metrics](https://research.nvidia.com/labs/sil/projects/kimodo/docs/benchmark/metrics.html): foot-skate, contact consistency and constraint error. Our whole-skin floor tests add information that joint-level contacts cannot supply.
- [Ryan Juckett's analytic two-bone IK derivation](https://www.ryanjuckett.com/analytic-two-bone-ik-in-2d/): analytic limb geometry. Implementation reuses this project's existing bend-plane-preserving two-bone solver.

## Algorithm and scope

`scripts/floor_contact.py` inspects geometry without reading action names or prompts:

1. Evaluate the actual SOMA mesh with all eight skin weights against Y=0.
2. Where a low wrist has downward-pointing fingers and penetrating hand skin, find a bounded pitch towards a horizontal hand direction, then smooth its rotation-vector curve over time. Maximum global wrist-pitch request is 65 degrees. Fingers retain their local articulation.
3. Smooth the residual surface-clearance requests and apply length-preserving two-bone IK to hands and feet. The original bend side and end-effector orientation are retained by that IK stage. Maximum cumulative upward request is 7 cm for hands and 2.5 cm for feet. Clearance target is 2 mm. Three fixed passes run; unreachable targets are recorded, not forced by bone stretching.
4. Reconstruct skeletal motion from rotations, preserve the root trajectory and original foot-contact channels, and measure the full body again.

Root translation, timing, headings and source auxiliary arrays stay unchanged. Float32 rotation matrices are projected onto SO(3) to prevent numerical drift; local finger changes are limited to this numerical normalization. This is a one-pass offline authoring operation, not an idempotent filter or a dynamics solver. It does not infer planted hands, lock support points, flatten palms, solve torso/knee penetration, enforce anatomical joint limits, solve self/object/partner collisions, or guarantee continuous-time clearance between 30 fps samples. It currently requires SOMA77 and its supplied skin; external-rig transfer remains separate.

The method may trade finger penetration for a different contact patch, palm height, wrist posture or support drift. We explicitly measure these costs. A no-penetration result alone cannot establish believable weight bearing.

## Evaluation protocol

Four existing clips were used for development: crawl/get-up/run-roll/wave, seed 11. Remaining existing examples, two prior custom actions, and seven newly generated seed-55 clips were evaluated afterward. Existing seed-22 audit depths had already been seen: this is not a blind held-out dataset. Shrug/balance and the new seed provide additional checks, not proof of universal action coverage. No new action descriptions were encoded for this milestone.

The new-seed batch reuses exact previously verified text embeddings: identical strings, encoder revisions and feature hashes. `prepare_floor_holdout.py` records that reuse explicitly. It performs new motion inference for every seed-55 request. `benchmarks/floor-contact-v1-freeze.json` records the initial implementation freeze. The amended freeze records a numerical rotation-orthogonality repair made before holdout evaluation. Subsequent changes fixed export path handling and separated inherited raw flags from corrected flags; no threshold tuning or motion-policy changes followed held-out results.

Whole-surface depth examines every vertex at every stored frame. For sliding/gap comparisons, choose low, slow patches from the **raw** mesh and measure those same vertices and intervals in both versions. Raw patch thresholds: minimum region height below 3 cm at both frames and region-centroid horizontal speed below 0.35 m/s; patch vertices are within 1 cm of the raw region minimum. These are geometric candidates, not ground-truth support labels. A patch-gap regression does not by itself mean the entire hand floats: a different patch may be touching.

Provisional correction flags:

- Residual skin penetration above 1 cm, or depth worsening by more than 1 mm.
- Any joint displaced more than 22 cm or peak added joint speed above 1.5 m/s.
- Fixed raw support-patch p95 horizontal speed worsening by more than 2 cm/s for feet or 8 cm/s for hands, when at least three intervals exist.
- Fixed raw support-patch p95 gap worsening by more than 1.5 cm.

Per-frame depth, region depths, absolute before/after patch speeds and gaps, joint displacement, rotation distortion, added speed and acceleration, source sequence-boundary diagnostics and end-pose proxies are saved. These thresholds are engineering screens, not psychophysical realism thresholds. Independent animator ratings, action correctness, manual correction time and engine import remain unmeasured. All clips retain `human_approved: false` and `engine_import: null`.

## Outputs and reproduction

- `reports/floor-contact-v1-reviewed`: 16 existing clips and corrections, 10 numerical passes.
- `reports/floor-contact-holdout-v1`: 7 new-seed clips and corrections, 4 numerical passes.
- `reports/action-jobs/floor-holdout-seed55`: all new raw generations, constraints/settings, timings, encoding provenance, logs and exports.
- Each corrected take includes GLB, BVH, NPZ, root track, unchanged predicted foot contacts, timeline, request, recipe, raw comparison files, measurements and a ZIP package with license.

Run from `C:/wassup/strep`, using a fresh output folder:

```powershell
.venv\Scripts\python.exe scripts/run_floor_contact.py reports/action-coverage-v1 reports/action-jobs/20260925-165323-a7448117 reports/action-jobs/20260925-184620-15dd1b9d --output reports/floor-contact-repeat
.venv\Scripts\python.exe scripts/run_floor_contact.py reports/action-jobs/floor-holdout-seed55 --output reports/floor-contact-holdout-repeat
.venv\Scripts\python.exe scripts/verify_floor_study.py reports/floor-contact-repeat reports/floor-contact-holdout-repeat
node scripts/validate_action_exports.mjs reports/floor-contact-repeat
node scripts/validate_action_exports.mjs reports/floor-contact-holdout-repeat
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe scripts/build_desktop.py
```

The reusable CLI accepts finite SOMA exports from any studio request. Automatic application to all future generated clips is deliberately not enabled while contact regressions remain. New correction collections must be explicitly allowed in `action_studio_server.py` before serving; the server does not expose arbitrary project files.

All 23 corrections repeat exactly from the same raw arrays in the exporter. All corrected GLBs and seven new raw GLBs validate with zero errors/warnings. Every exported GLB frame is decoded and compared to source joints, rotations and whole-surface depth. BVH roundtrips also pass. Separate verification checks exact eight-weight skinning, original asset hashes, ZIP members, root timeline and foot-contact intervals. 73 project tests pass, including new checks for preserved bone lengths/root/fingers, bounded smoothing and airborne-motion preservation.

Browser checks confirm raw/corrected switching at the same frame, including the last frame; model visibility after clicking the preview; comparison inspector data; and clean console logs. This is a functional UI check, not independent animation review.

Next research target: a whole-body support/contact solver that can address torso/knee collisions without introducing floating feet or damaging rolling/get-up poses, followed by independent naturalness and cleanup-time review. The current failures supply the test cases.

## Per-clip whole-body results

| Clip | Raw depth (cm) | Corrected depth (cm) | Screen |
|---|---:|---:|---|
| jump-land-seed-11 | 0.76 | 0.00 | within provisional screen |
| jump-land-seed-22 | 1.21 | 0.00 | within provisional screen |
| crawl-seed-11 | 11.03 | 4.60 | flagged |
| crawl-seed-22 | 7.14 | 3.62 | flagged |
| dance-seed-11 | 1.03 | 0.00 | within provisional screen |
| dance-seed-22 | 1.00 | 0.00 | within provisional screen |
| wave-seed-11 | 1.00 | 0.00 | within provisional screen |
| wave-seed-22 | 1.04 | 0.00 | within provisional screen |
| kick-seed-11 | 1.22 | 0.00 | within provisional screen |
| kick-seed-22 | 0.83 | 0.00 | within provisional screen |
| get-up-seed-11 | 13.63 | 12.62 | flagged |
| get-up-seed-22 | 13.96 | 8.99 | flagged |
| run-roll-stand-seed-11 | 6.61 | 1.89 | flagged |
| run-roll-stand-seed-22 | 8.12 | 2.04 | flagged |
| custom-motion-seed-33 | 1.14 | 0.00 | within provisional screen |
| custom-motion-seed-44 | 0.78 | 0.00 | within provisional screen |
| jump-land-seed-55 | 1.70 | 0.00 | within provisional screen |
| crawl-seed-55 | 13.71 | 5.01 | flagged |
| dance-seed-55 | 1.25 | 0.00 | within provisional screen |
| wave-seed-55 | 1.38 | 0.00 | within provisional screen |
| kick-seed-55 | 0.56 | 0.00 | within provisional screen |
| get-up-seed-55 | 16.50 | 16.34 | flagged |
| run-roll-stand-seed-55 | 5.24 | 1.03 | flagged |
