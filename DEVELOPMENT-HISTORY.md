# Historical development notes

This is the README snapshot retained when the public repository was prepared on 2026-09-28. Statuses, test counts, localhost links, and local report references below describe their recorded development snapshots; use the current README for the project overview.

# strep — offline game animation authoring

Current status (2026-09-27): development system, with the full-project goal active. Open-vocabulary generation, rig import/transfer, clip editing and game-engine checks have working development evidence. Broad reliability, calibrated character controls, independent animator review and a reproducible offline installation remain release requirements.

Latest: the [broad motion study](docs/breadth-baseline-v2.md) is running 72 cases across all 12 release families and five seeds: 390 planned actor clips. [Open the live coverage viewer](http://127.0.0.1:8767/reports/breadth-baseline-v2/viewer.html) to inspect completed exports, missing outputs and applicable surface diagnostics. Raw generation does not establish scene contacts, semantic correctness or release readiness. The generator and environment remain frozen during the study.

The [personal offline installation](docs/offline-install-v1.md) has new-prompt generation, rig transfer, retiming and 487 actual Godot frame checks from a separate runtime. Last complete suite: **569 passing tests**, five existing warnings; the new breadth protocol has four additional focused passing tests. This remains one-machine development evidence. [Interaction research](docs/interaction-research-v2.md) records why available research models are not automatic product replacements. The project-wide goal and release gates remain open.

The first breadth round also has a [portable independent-review packet](docs/portable-human-review-v2.md): all 65 clips, no model installation, verified from a separate folder. The reviewer workflow is ready; actual independent ratings and cleanup measurements remain missing.

The [broad character-transfer study](docs/breadth-transfer-v1.md) completed all 195 transfers and 260 native/target engine checks (48,600 frames). [Its report](http://127.0.0.1:8767/reports/breadth-transfer-v1/review.html) separates successful import from widespread floor penetration and hovering. A [twenty-candidate correction comparison](docs/breadth-contact-v1.md) is running with unchanged edit limits and paired clearance-only controls. These are development diagnostics; no character or action is approved by passing the import check.

The [independent partner study](docs/breadth-partners-v2.md) now tests ten handshake/high-five pairs with fixed scene contact requests. An excessive-memory collision audit was stopped and preserved; bounded vertex batches restored headroom and the unchanged generation study resumed. [Inspect both original actors together](http://127.0.0.1:8767/reports/breadth-partners-v2/review.html); pending collision/engine checks and contact failures remain explicit.

Earlier: [experimental body collision](docs/actor-collision-proxies-v1.md) deflects props from a prescribed animated character, but oversized envelopes and a settling failure prevent general-use qualification. Actor reaction remains unsolved.

**Active project-wide goal:** [Complete Strep](docs/project-goal.md). Keep this one goal active across all milestones until the end-to-end release contract is met; see `benchmarks/project-release-v1.json`. Evaluation categories measure coverage; they do not restrict which actions users may request.


Earlier experiment (2026-09-26): [support-contact fitting](docs/support-contact-v1.md) added four-way comparison and clickable inferred support intervals. Seed 11 improved from eight numerical flags to one, but all four get-ups remained flagged and three introduced new regressions; no candidate was promoted. The original 30-clip baseline is preserved. That snapshot had 81 passing tests.


Turn rigged humanoid characters and action descriptions into editable animation assets for games. The scope includes locomotion, object handling, social interaction, combat, and clip editing. This is an offline authoring workflow; runtime pose generation and image-to-3D reconstruction are outside the initial study.

## Earlier development history — 2026-09-25

The results and test counts below describe earlier snapshots. For current rig transfer, editing and import work, see [Studio characters](docs/studio-characters-v1.md), [native pose targets](docs/pose-target-authoring-v1.md) and the latest studies above. Earlier statements that engine import or rig editing were still future work are historical.

**Body-clearance experiment:** [Open the three-version comparison](http://127.0.0.1:8768/studio): raw motion, hands/feet baseline and body candidate. Adds bounded pelvis/torso correction, support-regression checks and between-frame floor sampling. Getting-up support remains unsolved. [Results and reproduction](docs/body-contact-v1.md).

**Desktop OS studio:** macOS-inspired windows, Dock, menus, local generation and searchable motion library. [UI behavior and limitations](docs/macos-interactions-v2.md).

**Open-vocabulary action studio:** [Describe and generate a motion](http://127.0.0.1:8768/studio), add timed sequence steps, preview on the grey SOMA body and download editable assets. This executes real local generation for new prompts. The examples are not an action whitelist. [Usage, results and limitations](docs/action-studio.md).

Seven diverse requests × two seeds produced fourteen fresh clips spanning jumps, crawling, dance, gestures, kicks, floor recovery and run → roll → stand. Seven have numerical contact/depth flags; none is animator-approved. Objects/partners, arbitrary rig transfer, engine import and numeric game-stat mapping remain unsolved. The next work is broad contact reliability, not more running-only refinement.

The previous [running pace/style controls](http://127.0.0.1:8767/reports/pace-controls-v1/viewer.html) remain available as a specialized study.

Previous milestone: **five movement profiles × three takes generated and reviewed in a local character viewer**. All 15 raw/processed takes and CesiumMan GLBs are retained; 13 pass the combined source screens and two sprint takes remain flagged. [Open profile/take viewer](http://127.0.0.1:8767/reports/profile-pilot-v1/viewer.html) · [Results and reproducible commands](docs/profile-pilot-results.md) · [Research](docs/profile-pilot-research.md).

Descriptions produce measurable motion differences, but precise style compliance is imperfect. Agility/strength/endurance numbers are recorded intent, not calibrated model controls. Thirty-one tests pass; all 15 GLBs validate without errors, and one independent raw rerun matches exactly. Character foot floating, human realism review and game-engine import remain open.

Earlier completed milestones and setup history:

- Recreated the project from the supplied handoff; the original Mac files were not present.
- Inspected this laptop, cloned and pinned official Kimodo source, and downloaded a licensed skinned test character.
- Defined four cases and five seeds, with separate unprocessed and upstream-postprocessed conditions.
- Python 3.10, CUDA PyTorch, and Kimodo inference dependencies installed locally. Exact package versions saved in `benchmarks/environment.windows.txt`.
- The pinned motion checkpoint is downloaded, hashed, and successfully loads on the GPU (~1.1 GiB allocated at load, not a generation peak).
- Run recorder, motion validation, foot-slide/joint-penetration proxies, root/contact exports, and an offline skeleton viewer are implemented and tested.
- Hugging Face login and gated access verified; all pinned encoder weights downloaded and hashed. Five benchmark prompts encoded locally using original-precision disk offloading.
- **First new motion generated:** four-second running sample, 120 frames, SOMA77, seed 11, editable NPZ/BVH. See [the result and limitations](docs/first-run.md). It is not yet a seamless loop or fitted to the test character.
- Completed all 25 unprocessed actor jobs (20 case/seed trials), with every result and failure mode retained. [Results](docs/baseline-results-v0.md), [realism criteria](docs/realism-rubric.md), and [all-seed gallery](reports/baseline-review.html). All files pass structural validation; no clip has completed full realism acceptance.
- Completed deterministic run-loop correction across all five seeds: two pass loop and sliding-regression checks, three retain sliding flags. All five NPZ/BVH exports are validated; a separate rerun exactly reproduces arrays and metrics. Seventeen tests pass. [Correction results](docs/loop-correction-results-v1.md) and [before/after comparison](reports/loop-correction-v1-reviewed/comparison.html).
- Streamed encoder loading matches resident PEFT on a small synthetic model; full 8B equivalence remains untested. Independent contact/collision assessment, human ratings, native cleanup, and engine import are pending; CesiumMan retargeting is now implemented.

See [the execution plan](docs/next-steps.md) and [newly generated preview](runs/run_loop/seed-11/unprocessed/actor-A/attempt-002/inspection/preview.html). The older preview under `reports/upstream-example` is a third-party example.

Start with [the machine report](docs/machine-report.md), [the baseline runbook](docs/baseline-runbook.md), and [the research protocol](docs/research-plan.md).

## Inputs and outputs

Inputs: rigged character, action prompt/list, optional rough clip, reference video, style/timing constraints, scene objects, and partner character.

Intended outputs: rig-fitted clips, root tracks, contact and gameplay event markers, compatible boundaries/transitions, previews, and engine-importable assets. Object and partner actions require geometry and shared contact targets. These are product requirements, not completed features.

## Reproduce the experiment plan

From this folder, run:

```powershell
node scripts/plan-baseline.mjs
```

This validates the benchmark, pinned source, and character file, then writes `benchmarks/generated-plan.json` with command argument arrays and pending run records. It does not run Kimodo. There are 50 single-character generations: four cases, five seeds, two processing conditions, and two separate actor tracks for high-five. These represent 40 case-condition trials.

The default test rig is [CesiumMan](assets/characters/cesium-man/UPSTREAM-README.md), © 2017 Cesium, CC BY 4.0, with separate logo terms retained beside it. It is a coarse humanoid transfer fixture, not a production hand rig. Engine selection remains open; start with NPZ and standard-T-pose BVH, then add GLB/FBX after retargeting.

## Layout

- `HANDOFF.md`: durable context and next-session instructions.
- `docs/`: hardware findings, research protocol, sources, and runbook.
- `benchmarks/v0.json`: prompts, seeds, desired targets, and conditions.
- `benchmarks/sources.lock.json`: inspected code/model revisions; not an installed dependency lock.
- `assets/characters/cesium-man/`: original GLB, attribution, license, and checksum.
- `vendor/kimodo/`: unchanged official implementation and its original licenses.
- `runs/`: original recorded generation attempts; preserve each attempt and failure separately.
- `reports/loop-correction-v1-reviewed/`: validated correction study, exports, and all-seed comparison.

Next stages: target-rig foot placement and independent review → broader contact/transition corrections → event extraction and engine validation → only then a measured decision about learned editing or scene-aware training. Do not train on raw BONES-SEED under its current license.


The [personal offline installation experiment](docs/offline-install-v1.md) now runs a new prompt, character transfer, timing edit and 487 actual Godot frame checks from a separate runtime without development Python/Git/Node on PATH. It caught and fixed user-site leakage and overhead-motion camera cropping. This is one-machine development evidence; the single full-project goal and release gates remain open.
