# Interaction alternatives and the next path experiment

Checked 2026-09-27. This extends the earlier source survey; no alternative weights, training data or body models were downloaded, and no third-party model code was executed.

## Additional primary sources

- **InterMask** publishes an interaction-generation implementation and a download script for its model checkpoints. Its repository code is MIT licensed. The InterHuman inference representation contains 22 joints per actor; the Inter-X route adds separate SMPL-X and dataset requirements. The inspected README, LICENSE and download script do not establish a separate checkpoint-specific commercial permission statement. Keep checkpoint, code and underlying data permissions distinct. This is a research comparator, not a selected product dependency. [Author repository](https://github.com/gohar-malik/InterMask), [code license](https://github.com/gohar-malik/InterMask/blob/main/LICENSE), [download script](https://github.com/gohar-malik/InterMask/blob/main/prepare/download_models.py).
- **Interact2Ar** releases an autoregressive human-interaction implementation and checkpoint manifest. The main checkpoint is listed as 3,522,226,119 bytes; this file size is not an inference-memory measurement. Its repository license restricts use to noncommercial research. The README also requires separately obtained Inter-X/SMPL-X assets. It is not selected for Strep product integration under these terms. [Author repository](https://github.com/pabloruizponce/Interact2Ar), [repository license](https://github.com/pabloruizponce/Interact2Ar/blob/main/LICENSE), [checkpoint manifest](https://github.com/pabloruizponce/Interact2Ar/blob/main/assets/checkpoints.json).

The earlier Uni-Inter, InterControl and InterAct findings remain in [interaction-research-v2.md](interaction-research-v2.md). Public availability does not establish local Windows feasibility or arbitrary-rig export support. No learned replacement is qualified by this survey.

## Evidence driving the next implementation

The complete native body-fit plus authored-fingers audit contains 15 scenes across five seeds, 180 decoded samples per scene and 4,500 verified engine actor-frames. All five authored-finger variants pass the recorded contact-event region screen, but all fail the whole-clip collision and floor screens. Their worst penetrations range from 20.21 to 22.92 mm. The peaks involve forearm/hand/finger vertices and occur at frames 56, 64.5, 66, 73 and 83.5. A correction restricted to frames 60–90 cannot repair the frame-56 failure.

`reports/paired-pose-posture-summary-v2` independently checks asset hashes, engine population, sample population, extrema, source target placement/clock/contact specification, and per-vertex skin influences. The older summary-v1 is retained because the new path trial already referenced it; v2 strengthens scene provenance without changing metrics. Skin weights identify influences, not anatomically reviewed labels. Sample runs do not certify continuous collision intervals.

Using the full rotation norm budgets improves the difficult event-pose orientation error from 18.11° to 4.46°, but still leaves one of ten actors outside the fixed 0.5° tolerance. This is a local optimizer result, not a proof of infeasibility. Increasing event accuracy alone does not solve the measured approach and recovery collisions.

## Selected development trial

`reports/bounded-surface-path-v1` starts from the first declared seed, 1301, with matched event-pose initialization and the separately authored finger layer. It uses five timed arm-control vectors per actor over frames 45–105, full per-control norm budgets, and the existing adjacent correction-speed cap. The fitting samples include a fixed broad clock, half-frame contact neighbors, and recorded failure peaks. Frozen local surface constraints are refreshed between iterations; actual mesh queries guard trial steps. Restoration slack is an optimizer aid and never an accepted penetration tolerance.

The current trial is sparse fitting, not full validation. Every candidate and unsuccessful iteration must remain visible. Export decoding, integer/half-frame geometry, engine import, preservation and joint-budget checks are required afterward. Root and legs stay fixed, so existing floor failures remain. If the local method stalls again, report that result rather than relaxing quality thresholds or declaring the interaction solved.
