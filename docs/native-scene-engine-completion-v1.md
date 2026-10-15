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

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/38691867528) passes all **18 new checks on each OS** at `32651d6`: Ubuntu 6.93 seconds, Windows 111.74 seconds. This includes the final moving-prop fixture. Broader hosted checks remain separate.

The real high-five imported geometry journal now completes and verifies **all 2,017 samples**, then streams the full assembly without another geometry query. Its final result remains failed on sampled scene conditions, with the original source selected. The exact assembly digest and complete batch/resource history are recorded in the [journal evidence](native-geometry-journal-v1.md). The actual completion bridge is running against that complete journal under ignored `reports/high-five-captured-engine-completion-v1`; its full imported/native skin/contact comparisons remain pending until its authoritative result. This is a CPU-only comparison against the sealed actual capture, with no new engine or model run. Its 1 GiB guard estimate combines the previously measured imported-job peak and a conservative eightfold heap allowance for the 19.8 MB geometry JSON; the separate engine/model admission estimate is unchanged. No fidelity, packaging, physics, quality or release success is inferred from a running job.

## Named-region diagnosis of the existing overlap

A read-only diagnostic attributes the already measured frame 579 (1.1395833333333334 seconds) through its canonical source vertex/face indices and loaded skin weights. It does not query geometry again or edit either clip.

| Measured source inside target | Depth | Deepest canonical vertex | Dominant named source influence |
| --- | ---: | ---: | --- |
| A inside B | 7.143309 mm | 3018 | `RightHandThumb1`, 84.216% |
| B inside A | 21.138625 mm | 17515 | `RightHandPinky3`, 95.663% |

All **301** recorded surface outcomes at that frame are proper crossings, and all map to dominant right-hand/finger skin labels. Every recorded outcome is included in the attribution. The intended contact vertex 16974 itself blends mainly index/ring/middle finger-base influences; only 9.812% of its loaded weight is on `RightHand`. A single wrist-joint condition therefore does not describe this deforming material effector. These are named skin-weight observations, not reviewed anatomical annotations or palm-side/normal verification.

The separately labelled native-source Hips references are about 1.085 m apart horizontally at that time; this is not a body-COM or physical-clearance measurement. The checked failure supports a correction study of hand-surface orientation, finger geometry and contact approach timing. Floor/stance failures remain separate, and other times still need the full audit. The diagnostic guard completes in **19.297 seconds**, peak **113,696,768 bytes**, with all **21** resource observations replayed. Complete local results remain under ignored `reports/high-five-overlap-attribution-v1`.

Studio's default monolithic authoring path, recipe continuation and combined prop-asset packaging are not automatically converted to this completion path. The bridge supplies verified downstream observations; it does not establish a complete scene/game ZIP, real-time playback, rendering, physics, calibrated realism, held-out coverage or human cleanup evidence. The journal's documented fallback-RNG limitation remains. All fourteen release capabilities and calibration gates remain unapproved under the same project-wide goal.
