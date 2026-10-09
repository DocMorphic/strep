# Cover remaining contact windows without losing prior repairs

The batch runner makes a bounded pass over the remaining measured contact windows. Each stage ranks all failures in the current retained interval, selects the highest-ranked window that has not been attempted in this pass, and preserves the original source references, physical thresholds and saved precision. Attempted windows remain in every full-interval measurement; skipping another attempt does not make them pass.

One owned worker lock covers the entire batch. Every native stage fully replays the retained history before fitting and compares the proposed state across the complete interval and exterior body boundaries. Only a globally preserving retained result can become the next starting state. A rejected diagnostic stays on disk, its window is recorded as attempted, and the next stage starts from the last retained state. The source clip and preview are not replaced.

The schedule binds ancestral protocols/results/pipelines and archived implementations. Exclusions must be distinct complete canonical windows; incomplete, duplicate or altered rankings are rejected. The between-stage admission budget reserves local-fit time plus 300 seconds before starting another stage. It is not a hard wall-clock limit: use the owned time/memory supervisor for that. Native history replay currently permits at most 32 ancestors. Exhausting a schedule means every window was attempted, not that animation quality passed.

```powershell
.venv/Scripts/python.exe scripts/batch_contact_interval.py reports/box-lift-authored-height-v1 reports/new-contact-batch --start 60 --end 121 --width 3 --stages 3 --seconds 300 --iterations 8 --trust .03 --solve-iterations 10 --max-seconds 1800 --resume-interval reports/box-lift-interval-repair-v2/interval-60-121
```

An asset-free fixture passes 545 checks across seventeen focused modules. Tests cover excluding attempted windows while retaining the complete failure population, rejection of invalid schedules, one batch lock, refusal to adopt rejected results, preservation of completed stages when admission stops, and detection of modified stage records. Another 196 checks across four modules pass without Torch. The CPU-native CI command includes the batch tests; the model-free inventory remains 407 Python modules and 39 Node suites.

## Native evidence

The guarded V1 batch starts from the previously retained original-source V2 interval. Two native stages complete before the memory guard interrupts the third at frames 63–65. 17 of 21 canonical windows have not completed an attempt. The partial window is not adopted. 4 attempts include the two predecessor windows, 69–71 and 72–74. The supervisor exits with code 15 after 1465.407 seconds, with peak process-tree RSS 1,408,827,392 bytes. Guards remain 3,600 seconds, 7 GiB process-tree RSS and 600 MiB available RAM.

| Stage | Frames | Globally retained | Accepted local steps | Local fit | Maximum normalized violation | Squared violation |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [60, 61, 62] | True | 6 | 301.391 s | 2.557511 → 2.549141 | 3645.340635 → 3617.194312 |
| 2 | [78, 79, 80] | True | 8 | 216.610 s | 2.549141 → 2.536970 | 3617.194312 → 3526.205870 |

Each stage checks 22,720 rows per complete interval population, including exterior body boundaries. The retained states lose no passing original row and regress no protected failed original row; previously edited poses outside the new window stay exactly unchanged. These are diagnostic improvements under fixed original gates.

| Frame | Prior penetration | Proposed penetration | Prior maximum palm error | Proposed maximum palm error |
| --- | --- | --- | --- | --- |
| 60 | 22.417 mm | 21.828 mm | 25.549° | 25.192° |
| 61 | 24.777 mm | 23.439 mm | 25.980° | 25.809° |
| 62 | 25.564 mm | 23.958 mm | 26.574° | 26.556° |
| 78 | 24.976 mm | 20.712 mm | 21.469° | 19.663° |
| 79 | 25.336 mm | 20.935 mm | 21.620° | 19.669° |
| 80 | 25.480 mm | 21.046 mm | 21.913° | 21.337° |

The latest retained state still has **0/62 complete physical passes** and **0/62 complete keyed passes**. Failure-family counts are `{"all-reference-position": 9, "normal": 62, "object": 62, "point": 27}`. Worst physical penetration remains 25.359 mm at frame 63. No source clip or preview is replaced.

