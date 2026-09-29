# Fixed-patch support coverage experiment

The repaired kick-22 passes its numerical screens, but one case is insufficient to enable the new constraint by default. This declared follow-up compares three different retained requests: wave-22, crawl-22 and jump/landing-22. They exercise an upright gesture with a foot pin, ground movement with a hand pin, and a landing foot pin at a later interval. They are development cases already examined for failures, not a held-out test set or an exhaustive action list.

Each case runs control first, then fixed-patch support, from the same original source, warm seed and checked request. Both modes use four outer stages with 60 optimizer iterations per stage. The separate native-body objective is off in both arms. Root/rotation limits, contact tolerances, fixed source rate limits, floor limits and held poses remain unchanged. The sole per-pair optimization difference is `--support-screen`.

The existing runner exports both candidates, independently measures contact/body/rate/preservation results, computes saved NPZ body peaks, and runs actual engine playback with the corrected authored event mapping. Neither mode automatically replaces the source or approves motion quality. All original, warm, failed and intermediate artifacts remain available. Snapshot and completion hashes are checked after each mode and again at batch completion; the pair's source snapshots and protocols must match except for the support switch.

The six fits run sequentially under the normal local worker lock. The completed batch is retained under `reports/native-support-breadth-v1`. All six modes are terminal and independently verified. The final outcome below supersedes the intermediate running-state notes retained in this report. Study source remained frozen through completion and verification.

The per-mode command, after acquiring the original local study data and runtime, is:

```powershell
.venv\Scripts\python.exe scripts/study_native_body_constraints.py --source reports/contact-jobs/contact-breadth-v1-wave-22-repair/source-take --seed reports/contact-jobs/contact-breadth-v1-wave-22-repair/seed --checked-plan reports/contact-jobs/contact-breadth-v1-wave-22-repair/checked-plan --output reports/new-wave-control --no-body-screen --outer-stages 4 --iterations 60
```

Repeat into a fresh output directory with `--support-screen` for the paired arm. Substitute the declared crawl-22 and jump-land-22 input directories for the remaining pairs. Do not reuse output folders, alter inputs between arms or treat the public source repository as including the locally acquired character/model/study data.

After completion, compare every screen and fit time, not just the previously failing foot metric. Any export-feedback repairs must be separate, retained follow-ups using the original budgets. A default change requires broader evidence and end-to-end Studio verification; semantic ratings and cleanup-time review remain outstanding.


## First completed control

Wave-22 control completed 379 evaluations in 247.78 seconds. All 81 authored foot-pin samples pass (2.953369 mm maximum), with zero added floor depth, no body-review flags, passing original global rate limits and exactly zero audited outside-window errors. The contact screen still fails: approach acceleration exceeds its original ceiling by 0.0000112212 m/s². Hold and release point-rate limits pass. Actual engine playback passes 284 pose observations and the authored event checks.

The saved NPZ support measurements independently match the body report within 1e-10 for every measured reference/foot pair; native body peaks and all original input, current/archived method and completion hashes were verified. The result remains unapproved and does not establish the effect of the new support objective. Its matched support-enabled run is still fitting; crawling and landing pairs remain queued. Partial evidence is retained as `reports/native-support-breadth-v1/wave-control-verification.json`.


## Completed waving pair

The support-enabled wave-22 fit completed 325 evaluations in 281.60 seconds. All 81 pin samples pass (2.954089 mm maximum), every original point-phase/global rate ceiling passes, added floor depth is zero, outside-window errors remain exactly zero and no body-review flag is added. Its saved output passes the numerical contact screen without a separate export-feedback repair. Both modes pass 284 engine pose observations each, including the requested 50/70-frame event boundaries.

Verification confirmed identical original inputs and method snapshots, with the support switch as the sole protocol difference. Independent saved-NPZ support/body replay, complete export-audit replay and replay of the captured engine observations all pass. The left-foot slide p95 is 0.020256981 m/s (control 0.020391423); the right-foot value is 0.027324274 m/s (control 0.027302977). Both modes were already comfortably inside the fixed support limits. This is evidence of nonregression on this development case, not proof that the support term generally improves motion or that the control's small rate failure was physically meaningful. All numerical acceptance thresholds remain unchanged.

Evidence is retained in `wave-support-verification.json` and `wave-pair-engine-verification` under the local batch folder. Two of six runs are complete; the crawl-22 control is now running and the remaining modes stay queued under frozen methods. No default Studio change, human-quality approval or release claim follows from this pair.


## Completed crawling pair

