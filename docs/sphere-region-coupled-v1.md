# Coupled grasp and release fitting

Fitting the last grasp poses and the start of release together reduces the release's angular discontinuity while retaining every sampled grasp, collision and edit-limit check. A hand-speed tradeoff remains, and neither fit converged within its declared evaluation budget. These are development candidates, not approved animations.

The [endpoint-rate experiments](sphere-region-tangent-v1.md) showed that exact next-key continuation with the final grasp poses frozen exceeds the original arm-edit budget. `coupled_release.py` instead fits nine keys, frames 116–124, jointly. This includes six grasp/release-guard keys through frame 121 and three post-release keys. Each key has 24 arm variables; the shoulder, arm, forearm and wrist on both sides may change. The original bounded-rotation map enforces their norm limits. Non-arm physical edits and root remain exact, as do all 171 outside frames.

## Objective and verification

The first variant preserves the measured passing hand points, region normals and tangents tightly during grasp, and treats the prior post-release hand frames as weaker guidance. Point scales are 0.02 mm during grasp and 5 mm after release; direction scales are 0.001 and 0.05. These are optimization weights, not changes to authored acceptance tolerances or contact events. Floor and all sphere-object clearance deficits also contribute to the fit. The object-clearance fitting target includes a 0.05 mm reserve.

The temporal term penalizes second differences of eight local arm rotation matrices. Its stencil includes two fixed keys on each side, so entry and exit joins contribute. This chordal objective is useful for fitting but does not equal physical angular acceleration. V2 adds second differences of the two world-space skin anchors, with a 0.5 mm scale, after V1 improved angular continuity but increased hand speed.

The problem has 216 variables. V1 has 1,197 residuals; V2 has 1,263. An independent finite-difference directional check of the complete geometry and temporal Jacobian has maximum scaled discrepancy 8.31e-6 in both variants, within the declared 2e-4 check. V1's squared fitting residual decreases from 29.597235 to 20.863617; V2's from 575.981698 to 508.304251. Those totals use different objectives and must not be compared as motion-quality scores.

Both fits hit the fixed 20-evaluation limit without convergence. V1 takes 54.484 seconds and V2 takes 56.547 seconds including preflight and output work. Their solver failures are retained. Bounds, contact and export feasibility are established by subsequent checks, not by the optimizer's termination status.

The extended auditor checks source/snapshot hashes, the exact nine-key/joint scope, all frozen parameters, native reconstruction and all 171 protected frames. It reconstructs the measured hand guidance from the source skin, then exports the candidate and rechecks the complete 245-sample grasp population. Because grasp poses changed, earlier grasp passes are not simply inherited.

Both variants pass all 245 grasp samples and have zero geometry or original edit-budget failures across 717 full-clip integer/quarter-frame samples. Minimum floor height remains 2.001973 mm and sphere clearance 2.069914 mm. Maximum rotation edit is 38.697601 degrees in V1 and 38.634199 in V2. The original fixed-point condition remains unsolved; these results concern the explicitly authored region condition.

## Measured tradeoffs

| Measurement | Input spatial return | Coupled V1 | Coupled V2 with hand path term |
| --- | ---: | ---: | ---: |
| Largest arm rate-step difference at release | 1.351084 rad/s | 1.110340 rad/s | 1.137169 rad/s |
| Right-hand release relative speed | 0.168194 m/s | 0.192219 m/s | 0.174148 m/s |
| Left-hand release relative speed | 0.086946 m/s | 0.087934 m/s | 0.087777 m/s |
| Whole-clip peak joint speed | 1.364917 m/s | 1.364917 m/s | 1.364917 m/s |
| Whole-clip peak joint acceleration | 40.041065 m/s² | 40.041065 m/s² | 40.041065 m/s² |

V1 reduces the largest arm rate-step difference at frame 121 by about 18%, but increases right-hand speed. V2 reduces that speed regression while retaining an angular improvement. Neither dominates the input across every measure. The unchanged global speed peak is outside this window, and the acceleration peak at frame 132 is also outside the fitted window. Global aggregates alone would miss these local improvements and regressions.

Window joins are measured too. At frame 115 the largest arm rate-step difference changes from 0.087161 to 0.109176 rad/s in V1 and 0.087662 in V2. Frame 125 changes from 0.295188 to 0.293140 and 0.273956 rad/s. The later return endpoint at frame 145 is untouched. These decoded local-relative rotation step differences are continuity diagnostics, not inertial angular acceleration.

An additional check records the authored object's velocity: it changes by 0.064936 m/s at frame 121 and is stationary afterward. This track was not edited. Matching object motion during contact and then leaving it must be assessed together; these studies do not claim physical grip forces or object dynamics.

## Scope and next work

Godot imports both candidates and matches all 360 actor-frames with 77 bones, within 0.311 micrometres in position. Thirty-eight focused tests pass, including temporal boundary stencils and previous rotation, grasp, clearance and floor tests. Full Jacobian checks use the actual character fixture. Engine fidelity does not approve naturalness, self-collision, balance, continuous/triangle-interior collision, physics or gameplay behavior.

Next use these measured tradeoffs to improve the constrained trajectory objective: preserve per-hand release behavior as well as angular continuity, and evaluate how much of the already-authorized contact-region freedom can be used without relaxing its acceptance gates. The unchanged frame-132 torso/arm acceleration also needs coordinated treatment. Extending fitting effort should be justified by convergence or feasibility evidence, not by repeatedly changing acceptance criteria.

Raw evidence stays under `reports/sphere-region-coupled-v1`, `reports/sphere-region-coupled-v2`, their `-audit` siblings, `reports/sphere-region-coupled-boundaries-v1`, `reports/sphere-region-coupled-boundaries-v2` and `reports/sphere-region-coupled-engine-v1`. No Studio default, model checkpoint, training data or held-out trial changes. All 14 release capabilities remain unapproved; broad action/rig/object/partner coverage and human ratings/cleanup evidence remain required. The earlier developer comparison question is still pending.

## Reproduction

Existing local fixtures and licensed dependencies are required; use fresh output directories.

```powershell
.venv\Scripts\python.exe scripts/coupled_release.py reports/sphere-region-spatial-v1 reports/new-coupled --cartesian-curvature-scale-m .0005
.venv\Scripts\python.exe scripts/audit_region_grasp_track.py reports/sphere-region-track-v2 reports/new-coupled-audit --approach-patch reports/sphere-region-approach-v1 --floor-patch reports/sphere-region-floor-v1 --release-patch reports/sphere-region-release-v1 --spatial-patch reports/sphere-region-spatial-v1 --coupled-patch reports/new-coupled
```
