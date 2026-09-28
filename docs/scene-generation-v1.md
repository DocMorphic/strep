# Scene pose guides and paired-actor export — 2026-09-26

The generation pipeline now accepts a fitted scene and a prompt schedule for each actor. It derives hand/foot guides from the contact frames, combines simultaneous effectors into a single guide, generates actors independently, restores the authored placements on a shared clock, and measures actual skin contacts afterward. This is a connection between scene authoring and the existing checkpoint; Kimodo itself has not become scene-aware.

`scripts/scene_generation.py` provides `prepare` and `build`. Preparation checks actor hashes, native pose consistency, contact-frame bounds, matching actor schedules, ground-level yaw-only placement, and fitted source point/orientation accuracy. A changed contact target that the source pose misses is rejected before inference. Known source collision defects are retained, not hidden by this preflight. Objects and partner surfaces never enter the denoiser; the selected native actor poses do. Whole-body/scene geometry and finger conditioning remain limitations.

## Experiment

Source: the existing `hand-frame-fit-v1` high-five candidate, fitted from seed 11. Its palm-point error is small, but the prior full partner audit found 20.10 mm penetration. It is not a physically approved interaction. Both source actors use the same native source pose with opposite scene placements. Generated actors use distinct seeds:

| Pair | Actor A | Actor B |
|---|---:|---:|
| 1 | 77 | 88 |
| 2 | 101 | 202 |

Each pair has a text-only baseline and a pose-guided version: eight new raw clips, four shared scenes, each 120 frames at 30 fps. The unchanged original high-five description is used for both actors. Actual text features are extracted without numeric conversion from the original hash-verified v0 cache, with original encoder-loader provenance retained. The original BF16/FP32 disk-offload qualification remains; full-resident encoder equivalence is untested. No training or new data acquisition.

This is an in-sample engineering experiment, not held-out action, object, rig or human-review evidence. Some seeds have appeared in earlier studies. `freeze.json`, `source-snapshot`, source pose hashes and actor plans preserve the protocol. `authoring-guard-amendment.json` records the later preflight rejection and display-label improvements; the actual source fixture passes the new checks without changing a target or rerunning inference.

## Measured contacts

All numbers below refer to the authored frame 60 and actual skinned palm vertices, not just skeleton joints.

| Pair / condition | Actor A to target | Actor B to target | Palm-to-palm gap | Opposing-normal error |
|---|---:|---:|---:|---:|
| 1 baseline | 99.20 cm | 93.25 cm | 136.69 cm | 44.58° |
| 1 guided | 1.97 cm | 1.65 cm | 3.33 cm | 18.14° |
| 2 baseline | 81.95 cm | 66.68 cm | 85.47 cm | 72.66° |
| 2 guided | 2.51 cm | 1.48 cm | 3.59 cm | 13.63° |

Both guided pairs miss the 3 cm palm-to-palm screen. Pair 1 also fails the 15° opposing-normal screen and actor A's model-conditioning screen. Pair 2 passes the current orientation screens but still fails contact distance. Foot-speed p95 proxies stay below 3.3 cm/s across all eight clips; these are predicted-contact diagnostics, not confirmed support.

The source pose's SOMA77→30→77 conversion changes the selected palm point by about 0.53 micrometres and its surface normal by 0.00026°. For this fixture, skeleton reduction does not explain the centimetre-scale residual after generation. The fitted files lack `smooth_root_pos`, so the existing explicit hip-XZ fallback is recorded; guided smoothed-root errors are about 2.2–2.3 cm. The model's constraints remain approximate.

Collision audits are stored per scene in `partner-surface-audit.json` and aggregated in `scene-quality-audit.json`. They cover all 18,056 skin vertices in both directions on every frame against the other posed triangle mesh. This is a discrete vertex test, not continuous/edge-only/self collision certification. The source body is topologically closed, but posed self-intersections can still make inside/outside classification ambiguous.

