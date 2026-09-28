# Unprocessed feasibility results — 2026-09-24

Completed all 25 planned unprocessed actor jobs: 20 case/seed trials across four cases and seeds 11, 22, 33, 44, 55. The first run sample was reused with its hash verified; 24 new jobs ran. Execution took 525.94 seconds including repeated setup, preflight, export and inspection. Every actor file passed structural validation. **This is not a 100% realism success rate.** No trial has completed all required realism assessments.

The motion checkpoint and vendor source are unchanged. Text conditioning uses the original-precision streamed encoder cache, with small-model equivalence checked and full 8B resident equivalence still untested. These results belong to that explicitly labeled execution variant. No training, raw BONES-SEED data, quantization, or cloud compute was used.

## Results and limits

| Case | Five-seed result | Interpretation |
|---|---|---|
| Run loop | Next-pose boundary prediction RMS 16.3–35.7 cm; all five flagged | Raw output does not satisfy the provisional 2 cm loop screen. Do not call these seamless loops. |
| Run → roll | All five have 210 frames with the expected 85–89 blend and second segment beginning at 90. Joint-only maximum ground depth ranges 1.24–8.26 cm | Seed 11's roll was visually spot-checked, not animator-rated. Ground and transition corrections need evaluation; meshes and physical plausibility remain unassessed. |
| Lift box | All five skeleton clips generated; no object trajectory/attachment is produced | Complete object-lift task is unsupported by this baseline output. A gesture is not a successful interaction. |
| High-five | Five independently generated A/B pairs, identical native joint trajectories within each pair under same prompt/seed | This symmetric protocol is not joint inference and does not measure independent partner adaptation. |

High-five pairs were placed using the unchanged provisional scene transforms: origins at Z ±0.55 m, B yaw 180°, shared 30 fps clock. No timing shift or spatial fitting was applied. At the requested two-second evaluation time, right-wrist separation ranges **0.629–1.371 m**. Minimum separation anywhere ranges 0.017–0.132 m and occurs around 0.97–1.37 seconds. Reporting only the closest frame would hide timing and target errors. These are **uncalibrated wrist diagnostics**, not palm-contact acceptance results. Scene targets were evaluation targets, not constraints supplied to the prompt-only model. Side and top views of pair 11 were inspected; the side projection obscures lateral separation.

Predicted-contact foot-speed p95 ranges (cm/s): run 9.92–19.55, run→roll 14.97–25.15, lift 2.42–3.96, high-five 1.64–2.73. The model supplies these contact labels; this is not independently verified foot skating. Joint depth is not mesh penetration. No unsupported or missing measurement was replaced by zero.

## Artifacts

- `reports/grid-v0.json`: every job, attempt, status, and reuse.
- `reports/quality-v0.json`: all numeric screens, limitations and provisional paired-scene diagnostics.
- `reports/baseline-review.html`: all-seed gallery and five paired previews; serve project root locally.
- Each attempt preserves raw NPZ/BVH, generation log, source hashes, metrics, root CSV, predicted foot-contact intervals and a preview.
- `benchmarks/acceptance-v0.json` and `docs/realism-rubric.md`: provisional criteria and human review requirements. Thresholds were set after inspecting the first run sample; this is exploratory, not preregistered.

Thirteen tests pass. The new tests distinguish a smooth sampled periodic cycle from a discontinuous seam and detect a synthetic transition teleport. Browser inspection verified the gallery, a rolling pose, and a two-actor scene at the target time.

## Still required

The upstream-cleanup comparison did not run because native MotionCorrection bindings are unavailable. Independent support labels, calibrated palms/grips/scene scale, mesh collisions, two independent human reviewers, animator cleanup timing, retargeting and engine import remain pending. The frozen `v0.json` definition still contains its original planning status because changing it invalidates the bound cache; execution truth is in the separate run reports.

Next work should address the measured failures through loop/contact/transition correction and scene-aware constraints, preserving corrected copies and rerunning the same metrics. Compare against the raw records; only then consider additional learned editing or training. More actions, held-out rigs and objects, reference motion and larger samples are needed before a broad reliability claim.
