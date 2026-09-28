# v0 research protocol

Hypothesis: a pretrained single-human motion model plus deterministic retargeting/contact/transition tooling can reduce animator effort across varied game actions. The four initial cases are a feasibility study, not evidence of coverage for every action.

## Conditions

Use Kimodo-SOMA-RP-v1.1, seeds 11/22/33/44/55, batch size one, and 100 diffusion steps. Keep the checkpoint and text encoder unchanged. Record the actual precision, encoder placement, package lock, model hashes, hardware, and numerical nondeterminism. A seed alone does not guarantee cross-device bitwise identity.

For each case compare generation with `--no-postprocess` against the upstream default postprocessor using the same prompt/seed. Both are in source-skeleton space. Preserve a separate transferred copy of each; later deterministic corrections form another condition. Do not call default postprocessed output untouched raw diffusion. First preserve one no-postprocess NPZ before testing optional BVH or native correction dependencies.

Run-to-roll uses two timed prompts and the upstream five-frame transition mechanism. This is a sequence baseline; it does not yet establish compatibility with a separately generated run-loop clip. Evaluate both its internal join and, later, the external clip splice.

High-five consists of two independently sampled actor tracks sharing a scene clock. They are not joint two-person inference. The same seed across actors is the initial symmetric protocol; report this and later test independent paired seeds separately. Box and high-five scene targets in `v0.json` are **evaluation targets**, not automatically supplied kinematic constraints. `constraints` is null for this first prompt-only condition. A future constrained experiment must save the exact upstream-format constraint JSON and label it separately.

## Geometry and transfer

Use metres, Y-up, right-handed coordinates, +Z forward for the study scene. Preserve native output coordinates and save the explicit transform into study space. Place the box and actors using benchmark transforms. Calibrate the rig scale/rest pose and wrist/palm offsets before contact scores; targets are provisional until the fixture's reach is verified, then freeze/version them before generating scored trials.

CesiumMan is a coarse skinned humanoid with limited hands. Wrist proxy contact can be measured with declared offsets; finger/palm-surface accuracy cannot be claimed from missing anatomy. Keep its original animation as a transfer sanity fixture, never as generated evidence. Future held-out rigs need different body proportions and fuller hands.

## Measurements

| Measure | Definition |
|---|---|
| Foot slide | Horizontal world-space foot speed (m/s) during independently checked support intervals; report mean, p95, max, and supported duration. Report model-predicted contact consistency separately. |
| Ground penetration | Maximum and time-integrated depth below ground (m, m·s); joint-only checks are proxies, mesh checks required for body conclusions. |
| Object/partner penetration | Mesh/collider overlap depth and duration; mark unavailable until geometry evaluation exists. |
| Grip/contact position | Per-hand distance to frozen world grip/palm target (m), plus hand-hand distance for high-five. Report misses, not only best frames. |
| Contact timing | First valid contact time minus target time, plus both actors' synchronization error; a miss is not zero. Use three frames for a sustained box grasp, one impact frame for high-five. Provisional 3 cm/two-frame targets and limitations are in `realism-rubric.md`; calibrate before acceptance scoring. |
| Box attachment | Time of two-hand grasp, subsequent hand/grip error, object pose consistency. A box driven by an external attachment rule is labeled a correction, not model output. |
| Loop seam | Root-displacement-normalized pose/orientation gap and velocity gap at repeated boundary; preserve intended forward travel. |
| Transition | Root position, heading, joint orientation, and velocity discontinuities at join; document actual overlap indices. |
| Action correctness | Blind animator rubric, 1–5: recognizable action, physical plausibility, usable start/end. Include failure category and confidence. |
| Rig transfer | Same metrics before/after transfer; compare bone mapping, rest alignment, proportions, twist artifacts. |
| Import | Target engine/version, file/version/hash, scale, axes, duration, root trajectory, markers; pass/fail with diagnostic. Pending until engine chosen. |
| Cleanup | Active minutes to a fixed animator acceptance rubric; log operations, reviewer, time limit, and unfinished/censored trials. |

The follow-up implements horizontal foot-speed proxies, joint-ground penetration, and root displacement in `scripts/inspect_motion.py`. A first new sample has been generated, and the unprocessed five-seed grid is running. The execution uses an explicitly labeled original-precision streamed encoder variant; full 8B resident equivalence is untested. See `realism-rubric.md` for acceptance gates and `reports/grid-v0.json` for actual execution status. Missing scene, rig, engine or animator measures remain null with a reason. Do not report FID as meaningful with this tiny set.

## Review and storage

Keep one immutable attempt directory per case/seed/actor/condition, with command, environment, logs, elapsed time, raw files and hashes. Retry into a new attempt; keep OOMs and dependency failures. Retargeted outputs reference their source hash and rig hash. Save preview and event files separately. Root tracks and contacts embedded in source NPZ must later be extracted and validated; gameplay markers are not inferred merely from prompt text.

Randomize neutral preview IDs for blind comparisons; keep the condition key away from reviewers. Report all five seeds, not best-of-five highlights. Separate tool/setup failures from motion failures. Freeze the rubric before review.

After the baseline, compare deterministic corrections against unchanged output. Only collect self-captured or separately licensed training data for measured failure categories. A paper needs held-out actions, objects, partners, and rigs; ablations; animator ratings and cleanup time; learning curves; and explicit failure reporting.
