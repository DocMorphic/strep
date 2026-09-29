# Planning edits around existing geometry failures

The full moving-box solve uses native keys 48–133. A preflight analysis of its exact starting clip exposes a conflict: 50 failing exported geometry samples have both interpolation keys outside that window. Their box clearances cannot change under exact preservation of those keys. Continuing optimization inside the window cannot fix the whole clip.

`scripts/plan_scene_edit_window.py` now consumes a completed seed fit and its independent exported geometry audit. It verifies result, protocol, scene, native motion and GLB identities, requires a complete ordered quarter-frame clock, and recomputes failures from measured floor/object distances using the audit's existing clearance thresholds. It does not trust stored pass flags. It separates locked, boundary-straddling and selected samples, retains their causes and measurements, and suggests a conservative key envelope covering both interpolation keys of every observed failure. It never changes the requested window or launches a solve.

## Observed seed conflicts

The candidate from `region-windowed-arm-guide-v1` is the exact initializer of the running `region-windowed-surface-v1` solve.

| Region | Geometry failures | Observed causes |
| --- | ---: | --- |
| Locked interpolation segments | 50 | Box clearance, between frames 23.5 and 47 |
| Outside-time boundary segments | 3 | Box clearance at 47.25–47.75; floor clearance at two samples |
| Selected window | 326 | Box clearance; floor clearance at one sample |

There are 379 failing samples in total. Causes can overlap within a sample. The pre-window peak box penetration is 28.5746 mm. The geometry envelope suggested by the report is **[23, 133]**, compared with the current **[48, 133]**. This is a necessary scope correction for the observed locked failures, not proof that the wider optimization will succeed. The spline control space, original edit budgets, contacts, feet, timing and remaining sampled or unsampled collisions may still prevent a usable solution.

The current run remains intact with its original selection. Once it and its queued audits finish, compare its selected-window result and preserved outside failures before testing the wider scope. Do not restart a live worker or rewrite its captured implementation.

## Validation and reproduction

Fifteen focused planner and preservation-audit tests pass. Planner cases cover an incorrect stored pass flag, immutable outside collision, movable boundary collision, interior-only failure, clean sampled input, missing clock samples, nonfinite distances and invalid thresholds. The real report is retained at `reports/edit-window-plan-v1/verification.json`, with hashes of the seed and audit inputs and the planner implementation.

```powershell
.venv\Scripts\python.exe scripts/plan_scene_edit_window.py reports/region-windowed-arm-guide-v1/fit reports/region-windowed-arm-guide-v1/audit/geometry/verification.json reports/fresh-window-plan/verification.json --window 48 133
```

This is currently a CLI preflight, not a Studio interaction. It uses already-audited completed fits; direct preflight of arbitrary imported motion remains future work. Geometry coverage is sampled at 120 Hz, not continuous, and does not cover self-collision, dynamics or human judgments. All fourteen release capabilities remain unapproved.
