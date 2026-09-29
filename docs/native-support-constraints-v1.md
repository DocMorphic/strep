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

The runner now exposes explicit body/support mode and stage/iteration options while retaining its previous defaults. Each run snapshots inputs and methods, preserves all outputs, independently checks exported motion and runs engine playback. At launch, the control worker was confirmed live; neither outcome is established yet. No human evidence or release approval is inferred.
