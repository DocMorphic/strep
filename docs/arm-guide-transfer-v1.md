# Arm-guide transfer: useful grasp signal, rejected whole clip

Adding shoulder, upper-arm and forearm frame targets improves arm placement during the grasp but makes the whole animation worse. The candidate is rejected: hand-contact failures, total geometry failures, peak penetration and motion acceleration all increase. The optional mode remains an explicit experiment; the default hand-only initializer is unchanged.

## Implementation and matched test

`run_object_grip_seed.py --guide-mode arms` adds six joint-frame targets to the existing hands and fingers. All guide frames move with the prescribed object, using the same position/orientation objective. The protocol records the mode and target names; the recipe records the mode. `hands` remains the default and preserves the original target order and objective. Unknown modes are rejected.

The new trial and the completed hand-only transfer use identical input hashes: the original 180-frame scene, initial full-pose seed, qualified static projection, frame-121 reference and mesh. They retain the same 100-iteration budget, original source-relative rotation limits, fixed root and correction spline. Only target selection and the runner's corresponding configuration recording change; the numerical fitting implementation is identical. Adding six targets also changes the mean's denominator, so this is not a fixed per-joint-weight experiment.

Eighteen focused tests pass, including preservation of the default target list, addition of the six proximal frames without losing hand targets, guide transport across start/middle/end references, original bounded fitting and invalid-reference rejection.

## Independent export evidence

| Measurement | Hand-only guide | Arm guide |
| --- | ---: | ---: |
| Runtime | 12.532 s | 12.359 s |
| Failed hand contacts / 490 | 465 | 484 |
| Failed geometry samples / 717 | 357 | 390 |
| Maximum box penetration | 34.874050 mm | 61.531520 mm |
| Peak joint speed | 1.283916 m/s | 1.428788 m/s |
| Peak joint acceleration | 36.765938 m/s² | 66.981300 m/s² |
| Maximum original rotation edit | 19.404253° | 35.511947° |

Original edit bounds and fixed-root checks pass. The new arm-guided source/candidate pair passes 360 actual Godot actor-frames, with maximum joint-position discrepancy below 0.335 micrometres. Those import checks do not approve contact or motion quality. The hand-only engine evidence is reused, not counted as new work.

The native phase diagnosis explains why a whole-clip aggregate alone is insufficient. During the authored grasp, frames 60–121, worst penetration improves from 32.332989 mm at frame 121 to 6.685686 mm at frame 102. At frame 121 itself, arm guidance leaves 2.943589 mm penetration. Outside the grasp, however, it produces 61.531549 mm penetration at frame 54, versus the hand-only result's 34.874068 mm at frame 124. These are integer-key localization measurements; the quarter-frame export audit remains authoritative.

The current spline is fitted globally, with target loss active only during the grasp and soft pose/temporal regularization elsewhere. Outside poses are not constrained to the original motion. Joint-frame targets also trade against one another rather than enforcing hand skin contacts. This test supports investigating explicit hand-contact preservation and controlled approach/release edits together with arm guidance. It does not justify accepting this initializer or merely increasing the guide weight.

## Retained evidence

`reports/region-arm-guide-transfer-v1` retains the fitting and audit driver, source snapshot, native diagnosis, matched comparison and result hashes. Studio collection `arm-guide-transfer-review-v1` exposes the failed source/candidate comparison with geometry, timing and engine reports. Twelve package file hashes and eleven permitted offline routes are checked; its Python snapshot is intentionally unserved. No live browser or human quality review was performed.

The earlier static projection remains valid evidence for one repeated pose. Neither moving initializer is approved, and all fourteen release capabilities remain open.
