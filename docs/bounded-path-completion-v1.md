# Automatic export and independent path verification

`finish_bounded_surface_path.py` waits for the exact wider-path solver owner to exit successfully and for the previous geometry audit to finish. Quiet output never triggers a solver restart. It records implementation snapshots and validates source hashes before processing the result.

The adapter reconstructs the candidate from the saved authored-finger source and final arm-control vectors. It checks control/norm budgets against the declared limits, verifies the saved trajectory against its interpolation basis, preserves nonedited local transforms and translations, and exports the candidate next to the original motion. The frame/joint axes are selected explicitly when producing motion arrays.

Before acceptance of the export as structurally valid, it independently decodes original and candidate GLBs at all **299 integer and half-frame samples** across the clip. It checks total local rotation edits, correction speeds, unchanged root motion, protected joints and the motion outside frames45–105. Failed checks retain their reports and candidate; nothing is silently clamped or approved.

The actual Godot stage verifies all77 bone transforms over150 frames for both actors in each of the original and candidate scenes:600 actor-frames. The geometry stage then checks the entire299-sample clock for each scene, records both directional mesh penetration and floor depth, and measures the palm region at event75. These are sampled geometric checks, not continuous collision, anatomy, semantics, physical balance or human review.

The completion job is `reports/bounded-surface-path-completion-v1`. At creation it is waiting for the live solver; no candidate export or quality success has yet been claimed. Three focused tests pass in0.89s: two cover path composition with non-topological hierarchy, protected transforms and malformed controls; the existing export-axis regression also passes.


## Completed outcome, 2026-09-27

The exact strict solver and completion worker have both exited successfully as processes. The three fixed refinement iterations accepted zero steps; each retained the same contact-corrected initializer. This is a failed correction result, not a quality success. All four exported actor clips pass 600 actual Godot actor-frame transform checks, and both actors pass 299-sample decoded edit bounds.

The full 299-sample geometry audit reports maximum body penetration of 21.6226 mm for the raw pair and 24.7404 mm for the retained corrected pair, with 9 versus 14 samples exceeding the collision screen. Maximum floor penetration remains 11.9591 mm. At the contact event, the reference-point gap improves from 64.9504 to 22.6281 mm and opposing palm-normal error from 30.2879 to 5.1917 degrees, but the surrounding motion still fails. Since the strict refinement accepted no step, the raw/candidate difference comes from the retained initializer; do not attribute it to a newly accepted refinement.

Verified evidence is in `reports/bounded-path-final-summary-v1.json` and `reports/bounded-surface-path-completion-v1`. The separately frozen screen-preserving path trial began automatically after this audit; it is still running and has no final result. No human, anatomy, physics or release approval is inferred.
