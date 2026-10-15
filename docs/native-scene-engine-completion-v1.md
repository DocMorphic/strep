# Completing a captured scene audit from its geometry journal

`scripts/native_scene_engine_complete.py` connects a **complete imported-geometry journal** to the existing scene replay, original-reference fidelity and explicit game-track tools. It performs fresh full-clock imported/native skin and contact comparisons, while reusing the already executed Godot capture and committed geometry measurements. It does not launch Godot, generate another motion, repair a clip or approve an interaction.

The completed producer has its own `strep-native-scene-engine-journal-completion-v1` schema. The copied `request.json`, raw engine receipt/output, log, executed scripts and Animation resources retain their original bytes. A separate `completion-request.json` binds the complete journal, current measurement methods and source snapshots. An executed request is never rewritten to look as though it was run in the new output directory.

Before completion, the bridge verifies the caller-pinned journal result, every ordered checkpoint/frame, full geometry clock, final JSON samples and every numeric array's logical dtype/shape/bytes against the committed frame receipts. A native-source journal cannot substitute for imported observations. Partial populations, changed captures/resources/scripts, changed source assets or mismatched native payloads are rejected.

The imported clock can include contact times outside an explicitly chosen geometry clock. All captured pose/skin/contact times are still evaluated, and geometry is checked against its complete declared population. The tests deliberately use three geometry times and an additional touch time, requiring four imported comparison samples. There is no silent narrowing to the geometry-only subset.

Both `verify_native_scene_engine.py` and the actor-only `verify_native_actor_scene_engine.py` recognize the new producer through a strict loader. Their ordinary full numeric-array, skin/contact, plane/degeneracy and retained geometry-reduction replay remains in place. The actor-only loader rejects declared objects. Original-reference fidelity and explicit root/event-track consumers can use the completed observations through the generic loader. A passing fidelity or root-track check cannot overwrite a failed scene condition; measured contact intent never becomes an automatically confirmed gameplay event.

## Commands

Use the configured pinned Python environment, an existing complete imported journal, and its recorded final result digest. Choose a fresh output directory:

```powershell
python scripts/native_scene_engine_complete.py reports/scene-journal reports/geometry-complete/result.json <recorded-result-sha256> reports/engine-completed
python scripts/verify_native_scene_engine.py contacts.json geometry-policy.json reports/engine-completed reports/engine-completed-replay
```

Successful completion means that the audit finished. Inspect `all_sampled_conditions_pass` and individual conditions separately. The bridge retains failures, leaves the original selected, and sets quality, training and release approval to false. Partial writes and synchronous failures retain their copied source evidence; a failed pipeline cannot publish a completed result.

## Evidence and remaining integration

The first integration selection passes **81 checks in 150.67 seconds**, including passing/failing actor scenes and object observations through both appropriate replay paths, plus existing journal, generic replay and fidelity checks. Its 512 MiB guard completes in 167.813 seconds with peak sampled process-tree RSS 124,370,944 bytes; all 167 resource observations replay.

The expanded selection passes **120 checks in 356.04 seconds**, including original-reference fidelity, explicit root/event exports, a fully rebound but invalid native payload, failed archive writes, existing actor-only Studio jobs and game-track tests. Its guard completes in **372.594 seconds**, peak **153,608,192 bytes**, with all **367** resource observations replayed. The final prop fixture then adds an independently constructed analytic translating/rotating box; that complete journal-to-replay/fidelity/root-track case passes in **17.04 seconds**. Its guard completes in **33.422 seconds**, peak **116,793,344 bytes**, with all **35** observations replayed. Fixtures use explicitly synthetic capture transport and do not claim an actual Godot execution, lift action or validated physical interaction.

The real high-five geometry journal separately reaches **720 of 2,017** committed samples. Its third batch verifies the prior 592-frame prefix and computes 128 new samples, with prior checkpoints unchanged. The 768 MiB CPU guard completes in **547.031 seconds**, peak **667,226,112 bytes**, with all **540** resource observations replayed. The remaining **1,297** times and full assembly are still pending; this real partial journal cannot yet enter the completion bridge. The next predeclared 256-frame batch is running under ignored `reports/high-five-imported-geometry-journal-batch4-v1`, targeting a 976-frame prefix under the unchanged CPU guard. The geometry methods recorded by the existing journal remain byte-identical.

Studio's default monolithic authoring path, recipe continuation and combined prop-asset packaging are not automatically converted to this completion path. The bridge supplies verified downstream observations; it does not establish a complete scene/game ZIP, real-time playback, rendering, physics, calibrated realism, held-out coverage or human cleanup evidence. The journal's documented fallback-RNG limitation remains. All fourteen release capabilities and calibration gates remain unapproved under the same project-wide goal.
