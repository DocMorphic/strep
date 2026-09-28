# Open-vocabulary action studio

The product covers general game animation authoring. The original four examples and later running studies are measurement fixtures, never an action whitelist. The system must grow across locomotion, aerial and floor movement, gestures, dance, sports, combat, tools, object handling, interactions, traversal, styles, transitions and editing. No finite test set establishes “all motions.”

## Delivered milestone — 2026-09-25

Open http://127.0.0.1:8768/studio. Enter your own description, optionally add timed steps, choose seeds, and select **Generate locally**. This starts real offline text encoding, motion inference and finite-clip export. The form is not restricted to examples or to running. The status survives a page refresh; completed jobs appear as collections. Requests and failed attempts are preserved in `reports/action-jobs`.

Current execution scope: one humanoid on SOMA, 1–6 sequential prompts, 1–9 seconds each and at most 30 seconds total, with 1–4 seeds. These are local workload limits, not limits on action names. Each new description is encoded by the existing original-precision disk-offload encoder. There is no prompt substitution, new training or paid service. Full 8B resident-encoder equivalence remains untested. The unchanged pinned Kimodo checkpoint uses 100 diffusion steps, separated CFG [2,2], no scene/path constraints or postprocessing, and five-frame upstream sequence blending.

A checked scene requirement is retained and explicitly flagged as unsolved. It does not create objects, simulate loads, generate a partner, solve contacts or calibrate character stats. Arbitrary source/target character rig import and rough-clip editing remain future work.

## Measured breadth

`benchmarks/action-coverage-v1.json` contains seven illustrative requests, two seeds each: jump/land, crawl, dance/turn, wave, kick/recover, get up from the floor, and a three-segment run → roll → stand. All fourteen were newly generated locally. This broadens the sample; it does not measure held-out generalization or certify these actions.

Seven takes have provisional numerical flags. Both crawl takes, both get-up takes, both roll sequences and kick seed 11 exceed the 1 cm joint-ground-depth threshold. Crawl seed 11 and both roll sequences also exceed 15 cm/s predicted-contact foot-speed p95. Maximum joint depths reach 13.8 cm, so floor interaction needs substantial work. Those flags stay visible, and every take remains unreviewed for action correctness and realism. Joint depth is not full mesh collision, and contact predictions are not independent stance labels.

The sequence requests boundaries at 2 and 5 seconds, with upstream blending in frames 55–59 and 145–149. Each result has 210 frames; the last key is at 6.9667 seconds, with 7 seconds of sample coverage. Boundary samples report joint steps and root velocity changes; requested boundaries are not detected action or gameplay events. End-pelvis height/speed/orientation are diagnostics, not a standing classifier. Browser inspection of seed 11 sampled entry, rolling and upright ending poses; it is not a blind animator review or confirmation of a physically correct shoulder roll.

A separate browser-submitted request, **Someone shrugs both shoulders and spreads their hands, then relaxes.**, uses seed 33 and is deliberately outside the example list. Its preserved folder is `reports/action-jobs/20260925-165323-a7448117`. The browser job completed successfully, its GLB validates without errors/warnings, and all ZIP hashes match. Sampled poses show raised shoulders and open hands at 0.60 seconds, followed by relaxation at 1.67 seconds. This checks end-to-end free-text execution rather than a canned gallery. It is not a human quality score.

## Assets and verification

Every clip includes the raw NPZ/BVH, grey SOMA GLB, root motion, predicted foot-contact intervals, requested timeline, generation record, request, measurements and a ZIP with the vendor license. Finite actions are not looped or run through running-specific corrections. Raw source hashes are checked; the GLB is verified against every source frame. SOMA mesh skinning retains all eight weights.

The root track is the SOMA Hips world transform in meters, Y up, +Z forward, with xyzw quaternions. Engine-specific ground-root extraction remains undecided. Contact intervals are half-open frame segments on the exact exported clock, with boundary clipping marked. The last key time differs from frame count / FPS by one frame, as explicitly recorded in timeline JSON.

Fourteen coverage GLBs validate with zero errors/warnings. All fourteen ZIPs, hashes and root/contact clocks verify. Maximum GLB joint round-trip error is 6.12e-7 m; maximum BVH joint reimport error is 1.09e-5 m. Read `reports/action-coverage-v1/summary.json`, `export-validation.json` and `pack-validation.json` for per-take evidence. All 69 project tests pass (four upstream Torch deprecation warnings). Browser verification covered real submission, completion, page-refresh recovery, clip selection, custom gesture poses, sequence scrubbing and final-frame clicking without disappearance; no console warnings/errors. No target game-engine import has been tested.

## Run and reproduce

From `C:\wassup\strep`:

```powershell
.venv\Scripts\python.exe scripts/action_studio_server.py
.venv\Scripts\python.exe scripts/run_actions.py benchmarks/action-coverage-v1.json --output reports/action-coverage-repeat
node scripts/validate_action_exports.mjs reports/action-coverage-repeat
.venv\Scripts\python.exe -m pytest tests -q
```

The local server binds only to 127.0.0.1:8768 and serves the studio, Three.js and action artifacts. POST requires the same local origin and validated JSON; no shell command is built from the prompt. A Windows OS file lock prevents concurrent model workers and releases on process exit. Memory/time guards preserve logs on failure. An output folder rejects a different request digest; successful raw attempts may be resumed only if their hashes match.

Request format:

```json
{"schema_version":1,"requests":[{"id":"my-action","label":"My action","segments":[{"prompt":"Describe any humanoid motion here.","duration_s":4}],"seeds":[11,22],"scene_requirements":[]}]}
```

Do not edit a saved request to retry a different configuration in the same folder. Use a fresh output. Browser-created folders use unique IDs. The existing server on port 8767 still serves historical reports; the new studio runs on port 8768. A CLI reproduction outside the two served action directories can be inspected on the existing project server or integrated as a collection deliberately; it does not silently replace the first study.

## Next work: reliability across motion families

1. Measure and correct full-body ground support for hands, knees, torso and feet, preserving intentional airborne phases. The new crawling/get-up/roll failures make this more urgent than further running sliders.
2. Add explicit scene geometry, contact targets and object attachment/release; then coordinate partner tracks. Use several tasks and held-out targets, not one hardcoded box or high-five.
3. Expand the coverage suite with new user requests, held-out action combinations and rigs; record action correctness, animator cleanup time and failure rates.
4. Add reusable transitions, rough-clip editing and engine-specific exports. Calibrate capability/style controls across actions only where measurements and review support the mapping.

Avoid a catalog of handcrafted motion handlers presented as general intelligence. Keep free-text requests open, make constraints and correction components reusable, and measure where the model cannot deliver the requested motion.
