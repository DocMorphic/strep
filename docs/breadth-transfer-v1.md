# Broad motion transfer and engine diagnostic

The first complete breadth round contains 65 native actor clips, covering one case from every family and all five seeds. This study transfers **every one** to the three existing bundled characters: CesiumMan and Quaternius female/male. That is **195 planned transfers** and **260 planned native/target Godot imports**. The Quaternius characters share a skeleton family; this is three assets from two families, not three independent rig designs or held-out rig validation.

The protocol, original rig/profile/license copies and implementation snapshots are frozen under `reports/breadth-transfer-v1`. Raw input hashes bind the completed breadth artifacts. Existing mapping profiles remain fixed across actions; no contact fitting, floor lift, per-action calibration or model changes are applied. Failed and missing outcomes remain in the denominator.

The CPU-only runner limits numerical threads to one and hides CUDA from its own process. It can run alongside the separate frozen motion study without using the model GPU. Its CPU/I/O work still affects the shared machine; wall times must not be presented as isolated performance benchmarks.

For each target, the existing exporter verifies every decoded joint transform and skin vertex against its transfer result. An independent decoded audit checks the root track against the scaled source trajectory, the root sidecar against the exported pose, and contact intervals against the original model predictions. Those predictions remain unconfirmed; they are not gameplay events or authored contacts.

Declared flat-floor cases also receive full target-skin depth and predicted-support foot-hover measurements. Inapplicable scene/water/partner cases receive no floor acceptance result. The comparison keeps native and target floor depths separate, so a transferred character floating above the ground cannot count as a complete contact fix. The same 10 mm diagnostic floor threshold is used; hover values are reported without fitting a new acceptance threshold to these results.

Each source take is then imported into Godot together with its available target exports. The audit checks all frames, joint names, joint world transforms, clip duration and retained skinned surfaces. It is bounded to four clips per engine process to avoid accumulating the entire study's pose/mesh data in one engine instance. It does not verify GPU skinning, action meaning, balance, forces or independent animator usability.

[Live transfer report](http://127.0.0.1:8767/reports/breadth-transfer-v1/review.html) shows all planned target rows, native/target depths, foot hovering, engine evidence and editable asset links. The main animation-generation implementation stays frozen while it runs.

Operational evidence: `pipeline.json` records the active transfer/engine phase; `runner.json` records actual process identity; `results.json` retains all attempts and errors; `coverage.json` keeps every planned row. Inspect a live PID and creation time before declaring the run stopped. An observation timeout does not justify restarting. The runner refuses to overwrite a started study. Source/rig/implementation changes also require investigation and an explicit new protocol.

This study finished on 2026-09-27 at 14:03:49 UTC. It is development evidence, not completion of the full-project goal or any semantic/physics release gate.

## Complete population

All **195 transfers** and **260 actual Godot imports** completed. The independent final audit verified 1,680 retained transfer-file hashes, all 65 source motion hashes and all 65 native GLB hashes. The engine checks cover 48,600 frame samples across native and target clips; maximum world-position discrepancy is 1.82e-6 m and maximum basis-element discrepancy is 8.85e-7. See `final-verified.json` and `completion-verification.json`. No runtime restart or omitted failed take was needed.

There are 40 floor-applicable motions and 25 context-dependent motions per rig. Native skin fails the 10 mm floor screen in 29/40 applicable motions. CesiumMan fails in **40/40**, including all eleven native passes. Both Quaternius characters pass that floor screen in 40/40, but their maximum predicted-support foot-region hover is **199.9 mm (female)** and **183.7 mm (male)**. Cesium's low maximum hover coexists with penetration and is not a positive contact result. The same source population is used for every rig.

The follow-up [bounded correction comparison](breadth-contact-v1.md) retains the complete baseline and compares surface-only fitting against added predicted-support drift correction. Nothing in this study establishes semantic correctness, physical balance, object/partner coordination or independent animator acceptance.

## Retained interim evidence

`interim-verified-01.json` captures 115 completed transfers, one running and 79 pending, with 152 actual Godot clip checks. The independent reader `scripts/analyze_breadth_transfer.py` verified all 1,005 retained completed-transfer artifact hashes and matched the engine evidence to the available input population. This is a snapshot, not the final study outcome.

Among the completed floor-applicable takes in this snapshot, CesiumMan has 29/29 target floor failures, including ten whose native skin passed the 10 mm screen. Quaternius female and male have no target floor failures in their 28 completed eligible takes each, but maximum predicted-support foot-region hover reaches 199.9 mm and 183.7 mm respectively. The denominators differ because the snapshot was taken during processing. A floating body is not a successful contact correction. Predicted support still needs review; these maxima do not certify that every flagged interval is genuinely weight-bearing.

Browser checks verified the family/character/seed filters on combat seed 3253: native floor 9.8 mm, female target floor 0 mm, foot-region hover 132.6 mm, and successful engine transform checks. Four linked clip/sidecar/report files and the engine evidence were downloaded over HTTP and matched the retained bytes; console errors were empty. See `ui-verification.json`.

The complete population above supersedes these interim counts. Candidate corrections must still retain all seeds and failures. Prior constant-height calibration already caused pose-dependent regressions, and existing bounded mesh fitting can trade clearance for sliding or abrupt edits. The correction comparison measures those effects together rather than treating low floor depth as success.
