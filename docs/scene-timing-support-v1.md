# Support and joint-rate review after timing edits

Studio trim and speed jobs now compare the exported source and edited actor meshes at matching motion phases. Review notes include ground-slide p95, peak joint acceleration and floor depth; a downloadable report contains all joint peaks and inferred ground-support edges. Original and edited motion remain available. The measurements do not approve the animation.

`scripts/audit_scene_timing.py SOURCE CANDIDATE OUTPUT [--first F --last L]` reads hashed portable scene packages, verifies unchanged rigs/mesh data/placements and decodes both exports. It uses source-quarter-frame samples (120 Hz), with the corresponding edited time step. It measures world-space full-mesh floor depth and each joint's linear speed/acceleration and world angular speed/acceleration. Finite differences on interpolated curves are sampling-dependent diagnostics, not estimates of joint forces.

Ground-support hypotheses use source foot patches whose lowest points are within 25 mm of the ground at both endpoints and whose patch-center horizontal speed is at most 0.2 m/s. The source's lowest material vertex is tracked across that edge in both variants, even if another vertex becomes lower. Keeping source selection fixed avoids improving a score merely by changing which support edges are included. P95 and counts above 0.05 m/s are reported without promoting these hypotheses to authored or verified contacts. No minimum stance duration is imposed.

## Three-scene development comparison

| Scene / actor | Speed | Ground-slide p95, source → edited (m/s) | Peak joint acceleration, source → edited (m/s²) |
| --- | ---: | ---: | ---: |
| Paired high-five / A | 0.671171× | 0.01581 → 0.01061 | 94.26 → 42.46 |
| Paired high-five / B | 0.671171× | 0.01723 → 0.01157 | 118.28 → 53.28 |
| Box release / A | 1.491667× | 0.04350 → 0.06489 | 44.72 → 99.50 |
| Moving-platform scene / A, ground only | 0.748954× | 0.04350 → 0.03258 | 44.72 → 25.08 |

Across **2,628 matched actor-phase samples**, maximum source/edited skin discrepancy is below **0.561 micrometres**. Per-joint linear and angular rates follow the expected time-scale changes within the recorded numerical tolerances. The faster box-release motion increases inferred edges above 0.05 m/s from **47 to 138**. Slowing the pair reduces sliding but retains actor B's **11.96 mm** floor penetration, with 95 sampled poses above 10 mm. Preserving a path does not repair its geometry.

Evidence: `reports/scene-timing-support-v1` retains methods, input/implementation hashes, complete reports and a separate numerical verifier. These are existing development fixtures, not held-out validation. The platform fixture's actor ground motion reuses the release source; this report does not measure motion relative to the platform or certify platform support.

A separate actual Studio box-release speed job passes preparation, execution, immutable snapshot checks, refreshed scene measurements, seven file-route checks and report inclusion in the review note. That fixture is different from the comparison above: p95 changes **0.02560 → 0.03819 m/s** and peak acceleration **27.44 → 61.07 m/s²**. Evidence is retained in `reports/studio-timing-support-v1` and `reports/scene-trim-jobs/studio-timing-support-release-v1`.

Fifteen focused Python tests pass, including an actual paired-scene trim worker, rate scaling, changing lowest-vertex identity and exclusion of airborne/deeply penetrating/fast patches. Engine export/playback code is unchanged; this study adds no new engine or browser validation. Moving-support reference frames, sustained contact classification, body balance, forces, continuous collision, semantics and independent review remain open. All fourteen release capabilities remain unapproved.
