# High-five motion changes by correction stage

The per-joint audit now covers a different interaction: all five retained high-five seeds, both actors, and three saved stages. It identifies body correction as the larger contributor to increased acceleration near the contact event, with additional changes from the finger-authoring layer. No animation is changed or approved by this audit.

## Population and provenance

The source is `reports/paired-pose-posture-v1`: seeds **1301, 2089, 3253, 4099 and 5101**, actors A and B, and raw generation, deterministic body correction, and body correction plus authored fingers. These are previously inspected development samples, not new generation or reserved held-out trials. Each clip has 150 frames at 30 fps. The finger layer covers frames 60–90 and reaches its target at the single frame-75 contact event.

`audit_paired_stage_rates.py` verifies the complete scene/stage/actor population, source motions, GLBs, scene transforms, contact definitions, method snapshots and existing engine evidence against the hash-bound `paired-pose-posture-summary-v2` proof. Stage placement and authored contact must agree before comparisons proceed. It decodes every clip at integer and quarter frames: **30 actor clips × 597 times = 17,910 actor samples**, each with 77 joints in placed world coordinates.

Every actor receives three comparisons: raw→body, body→body+fingers, and raw→body+fingers. The existing rate utility records speed and acceleration peaks and their times for every joint over the whole clip, before, approach, event, release, after, entry join and exit join. Event coverage is 73–77; joins are 58–62 and 88–92. Windows overlap intentionally. Speed is a first position difference at the edge midpoint; acceleration is a second position difference at the stencil center. Neither is a force or perceptual naturalness measurement.

The separate `verify_paired_stage_rates.py` checks all actor/clip/result hashes and recomputes **73,920 source/candidate joint-peak values**, their locations, differences and increased-joint counts using direct difference expressions. Maximum disagreement is 1.31e-12. A comparison that reduces the largest joint while worsening a smaller one must still report that increase.

## Completed findings

An increase means greater than 1e-5 in the reported unit. This is a reporting convention, not a newly introduced quality threshold. Authoring a contact pose intentionally changes motion, so an increase alone does not prove the result looks worse.

| Acceleration comparison | Actors with any joint increase | Increased actor-joint peaks / 770 | Actors whose global maximum hides a joint increase |
| --- | ---: | ---: | ---: |
| Raw→body, whole clip | 10 / 10 | 284 | 1 |
| Body→body+fingers, whole clip | 5 / 10 | 27 | 1 |
| Raw→body, event window | 10 / 10 | 244 | 3 |
| Body→body+fingers, event window | 10 / 10 | 68 | 3 |

The largest body-stage event increase is **38.023338 m/s²**: seed 1301, actor B, left middle fingertip, 64.703891→102.727229 m/s² at frame 74. The largest finger-stage event increase is **10.557579 m/s²**: seed 1301, actor A, left thumb tip, 82.220591→92.778170 m/s² at frame 74. The latter actor's whole-clip maximum remains 95.406247 m/s², demonstrating why the global number alone misses the added thumb peak.

Body correction also increases per-joint acceleration in all ten actors at both posture joins. The finger layer has increases in six actors at entry and five at exit. Its largest entry increase is 1.037933 m/s² and exit increase 1.314400 m/s². The strongest event changes are therefore not explained solely by the ends of the finger blend.

The whole-clip body-stage maximum individual increase is 29.926413 m/s² at seed 2089 actor A's left middle fingertip, frame 63. This is distinct from the event-window comparison and should not be substituted for it. Every detailed phase, joint and timestamp remains in the retained reports.

## Geometry, engine and test limits

The historical surface audit remains authoritative for its original sample population: all five authored-finger pairs pass the recorded event region screen, while **all five fail whole-clip collision and floor screens**. The new audit rechecks the hashes binding those results; it does not rerun them or claim quarter-frame surface clearance. The previous **4,500 Godot actor-frame observations** are reused with exact source identities. There are **zero new engine observations**, since no animation changed.

Thirteen focused model-free tests pass. They cover duplicate/missing scenes or actors, clock and frame population, both join windows, timestamp verification, per-joint increases hidden by a lower global maximum, and the preceding motion-cap comparisons. The new population/replay tests and existing joint-rate tests are added to Windows/Linux CI.

This audit does not certify continuous collision, self-collision, anatomy, balance, contact forces, semantic intent or naturalness. Developer/animator ratings and timed cleanup evidence remain absent. All fourteen release capabilities remain unapproved.

## Next decision

Use the first declared development pair, seed 1301, for a coordinated body-and-hand temporal correction; a finger-blend-only change cannot address the larger body-stage event increase. Keep the authored event pose and its independently measured contact evidence, then measure per-joint motion around it and at both correction joins. Full-scene partner collision and floor failures must remain explicit: improvements near frame 75 cannot be promoted as a successful high-five while the recorded failures elsewhere remain. Preserve the other four seeds for comparison rather than selecting a convenient passing actor or replacing held-out reservations.

Evidence is retained under `reports/paired-stage-rates-v1` and `reports/paired-stage-rates-review-v1`. Reproduction requires the existing licensed assets and historical proof files; use fresh output directories:

```powershell
.venv\Scripts\python.exe scripts/audit_paired_stage_rates.py reports/paired-pose-posture-v1 reports/paired-pose-posture-summary-v2/summary.json reports/<new-stage-audit>
.venv\Scripts\python.exe scripts/verify_paired_stage_rates.py reports/<new-stage-audit> reports/<new-stage-review>
```