Independent NumPy replay checks 248 complete native contact poses, 8 boundary frames and 90,880 rows across all stage populations, plus 103 local windows / 309 local poses, 14 retained decisions and 165 proposal archive files. It checks recorded proposal/cut/cap/correction data, solver/saved geometry and retention, carried state/current neighbors, whole-interval selection, exact prior edits and direct original-source rows. Proposal derivatives and optimality are not independently certified. Batch replay additionally binds the schedule, stage records, retained-state flow, remaining attempts and implementation/input hashes.

Batch protocol SHA-256: `11ec0a6a346b600fef9482046e39931af30fe3f5174e52fcdc940db47a7f50f6`. Last completed progress-record SHA-256: `56356c18020f79aa8c2af802bcf177bcbf9bc89b6361cb8e909d4f408a99c8ea`.

The guard records 494,641,152 bytes available RAM below the unchanged 629,145,600-byte minimum. Elapsed time and process-tree RSS stay below their limits. Both owned processes terminate and the lock is free. No completed batch result or third-stage result exists; processing-state partial artifacts remain immutable beside the authoritative failed supervisor record. The latest eligible state is stage 2. The partial 63–65 fit must be retried from that state under the same guards.

These studies cover exact saved native poses and measured geometry/reference/rig/root constraints. Between-key behavior, complete clip quality, self-collision and dynamics, omitted contact/heading/event metadata, retargeting, engine import and human cleanup are still outside approval. All fourteen release capabilities remain unapproved and the full-project goal stays active.

## Completed retry at frames 63–65

Native V6 resumes from the immutable V1 stage 2, replays all four retained ancestors, and completes the previously interrupted window in a fresh report. Admission retains the 2 GiB estimate, 600 MiB reserve and fifteen-second stable-headroom requirement. The worker exits zero after 509.672 seconds; local fitting takes 189.312 seconds, with 34 measurements and eight accepted steps. Sampled peak process-tree RSS is 1,264,013,312 bytes. Independent resource replay verifies all 489 observations, the admission decision, original limits and termination.

| Frame | Prior penetration | Retained penetration | Prior maximum palm error | Retained maximum palm error |
| --- | --- | --- | --- | --- |
| 63 | 25.359 mm | 16.412 mm | 27.325° | 24.836° |
| 64 | 25.050 mm | 16.250 mm | 27.975° | 25.167° |
| 65 | 24.439 mm | 16.138 mm | 28.419° | 25.735° |

Both original grip checks remain passing at the edited keys. Across all 22,720 original rows, no passing row is lost and no protected failed row regresses. All twelve previously edited keys outside the window remain exactly unchanged. The whole-interval maximum normalized violation changes 2.536970 → 2.535837 and squared violation 3526.205870 → 3362.982478. The new worst window is 81–83, with worst penetration 25.347 mm at frame 81. Five of 21 windows have completed an attempt; sixteen remain.

Independent NumPy replay reconstructs 124 complete native contact poses, four exterior boundary evaluations and 45,440 whole-interval rows, plus 35 local windows / 105 local poses, eight retention decisions, eight margin attempts, eight correction proposals and 72 proposal archive files. It also binds the complete four-ancestor chain, selection exclusions, unchanged original references, carried pose arrays and batch state. The audit exits zero in 32.485 seconds, with 33 independently replayed resource observations and sampled peak RSS 1,850,830,848 bytes. Its initial 512 MiB admission estimate underestimated full NumPy replay memory; future full interval audits should reserve 2 GiB plus the unchanged 600 MiB floor. The actual RSS/time/RAM guards stayed active and passed. Derivatives and optimality are not independently certified.

Stage result SHA-256: `42c7d008f4b2606fea2a7b6753cc6394d265026fd8e3aef2e8ab16d67073cf07`. Completed batch result SHA-256: `ff3d5ae2034754dd958b2b2781e2e5c84e78721271f5cabca035f8996b29c210`. Local immutable artifacts and bound independent auditors live under `reports/box-lift-interval-batch-v6/`; bulky outputs and vendor assets are excluded from the public repository.

This is a retained diagnostic improvement: **complete physical and keyed passes remain 0/62 and 0/62**. All 62 keys still fail normal and object clearance; 27 fail point constraints and nine fail reference position. Original and earlier interrupted artifacts stay unchanged. No clip/preview replacement, newly generated or trained motion, engine acceptance, human cleanup evidence or release approval follows from this result. Continue from the verified V6 state, beginning with 81–83, under the original physical and resource limits.
