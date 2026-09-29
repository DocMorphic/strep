# Fit saved stationary contact checks

Studio now has a separate **Fit saved checked pins** action. It consumes the saved successful timing check and its exact revision, including material-point IDs, held edit window and original per-phase rate ceilings. Changing the draft does not change this request. Conflicting checks, changed sources, altered artifacts and changed rate calculations are rejected. The existing Apply contact edit action retains its previous behavior.

Each job snapshots the selected clip, original raw/limb history, checked artifacts and Python implementation. The current clip is the newer fitter's edit reference; the source remains unchanged. The fitter uses sparse eight-weight skin, physical root bounds, two stages of at most 60 iterations, whole-body and individual-point rate objectives. These objectives do not guarantee feasibility. Every candidate remains unapproved and exposes a separate decoded-export audit.

## Actual retained result

The development fixture uses the existing get-up clip, with a revised single left-foot pin on fixed vertex 8845 over frames 90–110 inside held window 20–159. Its target comes from that vertex at frame 100 plus 3 mm horizontally. This is a new authored request; the earlier conflicting two-foot request remains retained. The revised request passes necessary endpoint travel checks with zero conflicts.

The actual supervisor completed fitting and export, preserving the checked specification and rate reference exactly. **The candidate fails motion-quality checks:** all 81 contact samples exceed 5 mm, with maximum error **99.5805 mm**. Hold acceleration exceeds its checked ceiling by **0.0450445 m/s²**; release speed exceeds its ceiling by **0.00132512 m/s**. Full-skin floor penetration rises from **2.33564 to 10.3989 mm**. Other body-support regressions remain recorded. Passing the timing preflight therefore does not establish a feasible or successful correction.

The independent audit samples all 717 quarter-frame times using decoded GLB interpolation and all eight skin influences. It inspects every authored interval, including multiple intervals on one region. All 160 outside-window samples preserve the source within numerical tolerance; maximum skin difference is **8.94e-8 m**. Finite sampling does not certify continuous collision avoidance, anatomy, balance or naturalness.

Actual headless Godot playback passes 407 pose observations, two authored marker events, forward/reverse playback, four callback-mutation rejections and unloading. Maximum actor matrix component error is **1.26e-6**. The markers denote requested pin boundaries, not measured successful contacts. Engine fidelity does not approve motion quality.

Thirty-two focused Python tests and the offline Node editor checks pass. Direct invocation of the real study-list handler confirms the candidate can be previewed; four download routes resolve, including the audit and export archive. No HTTP/browser rendering or human review was performed. Local evidence remains under `reports/studio-checked-fit-v1` and `reports/contact-jobs/studio-checked-fit-v1`; generated payloads are excluded from Git.

The next numerical task is to diagnose why the checked fitter misses this explicit pin and introduces support/floor regressions, retaining this failed candidate as a control. More iterations or a passing endpoint check alone are insufficient evidence. This authoring integration closes no release capability; all fourteen remain unapproved.
