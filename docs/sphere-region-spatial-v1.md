# Spatial arm return after a grasp

Replacing the post-release arm path brings whole-clip peak joint speed below the original V13 comparison while preserving all previously passing sampled contact, collision and edit-limit checks. Acceleration and endpoint continuity still require work. This is a development result for one sphere interaction, not motion-quality or release approval.

The [timing-only experiments](sphere-region-release-v1.md) could not remove the speed regression. Their V2 peak remains at the right index finger over frames 129.25–129.5. `spatial_release.py` instead takes each of eight shoulder/arm/forearm/wrist local rotations directly from the frame-121 release pose to the frame-145 return pose along its shortest rotation arc. A quintic time curve eases both ends. Fingers, torso, legs and root retain the V1 24-frame return's physical edits. Frames 122–144 change; all 157 other native frames, including grasp and approach, stay exactly equal to that input.

## Clearance correction and evidence

The uncorrected spatial path fails the original 2 mm sphere-clearance requirement at frames 122–125: its minimum is 0.058071 mm, still positive but insufficient. This failed path is retained as `uncorrected-motion.npz`; it is not silently discarded.

For those four keys, radial guidance moves the influenced left-hand skin away from the sphere, preserving its proposed orientation. The same bounded arm solver fits the resulting anchor/normal/tangent targets. Guidance includes mixed arm/hand skin weights; all skin is checked again after articulation and export. The original acceptance remains 2 mm while the guide targets 2.5 mm. No event is delayed or advanced.

| Frame | Left radial guide | Solver evaluations | Resulting sphere clearance |
| --- | ---: | ---: | ---: |
| 122 | 1.236547 mm | 5 | 2.500000 mm |
| 123 | 2.069849 mm | 5 | 2.500031 mm |
| 124 | 2.441932 mm | 6 | 2.499988 mm |
| 125 | 1.754474 mm | 5 | 2.500013 mm |

All four solves report convergence, taking 4.890 seconds in total. The first solve's directional derivative error is 1.90e-7 or less. Other release keys require no radial correction. Original physical rotation/root budgets remain enforced; maximum decoded joint edit is 38.563710 degrees.

The extended auditor independently reconstructs each shortest-arc path with SciPy Slerp, verifies preserved non-arm parameters, replays native corrected and uncorrected arrays, checks input/snapshot hashes, and measures the actual exported GLB. It does not claim independently reproducing the optimizer's chosen solution. The export retains:

- All 245 passing grasp/release-guard samples.
- Zero object/floor or original edit-budget failures across 717 integer/quarter-frame samples.
- Minimum floor height 2.001973 mm and sphere clearance 2.069914 mm.
- Exact preservation of the protected input frames.

## Motion tradeoffs

| Clip | Peak joint speed (m/s) | Peak joint acceleration (m/s²) |
| --- | ---: | ---: |
| Original V13 comparison | 1.409751 | 38.516182 |
| Symmetric 24-frame edit return | 1.697571 | 36.587825 |
| Spatial arm return with clearance correction | 1.364917 | 40.041065 |

The new speed peak is at `HeadEnd`, frames 52–52.25, outside the changed release interval. The remaining acceleration peak is at `RightHandIndexEnd`, frames 131.75–132.25. Local relative-rotation diagnostics identify torso/neck curvature at that time; the exact world-space acceleration includes parent transforms and the exported piecewise interpolation. These diagnostics localize a problem rather than establish causality or natural motion.

There is also a boundary defect: the arm path eases to zero local angular velocity, whereas the surrounding motion has nonzero velocity. At frame 121, right-shoulder local angular speed changes from 1.331163 rad/s on the preceding interval to 0.020869 rad/s on the next. Right-hand release-boundary relative speed increases from V1's 0.139982 m/s to 0.168194 m/s; the left decreases from 0.103389 to 0.086946 m/s. A lower whole-clip speed does not excuse this mismatch. The next correction needs endpoint tangent matching and coordinated torso/arm trajectories under unchanged collision and edit limits.

## Validation and scope

Twenty-three focused tests pass across shortest-arc rotation wraparound, invalid path fractions, release profiles, grasp transport, radial guidance and floor constraints. Godot verifies all 180 frames with 77 bones; maximum joint-position discrepancy is 0.311 micrometres. This is playback fidelity, not physics or visual approval.

An offline preview compares the previous and spatial returns using the actual SOMA skin and authored sphere. Its software triangle rendering has approximate lighting and occlusion. Developer review was chosen earlier, but no ratings or cleanup time have been recorded.

Evidence is retained under `reports/sphere-region-spatial-v1`, `reports/sphere-region-spatial-v1-audit`, `reports/sphere-region-spatial-diagnostic-v1`, `reports/sphere-region-spatial-engine-v1` and `reports/sphere-region-spatial-preview-v1`; the initial geometric probe is under `reports/sphere-region-spatial-preflight-v1`. The raw failures and prior variants remain immutable. Assets and bulky reports stay out of Git.

The original fixed-point grasp condition remains unsolved; this uses the explicitly authored region condition. Sampled vertices do not prove continuous/triangle-interior collision freedom, self-collision, anatomy, balance, grip forces or naturalness. No Studio default, checkpoint or held-out test changes. All 14 release capabilities remain unapproved; broad action, rig, object, partner and real human evidence is still required.

## Reproduction

Existing local fixtures and separately acquired licensed dependencies are required. Use fresh output directories.

```powershell
.venv\Scripts\python.exe scripts/spatial_release.py reports/sphere-region-release-v1 reports/new-spatial
.venv\Scripts\python.exe scripts/audit_region_grasp_track.py reports/sphere-region-track-v2 reports/new-spatial-audit --approach-patch reports/sphere-region-approach-v1 --floor-patch reports/sphere-region-floor-v1 --release-patch reports/sphere-region-release-v1 --spatial-patch reports/new-spatial
```

Follow-up: [endpoint-rate experiments](sphere-region-tangent-v1.md) retain failed budget/clearance variants and motivate solving the final grasp and release jointly.
