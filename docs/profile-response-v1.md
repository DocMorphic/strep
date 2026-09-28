# Single-rule response across actions

2026-09-27. Development study; generation, export verification and engine playback are complete. This does not expand the approved release scope.

The previous profile integration check changed several descriptions at once. This experiment isolates the existing mobility rule, keeping style, training, state and other stats absent. Wave hello, squat-and-stand and forward kick each receive four conditions: no profile, mobility 0, mobility 50 and mobility 100. Three shared seeds (301–303) produce 36 four-second takes. The unchanged checkpoint uses 100 steps, no motion correction and no scene/pose constraints. Every attempt and raw output is retained.

The exact requests and protocol were frozen before execution in `benchmarks/profile-response-v1.json` and `reports/profile-response-v1/protocol.json`. Request digest: `a4107f0787d070958796426f0dc0a168ce336e6494c3693f39d56a6e606f4bcf`. The analysis implementation was also snapshotted before generation. These are development probes, not release holdouts or a learned stat channel. Values within a profile band produce the same text.

## Measurement and decision

The primary descriptor is the 95th minus 5th percentile of a segment angle over the whole clip. Waving uses right upper-arm elevation relative to torso-down. Squatting uses mean bilateral knee-flexion excursion. Kicking uses right thigh angle relative to torso-down; it is unsigned and not anatomical signed hip flexion. These definitions remain unchanged after results arrive. Their limitations include wrist-only waving, action-dependent timing, wrong actions, jitter, and unmeasured movement planes.

For each action, the frozen numerical direction screen requires low < middle < high median excursion and a high-minus-low increase greater than five degrees in at least two of three matched seeds. The five-degree margin is a provisional engineering choice, not a perceptual or biomechanical standard. Plain is reported separately; adding the middle description can itself change the output. A numerical pass never grants action, style or naturalness approval. Reviewers must establish action preservation and recognizable range change across all seeds, including failures.

Seven focused tests pass, checking known angle excursion, rigid-transform/scale invariance, invalid geometry, complete matched pairs, strict margins and separation of numeric response from semantic approval. The comparison viewer uses synchronized frame/seed controls and retains all four conditions. Independent animator review and cleanup-time evidence remain missing.

The release matrix currently proposes 10 mm maximum surface penetration. Recent contact experiments additionally used a stricter 5 mm diagnostic. These must remain separately named; neither is a final frozen perceptual standard. The prior profile integration report was corrected to distinguish them, without changing motion or measurements.

## Reproduction

The frozen study already exists; do not run `freeze` again or overwrite its protocol. Generation uses:

```powershell
.venv\Scripts\python.exe scripts/run_actions.py benchmarks/profile-response-v1.json --output reports/action-jobs/profile-response-v1
```

After the live worker completes, run the full-skin audit and matched provenance analysis, then validate and exercise every exported GLB in Godot:

```powershell
.venv\Scripts\python.exe scripts/audit_body_ground.py reports/action-jobs/profile-response-v1
.venv\Scripts\python.exe scripts/profile_response_study.py analyze
& 'C:\Program Files\nodejs\node.exe' scripts/validate_rig_exports.mjs reports/action-jobs/profile-response-v1
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/action-jobs/profile-response-v1 --output reports/godot-profile-response-v1
```

Godot output requires a fresh directory. Do not repeat generation or engine jobs merely because an observation times out. The all-frame skin audit is not a continuous collision test; half-frame skin evaluation is not included in this study.

## Completed results

Only waving passes the frozen numerical direction screen. The table reports medians over three seeds; every individual take remains in the comparison and machine-readable report.

| Action | Plain excursion | Low | Middle | High | High-low margin passes | Numerical screen |
|---|---:|---:|---:|---:|---:|---|
| Wave | 50.4° | 30.3° | 47.8° | 62.6° | 3/3 | Pass |
| Squat | 152.0° | 145.2° | 152.3° | 146.0° | 1/3 | Fail |
| Kick | 19.9° | 32.9° | 44.8° | 59.3° | 1/3 | Fail |

A median alone hides important kick failures: high-minus-low changes are -8.14°, +53.28° and +3.54°. Squat medians do not increase in order. Waving's middle-to-high ordering also reverses at seed 302; the frozen screen checks median ordering and paired low/high margins, not monotonicity at every seed. No action/style or animator approval follows from its numerical pass.

A post-hoc bilateral diagnostic investigates low right-leg excursions without changing primary scoring. Kick low/302 has 81.5° left-thigh excursion versus 12.1° right, despite the prompt requesting the right leg. Kick high/301 also moves the left thigh more (48.4° versus 24.8° right). These are possible limb-identity failures, not evidence of low physical mobility. `kick-side-diagnostic.json` is explicitly post-hoc; no semantic ratings are inferred.

All 36 raw clips and packages pass provenance checks. All 36 GLBs have zero errors and warnings, and actual Godot playback passes across 4,320 frames (maximum joint-position error 4.35e-7 m). All 72 served GLB/ZIP downloads match local hashes. The full-skin audit finds 35/36 clips above the proposed 10 mm floor limit, with maximum depth 98.93 mm, including hand penetration in squats. Fifteen clips exceed the proposed 5 cm/s predicted-support speed screen; predicted labels are not independent contact annotations. No half-frame or self/object-collision audit is claimed.

Execution took 581.70 seconds including encoding and export, with peak process-tree RSS 3.258 GB. The initial analyzer stopped because its leg labels used UpLeg/Leg instead of SOMA's Leg/Shin. The mapping was corrected before any response scores were obtained, and a test against the actual skeleton was added. Original frozen code, executed code and an amendment record preserve the change. Metric definitions, thresholds, prompts and outputs were unchanged. Seven focused tests pass in 0.47 seconds; no full-suite rerun is claimed for the standalone study and informational UI text.

[Open the synchronized comparison](http://127.0.0.1:8767/reports/profile-response-v1/viewer.html). Browser checks cover all three actions, seed changes, all four conditions, synchronized scrubbing and playback. Studio now explains the observed mobility limitation alongside the experimental profile controls.

Decision: keep generic mobility text experimental. It does not provide reliable cross-action capability control. Next test action-preserving geometric controls using existing pose guidance/editing, with explicit limb identity and contact checks. Do not improve headline scores by changing this study's thresholds or dropping failed seeds. Training remains unjustified by this small study alone, and broader interaction, rig, offline and animator release gates remain open.
