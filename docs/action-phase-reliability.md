# Action phase reliability

The authoring system needs to preserve all requested phases, not merely produce smooth motion related to a prompt. A native-output inspection exposed a concrete failure in the existing kneel-rise action:

> A person lowers onto both knees, pauses upright on their knees, steps one foot forward and rises to standing.

All five saved breadth-study seeds begin in a kneeling posture and later stand. Retargeting and contact cleanup cannot account for the missing standing/descent phase because it is already missing in the native model output.

## Historical evidence

`reports/kneel-historical-phase-screen-v1/summary.json` binds all five original NPZ assets to their generation records and saved posture traces. Every clip has 180 frames at 30 fps. The table reports fixed diagnostic intervals with exclusive ends; these are posture proxies, not complete semantic annotations.

| Seed | Initial kneeling interval | Final standing interval | Full standing–kneeling–standing proxy |
|---:|---|---|---|
| 1301 | 0–117 | 151–180 | Missing |
| 2089 | 0–87 | 122–180 | Missing |
| 3253 | 0–57 | 98–180 | Missing |
| 4099 | 0–26 | 79–180 | Missing |
| 5101 | 0–66 | 113–180 | Missing |

The diagnostic uses native SOMA-scale joint positions: at least 0.3 seconds of pelvis height ≥0.8 m with both knees flexed ≤35° for standing, and both knees at height ≤0.15 m with flexion ≥85° for kneeling. These rules were fixed before the new paired generation experiment. A correct fast or stylized clip can fail them; a clip matching the intervals can still omit an upright kneeling torso, forward step or believable descent. Keep human action correctness separate.

## Paired development experiment

The prepared request `benchmarks/kneel-start-guides-v1.json` generates eight fresh clips: four fixed seeds, each with the original prompt alone and with the same prompt plus a full-body guide at frame zero. The guide uses the original seed1301's standing endpoint. Both conditions use the same model and sampling settings. This is repair informed by an observed failure, not held-out release evaluation.

The plan and source hashes are in `reports/kneel-start-guides-plan-v1`. Its actual constraint compiler and forward-kinematics checks passed. Execution started at 2026-09-28 16:08 UTC after the previous solver terminated successfully and its handle was consumed. The launch check verified the six prepared implementation files, request, source pose, compiled guides and audit implementation, with 3.94 GiB available RAM. Current progress is recorded in `reports/action-jobs/kneel-start-guides-v1/pipeline.json`; the fixed preparation protocol remains preserved separately. The worker retains its memory/time guards.

`scripts/audit_kneel_start_study.py` completed the eight-clip audit in `reports/kneel-start-guides-audit-v1`: source and conditioning identities checked, native posture traces retained, 359 decoded whole/half-frame mesh samples per clip, and 1,440 actual Godot actor-frames passed. Generation was interrupted after one saved clip; the exact owner and all generation children were confirmed absent before resuming. The unfinished attempt remains saved alongside its successful retry. A guide match or successful engine import does not count as action correctness.

## First outcome and coordinate correction

All four guided clips have a sustained upright start. Two pass the fixed standing–kneeling–standing posture proxy, versus zero of four fresh baselines. Guided seeds3253 and4099 have no sustained both-knees-low interval under the fixed rule. Worst decoded mesh floor depths are 42.48,32.27,9.72,9.54 mm for guided seeds1301,2089,3253,4099 respectively; physical quality remains unresolved. No visual or human rating was obtained: browser security policy blocked access to the local Studio page.

All four initial guide audits flag root-path and joint-position errors. Inspection then found a setup issue: the source endpoint has smoothed-root XZ=(0.04853224,-0.03636461) m, and the compiler copied this into a frame-zero guide. The pinned upstream `vendor/kimodo/docs/source/user_guide/constraints.md` requires the starting smoothed-root XZ at the canonical origin. Do not attribute the full positional error to model limitations without separating this incompatible starting placement. The unchanged v1 results and interpretation are preserved.

The repeat `benchmarks/kneel-start-guides-v2.json` and `reports/kneel-start-guides-plan-v2` translate the complete guide source uniformly by the negative endpoint XZ offset. Source heights, rotations, contacts and heading are unchanged; selected-frame smoothed-root XZ is exactly zero. The original NPZ is untouched. All eight repeated clips and their audit are complete; all1,440 Godot actor-frames pass.

`reports/kneel-origin-comparison-v1` verifies unchanged model settings, identical text-conditioning tensors, byte-identical baseline NPZs, requests differing only in guide source, and the uniform horizontal source translation. Root-path error falls from61.6–63.2mm to2.8–5.2mm. Joint-position error falls to38.8–50.0mm and still fails the provisional30mm screen. The action-order proxy remains2/4, and physical defects remain. Correct placement improves pose accuracy but does not supply the missing middle phase.

After both studies terminated, the request compiler gained an explicit optional `guide_origin: "start_pose"`. It applies a shared XZ translation to every compiled guide using the frame-zero guide, records the transformation, and leaves source files untouched. Omitting it preserves old behavior. Seven focused tests plus existing constraint/request tests pass40/40, including equivalence to the independently translated source, shared-target preservation, unchanged rotations/heights/source bytes, and invalid-mode/missing-anchor rejection. This is a request-JSON feature; no Studio control or automatic scene-placement change has been added.

