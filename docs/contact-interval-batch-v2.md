# Interrupted continuation after one completed contact window

Native V7 continues the [independently verified V6 state](contact-interval-batch-v1.md), with identical original references, tolerances, saved precision and root/rig limits. The first window, 81–83, completes and is retained by the native whole-interval check. It makes three guarded steps, with 45 measurements and 23 nonlinear inner queries in 305.078 seconds, stopping at `time_or_measurement_budget`. The local budget is checked between computations, so it is not a strict wall-clock cutoff.

| Frame | Prior penetration | Recorded retained penetration | Prior maximum palm error | Recorded retained maximum palm error |
| --- | --- | --- | --- | --- |
| 81 | 25.347 mm | 22.431 mm | 22.117° | 20.837° |
| 82 | 24.982 mm | 22.016 mm | 22.197° | 20.965° |
| 83 | 24.436 mm | 22.275 mm | 22.135° | 21.114° |

These are **recorded native measurements**, not an independent geometric reconstruction. Both recorded grip checks remain passing at these keys, while normals and box clearance still fail. Complete physical and keyed passes remain 0/62 and 0/62.

## Guarded interruption

The next window, 75–77, is interrupted before it produces a result. Free RAM falls to 574,029,824 bytes, below the unchanged 629,145,600-byte floor. The supervisor exits with worker code 15 after 1094.062 seconds; sampled peak process-tree RSS is 1,416,122,368 bytes. Independent resource replay verifies all 1,045 observations, admission, clock/peak/stop/exit accounting, input/method bindings and worker termination. The 2 GiB estimate, 600 MiB reserve, fifteen-second stable admission, 7 GiB RSS cap and 1,800-second execution guard remain unchanged.

Only stage 1 has a completed result. The batch progress record selects that state; stage 2 and the batch have no completed result. Partial observations stay immutable and are not adopted. Six of 21 windows have completed native attempts; fifteen remain, including interrupted 75–77.

## Verification still pending

A lightweight independent check verifies stage/input/method/output hashes, exact carried arrays outside 81–83 and complete recorded-row continuity. Across 22,720 original recorded rows, no passing row is lost and no protected failed row regresses. This check exits zero after 8.344 seconds, with sampled peak process-tree RSS 75,022,336 bytes. Independent resource replay verifies its ten samples. It does not remeasure geometric rows, certify contact errors or replay the complete proposal decisions.

Fresh NumPy geometry/local/batch auditors are prepared for the completed stage and the interrupted batch. Their guard defers after 60.688 seconds without starting a child. Independent admission replay verifies all 61 samples and the unmet 2,776,629,248-byte requirement. The full audit keeps its corrected 2 GiB estimate plus 600 MiB reserve; the previous underestimate is not reused. V7 therefore remains pending independent geometry validation. **Fully verified V6 remains the trusted baseline** until that replay succeeds.

Completed stage result SHA-256: `1bd99e5533f64d4a8b5cf09ed7c02e59c29d70606d858619c9a48cc2a323b113`. Progress record SHA-256: `dab538e62ec033259a4089c301a9e39cba9477fa01591bee336bdcf883834487`. Native guard protocol SHA-256: `8b16dafacaab81b976234e91657b3b1ed080b9ac0da28b4c4173e601b0d29c8f`. Frozen local artifacts, partial trials, bound auditor sources, resource traces and the smaller metadata check stay under `reports/box-lift-interval-batch-v7/`, excluded from the public repository along with vendor assets. Initially prepared completed-batch auditors remain unused; separate interrupted-batch auditors preserve the actual failure classification.

## Next work

Finish the independent replay when its resource profile admits it. Repeated full geometric replay of every retained ancestor is also a growing runtime cost. Investigate bounded same-worker reuse of verified history with complete artifact/input/method bindings rechecked, explicit context invalidation and no trust in saved attestations. This is planned, not implemented or benchmarked here.

Continue broader arbitrary-action, partner/object, rig transfer, editing/style, transition/engine and actual developer-review work. These exact-key diagnostics do not approve between-key behavior, foot sliding, balance/dynamics/self-collision, omitted metadata, action semantics, engine behavior or animator cleanup. No original clip/preview replacement, new generation/training or release approval is produced. All fourteen capabilities remain unapproved; the single project-wide goal stays active.

## Completed independent replay — 2026-10-09 follow-up

The earlier deferrals and interrupted native batch remain unchanged. A later fresh NumPy worker completes the full audit against the exact Python implementation used by the original V7 worker. Its frozen source snapshot was checked against the native archives before current replay code changed. No current implementation is substituted for the original geometric auditor.

Independent local replay reconstructs 46 recorded windows / 138 native poses, verifies three accepted steps, three margin-start attempts, four correction proposals and all 33 proposal archive files. Whole-interval replay reconstructs both baseline and proposed states across 62 contact keys and two exterior frames each, including all 22,720 original rows. Passing-row losses and protected failed-row regressions are both zero; prior edits and motion arrays outside 81–83 remain exact. The independent interrupted-batch replay confirms one completed retained stage, six completed window attempts, fifteen remaining windows, and no adoption of partial 75–77.

This independently confirms the measurements in the table above. **V7 stage 1 is now the latest verified retained state.** Complete physical and keyed passes still remain **0/62 and 0/62**. The worst remaining penetration is 24.831 mm at frame 71; because its window has already been attempted, 75–77 is the next unattempted window. No animation-quality or release gate changes.

The fresh guard exits zero in 61.656 seconds (48.391 seconds after launch), with 814,731,264 bytes sampled peak process-tree RSS. Independent resource replay verifies all 61 samples, admission, exit and bound sources. Full audits retain the conservative **2 GiB estimate plus 600 MiB reserve**, a three-second stable admission and the existing time/RSS limits; this one result does not lower that estimate. Native fits still require fifteen-second stable admission.

Replay guard protocol SHA-256: `49f336cc9fba0a6a946e94148583ffa1dc02f1bab347f557b9219bd0ab09d8bc`; trace SHA-256: `811efa48bec1e9add88734f660086f37b53f9ef6677f4fee52319dd4e83330ce`. Bound outputs are `stage-1-frozen-audit/independent-local-replay.json`, `stage-1-frozen-audit/independent-interval-replay.json`, `stage-1-frozen-audit/summary.json`, `independent-frozen-batch-replay.json` and `frozen-replay-guard-audit.json` under the same ignored V7 report directory. Source snapshots, original deferrals, incomplete native stage and all raw records remain preserved.
