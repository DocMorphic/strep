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
