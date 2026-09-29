# Full-duration regional contact transfer

The next development trial runs on the complete 180-frame motion behind the earlier five-frame box fixture. It preserves the original approach, grasp interval (frames 60–121), release, object keyframes, contact patches, anchors and tolerances. It applies the same declared +2-degree local wrist-X perturbation throughout the source and changes the target primitive to the earlier box dimensions. There is no repeated-frame padding or newly generated action. The original short crop differs by at most 1.79e-7 in rotation elements and 5.97e-8 m in positions because of reconstruction precision.

The fitter starts from this full perturbed source, not the corrected five-frame candidate. Its hard budgets are relative to that source, rather than the older sphere solver's cumulative reference. The recorded configuration is six stages of 100 iterations, a 3,600-second budget, balanced regional penalties, stage-wise witness refresh, full object-vertex coverage, per-vertex object multipliers, the earlier 0.05 mm clearance and 0.01 mm contact-gap solver margins, and sampled export-rate constraints with a 0.05% acceleration margin. All acceptance limits remain unchanged.

The initial four-subdivision box-floor check had a conservative lower bound of -0.799555 mm and could not decide nonpenetration. Refining that same bound to 120 subdivisions per frame certifies at least 1.100452 mm of box-floor separation; the smallest sampled gap is 1.165969 mm at frame 61. The distant prescribed prop rests on the floor with zero gap. Neither object requires a placement edit to resolve the initial uncertainty. The 2 mm skin-floor and skin-object fitting margins must not be silently repurposed as a requirement that every scene prop hover 2 mm above the floor. No object track or target was changed.

## Exact sparse skin calculation

The optional `--skin-backend sparse` compiles fixed skin weights and inverse-bind points into a sparse linear map from joint affine transforms to vertices. Duplicate coefficients are summed and exactly zero coefficients omitted. All vertices and all nonzero influences remain. This avoids allocating the large frame-by-vertex-by-influence rotation tensor. The default backend remains `gather`.

On all 180 frames, 18,056 vertices and eight influence slots of the retained motion, maximum position discrepancy is 8.89e-16 m and maximum transform-gradient discrepancy is 7.11e-15. Five-frame chunked forward/backward timings were 2.179 s for gathering and 0.403 s for the sparse map; the full sparse batch took 0.330 s. These are local kernel measurements, not whole-solver speed or peak-memory claims. The running full fit was observed using approximately 1.5 GB RSS; this is an observation, not a measured peak.

The existing three-stage, 40-iteration short sphere repair reproduces every native array and the candidate GLB bit-for-bit with sparse skinning. It retains 34/34 contact, 17/17 geometry and original edit-bound passes. Actual Godot checks pass ten actor-frames across source/candidate exports and 77 joints, with maximum position discrepancy below 0.211 micrometres. The focused regression suite passes 72 tests; three new rate-audit tests and two process-identity tests pass separately (77 distinct tests total).

## Full-motion validation

The full fit and its exact-owner completion audit have finished. The numerical worker took 1,509 seconds. Execution completed, but the candidate fails contact and clearance requirements. The completion process did not retry fitting; it audited decoded quarter-frame geometry, original edit bounds, per-joint rates and all source/candidate Godot frames.

`audit_scene_joint_rates.py` reports each joint's peak and its sample location over the whole clip, approach, grasp, release, and two-frame neighborhoods around each contact boundary. Speed samples are located at edge midpoints and acceleration at stencil centers; overlapping windows are explicit. An unchanged global maximum cannot hide local increases in this report. These diagnostics do not create new acceptance thresholds or infer naturalness.

Evidence is retained in `reports/linear-skin-full-clip-v1.json`, `reports/region-sparse-sphere-regression-v1`, its adjacent audit, `reports/region-sparse-engine-v1`, and `reports/region-full-transfer-v1`. The latter contains the immutable authored fixture, full input, fitting protocol and implementation snapshots. No human, held-out, additional-action or release approval follows. All 14 release capabilities remain open.

