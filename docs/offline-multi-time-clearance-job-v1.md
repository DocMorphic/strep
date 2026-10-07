# Offline multi-time partner-clearance jobs

`scripts/native_pair_clearance_guides_job.py` accepts a pinned original [stored-pair Job](native-stored-pair-job-v1.md) and multiple explicit partner guides. Each guide identifies two actors, their skin vertex groups, an exact existing native time, a world direction, clearance and scale. The command proposes edits to existing clips; arbitrary action generation remains a separate part of Strep.

```sh
python scripts/native_pair_clearance_guides_job.py --request reports/my-input/request.json --output reports/my-multi-time-job
```

The output must be fresh and outside immutable input studies. Paths resolve against the request directory and every input requires its exact SHA256. The request has exactly these fields:

```json
{
  "schema": "strep-native-pair-clearance-guides-job-v1",
  "job": {"path": "job.json", "sha256": "<exact Job SHA256>"},
  "guides": {"path": "guides.json", "sha256": "<exact guide-list SHA256>"},
  "families": ["original-norms", "event-key-preserved"],
  "event_times_s": [0.5],
  "axis_mode": "explicit"
}
```

Use the actual existing native event time, which may differ from the decimal value 0.5. `families` chooses solver variants rather than action categories. The event-preserving variant requires explicit unique event times; requesting only `original-norms` requires an empty event list. The original maximum of 16 times and 96 complete parameter-preservation rows applies. Preserving key parameters guides the proposal; actual decoded contacts must still satisfy their original limits.

`guides.json` is a list of one to 64 [eight-field descriptors](reusable-clearance-guide-v1.md), with up to 4,096 total vertex pairs. Descriptor order, unequal group sizes, reversed actor order, individual units and exact native times stay explicit. Exact duplicate final descriptors reject. The existing [multi-time API](multi-time-clearance-guides-v1.md) keeps every original native condition and shares the complete perturbation worlds across all guides.

With `axis_mode: "explicit"`, every supplied unit direction stays fixed. With `axis_mode: "rank-patch"`, each supplied direction is the baseline for a finite pose-specific search. Both patches must contain at least three vertices and a nondegenerate original indexed triangle. The command includes every original triangle wholly inside each explicit vertex group, remapping its indices without inventing a hull. It ranks both signs of the baseline, all contained face normals and all nonzero crosses of unique indexed patch edges at the authenticated decoded starting pose. It preserves the full candidate records and checks every recorded direction is finite and unit length. Only the descriptor's axis changes. An oversized complete family rejects rather than returning a truncated prefix.

Ranking minimizes the squared negative deficit over every selected pair, then maximizes the minimum pair gap, with the first stable tie. This is proposal guidance at the supplied pose. It does not prove a separating plane is optimal or that the whole mesh, edited motion or semantic contact is correct.

The command authenticates a decoded scalar/vector/reference feasible starting point and uses the original Job's difference, sparsity, trust, fractions and storage limits. Every requested solver variant and fraction is retained. Each fresh export receives the original authoring/storage audit, complete decoded motion/vector/contact observations, reference bounds and geometry queries at every declared guide time. A passing continuous proxy does not approve an exported clip.

Among exports passing all original motion/vector/reference/control bounds, selection minimizes the maximum partner depth across every declared guide time, then the total triangle records at those times, with stable variant/fraction order. Only that candidate receives the complete original scene geometry scan. Selection for a scan is separate from geometry acceptance. Original clips remain selected even if the scan passes; review and release approval remain explicit.

Outputs include pinned request/Job/guide snapshots, original and chosen axes, complete finite rankings, method snapshots, event support, complete stencils, the full native and guide systems/Jacobians, solver results, all exported actor files and decoded observations. Completed and failed workers write distinct terminal states. Input or implementation changes during a run reject. The existing single-guide command remains available.

This is an offline backend command. It adds no Studio controls, automatic storage repair, clip append, library selection, new inference or training. Runtime dependencies and original pinned assets must already be available. The public repository remains a development source snapshot, with third-party models and assets acquired separately under their own terms.


## Validation and retained failures

38 distinct focused command tests pass with zero skips: 23 new multi-time cases and the 15 existing single-guide command cases. The full second report and final targeted report establish the latest passing outcome for every distinct case. Earlier failing reports remain retained. They exposed test assumptions rather than a command defect: a valid request may yield no finite solver candidate, and a horizontal perturbation of a vertically moving fixture can stay within its original speed allowance. The final rejection case deepens the fixture's actual descent at the original normalized trust bound.

Actual placed meshes cover multiple native times, mixed units, reversed actor order, complete model/stencil populations, contained original patch faces, full finite rankings, strict stable selection, input mutation, failed descriptor/rank snapshots and terminal states. Controlled orchestration directions separately exercise real motion-valid and motion-invalid stored exports, with only the eligible candidate receiving a complete geometry scan. Those controlled directions are acceptance-path tests, not optimizer evidence. The unmodified solver's no-candidate outcome is retained without inventing an export or approving a motion.

A separate unmocked command run uses the verified 48-choice generated-fixture Job and seven declared guide times in `rank-patch` mode. It creates fresh complete native differences to validate the new orchestration entry point. A comparison bound to the previous complete independent replay reproduces all seven finite pose-axis rankings, every one of 180 native/point/gap stencils, all 90 native/guide columns, original systems, event rows and both solver results exactly. All eight A/B export pairs are byte-identical, and every saved decoded observation and seven-frame geometry query matches. No export passes original decoded motion, so no candidate is selected for full geometry. This repeats the model to validate a new command; it does not establish a new motion-quality improvement.

## Larger-step storage experiment

For a separate fixed-control experiment, keep the larger pose-axis half step with the greatest actual guide improvement among original-box/reference/continuous-proxy passing proposals. It initially fails six decoded native conditions. The existing balanced positional/angular one-ULP policy keeps the original 64-choice storage envelope, all original motion/contact/reference limits and the continuous controls fixed. The start plus 438 exported neighbors are retained, with a declared maximum of eight stages and 64 probes per stage.

| Stage | Selected stored candidate |
| --- | --- |
| 0 | `storage-0-2` |
| 1 | `storage-1-37` |
| 2 | `storage-2-61` |
| 3 | `storage-3-55` |
| 4 | `storage-4-20` |
| 5 | `storage-5-58` |
| 6 | `storage-6-53` |

The final candidate has 53 absolute choices and passes every original scalar/vector/contact/reference bound, with normalized vector-norm maximum excess -0.00000108017126599. Its complete original geometry scan still fails: 5.102497259 mm partner depth at 0.7968750149011612 s, 28,904 proper triangle crossings and 1,527 failing sampled checks. The previous seed has 4.969956705 mm depth and 29,478 crossings. Fewer crossings coexist with worse maximum depth; there is no monotonic whole-clip improvement.

A separate original-context manual decoder exactly replays all 439 actual exports, their complete native/scalar/vector/contact/static/reference observations and fixed controls. It reconstructs every complete original option population, round-robin prefix, absolute transition, merit and stable best eligible probed selection without importing the producer/search APIs. Full geometry archive transport is verified using shared predicates; collision arithmetic is not independently reimplemented or certified. The repaired candidate is retained for research, with the geometry failure attached. No new Job, clip append or library selection is created by this experiment.

These are generated-fixture backend results. They do not establish arbitrary-action correctness, production anatomy, continuous physics, game-engine quality, independent animator ratings or cleanup time. Original assets remain selected, all fourteen release evidence arrays remain empty and the full-project goal stays active. The new suite is registered once in Linux/Windows CI; hosted success remains unverified.
