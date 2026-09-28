# Broad motion diagnostic baseline

This study expands beyond the original example motions to **72 cases across 12 families**, each using five fixed seeds. Six partner cases generate both actors separately, yielding **390 planned actor clips**. These cases measure coverage; they are not a prompt whitelist or proof of universal action support.

The frozen protocol is `reports/breadth-baseline-v2/protocol.json`. Seeds are 1301, 2089, 3253, 4099 and 5101. All clips use the unchanged pinned Kimodo checkpoint, 100 sampling steps and 30 fps. Twelve bounded batches preserve existing product request limits. Fifth-seed batches reuse validated, byte-identical conditioning from the corresponding four-seed batch.

The families are locomotion; parkour; ground movement/recovery; combat; gestures/expression; dance/performance; everyday tasks; object manipulation; partner interaction; environment traversal; aerial/nonwalking motion; and stylized/capability motion. Prompts include crawling, swimming, climbing, gestures, dancing, carrying, sitting, handshakes, guarding an injured arm and many other actions.

## Evidence and limits

- Freeze files bind prompts, seeds, model acquisition, pinned source and generation implementations. Do not edit the running pipeline or dependencies during this study.
- Raw motion and exported assets remain separate. Export verification checks every pose; the report revalidates completed files against retained hashes.
- All 390 planned rows remain in the denominator. Failed/missing outputs are not discarded. Human semantic scores remain null until actual reviews are submitted.
- Flat-floor cases receive joint/foot diagnostics and a full native skin audit across all frames, 18,056 vertices and all eight skin influences. The 10 mm floor screen is diagnostic, not a complete realism test.
- The predicted-support foot-speed diagnostic uses the existing 0.15 m/s screen. It does not replace the stricter proposed release criterion or constitute the full official Kimodo benchmark.
- Cases requiring stairs, walls, objects, partners, water or other context are explicitly missing scene validation. A separately generated actor pair is not a solved interaction; floor checks are inapplicable for designated contexts, not silently passed.
- A limited local prompt/seed audit found no exact overlap in the scanned prior request records. Training-data overlap is unknown. This is a frozen development diagnostic, **not an untouched final release set**.

## Operation

The [live diagnostic viewer](http://127.0.0.1:8767/reports/breadth-baseline-v2/viewer.html) indexes every frozen case/actor/seed and refreshes coverage after completed batches. It offers the existing grey SOMA character, playback/scrubbing, camera fitting, root-follow/world views and original asset/evidence downloads. Unavailable clips disable playback and download links. Context-dependent motions start without a fictitious ground grid. This is an organizer diagnostic page, not a blinded reviewer packet.

Rebuild that independent page with `scripts/build_breadth_viewer.py`; it does not edit the protocol, generation implementation or raw outputs. Build evidence checks all 390 unique entries and JavaScript syntax. Actual browser checks cover locomotion, swimming, partner actor selection, pending cases, camera modes and canvas interaction; nine HTTP asset downloads match saved export hashes.

Use `scripts/breadth_study.py report` for a validated snapshot between runner report writes. The runner's `pipeline.json` and `runner.json` record current batch/stage and process identity; verify the live PID and creation time before deciding a job stopped. Log files remain in each batch's action-job folder. Do not restart because a tool observation timed out.

The runner skips only completed, revalidated batches with surface audits. Existing non-complete batches require investigation; failures are retained and never automatically overwritten. Do not run another model in the independent portable installation concurrently: the installations have separate worker locks and share this laptop's GPU.

No release capability is approved by this study. Subsequent correction/adaptation experiments must preserve this raw baseline and use a distinct protocol. See [interaction research](interaction-research-v2.md) for the current adaptation decision.


## Completed population, September 27

All 12 batches completed at 15:06:44 UTC: 390/390 actor clips, all 72 cases and five seeds. The independent completion verifier checked 3,900 exported artifact hashes, request/prompt identity, every surface-audit source binding and the frozen implementations. The earlier memory-guard failure remains preserved separately; its recovered batch did not change the protocol.

| Family | Clips | Eligible flat-floor clips | Skin-floor failures >10 mm |
| --- | ---: | ---: | ---: |
| locomotion | 30 | 30 | 22 |
| parkour | 30 | 15 | 14 |
| ground_and_recovery | 30 | 30 | 26 |
| combat | 30 | 25 | 10 |
| gestures_and_expression | 30 | 30 | 17 |
| dance_and_performance | 30 | 30 | 26 |
| everyday_tasks | 30 | 10 | 9 |
| object_manipulation | 30 | 0 | Not applicable |
| partner_interaction | 60 | 0 | Not applicable |
| environment_traversal | 30 | 0 | Not applicable |
| aerial_and_nonwalking | 30 | 0 | Not applicable |
| stylized_and_capability | 30 | 30 | 15 |

Across the 200 eligible clips, 139 fail the skin-floor screen, 47 fail the joint-floor screen and 12 fail the existing predicted-support-speed screen of 0.15 m/s. The other 190 require context validation and do not receive flat-floor passes. There are zero independent ratings and zero established supported-action claims.

[All 390 native clips subsequently passed actual Godot import checks](breadth-native-engine-v1.md). A separate finger audit checks every raw clip against the bundled relaxed-hands asset: all 38 articulated finger joints are constant and match that default in all 390 clips. Prompt-conditioned body motion must not be presented as generated finger articulation. Original exports and their historical evidence remain unchanged; these later studies are separate evidence.