Reproduce with `prepare_region_transfer_study.py` in a fresh report directory, then `fit_scene_regions.py` with the configuration above. The fixture builder requires the preceding local development assets. `verify_linear_skin_operator.py` independently compares a supplied native motion against gathered skinning; `audit_scene_region_fit.py` and `audit_scene_joint_rates.py` consume a completed fitting directory. Weights and generated artifacts remain excluded from Git.

The refined object-only evidence is retained in `reports/region-full-transfer-v1/object-floor-diagnosis.json`. Its two-millimetre comparison is a diagnostic reference, not an authored prop-floor acceptance gate. Nonpenetration does not establish physical support, friction, contact forces or valid actor contact. The full character fit and independent audit are now complete, with failures detailed below.

## Completed full-motion result

| Measurement | Original full source | Candidate |
| --- | ---: | ---: |
| Hand-contact failures | 490 / 490 | 490 / 490 |
| Full-body geometry failures | 382 / 717 | 267 / 717 |
| Worst body-box penetration | 54.256846 mm | 5.272749 mm |
| Whole-clip peak joint speed | 1.364918 m/s | 1.342813 m/s |
| Whole-clip peak joint acceleration | 37.982124 m/s² | 36.839410 m/s² |
| Release-boundary peak speed, frames 119–123 | 0.337513 m/s | 0.788448 m/s |
| Release-boundary peak acceleration, frames 119–123 | 22.747577 m/s² | 36.839410 m/s² |

The candidate's worst penetration occurs at frame 121.75, outside the integer fitting keys. All 245 left-hand samples still fail the normal limit; 221 right-hand samples fail it. Missing distributed-contact witnesses remain in 183 left and 130 right samples, and anchor failures increase from zero to 26 and 111 respectively. Original edit bounds pass with a maximum 31.589323-degree edit. Root lift stays approximately 0.022 mm despite its larger allowed range; that observation does not by itself prove that root motion would resolve the contact errors.

Whole-clip peaks conceal local changes: 47 joints increase their speed maximum and 14 increase acceleration by more than 1e-5 in the respective units. Across the release boundary, those counts are 69 and 68. No temporal-quality approval follows from the lower global maxima. Actual Godot imports pass all 360 actor-frames and 77 joints, with maximum position discrepancy below 0.317 micrometres. Playback fidelity does not approve the failed motion.

The complete source/candidate scene is available in Studio's Scene interactions collection as `full-box-transfer-review-v2`, labelled “needs correction.” It preserves object tracks and target regions and includes the geometry, joint-rate and engine evidence. The comparison is summarized in `reports/region-full-transfer-v1/comparison.json`; all raw outputs and snapshots remain intact.

## Bounded pose-seed diagnostic

A separate inexpensive initializer applies the passing short grip's source-relative rotation correction at frame 60 and tapers its original spline control parameters around contact frames 60–121, using a 24-frame fade. The two source conditions have matching contact definitions, primitive geometry and object transform at the reference frame. This is a parameter-transfer test, not rigid transport of a grip with the object.

`scene_pose_seed.py` retains the original body/finger rotation balls and physical finger parameter units. Its full 180-frame seed passes original edit and bone-offset checks and is recoverable by the unchanged spline to 4.08e-8 radians. Two focused tests verify representability, bounds and invalid-guide rejection. However, each hand passes distributed contact in only one of 62 native grasp frames. Worst anchor errors reach 21.50 and 27.06 mm, and whole-body box penetration remains 52.62 mm. This seed was not submitted to another expensive full solve. Evidence is in `reports/region-full-pose-seed-v1`.

The next initialization must account for the object's moving frame, rather than repeating a local-joint correction. Short-fixture success has not established full-action contact reliability. All 14 release capabilities remain unapproved; no training, human ratings or held-out coverage were added.

The updated publisher flags per-joint and phase/boundary rate increases even when both whole-clip peaks improve. Eleven focused seed, initializer and publisher tests pass. The earlier `full-box-transfer-review-v1` package remains retained; v2 copies the same motion and adds these diagnostic warnings, rather than representing another animation trial.
