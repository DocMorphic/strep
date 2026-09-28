# Bounded surface and predicted-support correction comparison

This development experiment follows the completed 195-transfer breadth study. It uses every one of the five jab-cross-retreat seeds on CesiumMan and Quaternius female: ten inputs spanning two rig families. Each input has a clearance-only control and a support-aware candidate, for twenty planned outputs. This is a deliberately bounded correction test on an observed failure family, not held-out validation or a restriction of the product's action scope. The separate 390-clip all-family generation study has now completed.

Both methods use the existing analytical target-mesh clearance fitter and the same six-sweep, 80-evaluation-per-subproblem budget. Both follow native foot-surface clearance scaled by leg length, clamp requested penetration at zero, penalize floor penetration across every skinned vertex, and penalize displacement from original horizontal foot-surface trajectories. All frames of the derived clip may change within the existing limits: 4 cm horizontal and 12 cm vertical root movement, the existing per-joint angular budgets, and adjacent correction changes of at most 15 mm and 5 degrees. Original inputs remain unchanged. No limit is raised to obtain a pass.

The support candidate adds one horizontal foot-region centroid penalty with weight 40. Candidate intervals require an existing model foot/toe support prediction and native foot-surface height within 30 mm of the floor, for at least four consecutive frames. The anchor is the median of the first three target centroids; the penalty fades over three frames at each edge. These are **unconfirmed support hypotheses**. Centroid movement can be valid during foot roll or pivot, predictions may be wrong, and floor proximity does not prove weight-bearing. The control receives zero weight for this term; a numerical regression test confirms equivalence to the prior objective.

Each completed output is decoded independently. The audit measures full skin penetration at every frame and half frame, native-height mismatch, hover, predicted-support horizontal speed, drift from drafted anchors, peak local joint rotation steps and root acceleration. It verifies all root/joint/adjacent edit budgets, unchanged nonroot translations and unselected transforms, the exported root track and exact preservation of original contact predictions. Each source/control/candidate group is then imported into Godot. Numerical improvement does not imply action correctness, balance, naturalness or engine GPU-skin approval.

`scripts/breadth_contact_fit.py` implements the objective and raw-transfer adapter. `scripts/verify_breadth_contact.py` evaluates decoded GLBs. `scripts/study_breadth_contact.py` freezes the protocol, baseline input hashes and implementation sources, retains all twenty planned rows, and records every failure. It refuses to restart an existing attempt. The CPU runner uses one numerical thread and hides CUDA from its own process; shared-machine timings are not isolated performance measurements.

The study is **running**, with no candidate quality decision yet. Artifacts and live progress are in `reports/breadth-contact-v1/{protocol,freeze,runner,pipeline,results}.json`, with per-candidate sweep/frame progress under `takes`. Check the actual PID and creation time before interpreting a stale status file. Do not modify the frozen implementation or restart on observation timeout.

Four focused tests passed in 5.01 seconds: analytical objective derivatives, exact zero-weight control residual equivalence, short/airborne interval rejection and edge fades, plus actual GLB verification and rejection of an excessive vertical root edit. No full-suite rerun is claimed. No model weights, raw motion data, independent human ratings or release gates changed.

## First completed pair, 2026-09-27

CesiumMan, jab-cross-retreat seed 1301 is the first completed pair in protocol order. It is not selected for its score. The other nine paired inputs remain in the live study and in the review snapshot's population record.

| Diagnostic | Original transfer | Clearance only | Added predicted support |
| --- | ---: | ---: | ---: |
| Integer-frame skin floor depth | 59.45 mm | 0.22 mm | 0.22 mm |
| Half-frame skin floor depth | 59.69 mm | 0.74 mm | 0.74 mm |
| Left support centroid speed p95 | 6.15 cm/s | 6.14 cm/s | 2.37 cm/s |
| Right support centroid speed p95 | 4.27 cm/s | 4.27 cm/s | 2.52 cm/s |
| Left support hover | 0 mm | 1.28 mm | 1.26 mm |
| Right support hover | 0 mm | 6.34 mm | 6.34 mm |
| Peak pelvis acceleration | 4.35 m/s² | 4.98 m/s² | 4.66 m/s² |
| Peak adjacent local joint rotation | 43.81° | 43.81° | 43.81° |

Both speed measurements use the same 145 left and 135 right predicted-support steps. Zero original hover coexists with penetration. Both candidates meet the decoded edit budgets and preserve unselected transforms. Both consume all six sweeps without the small-update stopping condition, and neither has a stationarity certificate. The support candidate improves these contact proxies relative to the clearance control; it still increases peak pelvis acceleration relative to the original and retains its large local joint step. Whether those motions are suitable for the requested action needs review. One seed and rig do not establish general reliability.

Actual Godot imports check all three 150-frame clips (450 frame samples, 19 bones); maximum position discrepancy is 2.38e-7 m and basis discrepancy is 5.69e-7. Khronos validation finds zero errors and one inherited warning in each file. Those are structural checks, not physics, GPU-skin or animator approval.