The timed run, `benchmarks/kneel-timed-phases-v1.json`, is complete. It uses2seconds for lowering,1second for the kneeling pause and3seconds for rising, with four seeds both unanchored and start-guided. It exercises the new origin option on the original source directly. All eight clips exported, and the audit passed1,440 actual Godot actor-frames. The fixed posture rules and physical checks remain unchanged. The no-guide condition is the baseline within this timed experiment.

## Timing outcome and developer review

`reports/kneel-timing-comparison-v1` compares all16 canonical single-prompt and timed clips. Every timed clip covers the entire requested2–3s interval with the sustained kneeling posture proxy. Both timed conditions pass the complete ordered-posture proxy in2/4seeds. Segmentation supplies the middle phase reliably in this small development set, but does not reliably finish the rise. It also increases floor penetration for six of the eight matched clips; timed depths range33.30–87.02mm.

The two end-check failures differ. Seed2089 ends low, with pelvis height about0.54m and knees still flexed about111–117degrees: the rise is missing. Seed4099 ends with pelvis near1m but the left knee flexed53–58degrees; it has begun rising and may still be moving. The fixed standing-finish proxy fails, but a human must judge endpoint usability. Do not equate those two failure modes or change the fixed threshold to hide either.

The new timing diagnostic reports overlap with the requested pause, torso tilt and pelvis speed without introducing a semantic pass threshold. Three focused tests cover partial overlap, exclusive frame boundaries and standing-still ambiguity. Transition samples from the exporter remain available separately; quiet pelvis motion alone does not establish a natural pause.

`reports/kneel-phase-developer-review-v1.zip` contains16 labeled GLB/BVH clips, root/predicted-contact sidecars, licenses, a manifest and blank developer notes. Copied/archive bytes and ZIP CRC were verified against the engine-checked source files. This is a labeled developer packet, not a blind independent animator study; no human observations or cleanup times have been entered. Browser inspection remains blocked by browser security policy and was not bypassed.

The next controlled test should add an ending-pose guide to the timed sequence and measure whether it restores the rise without creating an abrupt finish. Compare a final-frame target with a short held ending, preserve the complete seed population, and retain floor/dynamics failures. Current results do not justify adopting any prompt/guide configuration as a release-ready default.

If a single start guide fails, inspect how it fails before choosing the next intervention: a rapid snap back to kneeling, missing middle phase and missing final standing pose call for different changes. Timed sub-action prompts and additional authored pose guides are existing capabilities worth comparing before considering learned adaptation. Do not substitute a canned kneel animation for arbitrary prompt support.

No independent human observations or cleanup-time results have been received. All artifacts remain development evidence; the project-wide release goal remains active.


## Ending guides: completed development comparison

`reports/kneel-ending-comparison-v1` binds the timed start-only reference to eight new matched clips. Both ending conditions share the same frame-zero pose, timed descriptions and fixed four seeds. A final-frame guide targets frame179; a held ending targets frames170–179. Both impose the same source standing pose and location. Exact cached conditioning tensors and checkpoint/sampling settings match.

Both ending treatments pass the fixed standing–kneeling–standing proxy in4/4seeds, versus2/4for start-only. All preserve100%kneeling-proxy coverage during2–3seconds. Holding the ending does not establish smoother motion: final-second joint acceleration is higher in3/4pairs versus final-frame; floor penetration improves in2/4and worsens in2/4. These derivative measurements are diagnostic, not a naturalness classifier.

All eight new clips retain guide residuals and33.30–98.45mm worst sampled surface penetration. Decoding the exact worst whole/half-frame in each of the12reference/new clips locates the lowest vertex on shin-dominated skin, during descent or rise. Weight attribution is approximate, not an anatomical support annotation. All1,440new Godot actor-frames passed. Raw outputs and failed physical screens are preserved; no default promotion or human quality claim follows.

The next replay applies the existing body-clearance implementation unchanged to all eight ending-guided clips, retaining raw and limb-only baselines. It must preserve action phases and report knee support gaps, motion changes and guide drift rather than treating a clear floor as success. New audit implementation is frozen in `reports/kneel-body-clearance-plan-v1`.


## Clearance replay: phase preservation and support loss

The unchanged body-clearance replay is complete in `reports/kneel-body-clearance-v1`, with an independent audit in `reports/kneel-body-clearance-audit-v1`. It retains all eight sources and raw, limb-only and body versions. All 24 versions preserve the fixed ordered posture proxy and full requested pause coverage. Body clearance removes penetration at all decoded whole and half frames, with root lifts up to 100.45 mm.

Seven of eight body candidates retain knee gap or sliding regression flags. Guide joint error still reaches 56.96 mm. Clearing a floor plane therefore does not establish usable knee support or exact pose adherence. The decision remains experimental with no default promotion. The raw files remain untouched. Root guide diagnostics explicitly distinguish the original smoothed trajectory from the edited pelvis fallback.

Sixteen new limb/body GLBs passed 2,880 actual Godot actor-frames; the eight raw GLBs already passed 1,440. The labeled packet `reports/kneel-clearance-developer-review-v1.zip` contains all 24 versions, editable GLB/BVH files, actual root tracks, predicted contact tracks and blank developer notes. Copied and archived bytes and CRC are verified. It has not been visually reviewed by the agent, and no human observations or cleanup times have been entered.

Next: test explicit knee surface support targets with foot contacts and whole-surface clearance, within existing edit bounds. Begin with a bounded pose feasibility comparison before a full temporal solve. Preserve phase timing, boundary pose errors and failed candidates; do not treat skin clearance alone as acceptance.
