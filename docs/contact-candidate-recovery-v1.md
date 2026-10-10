# Saved contact candidates after a RAM stop

The [V12 continuation](contact-interval-batch-v7.md) stopped during an inner solve. Its three locally retained poses were complete, but its optimizer report and whole-interval result were absent. A new geometry recovery format can inspect those saved poses without inventing a finished optimization or mutating the interrupted stage.

## Independent saved-pose measurement

A fresh isolated NumPy replay checks all **38 partial observations / 114 native poses**, using the original forward kinematics, full eight-weight skin, 18,056 vertices, source references, rows and limits. It also checks the three locally retained candidates over all **22,720 original interval rows**, including the exterior body edges. Each passes the original zero-tradeoff retention policy against V10 stage 2: no source passing row is lost and no protected source row regresses. All outside selected-frame values stay unchanged; the existing root precision promotion policy still applies.

| Saved candidate | Original squared normalized violation | Candidate squared normalized violation | Worst normalized violation |
| --- | ---: | ---: | ---: |
| `iteration-1-backoff-6` | 3,132.339194884 | 3,124.392514335 | 2.484240303 |
| `iteration-2-backoff-10` | 3,132.339194884 | 3,115.162428278 | 2.484240303 |
| `iteration-3-backoff-14` | 3,132.339194884 | 3,107.173069317 | 2.484240303 |

These are small diagnostic improvements, not solved box manipulation. Full physical contact passes remain **0/62**. The local replay does not certify the interrupted optimizer's derivatives, tangent guards, start archives or completion. The interval replay certifies saved geometry, not dynamics, intermediate interpolation, metadata, export, engine playback or human realism.

The isolated replay completes in 37.234 seconds; the outer supervisor records 38.281 execution seconds, 201,306,112 bytes sampled process-tree peak and 42 resource observations. Independent resource replay verifies the unchanged 2 GiB plus 600 MiB admission profile and terminal success. A first launch with an incorrect positional argument failed before either numeric phase; its logs and resource receipt remain preserved.

Private receipts under ignored `reports/box-lift-partial-recovery-v1/`:

- `local-replay.json`: `adf6777299f86bb202912e43ba52064923bde978778e5d6b81dd3c9992a7f7ff`.
- `interval-replay.json`: `51651c34f5b4e53e15fc42df1d9de2aca3ddf22b63c54e008e295ff5ae84c39b`.
- `resource-audit-v2.json`: `848815071e310ca2180c8b4b07a5c8fd7fb1d7e6e9171fdfa786af668b11d23f`.

## Recovery and continuation

`scripts/contact_candidate_recovery.py` first replays the trusted native ancestry and independently checks the recorded supervisor stop. It accepts only a reaped RAM-stopped attempt with no final stage result. It binds every partial artifact and the original inputs, archived implementation, skeleton metadata and source history. Pose and resource-audit helper bytes are captured before ancestry replay and checked before/after copying and at completion. Persistent history binds immutable copies, allowing later code changes only with fresh complete numeric replay. Each saved retained candidate must reconstruct its pose, stay within the original coordinatewise normalized trust box and bounds, preserve both solver and stored local rows, and improve the complete current interval without any tradeoff. A failing global candidate remains rejected even when its local flags claim retention.

The tool writes a **new, separately named geometry recovery**, with `interrupted_stage_complete=false` and every approval field false. Resume replays the ancestry and recovered candidate geometry again; a saved receipt is insufficient. The existing in-memory history session can reuse only its own already verified state after rechecking every binding and returns independent array copies. Scheduling binds the new pose result to the original retained ancestor while adding **no completed attempt**. Completed rejected windows are preserved by an explicitly supplied prior batch schedule.

Always run the native tool under its existing resource supervisor, with fresh output folders. Example argument structure, replacing the source paths with the exact intended study:

```powershell
.venv/Scripts/python.exe scripts/run_guarded_job.py --worker scripts/contact_candidate_recovery.py --output reports/FRESH-GUARD --expected-rss-mib 2048 --stable-seconds 15 --admission-seconds 600 --max-seconds 1800 -- STUDY INTERRUPTED-STAGE INTERRUPTED-GUARD VERIFIED-INTERVAL reports/FRESH-RECOVERY --start 60 --end 121
```

