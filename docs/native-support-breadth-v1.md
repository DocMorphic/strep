# Fixed-patch support coverage experiment

The repaired kick-22 passes its numerical screens, but one case is insufficient to enable the new constraint by default. This declared follow-up compares three different retained requests: wave-22, crawl-22 and jump/landing-22. They exercise an upright gesture with a foot pin, ground movement with a hand pin, and a landing foot pin at a later interval. They are development cases already examined for failures, not a held-out test set or an exhaustive action list.

Each case runs control first, then fixed-patch support, from the same original source, warm seed and checked request. Both modes use four outer stages with 60 optimizer iterations per stage. The separate native-body objective is off in both arms. Root/rotation limits, contact tolerances, fixed source rate limits, floor limits and held poses remain unchanged. The sole per-pair optimization difference is `--support-screen`.

The existing runner exports both candidates, independently measures contact/body/rate/preservation results, computes saved NPZ body peaks, and runs actual engine playback with the corrected authored event mapping. Neither mode automatically replaces the source or approves motion quality. All original, warm, failed and intermediate artifacts remain available. Snapshot and completion hashes are checked after each mode and again at batch completion; the pair's source snapshots and protocols must match except for the support switch.

The six fits run sequentially under the normal local worker lock. The batch is launched under `reports/native-support-breadth-v1`; at publication the first control is running. No outcomes are claimed yet. Existing Python/Godot study source stays frozen until the batch is terminal and accounted for.

The per-mode command, after acquiring the original local study data and runtime, is:

```powershell
.venv\Scripts\python.exe scripts/study_native_body_constraints.py --source reports/contact-jobs/contact-breadth-v1-wave-22-repair/source-take --seed reports/contact-jobs/contact-breadth-v1-wave-22-repair/seed --checked-plan reports/contact-jobs/contact-breadth-v1-wave-22-repair/checked-plan --output reports/new-wave-control --no-body-screen --outer-stages 4 --iterations 60
```

Repeat into a fresh output directory with `--support-screen` for the paired arm. Substitute the declared crawl-22 and jump-land-22 input directories for the remaining pairs. Do not reuse output folders, alter inputs between arms or treat the public source repository as including the locally acquired character/model/study data.

After completion, compare every screen and fit time, not just the previously failing foot metric. Any export-feedback repairs must be separate, retained follow-ups using the original budgets. A default change requires broader evidence and end-to-end Studio verification; semantic ratings and cleanup-time review remain outstanding.
