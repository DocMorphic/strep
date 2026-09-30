# High-five correction with joint-rate guards

The first retained high-five pair now has a changed GLB candidate that passes the declared source-relative motion checks. Unlike [uniform neighbor smoothing](paired-temporal-neighbor-v1.md), it preserves the measured entry/exit motion and has no per-joint acceleration increase above the existing reporting tolerance. **The completed skin audit finds four penetration regressions, so the candidate is not promoted.** It is not an approved high-five or a released correction feature.

## Fixed scope and method

Seed 1301, actors A and B, comes from the same body-corrected clips with authored fingers used in the preceding comparison. No model is trained or sampled, no reserved held-out trial is used, and no rig, scene placement or contact definition changes.

The editable keys are **74 and 76**. Frame 75 contact remains exact, as do every other stored key, translations, unselected channels, mesh and rig data. The ten editable body joints are the preceding experiment's spine, neck, head, left shoulder, arm, forearm and hand. Fingers remain unchanged. Each local rotation has a 5-degree full-vector additional-edit budget, with the existing 1e-4-degree numerical export tolerance. This is a source-relative budget, not an anatomical limit.

The fitter minimizes squared joint acceleration around contact. It constrains sampled joint speeds and accelerations against the unchanged source's individual joint peaks. A batched FK evaluator is checked against the existing independent GLB sampler before fitting. Actual float32 key clocks are used in rotation interpolation. Only strict descendants of editable rotations need numerical fitting constraints; independent export checks still include **all 77 joints**.

Changing only keys 74 and 76 confines altered interpolation to 73–77. The entry window 68–72 and exit window 78–82, including their finite-difference stencils, remain untouched. Whole clip, edited interval 70–80, event 73–77 and both joins are checked after export. The contact pose is held by its stored keys, not an optimization weight.

## Retained attempts

All runs remain local under `reports/paired-guarded-temporal-v1` through `v4`, with their method snapshots and inputs preserved.

1. The first SLSQP fit reaches 60 iterations with infeasible final iterates. Its saved feasible result is only a finite-difference probe, changing less than 0.000006 degrees. This is not counted as a useful correction.
2. Removing redundant phase constraints and checking only accepted iterates retains the exact original clips. Final infeasible parameters are also saved for diagnosis and continuation.
3. A continuation replaces a maximum inside each inequality with separate inequalities for every sampled rate. This represents the same peak limits while avoiding a switching maximum in the optimizer. Residual violations shrink, but the retained feasible output remains unchanged.
4. A feasibility-only least-squares repair starts from those saved final parameters. It uses small fitting reserves—at most 1e-5 m/s for speed and 1e-3 m/s² for acceleration, each limited to 1e-4 of the corresponding source cap. **Final exported checks keep the original caps and 1e-5 reporting tolerance.** Both repaired exports pass at full strength. Restoration ends at its 80-evaluation budget and is explicitly **not reported as converged**.

Source-relative per-joint caps are a development nonregression condition, not a universal physical or perceptual naturalness threshold. Solver termination does not approve an export. Every selected clip is independently decoded, checked against the original, and replayed with separate direct-difference peak calculations. Rejected line-search exports would be retained; the exact source is the explicit fallback if no edited export passes.

## Completed export evidence

| Actor | Event acceleration peak: source → candidate (m/s²) | Reduction | Entry / exit peaks |
| --- | ---: | ---: | --- |
| A | 92.778170 → 66.074361 | 28.8% | Unchanged |
| B | 105.824978 → 77.947267 | 26.3% | Unchanged |

Every joint passes speed and acceleration comparisons across all five windows. Actor A's largest positive speed difference is 5.67e-6 m/s, below the unchanged 1e-5 reporting tolerance; it has no positive acceleration-peak difference. Actor B has neither a positive speed nor acceleration-peak difference. Whole-clip maxima remain unchanged because they occur outside the correction.