The first guided pair increases worst partner penetration from 21.41 to 32.27 mm, and frames above 5 mm from 4 to 23. At the requested contact frame alone, penetration is 13.48 mm. Thus improved target positioning does not solve the interaction. The second guided pair has 33.19 mm maximum partner depth over 27 frames, versus no detected partner penetration in its distant baseline. Guided actor B also reaches 11.36 mm skin-floor depth on 33 frames; guided pair 1 actor A reaches 10.43 mm on 11 frames. All full-scene scans completed. The final aggregate is authoritative for every scene's collision/floor flags. No take is promoted or animator-approved.

## Engine and packages

`reports/godot-generated-scenes-v1/verification.json` records actual Godot 4.7.2 runtime import. Both actors are instantiated together under their authored parent transforms, then seek to the same source time. All 77 world-space bones are compared on every frame: 960 actor-frames across four paired scenes. Maximum position-element error is 7.16e-7 m; maximum rotation-element error is 2.69e-6. This does not test GPU skin rendering, physics, real-time synchronization, root extraction or marker playback for these new scenes.

`package_generated_scenes.py` builds a portable ZIP per audited scene: both actors' GLB/BVH/NPZ and tracks, actor placements, a portable scene specification, authored contact-window events, independent failure diagnostics, optional matching engine evidence and the SOMA license. An included Godot adapter can dispatch the authored markers; they do not assert successful contact. End markers use exclusive interval ends. Individual actor ZIPs and scene placements remain available separately.

Studio discovers generated-scene collections from the local study API. Its scene viewer retains contact/orientation/partner failures, a worst-penetration frame jump and links to actor and scene exports. Source and generated motion remain separate. Original intermediate scene bundles retain their inherited source-fit review note as historical metadata; the current manifest display note and portable scene specification identify the actual independent generation mode accurately.

## Verification

187 Python tests pass, including scene source/hash/placement/timeline validation, merging simultaneous effectors, rejecting a moved target before encoding, and authored marker endpoints. Eight new GLBs validate with zero errors/warnings and every exported pose matches raw motion. Four portable scene ZIPs verify all internal hashes, portable actor paths, authored event clocks and matching Godot evidence; all four and the eight actor ZIPs match their localhost HTTP downloads.

Browser checks verify automatic discovery of the four scene comparisons, two visible grey characters, contact jump to frame 60, the 3.6 cm gap and retained 1/3 missed-target flag, worst-overlap jump to frame 40, final-frame visibility at 119/3.97s, correct generation labels, floor-depth warning (1.14 cm / 33 actor-frames), scene/actor download links and a clean console. No independent animator rating or cleanup-time observation was obtained. All inference, audit and engine-import processes finished.

## Reproduce

Use a new output directory; existing raw clips, audit attempts and ZIPs are preserved.

```powershell
.venv\Scripts\python.exe scripts/scene_generation.py prepare reports/hand-frame-fit-v1/hand-frame-high-five-seed-11/candidate.json benchmarks/scene-generation-v1-plan.json reports/action-jobs/scene-generation-repeat --reuse-baseline-cache
.venv\Scripts\python.exe scripts/run_actions.py reports/action-jobs/scene-generation-repeat/request.json --output reports/action-jobs/scene-generation-repeat
.venv\Scripts\python.exe scripts/scene_generation.py build reports/action-jobs/scene-generation-repeat
.venv\Scripts\python.exe scripts/audit_generated_scenes.py reports/action-jobs/scene-generation-repeat
.venv\Scripts\python.exe scripts/run_godot_scene_import.py reports/action-jobs/scene-generation-repeat reports/godot-scene-repeat
.venv\Scripts\python.exe scripts/package_generated_scenes.py reports/action-jobs/scene-generation-repeat --engine-report reports/godot-scene-repeat/verification.json
node scripts/validate_action_exports.mjs reports/action-jobs/scene-generation-repeat
```

For a new prompt, omit `--reuse-baseline-cache`; the normal local encoder must encode that exact description. The fixed baseline cache rejects unknown text. No action-name whitelist is introduced.

Next work remains coordinated contact/collision correction after generation, reliable boundary pose constraints, broader scene/object/rig coverage and animator cleanup-time evidence. Continue the same project-wide goal, including general rig transfer and rough-clip/style authoring; this experiment does not complete it.
