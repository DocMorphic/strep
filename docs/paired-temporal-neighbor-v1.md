# High-five temporal smoothing experiment

Two matched local edits test whether small temporal corrections can reduce the acceleration increases identified by the [stage-rate audit](paired-stage-rates-v1.md). This is a development experiment on the first declared pair, seed 1301. It is not a new model, a released correction feature, or an approved high-five animation.

## Frozen comparison

The input is the retained body-corrected motion with authored fingers from `paired-pose-posture-v1`. The variants are unchanged input, upper-body smoothing, and the same smoothing with all 19 left-hand finger joints included. Upper-body joints comprise the spine, neck, head, left shoulder, arm, forearm and hand. Original body-stage clips supply the reference for finger edit budgets.

Only keys 71–74 and 76–79 can change. The contact key at frame 75, endpoints 70 and 80, and every other key remain exact. For each selected local rotation, the method averages the two source-relative neighboring rotation vectors and applies a strength-0.25 quartic envelope over 70–80. All updates use the original neighbors. The complete rotation-vector norm is clipped at 5 degrees; this is an additional-edit budget, not an anatomical limit.

Rotation accessors are replaced directly in the GLB. Translations, unselected animation channels, scene nodes, meshes and skins remain unchanged. This avoids altering frozen data through a native-motion conversion. The result is a GLB experiment only; no replacement native NPZ or complete scene package is claimed.

## Completed checks

Generation finished for both actors and all three variants. Every edited channel retains 142 exact keys. Maximum additional edits are 0.458864 degrees for actor A and 0.341839 degrees for B in both edited variants. All original source-relative finger limits pass: 60 degrees total and 5 degrees between adjacent correction rotations.

Actual Godot import verification covers six clips, 150 frames each: **900 actor-frames**, each with 77 bones and one skinned surface. Maximum position disagreement is 4.283e-7 m; maximum basis-element disagreement is 8.493e-7. Clips retain their nonlooping mode and duration. These results establish import fidelity only.

Fourteen focused tests pass across temporal edits, stage auditing and joint-rate reporting. New synthetic GLB tests exercise both variants, exact contact/outside keys, untouched translations and unselected channels. The temporal tests join Windows/Linux CI.

## Geometry audit remains pending

The separate audit decodes all 597 quarter-frame times per actor clip for per-joint rates, verifies protected world matrices and exact event skin, and queries complete partner surfaces in both directions at all 41 quarter-frame times from 70 through 80. It reports depth increases, new crossings of the existing 5 mm screen, floor changes, and contact-region evidence. It does not substitute a whole-body maximum for individual joint changes.

The first audit attempt failed before geometry sampling because it called a nonexistent skin-matrix adapter. Its output directory is retained. The corrected audit uses `RigAsset.vertices` with decoded world matrices and checks that both actors share the expected triangle topology. It runs in a fresh directory, `paired-temporal-neighbor-review-v2`. At this source checkpoint, its complete collision/rate results are **not yet available**; neither candidate is promoted.

Existing whole-clip partner collision and floor failures remain unresolved. Exact frame-75 contact cannot establish safety around it. Vertex queries also cannot certify continuous triangle intersection, self-collision, anatomy, forces, balance or naturalness. No developer/animator ratings or cleanup-time evidence have been supplied. All fourteen release capabilities remain unapproved.

## Reproduction

These commands require the previously retained licensed assets and hash-bound study evidence; use fresh output directories. Generated outputs remain local and ignored by Git.

```powershell
.venv\Scripts\python.exe scripts/study_paired_temporal_neighbor.py reports/<new-temporal-study>
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/<new-temporal-study> --output reports/<new-engine-review>
.venv\Scripts\python.exe scripts/audit_paired_temporal_neighbor.py reports/<new-temporal-study> reports/<new-geometry-review>
.venv\Scripts\python.exe -m pytest tests/test_paired_temporal_neighbor.py tests/test_paired_stage_rates.py tests/test_scene_joint_rates.py -q
```

Current local evidence: `reports/paired-temporal-neighbor-v1`, `reports/paired-temporal-neighbor-engine-v1`, and the retained failed/running review directories. Method snapshots and input/export hashes bind each run. Do not edit the running auditor's dependencies until it exits. The next decision depends on its completed geometry and per-joint results, not on successful export alone.