Focused checks initially pass 119 recovery/interval cases. The final recovery/scheduling suites pass **78 cases**, including changed pose bytes, resealed geometry mismatches, relaxed limits, wrong clock, live/completed sources, an exterior passing-row loss, ancestor/cycle errors, schedule preservation and changed cached inputs. The new recovery suite is registered in both Linux and Windows native CPU checks; the 423-module model-free inventory and 41 Node suites are unchanged. Hosted CI for this change is not yet claimed successful.

Native confirmation against the actual rig and mesh is separately guarded under ignored `reports/box-lift-candidate-recovery-v1/`. It **defers after 600.109 seconds with no child**: available headroom never remains above the unchanged 2 GiB plus 600 MiB requirement for the required 15-second stability interval. Independent replay verifies all 594 admission samples and the terminal decision; receipt SHA-256 is `8d58d6a35eecc17a89e6fe44db85d9e79030e215fdcf775559f8eaa5cc32ed90`. No native completion or numerical result is claimed from this attempt. At that first admission checkpoint, V10 remained the trusted motion and V11 the completed schedule. The raw deferred attempt stays preserved; the completed second attempt below supersedes the motion-state description.


## Completed native recovery and editable exports

After source checks finish and headroom improves, the second native attempt admits after **192.094 seconds**, executes for **569.187 seconds**, and completes with a sampled process-tree peak of **830,947,328 bytes**. Independent resource replay verifies all **728 observations**. It replays the ten-state V10 ancestry and rechecks each saved candidate, including the sequential complete-interval retention policy. All three are retained without a lost passing row or protected-row regression.

A separately guarded artifact comparison verifies that the native recovery's complete pose arrays and dtypes exactly equal the independently replayed third candidate. All 22,720 rows for each of the three candidates agree with the independent evidence, with **zero measured row difference**. This is complete parity with the earlier independent geometry replay, not a new skin or optimizer-trajectory replay. Its 54 resource observations are independently checked. The production scheduling function then passes on the actual saved V11 history and new recovery: all 13 completed attempts, including the rejected 120–121 attempt, remain present; 111–113 remains unfinished and eight windows remain. Its 19 resource observations are checked.

The existing native exporter produces `baseline.glb` and `candidate.glb`, each containing all **180 keys at 30 fps**, with the source mesh, materials and all eight weights intact. Fixed-skeleton reconstruction differs from the stored joints by at most **1.302 micrometres**; serialization differs from the reconstructed pose/skin by at most **0.102 micrometres** in position. The source and candidate exports meet the same existing reconstruction/serialization limits. These are editable body-only assets: object/partner scene context, event/foot-contact metadata, intermediate-time contact, dynamics, actual engine playback and human quality are not certified. The export supervisor completes in 13.969 execution seconds with 121,982,976 bytes sampled peak; all 19 resource samples are independently verified. The upstream SOMA license is copied alongside the private exports.

Native/parity/scheduling evidence remains under ignored `reports/box-lift-candidate-recovery-v1/`; exports and their immutable input/implementation manifest remain under ignored `reports/box-lift-candidate-preview-v1/`. Key receipts:

- Native result: `3a02c4f20a6a772a7a9d651667bed11ae47833a232f27489888933dba3622616`.
- Native resource replay: `0aa13a89fc941ef6188b6c81054b20b694f6e8f0a052424ac03a5b59b8c2ab4a`.
- Independent artifact parity: `b01fbf72654366344dd59d0532eb13fedf2b7affbd37b13d7374f011b1effe05`.
- Production scheduling replay: `e720c6396cc9c80d9e2a7b0bb9ea0c3955a1184addb4122ebb484aaa71fd8307`.
- Editable export verification: `a3903dfaebe2d155c27a0ac6e312d0b8c04605129445a6dc00db99fa2eddd78a`.

**The verified diagnostic resume motion is now the separate native recovery; V10 stage 2 is its fully replayed ancestor, and V11 remains the completed schedule.** Any subsequent worker must replay recovery before using it. V12 itself stays interrupted, completed attempts stay **13/21**, and box-lift physical contact passes stay **0/62**. No metadata, engine, human-review or release approval is granted. All fourteen capabilities and the same full-project goal remain open; continue bounded coverage and broad action/scene/partner/rig/edit/style/transition/engine plus genuine review and cleanup work. Hosted CI remains pending for the current source changes.
