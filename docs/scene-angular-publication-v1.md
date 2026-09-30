# Angular checks now gate new paired publication

New Studio paired jobs enable angular constraints in the fitter and run a separate angular replay after positional replay. A selected candidate cannot be published without passing evidence for both actors, every supported joint and the original sampling clock. Source-only results remain available when no candidate is selected.

`verify_scene_pair_angular.py` samples the actual source and selected GLBs, uses independent per-joint quaternion composition, and retains the original knot-span maxima. The comparison tolerances remain 1e-5 rad/s and rad/s². It binds the prepared policy, fit result, trial record, source/candidate bytes and replay implementation. The publication gate checks complete observation counts, both metrics, finite increases, actor identity, selection and matching evidence. Angular proof is also recorded in new publication provenance.

The current paired publication path still supports the existing 77-joint review rig. This change does not establish broad rig-transfer qualification, whole-clip dynamics, naturalness or release readiness.

## Historical candidate review

The previously published half step from `scene-pair-fit-v2` was accepted under the older positional and collision checks. Its new independent angular replay fails:

| Actor | Speed exceedances | Acceleration exceedances | Largest speed increase, rad/s | Largest acceleration increase, rad/s² |
| --- | ---: | ---: | ---: | ---: |
| A | 7 | 29 | 0.000493722 | 0.347719025 |
| B | 4 | 58 | 0.002326519 | 0.556342419 |

The replay covers 38,346 observations across 126 times and 77 joints per actor. These 98 numerical exceedances prevent approval under the current motion checks; they are not a perceptual rating. Its previous geometric and engine observations remain historical evidence rather than proof of the new condition.

The scene collection now has an appended, hash-bound display correction. Its candidate note starts with “Historical candidate: failed independent angular replay (98 limit exceedances).” All original publication files, including the manifest, clips and provenance, retain their hashes. The server applies the supplemental note when serving the manifest and returns an error if the bound supplemental evidence changes. This keeps historical outputs available without presenting their earlier local acceptance as current approval.

The server was restarted to load that display handling. Direct handler invocation verified the served note and all original publication hashes; listener-process checks confirmed the restarted service. No HTTP or rendered-browser verification is claimed.

## Evidence and remaining work

Local evidence:

- `reports/scene-pair-published-angular-v1`: completed historical candidate replay.
- `reports/scene-region-jobs/paired-curve-controls-trimmed-v1/angular-review`: copied supplemental evidence.
- The same collection's `review-update.json`: bound display correction.
- `reports/scene-pair-angular-display-v1.json`: direct-handler and listener verification.

Thirty-three focused tests cover actual GLB replay with synthetic rigs, source-only handling, changed evidence, job orchestration, publication rejection and immutable display updates. A synthetic orchestration test isolates Windows locking and optional runtime packages; it does not claim model or engine integration.

The newer full-step candidate with empirical export margins already passes independent angular replay and Godot import. Its existing 148-time mesh audit remains live under `reports/scene-pair-reserve-geometry-v1`; it has not been restarted or published. Its actual geometry result is the next decision point. All release capabilities remain unapproved, and no held-out population or human review has been consumed.
