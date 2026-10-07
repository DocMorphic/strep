# Offline pinned partner-clearance jobs

`scripts/native_pair_clearance_job.py` provides a command for proposing edits to existing native clips under their original [stored-pair Job contract](native-stored-pair-job-v1.md). The request supplies the actors, skin vertex groups, exact native time and fixed world axis. The command keeps every original motion/contact/reference bound and retains every requested solver variant and fraction, including failed exports. Original clips stay selected.

```sh
python scripts/native_pair_clearance_job.py --request reports/my-input/request.json --output reports/my-clearance-job
```

The output directory must be fresh and outside any input study with an existing `result.json`. Input paths resolve against the request directory; exact SHA256 pins are required. A request has exactly these fields:

```json
{
  "schema": "strep-native-pair-clearance-job-v1",
  "job": {"path": "job.json", "sha256": "<exact Job file SHA256>"},
  "guide": {"path": "guide.json", "sha256": "<exact guide file SHA256>"},
  "families": ["original-norms", "event-key-preserved"],
  "event_times_s": [0.5]
}
```

Use the actual existing native event time, which may differ from the decimal value 0.5. The `families` field selects numerical variants; it does not restrict action genres. `event-key-preserved` requires explicit unique native-clock event times; using only `original-norms` requires an empty event list. Up to 16 event times and 96 complete parameter-preservation rows are accepted. Event parameter preservation guides proposals; actual decoded contacts still have to pass their original limits.

The guide contains exactly `actor_a`, `vertices_a`, `actor_b`, `vertices_b`, `time_s`, `axis_world`, `clearance_m` and `scale_m`, as described in [the guide API](reusable-clearance-guide-v1.md). Actors must exist and differ; vertex groups must be explicit, unique and in range; the axis must already be unit length. No fixture hand IDs are built into the command. Existing limits of 96 complete controls and 4,096 selected pairs apply. This is a fixed-axis vertex-pair proposal guide, not a collision certificate or a learned interaction model.

The command authenticates the original Job, requires a decoded scalar/vector/reference feasible starting point, snapshots methods and inputs, and builds fresh complete native and guide stencils through the stored-key continuous proxy. It uses the Job's original difference, sparsity, trust and fraction budgets. Every export receives the original authoring/storage audit, full decoded motion/vector/contact observations and strict reference bounds. Complete native clocks and norm populations stay intact. Proposed clips passing all original motion/vector/reference/control bounds are ranked by guide-frame partner depth, then crossing count; only that declared selection receives full original scene geometry. No passing proxy substitutes for a decoded export.

Outputs include source snapshots, a full model and sparse Jacobians, complete stencil observations, solver records, every proposed actor clip, per-export decoded observations and failure records. Successful and failed runs have distinct terminal progress states. This command does not automatically repair storage, append a clip, select a library asset, generate a prompt, or grant geometry, semantic or human-quality approval. Required dependencies and original pinned assets must already be available; the repository remains a source snapshot rather than a bundled offline installer.

**122 focused local tests pass with zero skips**, including 15 new command cases. Tests exercise actual pinned clips with unequal vertex groups, both numerical variants, complete native arrays and exported payloads, immutable inputs, invalid schemas/pins/clocks, failure snapshots and mutation during solving. The first run passed 121 tests and exposed a real terminal-state bug: both completed and failed runs left progress marked `processing`. The command now writes the correct terminal status, with assertions for both outcomes; the failing test report is retained. The suite is registered once in Linux/Windows CI. Hosted success remains unverified.

At the [previous 46-choice internal anchor](reusable-clearance-guide-v1.md), a fresh study retains all 90 controls, 180 complete central stencils, 30,450 original vector norms, 1,707 native samples and 1,673 geometry times. The 64 hand-pair guide, axis, clock and all original limits stay fixed. All eight exports improve actual guide deficit and pass contacts, reference budgets and trust bounds, but decoded motion still fails:

| Guidance | Fraction | Decoded failures | Continuous proxy failures | Guide-frame depth, mm |
| --- | ---: | ---: | ---: | ---: |
| Original norms | 1 | 9 | 2 | 5.021658 |
| Original norms | 0.5 | 9 | 0 | 4.947227 |
| Original norms | 0.25 | 7 | 0 | 4.908700 |
| Original norms | 0.125 | 1 | 0 | 4.889092 |
| Event key preserved | 1 | 8 | 6 | 4.942761 |
| Event key preserved | 0.5 | 2 | 0 | 4.907061 |
| Event key preserved | 0.25 | 8 | 0 | 4.888426 |
| Event key preserved | 0.125 | 3 | 0 | 4.878904 |

No curve-study export qualifies for full geometry. A separate manual consumer reproduces all complete stencils, native/guide derivatives, event rows, strict rays, objectives, actual exported worlds and original reference/source-rate/contact observations. Its geometry transport flag stays false because no full scan was selected.

A matched run through the new public command reproduces all 180 complete stencils, both sparse Jacobians, original systems and event rows, and both complete solver records exactly. All eight A/B export pairs are byte-identical to the independently replayed study, and every common decoded observation and guide-frame query matches. The command's additional full vector-norm observations are separately reproduced from the legitimate original export context with manual storage choices. Correct terminal completion is verified. This repeats the model only to validate a new orchestration entry point; it introduces no new geometry selection or motion approval.

For a separate fixed-control storage experiment, choose the largest actual guide improvement among original-box/reference/continuous-proxy passing exports. This selects the original-norm half step despite its nine decoded failures. The existing balanced positional/angular search keeps the original one-ULP and 64-choice storage envelope. The start plus 200 exported neighbors are retained; stages select `storage-0-43`, `storage-1-0`, `storage-2-58` and `storage-3-7`. Final absolute choices number 48. All original scalar/vector/contact/reference bounds pass, with normalized vector-norm maximum excess -0.00000730310020938. No control, rate or contact acceptance tolerance is enlarged.

The repaired full geometry still fails: **4.969956705 mm**, **29,478 triangle records and 1,544 failed conditions**. The whole-clip depth is worse than the previous seed's 4.889799077 mm; improving the selected frame's guide does not establish monotonic whole-clip improvement. Source selection and all approvals remain unchanged.

A separate consumer replays all 201 actual exports from the legitimate original context, with manual absolute storage choices and complete native/scalar/vector/contact/static/reference observations. It reconstructs each full original option population, round-robin prefix, absolute transition, merit and stable best eligible probed selection without producer/search APIs. The full geometry archive is checked for transport fidelity using shared collision predicates. This verifies the retained failure and bounded search, not independent geometry arithmetic or exhaustive feasibility.

A fresh genuine next Job copies the repaired 48-choice seed and records the changed absolute storage choices explicitly. Every original non-anchor field remains exact. Fresh Job reopening and the separate original-context manual decoder reproduce its controls, payloads, full native worlds, scalar/vector norms and contact/static/reference bounds. The known full geometry failure remains attached. No library append or asset selection occurs. Both controls and storage changed, so another curve solve must rebuild its derivatives.

These generated-fixture results do not establish arbitrary-action correctness, production anatomy, continuous physics, game-engine quality, human ratings or cleanup time. All fourteen release evidence arrays remain empty, and the full-project goal stays active.