[Inspect the synchronized comparison](http://127.0.0.1:8767/reports/breadth-contact-review-v1/viewer.html). The package includes the original transfer, both candidates, root/contact sidecars, original native source, licensed test character and frozen implementation/solver/audit evidence. Every archive entry was byte-checked; the three GLBs, ZIP, canonical candidate report and license were downloaded through HTTP and matched their retained hashes.

The experimental fitter inherited some old diagnostic fields when copying baseline reports. The separate package now supplies canonical stage `report.json` files sourced from the independent decoded audits; the original report is preserved as `original-report.json` with an explicit warning about stale inherited metrics. This packaging fix does not modify the frozen live study or claim those old fields were measured on the candidate. The viewer reads verified metrics and preserves the selected frame when switching stages. No candidate is promoted into Studio's default transfer path.
## Second paired result: Quaternius female, seed 1301

The second input in protocol order now has both candidates and its paired engine audit complete. The unmodified transfer has no floor penetration but predicted-support hover reaches 93.0 mm on the left and 114.5 mm on the right. Clearance-only correction reduces those maxima to 2.57/10.57 mm while leaving predicted-support speed almost unchanged at 0.3975/0.2291 m/s. The support-weighted candidate gives 2.57/10.56 mm hover and reduces those speed proxies to 0.1537/0.1137 m/s, still above the proposed 0.05 m/s release criterion.

Both candidates remain within the fixed edit/preservation budgets. Their maximum half-frame floor depth is below 0.574 mm; source integer floor depth was zero and remains zero. Peak local rotation step remains 43.81 degrees, inherited from the source. The support candidate's peak root acceleration is 7.36 m/s² versus 7.03 originally. This is improvement on some proxies, not a contact-quality pass or evidence that the first successful Cesium speed result generalizes. Two of ten paired inputs are complete; all planned cases remain in the study.


## Interrupted worker and verified recovery, 2026-09-27

The original worker PID 7420 / creation 1790517897.9339893 disappeared and its exec handle 41004 was absent. Its status files still said fitting; no exception was present at the end of the retained log. Cause is unknown. Seven completed candidate outputs and three complete engine groups were rehashed/compared before recovery. The partial eighth fit (motion-007-rig-02-support, sweep 1 frame 100) had no saved parameter checkpoint.

`recover_breadth_contact.py` preserves the original runner/status/results/log and every partial output byte under `interrupted-attempts/recovery-01`. The partial folder was moved only after verifying both resolved paths remained inside the named study workspace, then every moved file hash was checked. Completed candidates and engine groups are skipped after evidence checks. Only the interrupted fit restarts, followed by previously pending cases, using the unchanged frozen solver/settings and six-sweep budget. The interrupted attempt remains in the row's attempt history; it is not erased or labeled a numerical failure.

The hidden background recovery worker was confirmed live as PID 28812 / creation 1790526634.8519664 (launcher 35044), with `recovery-01.log` and `.err`. Its identity must be rechecked before future decisions. All nineteen original implementation hashes still match the frozen protocol; the recovery driver is additional orchestration evidence. No quality or study-completion approval follows from recovery.


## Verified interim snapshot: five paired inputs

`reports/breadth-contact-interim-v1/summary.md` captures all five inputs with both candidates and complete engine groups at the snapshot time; ten of twenty candidates and five of ten input groups. Every stored verification, original/candidate GLB hash and three-clip engine population was checked. All twenty planned rows remain in its population record. There are 2,250 actual engine frame samples in these five groups.

All ten corrections have whole/half-frame floor depth below 0.75 mm. Cesium inputs improve from roughly 59–61 mm; the two Quaternius inputs start at zero and gain less than 0.70 mm penetration. The support term reduces the worst predicted-support speed for each of the five paired inputs; three support candidates meet the proposed floor/speed/hover proxy screens, while both completed Quaternius cases still exceed the 0.05 m/s speed threshold. Clearance-only meets those proxies on two cases. These partial-development counts are not final study success rates, confirmed support, physical balance or usable-animation approval. The original motion derivatives and any new regressions remain in the JSON summary.


## Complete declared population

The recovered worker completed at 2026-09-27 20:14:15 UTC and its exact process subsequently exited. `reports/breadth-contact-summary-v1` verifies all ten input groups, twenty corrected clips and 4,500 actual engine actor-frames. Original interruption/recovery history remains retained. All five rig-01 support candidates meet the proposed floor/p95-speed/hover screens; none of the five rig-02 support candidates do. Clearance-only passes three rig-01 cases and no rig-02 cases. Support improves p95 sliding on every paired input, but rig-02 remains at 0.0653–0.1537 m/s. These are development proxy counts, not realistic-motion success rates; subsequent time traces demonstrate why p95 alone misses endpoint spikes. No release or animator approval follows.
