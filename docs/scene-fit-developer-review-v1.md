# Audited scene fits in the developer viewer

`package_scene_fit_review.py` publishes a completed single-actor regional fit to Studio's existing Scene interactions collection. It copies both source and candidate GLBs and native motions, recomputes their scene measurements, and preserves object keyframes, region patches, target points and tolerances. It includes independent geometry and Godot audit downloads, plus a per-joint/boundary rate report when supplied.

The publisher requires matching result, protocol, artifact, original-input, geometry-audit and engine-export hashes. A rate report must bind to the same result. It rejects changed exports, missing engine evidence, mismatched audits, existing output directories and destinations outside the scene-review collection. Single-actor scope follows the available audit; multi-actor review publishing requires broader actor evidence and is not silently treated as verified.

Two retained short diagnostic comparisons are now available after reloading Studio and opening Scene interactions:

- `box-rate-guard-review-v1`: source and guarded candidate, 0/34 exported contact failures and 0/17 geometry failures. The global rate screen passes, while individual joint changes remain in the downloadable report.
- `box-rate-control-review-v1`: source and equal-budget control, 1/34 exported contact failures and a peak-acceleration regression. These failures remain visible.

Both have five frames and are explicitly labelled diagnostics. They are not complete-action review evidence. Four publisher tests pass, and both real packages verify 22 content hashes and 28 offline route mappings in total. Their existing Godot evidence is reused; no new engine run, live browser or HTTP verification is claimed. No human notes, scores or cleanup times were created.

The separately running 180-frame transfer retains its exact worker and completion-audit processes. Once it finishes, the same publisher can expose its successful or failed motion with the complete object context. Its contact, geometry and temporal outcomes are still unknown. All 14 release capabilities remain unapproved.

For actual developer feedback on complete motions, the existing Studio Characters → Review corrected motions → Floor constraint comparison contains nine cases and four versions each. Watch at normal speed first; then record the case, version, frame range and observed problem in **Your review notes** and export the feedback. This is unblinded developer evidence. Independent animator ratings and measured cleanup work remain separate release requirements.

Example for a completed fit and matching evidence:

```powershell
.venv\Scripts\python.exe scripts/package_scene_fit_review.py reports/completed-fit reports/completed-audit/verification.json reports/completed-engine/verification.json reports/scene-region-jobs/new-fit-review --label "Contact comparison" --rates reports/completed-rates.json
```

Local publication proof is retained in `reports/scene-fit-review-publication-v1/verification.json`. Packages live under ignored `reports/scene-region-jobs`; source and concise methodology are published to GitHub.
