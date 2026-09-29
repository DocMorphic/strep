# Audited scene fits in the developer viewer

`package_scene_fit_review.py` publishes a completed single-actor regional fit to Studio's existing Scene interactions collection. It copies both source and candidate GLBs and native motions, recomputes their scene measurements, and preserves object keyframes, region patches, target points and tolerances. It includes independent geometry and Godot audit downloads, plus a per-joint/boundary rate report when supplied.

The publisher requires matching result, protocol, artifact, original-input, geometry-audit and engine-export hashes. A rate report must bind to the same result. It rejects changed exports, missing engine evidence, mismatched audits, existing output directories and destinations outside the scene-review collection. Single-actor scope follows the available audit; multi-actor review publishing requires broader actor evidence and is not silently treated as verified.

Two retained short diagnostic comparisons are now available after reloading Studio and opening Scene interactions:

- `box-rate-guard-review-v1`: source and guarded candidate, 0/34 exported contact failures and 0/17 geometry failures. The global rate screen passes, while individual joint changes remain in the downloadable report.
- `box-rate-control-review-v1`: source and equal-budget control, 1/34 exported contact failures and a peak-acceleration regression. These failures remain visible.

Both have five frames and are explicitly labelled diagnostics. They are not complete-action review evidence. Four publisher tests pass, and both real packages verify 22 content hashes and 28 offline route mappings in total. Their existing Godot evidence is reused; no new engine run, live browser or HTTP verification is claimed. No human notes, scores or cleanup times were created.

The 180-frame transfer and its audits are now complete. The failed motion is available as `full-box-transfer-review-v2`, with all 490 hand-contact failures and release-boundary rate increases preserved. The publisher now includes per-joint and phase/boundary increases in its visible motion-regression warning even when global peaks decrease. These are diagnostics, not a calibrated naturalness test. The original v1 package remains retained. All 14 release capabilities remain unapproved.

For actual developer feedback on complete motions, the existing Studio Characters → Review corrected motions → Floor constraint comparison contains nine cases and four versions each. Watch at normal speed first; then record the case, version, frame range and observed problem in **Your review notes** and export the feedback. This is unblinded developer evidence. Independent animator ratings and measured cleanup work remain separate release requirements.

Example for a completed fit and matching evidence:

```powershell
.venv\Scripts\python.exe scripts/package_scene_fit_review.py reports/completed-fit reports/completed-audit/verification.json reports/completed-engine/verification.json reports/scene-region-jobs/new-fit-review --label "Contact comparison" --rates reports/completed-rates.json
```

Local publication proof is retained in `reports/scene-fit-review-publication-v1/verification.json`. Packages live under ignored `reports/scene-region-jobs`; source and concise methodology are published to GitHub.


## Scene-specific developer observations

Scene interactions now includes **Your scene review notes**. Load a saved scene, watch it at normal speed, enter your name or alias, select a frame range (or use the current frame), describe what you observed, and export feedback. Notes can describe either actor, an object or their interaction. No scores or observations are filled in automatically.

Each export records the exact scene JSON hash and the hashes of every actor GLB actually loaded into the viewer. This binds object tracks and placements through the scene file and motion through the actor files. Drafts are stored separately for each exact scene/actor combination. Loading another scene clears the active binding; editing placement disables saved-scene feedback until reload. Embedded GLBs are required for feedback so an external buffer cannot change without changing a recorded file. Camera and playback changes do not alter the source binding.

`scene_developer_feedback.py` imports a feedback JSON only when its saved collection, scene, all actors and frame range match. It supports nested collection bundles and multi-actor scenes, rejects changed object tracks or partner motion, and preserves existing imports. Notes are explicitly unblinded developer observations. The importer does not verify reviewer identity, correctness of the observation, independent animator ratings or cleanup timing, and never grants release approval.

```powershell
.venv\Scripts\python.exe scripts/scene_developer_feedback.py reports/scene-region-jobs/object-grip-augmented-review-v1/candidate.json path/to/exported-feedback.json reports/developer-feedback/my-first-scene-review
```

Thirty-one focused Python tests and two Node feedback checks pass. A duplicate form ID found during integration was fixed; a DOM uniqueness check now guards against recurrence. Offline file-backed checks fingerprint the real source and candidate box scenes plus a nested high-five scene with two actors; their serialized contexts pass the importer using synthetic observations held only in memory. The built module parses and the desktop bundle matches its sources. Evidence is in `reports/scene-developer-feedback-v1/verification.json`. No human notes were fabricated or saved, and no live browser rendering was verified. The pending full root-coordinate trial and its numerical source were unchanged.
