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

`scripts/contact_candidate_recovery.py` first replays the trusted native ancestry and independently checks the recorded supervisor stop. It accepts only a reaped RAM-stopped attempt with no final stage result. It binds every partial artifact and the original inputs, archived implementation, skeleton metadata and source history. Each saved retained candidate must reconstruct its pose, stay within the original coordinatewise normalized trust box and bounds, preserve both solver and stored local rows, and improve the complete current interval without any tradeoff. A failing global candidate remains rejected even when its local flags claim retention.

The tool writes a **new, separately named geometry recovery**, with `interrupted_stage_complete=false` and every approval field false. Resume replays the ancestry and recovered candidate geometry again; a saved receipt is insufficient. The existing in-memory history session can reuse only its own already verified state after rechecking every binding and returns independent array copies. Scheduling binds the new pose result to the original retained ancestor while adding **no completed attempt**. Completed rejected windows are preserved by an explicitly supplied prior batch schedule.

Always run the native tool under its existing resource supervisor, with fresh output folders. Example argument structure, replacing the source paths with the exact intended study:

```powershell
.venv/Scripts/python.exe scripts/run_guarded_job.py --worker scripts/contact_candidate_recovery.py --output reports/FRESH-GUARD --expected-rss-mib 2048 --stable-seconds 15 --admission-seconds 600 --max-seconds 1800 -- STUDY INTERRUPTED-STAGE INTERRUPTED-GUARD VERIFIED-INTERVAL reports/FRESH-RECOVERY --start 60 --end 121
```

Focused checks initially pass 119 recovery/interval cases. The final recovery/scheduling suites pass **74 cases**, including changed pose bytes, resealed geometry mismatches, relaxed limits, wrong clock, live/completed sources, an exterior passing-row loss, ancestor/cycle errors, schedule preservation and changed cached inputs. The new recovery suite is registered in both Linux and Windows native CPU checks; the 423-module model-free inventory and 41 Node suites are unchanged. Hosted CI for this change is not yet claimed successful.

Native confirmation against the actual rig and mesh is separately guarded under ignored `reports/box-lift-candidate-recovery-v1/`. It is waiting for the unchanged resource profile at this documentation checkpoint; no native completion is claimed. **V10 stage 2 remains the trusted motion, V11 the completed schedule: 13/21 attempts, eight remaining.** V12 remains interrupted. All fourteen release capabilities remain unapproved. The single full-project goal still includes arbitrary actions, scenes/partners, rigs, editing/style, transitions, engine validation and actual developer/animator review and cleanup measurements.
