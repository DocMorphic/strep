# Preserving inferred support points during scene fitting

The box-grasp diagnostic detects both feet as low and slow for all five source keys, yet its candidate moves their support points by up to 75.342 mm. The old solver gives inferred support a soft squared-distance preference; only explicit authored contacts participate in its point-constraint multipliers. A floor-penetration check therefore does not establish planted feet.

## Optional fitting and independent measurement

`fit_scene_regions.py --preserve-support LeftFoot --preserve-support RightFoot` now adds separate augmented inequalities for those inferred points on their existing active frames. The default remains off. Selection rejects unknown, duplicate, inactive, explicitly authored or disabled regions, so this option cannot replace an author's contact overrides. It preserves the inferred source material points and their targets; it does not invent contact during flight.

The inequalities use the existing 5 mm point tolerance. Their signed residual is divided by that tolerance before multiplier/penalty updates, yielding a dimensionless quantity without changing the feasible set. Hand-contact loss normalization remains separate. Recipes record the selection and normalization; protocols and implementation snapshots bind the setting. This is an optimization constraint, not a hard feasibility guarantee or a planted-sole/force/balance model.

`audit_scene_preserved_support.py` reconstructs the source inference and measures those points on independently decoded GLBs at 120 Hz. It binds the source, mesh, fit artifacts and inference implementation. It skips inactive intervals and records a coverage gap if the inferred material-point identity changes between keys; a gap cannot silently count as a successful preservation check. The report gives sample counts, failures and maximum drift for source and candidate. The existing geometry and hand-contact audit remains separate.

The exact-owner completion runner automatically runs this audit when the fit requests preserved supports. The Studio publisher requires the matching support report (`--support`), validates its selection, tolerance and recomputed summary, includes it as a download, and makes any failure visible in the candidate review note and regressions. Missing support evidence cannot be packaged as a complete comparison. No quality approval follows from packaging.

## Checks and retained trials

Forty-five focused tests pass, including normalization's unchanged feasible set/unit invariance, selection respecting author intent, changing material-point coverage, mismatched/tampered report rejection, initialization, regional objectives, root optimization, jobs and review packaging. `reports/support-preservation-final-integration-v1` compares frozen/current fitting on an existing five-frame fixture using two stages of two iterations: all legacy and physical-box output arrays remain bit-identical when preservation is off. All four outputs preserve original edit bounds and native FK discrepancy below 0.3 micrometres.

The first development trial used the raw metre residual with existing point penalties. It completed in 119.516 seconds and 1,121 objective evaluations, but all 34 foot-support samples still failed: maximum drift 75.634272 mm. All 34 hand-contact and 17 geometry samples also failed, with 5.973343 mm worst box penetration. This failed output and its exact implementation remain intact under `reports/region-preserved-support-v1`; it does not establish support preservation.

The normalized follow-up uses the same frozen original source, grip seed, scene, tolerances, six stages of 100 iterations, shared-pose controls, root bounds, full sparse skin, stage witness refresh, rate guard and 600-second budget. The intended difference is the support residual's normalization and multiplier units. It is retained separately under `reports/region-preserved-support-normalized-v1`. Neither trial is a new action, held-out example, full motion or human review.

## Completed normalized trial

| Measurement | Original soft inference | Metre residual | Tolerance-normalized residual |
| --- | ---: | ---: | ---: |
| Failed support-point samples / 34 | 34 | 34 | 0 |
| Maximum support drift | 75.341546 mm | 75.634272 mm | 4.973310 mm |
| Failed hand contacts / 34 | 34 | 34 | 34 |
| Failed geometry samples / 17 | 17 | 17 | 17 |
| Worst box penetration | 9.243853 mm | 5.973343 mm | 14.080265 mm |

The normalized solve finishes in 131.703 seconds and 1,045 evaluations. It preserves the sampled source support points within 5 mm while the grasp and body clearance remain invalid. Root lift is 7.531468 mm and minimum sampled skin-floor gap is 10.229638 mm, compared with roughly 77 mm lift/81 mm gap in the metre-residual candidate. The source points themselves are above the floor, so relative preservation is not a zero-gap ground-contact guarantee. Maximum original-source rotation edit is 27.313440 degrees. Original edit bounds pass, native frames remain identical, and exported acceleration is below 1.9e-11 m/s². No temporal motion improvement follows from this stationary diagnostic.

All six stages reach their iteration limit. The independent support result, rather than optimizer termination, establishes the narrow point-preservation outcome. Both new trials pass Godot import for 20 source/candidate actor-frames and 77 joints with position discrepancy below 0.232 micrometres. The automatic completion runner is also exercised on the retained metre trial: it saves the support hash and reproduces the support failure along with the other audits. That extra import check repeats an existing candidate; it is not another fitting experiment.

`reports/region-preserved-support-normalized-v1/comparison.json` binds the three-way comparison to output/audit hashes. Between the metre and normalized trials, all protocol settings and original inputs match; only timestamp and the recorded `support_contact_v8.py` implementation differ. `compare.py` and each fitting implementation snapshot preserve the methods.

Studio collections `preserved-support-metres-review-v1` and `preserved-support-normalized-review-v1` retain both failed overall results. Packaging each without its support report is confirmed to reject before creating a folder. Across the two packages, 26 file hashes and 24 permitted routes pass offline verification; Python snapshots are intentionally not served. The latest publisher additionally rejects nonfinite/negative support errors, covered by focused tests. No live browser or human review was performed.

This result justifies keeping optional normalized support constraints and their independent audit, not approving the grasp or launching another full animation solve. Next address forearm clearance and hand-region constraints together with the preserved supports, including inner-solver convergence. The original broad action, rig-transfer, editing, partner, export and human-cleanup requirements remain open; all 14 release capabilities are unapproved.
