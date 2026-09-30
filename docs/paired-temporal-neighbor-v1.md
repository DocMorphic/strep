# High-five temporal smoothing experiment

Two matched local edits test whether small temporal corrections can reduce the acceleration increases identified by the [stage-rate audit](paired-stage-rates-v1.md). This is a development experiment on the first declared pair, seed 1301. It is not a new model, a released correction feature, or an approved high-five animation.

## Frozen comparison

The input is the retained body-corrected motion with authored fingers from `paired-pose-posture-v1`. The variants are unchanged input, upper-body smoothing, and the same smoothing with all 19 left-hand finger joints included. Upper-body joints comprise the spine, neck, head, left shoulder, arm, forearm and hand. Original body-stage clips supply the reference for finger edit budgets.

Only keys 71–74 and 76–79 can change. The contact key at frame 75, endpoints 70 and 80, and every other key remain exact. For each selected local rotation, the method averages the two source-relative neighboring rotation vectors and applies a strength-0.25 quartic envelope over 70–80. All updates use the original neighbors. The complete rotation-vector norm is clipped at 5 degrees; this is an additional-edit budget, not an anatomical limit.

Rotation accessors are replaced directly in the GLB. Translations, unselected animation channels, scene nodes, meshes and skins remain unchanged. This avoids altering frozen data through a native-motion conversion. The result is a GLB experiment only; no replacement native NPZ or complete scene package is claimed.

## Completed checks

Generation finished for both actors and all three variants. Every edited channel retains 142 exact keys. Maximum additional edits are 0.458864 degrees for actor A and 0.341839 degrees for B in both edited variants. All original source-relative finger limits pass: 60 degrees total and 5 degrees between adjacent correction rotations.

Actual Godot import verification covers six clips, 150 frames each: **900 actor-frames**, each with 77 bones and one skinned surface. Maximum position disagreement is 4.283e-7 m; maximum basis-element disagreement is 8.493e-7. Clips retain their nonlooping mode and duration. These results establish import fidelity only.

Sixteen focused tests pass across temporal edits, stage auditing and joint-rate reporting. New synthetic GLB tests exercise both variants, exact contact/outside keys, untouched translations and unselected channels. Regression tests also check that selecting joint indices retains the time axis and that engine evidence cannot substitute duplicate or unrelated clips. The temporal tests join Windows/Linux CI.

## Completed motion comparison

The separate motion audit finishes without waiting for expensive surface queries. It decodes six clips at 597 quarter-frame times, totaling **3,582 actor samples**, and independently recomputes **6,160 joint peak values and timestamps** using direct position differences. Maximum replay disagreement is 5.69e-14. It binds the existing 900 engine observations to the exact six GLBs; it does not count them as a new engine run.

| Actor / variant | Event acceleration peak, input → candidate (m/s²) | Event joints with increased peaks | Largest entry / exit joint increase (m/s²) |
| --- | ---: | ---: | ---: |
| A / body | 92.778170 → 73.796704 | 6 | 0.038951 / 1.203168 |
| A / body + fingers | 92.778170 → 74.041538 | 6 | 0.038951 / 1.229328 |
| B / body | 105.824978 → 84.572036 | 11 | 1.748531 / 0.933762 |
| B / body + fingers | 105.824978 → 84.761626 | 11 | 1.735257 / 0.947250 |

Event coverage is frames 73–77, entry 68–72 and exit 78–82. An increase means greater than 1e-5 in the reported unit, a diagnostic reporting convention rather than a naturalness threshold. Both variants lower the largest event peak by about 20%, but neither protects every joint or both joins. Adding finger smoothing slightly worsens the largest event peaks. Actor A has 26 increased whole-clip joint peaks despite an unchanged whole-body maximum; actor B's unchanged whole-clip peaks hide local increases.

Neither candidate is promoted. The next temporal correction should explicitly protect per-joint motion and boundary stencils while preserving contact; uniformly smoothing every selected local rotation does not enforce those conditions. This is development evidence from one pair, not a held-out or general animation result.

## Verification repairs and incomplete geometry

The surface auditor is designed to query complete partner surfaces in both directions at all 41 quarter-frame times from 70 through 80. It reports depth increases, new crossings of the existing 5 mm screen, floor changes, and contact-region evidence. That full comparison has **not completed**.

The first surface attempt failed before sampling because it called a nonexistent skin-matrix adapter. The second used the correct adapter and produced partial input-only geometry before being deliberately stopped after the motion audit exposed an overly strict decoded-transform assertion. No edited-candidate collision result is claimed. Both directories remain retained; no worker remains live for this comparison.

Exact stored rotation keys can decode with floating-point differences below 1e-15. The corrected auditors therefore keep exact serialized-key verification separate from a 1e-12 absolute decoded-transform/skin tolerance. The completed motion audit's maximum protected transform difference is 7.78e-16. This numerical tolerance does not change any contact or collision gate. A second bug mixed NumPy advanced indexing with a scalar column index, moving the joint axis before time. The shared extraction helper now uses separate selection steps and is covered with unequal time/joint dimensions. Failed motion audit directories are retained; the repaired audit completed in `paired-temporal-rates-v4`.

Because motion regressions already prevent promotion, the expensive surface run is not restarted merely to finish a report. Full surface validation is still required for any successor candidate. Partial input samples cannot establish collision improvement or nonregression.

Existing whole-clip partner collision and floor failures remain unresolved. Exact frame-75 contact cannot establish safety around it. Vertex queries also cannot certify continuous triangle intersection, self-collision, anatomy, forces, balance or naturalness. No developer/animator ratings or cleanup-time evidence have been supplied. All fourteen release capabilities remain unapproved.

## Reproduction

These commands require the previously retained licensed assets and hash-bound study evidence; use fresh output directories. Generated outputs remain local and ignored by Git.

```powershell
.venv\Scripts\python.exe scripts/study_paired_temporal_neighbor.py reports/<new-temporal-study>
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/<new-temporal-study> --output reports/<new-engine-review>
.venv\Scripts\python.exe scripts/audit_paired_temporal_rates.py reports/<new-temporal-study> reports/<new-engine-review> reports/<new-motion-review>
.venv\Scripts\python.exe scripts/audit_paired_temporal_neighbor.py reports/<new-temporal-study> reports/<new-geometry-review>
.venv\Scripts\python.exe -m pytest tests/test_paired_temporal_neighbor.py tests/test_paired_stage_rates.py tests/test_scene_joint_rates.py -q
```

Current local evidence: `reports/paired-temporal-neighbor-v1`, `reports/paired-temporal-neighbor-engine-v1`, `reports/paired-temporal-rates-v4`, and the retained failed/interrupted review directories. Method snapshots and input/export hashes bind each run. The source checkpoint containing the initial experiment passed Windows/Linux CI; the subsequent audit repairs have the focused local test evidence above.