Each selected channel retains **148 exact stored keys**. Maximum protected decoded world-matrix difference is 4.45e-16, below the separate 1e-12 decode tolerance. Maximum measured local edits are 5.000001781 degrees for A and 5.000000655 for B, within the declared numerical budget tolerance. All original finger bounds also pass. These larger edits use substantially more of the allowed budget than the preceding uniform smoothing, making renewed skin validation necessary.

Independent direct-difference replay verifies **3,080 source/candidate joint peak values and timestamps**, with maximum disagreement 5.69e-14. A fresh Godot run imports both inputs and candidates: **600 actor-frames**, each with 77 bones, one skinned surface, original duration and nonlooping mode. Maximum position disagreement is 4.154e-7 m and maximum basis-element disagreement 8.493e-7. Import fidelity does not establish partner contact or naturalness.

Twenty-one focused model-free tests pass. New coverage checks batched FK with out-of-order parents, cycle rejection, sampled/exported agreement, exact zero edits and protected keys, full-vector rotation budgets, equivalent sampled-versus-peak inequalities, and a joint regression hidden by an improved global maximum. The new tests are included in Windows/Linux CI.

## Geometry and remaining work

`reports/paired-guarded-geometry-v1` binds the exact exports and engine evidence to the existing complete-skin bilateral vertex query. It completes all **17 quarter-frame times from 73 through 77** for both input and candidate: **34 scene samples and 68 directional queries**, each checking eligibility for all 18,056 source vertices. Its manifest adapter links to original GLBs without copying or altering them.

Both input and candidate fail the 5 mm penetration screen at **8 of 17 times**. No previously passing time becomes failing, but that count hides four depth regressions: frames 73.5, 73.75, 74.5 and 74.75. The largest increase is **0.938568 mm at frame 73.75**. Maximum interval depth rises from **20.808339 to 21.336780 mm**. Other times improve, including a 1.271629 mm decrease at frame 74.25. This is a tradeoff, not a geometric correction.

Floor depth remains zero within the measured interval. At frame 75, event skin agrees within 8.89e-16 m, regional contact retains 21/17 vertices within 3 mm in the two directions, and opposing normals remain 5.199 degrees. The original event screens continue to pass; collision depth there is 1.896658 mm. These local facts do not remove failures nearby or elsewhere in the clip. All audit workers are terminal.

Existing collision and floor failures elsewhere in the clip remain unchanged and unresolved. Neither this correction nor an event-only contact pass can approve the full action. The geometry method itself does not certify continuous triangle intersections, self-collision, forces, balance or anatomy. Developer/animator ratings and cleanup-time evidence remain absent. All fourteen release capabilities remain unapproved.

The next correction must account for both moving partner surfaces while preserving the newly verified motion and contact conditions. Optimizing each actor's rates independently cannot impose pairwise clearance. The four regressed times are development witnesses, not a replacement for complete interval validation. Existing full-scene failures also need correction, followed by other development pairs and held-out evaluation before product promotion.

## Reproduction

Historical licensed inputs and evidence are required. Use fresh output directories. To reproduce the restoration from the retained compatible fit:

```powershell
.venv\Scripts\python.exe scripts/study_paired_guarded_temporal.py reports/<new-restoration> --resume reports/paired-guarded-temporal-v3 --restore
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/<new-restoration> --output reports/<new-engine-review>
.venv\Scripts\python.exe scripts/audit_paired_guarded_geometry.py reports/<new-restoration> reports/<new-engine-review> reports/<new-geometry-review>
.venv\Scripts\python.exe -m pytest tests/test_paired_guarded_temporal.py tests/test_paired_temporal_neighbor.py tests/test_paired_stage_rates.py tests/test_scene_joint_rates.py -q
```

Running the study without `--resume` starts the current sampled-inequality fitter from the original clip; it does not recreate the superseded maximum-based implementation. That historical implementation remains in each original run's immutable snapshot. The current runner additionally verifies that retained fit parameters match their completed result before continuation.
