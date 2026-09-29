# Preserving hand speed during a coupled release fit

The coupled fit now improves release angular continuity without increasing either hand's measured release speed relative to the input spatial clip. All sampled grasp, geometry and edit-limit checks remain passing. Small angular regressions at the fitted window's joins and the later whole-clip acceleration regression remain unresolved, so this is not motion-quality approval.

The preceding [coupled experiments](sphere-region-coupled-v1.md) reduced the angular jump but increased hand speed. The new variant keeps their nine-key window (116–124), original joint limits, contact conditions, root and frozen non-arm parameters. It adds a separate object-relative release-speed fitting cap for each hand.

## Fitting and independent comparison

For each source hand, the writer measures the maximum native-key object-relative anchor speed over the four edges starting at frames 119–122. The caps are 0.0868824275 m/s on the left and 0.1680329239 m/s on the right. Subtracting a declared 0.001 m/s fitting reserve gives 0.0858824275 and 0.1670329239 m/s. Positive excess over these caps contributes a soft residual with a 0.0005 m/s scale. These are comparisons to this source clip, not physiological limits or a changed contact tolerance.

`speed_excess_pair` provides derivatives with respect to both anchor positions. The coupled Jacobian maps those through the authored object rotation and each arm's skin Jacobian. The complete real-character directional check has maximum scaled discrepancy 1.21e-5, within the declared 2e-4 check. There are 216 variables and 1,271 residuals. Squared fitting residual decreases from 583.991029 to 510.929353; this mixed objective is not a perceptual score.

The solve takes 55.828 seconds including preflight/output and reaches the 20-evaluation limit without convergence. The candidate is retained with that failure status. A fitting cap alone cannot establish that exported motion satisfies it.

The auditor independently reconstructs the native source caps and reserve, verifies all source hashes and native edits, and re-exports both the candidate and its exact pre-fit spatial input. It evaluates both GLBs at 717 integer/quarter-frame samples using the same decoder. Per-hand release preservation compares the measured peak object-relative speed over the existing release-boundary window, with only a 1e-7 m/s numerical comparison allowance. The source GLB hash also matches the earlier spatial study.

| Release measurement | Re-exported input | Candidate |
| --- | ---: | ---: |
| Left-hand peak object-relative speed | 0.086946 m/s | 0.085961 m/s |
| Right-hand peak object-relative speed | 0.168194 m/s | 0.167289 m/s |
| Largest arm local rate-step difference at frame 121 | 1.351084 rad/s | 1.173822 rad/s |

Both exported speed-preservation comparisons pass. The largest release rate-step difference improves by about 13%. Native fitting caps and exported maxima differ slightly because the latter include interpolation and serialization; the export comparison, rather than the optimization penalty, decides preservation.

## Preserved checks and remaining defects

The candidate revalidates all 245 grasp samples, including the six changed grasp keys, and passes all 717 sampled geometry and original edit-limit checks. All 171 outside frames and non-arm physical edits remain exact. Minimum sphere clearance is 2.069914 mm, floor height 2.001973 mm, and maximum joint edit 38.574322 degrees.

The new reproducible `audit_region_boundary_rates.py` decodes both exports, verifies their hashes, rig names and duration, and records every arm joint at the entry, release and exit boundaries. It retains these regressions:

- Frame 115: largest arm rate-step difference rises from 0.087161 to 0.095833 rad/s.
- Frame 125: it rises from 0.295188 to 0.302683 rad/s.
- The return endpoint at frame 145 is unchanged.

These local relative-rotation step differences diagnose joins; they are not inertial angular acceleration or calibrated perception thresholds. Whole-clip peak joint speed remains 1.364917 m/s and acceleration 40.041065 m/s². The latter still exceeds the original V13 comparison's 38.516182 m/s²; its frame-132 peak lies outside this fitting window. A passing release-speed comparison does not certify the rest of the motion.

Forty focused tests pass, including speed-residual derivatives and constant angular motion across rotation wraparound. Godot matches all 180 frames and 77 bones within 0.311 micrometres. These results establish computation/export fidelity; they do not establish anatomy, self-collision, continuous/triangle-interior collision freedom, balance, physical grip forces or human quality.

Next preserve window-join behavior explicitly while improving the trajectory, and address the later torso/arm acceleration as a coordinated path problem. Reuse the per-hand and per-joint comparisons rather than relying only on a whole-clip maximum. The broad action, rig, object, partner, editing/style and human evaluation requirements remain open; all 14 release capabilities are unapproved.

Evidence: `reports/sphere-region-coupled-speed-v1`, its `-audit` sibling, `reports/sphere-region-coupled-speed-boundaries-v1` and `reports/sphere-region-coupled-speed-engine-v1`. Raw inputs, failed earlier variants, protocols and source snapshots remain local and immutable. No Studio default, model, training data or held-out trial changes. The earlier developer review question is still pending; no ratings or cleanup time are fabricated.

## Reproduction

Existing local fixtures and separately acquired licensed dependencies are required. Use fresh output directories.

```powershell
.venv\Scripts\python.exe scripts/coupled_release.py reports/sphere-region-spatial-v1 reports/new-speed-fit --cartesian-curvature-scale-m .0005 --release-speed-reserve-m-s .001
.venv\Scripts\python.exe scripts/audit_region_grasp_track.py reports/sphere-region-track-v2 reports/new-speed-audit --approach-patch reports/sphere-region-approach-v1 --floor-patch reports/sphere-region-floor-v1 --release-patch reports/sphere-region-release-v1 --spatial-patch reports/sphere-region-spatial-v1 --coupled-patch reports/new-speed-fit
.venv\Scripts\python.exe scripts/audit_region_boundary_rates.py reports/new-speed-audit reports/new-speed-boundaries
```
