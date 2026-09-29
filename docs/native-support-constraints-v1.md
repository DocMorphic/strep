# Fixed-patch support constraints

The retained kick-22 fit passes its authored foot pin but adds a left-foot sliding flag. The regression occurs before the pin: its largest interval increases are at frames 40–44, outside the requested frames 50–70. Relative to raw, fixed-patch slide p95 rises from 0.161415226 to 0.187536916 m/s, above the existing 0.181415226 limit. The limb-relative comparison also fails. The right foot and both feet in jump/landing-22 pass their support screens.

The existing explicit-contact override replaces inferred contacts for an entire named region. The fitter excludes that explicit region from its inferred sliding term and constrains the authored material point only during its active interval. The independent reviewer still measures its fixed original hand/foot patches across the clip. This leaves a mismatch between what is optimized and what is reviewed; one stationary vertex does not preserve a whole foot.

## Optional constraint

`native_support_objective.py` builds the same fixed reference masks as `evaluate_floor_contact.compare`: consecutive region heights below 3 cm, horizontal mean-region speed below 0.35 m/s, and vertices less than 1 cm above that frame's original minimum. Regions with fewer than three qualifying intervals gain no constraints.

Each reference/region has two augmented inequalities. Slide p95 must stay within the original p95 plus 0.02 m/s for feet or 0.08 m/s for hands; gap p95 must stay within the original p95 plus 0.015 m. The reference patches and percentile limits never follow the candidate. All supplied skin influences are retained by the sparse operator. The new `native_support_references` argument in `support_contact_v8.refine` keeps these constraints independent of explicit contact selection, including intervals outside a pin.

This matches the existing numerical hand/foot review; it is not an annotation of load-bearing support, balance, anatomy, continuous contact or realism. Percentile constraints still allow individual outliers. Augmented optimization does not guarantee feasibility, and the final independent native/export review remains required. Studio defaults remain unchanged while the new mode is evaluated.

## Verification and matched experiment

Eight focused objective tests cover independent NumPy percentile parity, fixed patches, ignored high vertices, separate hand/foot allowances, insufficient support intervals, no-support behavior, finite/checked gradients, multiplier updates and invalid inputs. Fifty focused tests including existing body, support, held-pose and original-budget checks pass, with four existing Torch deprecation warnings.

Read-only replay on the actual kick-22 and jump/landing-22 candidates matches every independently recomputed foot p95 within 1e-10, with finite gradients and unchanged original input hashes. The kick objective flags only the left-foot slide residuals against raw and limb. The landing objective is zero. Reports are retained under ignored `reports/native-support-diagnosis-v1`.

`reports/native-support-fit-v1` compares two fresh warm restarts of kick-22: control and fixed-patch support. Both use the same original source, warm seed, pin target, held window, root/rotation limits and export point/global/floor guards. Both use four outer stages and 60 iterations per stage. The native body objective is disabled in both, isolating the support change. This is a new matched development experiment, not a replacement for the earlier four-stage/120-iteration batch.

The runner now exposes explicit body/support mode and stage/iteration options while retaining its previous defaults. Each run snapshots inputs and methods, preserves all outputs, independently checks exported motion and runs engine playback. Both modes are now complete and independently verified below. No human evidence or release approval is inferred.


## Completed matched control

The control mode completed 924 evaluations in 602.29 seconds. All 81 pin samples pass (4.751178 mm maximum), raw added floor depth is zero, and original global speed/acceleration limits pass. Release point acceleration still exceeds its fixed ceiling by 0.000077121 m/s². The left-foot sliding flag remains: raw-relative p95 is 0.194987017 m/s versus the 0.181415226 limit, worse than the original warm seed's 0.187536916.

Native exports and 284 actual engine observations pass. All original input, implementation-snapshot and completion-artifact hashes were verified after this mode completed. This control remains rejected and cannot establish the benefit of the new constraint by itself. The matched support-enabled result is recorded below; both modes used identical frozen methods.


## Completed paired comparison

Both modes are terminal and their shared worker has exited. Verification checked every original and snapshotted input, every current and archived implementation file, and every completion artifact. Inputs and method snapshots are identical between arms; the sole protocol difference is enabling the support objective. Saved NPZ support measurements match the independent body reviewer within 1e-10 for all measured reference/region pairs. Native body peaks were independently recomputed, and every audited outside-window error is exactly zero.

| Measurement | Control | Fixed-patch support |
| --- | ---: | ---: |
| Fit time | 602.29 s | 817.80 s |
| Optimizer evaluations (including line search) | 924 | 961 |
| Left-foot slide p95 | 0.194987017 m/s | 0.181411910 m/s |
| Original raw-relative slide ceiling | 0.181415226 m/s | 0.181415226 m/s |
| Maximum authored pin error | 4.751178 mm | 4.484613 mm |
| Pin samples exceeding 5 mm | 0 / 81 | 0 / 81 |
| Added floor depth | 0 m | 0 m |
| Body-review flags | Left-foot sliding | None |
| Engine pose observations passing | 284 | 284 |

The support-enabled fit removes the measured sliding regression against both raw and limb references without losing the authored pin. Its raw-relative peak joint displacement is 0.016093586 m and added joint speed is 0.140986990 m/s; limb-relative values are 0.013049051 m and 0.076736267 m/s. Both global speed/acceleration ceilings pass. These are edit nonregression measurements, not independent judgments of realistic motion.

The exported contact screen still fails: hold acceleration exceeds its original ceiling by 0.000240430 m/s²; release speed by 0.000000118404 m/s and release acceleration by 0.000641540 m/s². These small residuals are retained as failures, without relaxed acceptance tolerances. The control also fails release acceleration by 0.000077121 m/s².

This single matched case supports fixing the optimization/review coverage mismatch. It does not establish reliability across actions, rigs or seeds, and the support result sits only about 0.000003316 m/s below its raw slide ceiling. Neither output is quality-approved; Studio defaults remain unchanged. The next bounded experiment is the existing export-feedback repair on a separate copy of the support candidate, retaining the original request and budgets and rechecking support, pins, body, preservation and actual engine playback. No repair outcome is claimed here.

Local immutable evidence: `reports/native-support-fit-v1/verification.json`, each arm's `freeze.json`, `protocol.json`, `completion.json`, and saved native/export/engine artifacts. Generated motion, character payloads and machine reports remain excluded from the public repository.
