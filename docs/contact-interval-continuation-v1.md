# Continue a globally preserving saved interval

Independent window repairs can discard earlier edits and use stale neighboring poses. The interval runner now accepts a fully replayed predecessor state, carries its saved pose tracks and per-frame controls, and selects the next window from that state's complete measurements. Original source clips, timing, references, rig budgets and physical limits remain fixed.

Continuation requires a complete, globally preserving diagnostic result with matching original input bindings, coverage, clock and native definitions. The replay binds archived implementations, all retained/source/proposed snapshots, observations and streamed proposal records. It recursively checks an acyclic history of at most 32 stages, reconstructs the exact saved starting state and current exterior neighbors, remeasures every local observation, replays nonlinear/tangent/saved retention and proposal caps/corrections, and repeats the complete interval comparison. It rejects unmeasured queries, changed decisions, missing rows/observations, rebased inputs or altered saved precision. This replay does not independently certify proposal derivatives or optimality.

Both unedited and previously edited controls travel with the saved state. The next local window receives the current saved exterior keys; cache invalidation does not change original references. A repeated window keeps its exact saved seed. A neighboring window sees previous corrections across its boundary. Each new fit still needs complete saved-row preservation and improvement against its current predecessor; the replay chain establishes preservation against the original source without treating a new reference as the origin.

```powershell
.venv/Scripts/python.exe scripts/repair_contact_interval.py reports/box-lift-authored-height-v1 reports/new-interval-continuation --start 60 --end 121 --width 3 --iterations 8 --trust .03 --seconds 300 --solve-iterations 10 --resume-interval reports/box-lift-interval-repair-v1/interval-60-121
```

A fresh source-only fixture passes 520 focused checks across sixteen modules. Coverage includes successful two-stage continuation, unchanged original arrays, current neighbor/control propagation, cycle/capacity limits, wrong clocks/scopes/policies, and tampering of poses, decisions, rows, observations and archives even after outer hashes are rewritten. The new native replay test module is included in the CPU-native job. The declared model-free inventory stays at 407 Python modules and 39 Node suites, and the other workflow fields remain unchanged.

## Native continuation

V2 fully binds and replays V1 before fitting: 49 local observations, 124 complete contact-pose audits and 45,440 scalar rows across its original/proposed interval populations. It then selects **69–71** from the retained state and uses the corrected exterior frame 72. Both prior poses and their controls are carried into the new full-interval comparison.

Eight steps are retained in eight iterations. The local fit stops at its iteration limit after 299.687 seconds, with 73 measurements, 74 observations, eight margin starts, sixteen correction proposals and no unretained nonlinear inner queries. The supervisor exits successfully after 443.672 seconds, with peak process-tree RSS of 1,200,513,024 bytes under the unchanged 3,600-second / 7 GiB / 600 MiB available-RAM guards. Dense/coupled values match exactly, and maximum Jacobian difference is 4.441e-15.

| Frame | Previous penetration | Retained penetration | Previous failing palm angle | Retained failing palm angle |
| --- | ---: | ---: | ---: | ---: |
| 69 | 24.688 mm | 24.530 mm | 27.107° | 26.990° |
| 70 | 25.194 mm | 24.800 mm | 26.100° | 25.861° |
| 71 | 25.633 mm | 24.831 mm | 25.015° | 24.694° |

Improvements are modest and none of these contact poses passes overall. Frame 69's failing grip improves from 5.148 to 5.129 mm but still exceeds the unchanged 4.990 mm working limit. Previously passing grips and palm normals remain passing, and the prior 72–74 arrays remain exactly unchanged.

The new 22,720-row whole-interval comparison loses no passing row and regresses no protected failed row. Maximum normalized violation falls from 2.564381 to 2.557511 and squared violation from 3655.065891 to 3645.340635. A separate bound comparison against V1's original-source rows also finds zero losses/regressions. The update is retained as a diagnostic interval state; no source clip or preview is replaced.

Independent NumPy replay verifies both full populations (124 native contact poses plus four body boundaries, 45,440 rows), 74 local windows / 222 local poses, all eight retained decisions, eight margin attempts, sixteen corrections and 96 proposal archive files. It checks complete saved and solver geometry, native FK/eight-weight skin, current exterior context, carried parameters, exact prior-pose preservation, recorded proposal/cut/cap data, nonlinear/tangent/saved decisions and all original/method/output bindings. Proposal derivatives and optimality remain outside this independent certificate.

The next failure-first order begins **60–62**, **78–80**, **63–65**. The full worst physical depth is 25.564 mm at frame 62. All 62 contact keys still fail palm orientation and clearance, grip failures remain 28/62 and body-reference failures 9/62; there are still zero complete keyed or physical passes. Continuation can now accumulate verified repairs, but the next work must cover the remaining measured interval rather than presenting these two windows as a solved lift.

Protocol SHA-256: `1d303e55ca607b37137c9db688bb4af44434f4407fa078952637d1f5334ce50d`. Result SHA-256: `8d59e7c3640c5b7f14718a0e80fa80f6cd8991be658e886889cbdebea216b5d1`.

Saved interval adoption remains a diagnostic decision; omitted contact/event/heading metadata, complete action quality, between-key behavior, surface/self-collision, dynamics, retargeting, engine import and human cleanup remain unapproved. All fourteen release capabilities remain unapproved and the full-project goal remains active.