Both crawl-22 arms finish after 462 evaluations. Their native NPZ, BVH, GLB, exported contact audit and body evaluation are byte-identical. The control takes 298.89 seconds and the support-enabled fit takes 440.47 seconds on this local run. This case demonstrates no motion improvement and additional computation; neither arm is selected as a quality winner.

All 81 hand-pin samples pass, but the 4.999953099 mm maximum is only about 0.000046901 mm below the unchanged 5 mm limit. Both retain a release point-acceleration excess of 0.000036604731 m/s², so both contact screens fail. All other point/global rate limits pass, added floor depth and audited outside-window errors are zero, and no body-review flag is added. All eight measured raw/limb hand/foot support comparisons pass. Each arm passes 284 engine pose observations and its authored event checks.

Saved NPZ/body/support replay, complete export-audit replay, engine-observation replay and paired input/method/protocol verification pass. The original limits and failed candidates are retained. Local evidence includes `crawl-control-verification.json`, `crawl-support-verification.json`, `crawl-identical-artifacts.json` and `crawl-pair-engine-verification` in the batch folder. A later export repair can reuse one identical candidate, but must preserve the pin's very small remaining margin. No repair outcome is assumed.

Four of six runs are complete. The landing control is running, followed by its matched support arm. This partial population does not justify enabling the constraint by default or claiming general motion quality.


## Landing control: pose correction is still necessary

The landing control completes 383 evaluations in 252.34 seconds, with three of 61 pin samples outside 5 mm and a 5.371695 mm maximum error. Point-phase speed/acceleration failures remain, while original global rate limits, floor preservation, outside-window preservation and body-review flags pass. Actual engine playback passes 284 observations. Independent saved-NPZ support/body replay and all input/current/archived/completion hashes were verified; the support-enabled arm is still running.

A separate decoded-pin check isolates failures at frames 90, 99.75 and 100. Their horizontal errors alone are 5.003851, 5.141218 and 5.360478 mm. At frame 100, vertical error is only 0.346954 mm. Holding rotations and root XZ fixed cannot reduce the horizontal component: therefore root-height-only export feedback cannot repair this control to the unchanged 5 mm limit. This is a restriction of that repair subspace, not a proof that the authored landing request is impossible.

The candidate, hash-bound pin diagnostic (`landing-control-pin-diagnosis.json`) and independent control verification remain under the local batch folder. A future pose correction must preserve the original edit and rate limits; no failed result is replaced and no extra root-only retry is justified by this evidence. Five of six runs are complete; no paired landing outcome is claimed yet.


## Final six-run result

All six fits are terminal. Independent verification checks every original input, method snapshot and completion artifact, replays the complete saved GLB audits and NPZ support/body measurements, verifies identical paired protocols except for the support switch, and rechecks captured engine observations and actual authored event boundaries. Final evidence is `reports/native-support-breadth-verification-v1/verification.json`. There are **one of six numerical contact-screen passes and 1,704 passing engine pose observations**, with no human approval.

| Case | Control | Fixed-patch support |
| --- | --- | --- |
| Wave 22 | Approach acceleration failure | Numerical contact pass |
| Crawl 22 | Release acceleration failure | Identical motion and failure |
| Jump/landing 22 | 3/61 pin misses and point-rate failures | 2/61 pin misses and point-rate failures |

All six preserve original global-rate ceilings, per-time floor depth and outside-window poses, with empty body-review flag lists. These nonregression screens do not certify that the original motion was realistic. The landing support mode takes 328.34 seconds and 381 evaluations. Its maximum pin error is 5.370261 mm; the horizontal component alone is 5.359365 mm at frame 100. Thus neither landing arm can be repaired to 5 mm by root-height-only feedback with fixed rotations and root XZ.

The landing change is mixed: one fewer pin miss and lower approach/release acceleration excess, but a newly failing hold-speed ceiling (+0.0000354440 m/s), higher hold-acceleration excess (+0.0020341296 m/s²) and higher release-speed excess (+0.0002504587 m/s). It is not a general improvement. The control's recorded optimizer point maximum (5.371720 mm) already matches the exported failure closely: this is primarily unresolved optimization, not export rounding. Its last three stages reach their iteration limits while projected gradients remain nonzero; increased penalties barely reduce the pin residual.

Decision: keep the optional support objective off by default. Retain the earlier successful kick repair as separate case evidence, not a substitute for this population. A bounded export-feedback follow-up may address the single identical crawling candidate's small rate residual, with the original nearly saturated pin and all other limits rechecked. Landing needs a pose-capable feasibility correction that retains original source bounds and passes complete native/export audits. Do not retry its known-inadequate root-height subspace or infer feasibility from missing conflict certificates. Independent semantic review, broader held-out coverage and all release requirements remain open.
