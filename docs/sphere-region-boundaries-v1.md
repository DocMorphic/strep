# Collision-aware approach and floor correction

The development sphere-grasp clip now passes all 717 exported integer/quarter-frame object, floor and original edit-limit samples, while retaining all 245 passing grasp samples. The approach and floor defects recorded in the [moving grasp study](sphere-region-track-v1.md) are corrected. Motion-quality regressions, anatomical review, self-collision and broader validation remain unresolved; this is not release approval.

## Approach correction

`sphere_approach.py` computes a radial translation that places the influenced hand patch outside the sphere plus a guidance margin. Each skin vertex defines a forbidden interval along that translation ray. Merging these intervals handles a vertex that starts safe but would enter the sphere while another vertex is being moved out. The guidance includes every vertex with any positive hand-subtree influence, including mixed forearm/hand skin. It is a rigid estimate; the articulated result is checked separately.

`correct_region_approach.py` preserves the existing pre-contact hand orientation and non-arm edits, then fits the translated anchor with the bounded shoulder/arm/forearm/wrist solver. Per-frame reference rotations, root, offsets and object poses are refreshed before differentiable FK. No contact event is moved earlier. Only four native keys change; all 176 other frames, including the entire grasp and release, remain exactly unchanged.

| Frame | Left-hand outward guide shift | Actual minimum sphere clearance |
| --- | ---: | ---: |
| 56 | 2.006445 mm | 2.500127 mm |
| 57 | 5.656106 mm | 2.500002 mm |
| 58 | 6.262320 mm | 2.499970 mm |
| 59 | 4.241525 mm | 2.500004 mm |

Each solve takes five evaluations; total recorded projection time is 4.390 seconds. Original norm limits and all non-arm parameters are preserved. FK agrees with independent skin reconstruction within 0.105 micrometres; the scaled directional derivative error is below 1.23e-7. The guidance uses 2.5 mm clearance while acceptance retains the original 2 mm requirement.

The exported audit reduces the edited-window geometry failures from 17 to zero across 341 samples. The previously retained 3.760326 mm approach penetration is gone. Grasp measurements remain unchanged because those native frames are preserved exactly.

## Earlier floor clearance

The clip still had 104 samples below the 2 mm floor-clearance requirement before the approach. The worst measured floor height was 1.879032 mm; this was a clearance deficit, not ground penetration. `region_floor_envelope.py` solves a convex quadratic program for nonnegative root lift, minimizing lift energy and second differences subject to all dense sample constraints and the original root-lift budget. It uses the exported float32 clock to interpolate root keys. Frame zero and frames 48 onward are locked.

`correct_region_floor.py` adds at most 0.123291 mm to root Y and all joint heights over frames 1–47. Rotations and horizontal root coordinates stay exact. All 133 locked frames, including approach, grasp and release, remain byte-for-byte unchanged. The constraint target includes a 2 micrometre numerical reserve; the serialized export reaches a minimum floor height of 2.001973 mm. The added root motion has maximum speed 0.000664 m/s and acceleration 0.007727 m/s².

After both corrections, the complete exported clip has:

- Zero object/floor failures across all 717 sampled times, testing all 18,056 skin vertices and both authored objects.
- Zero original rotation/root edit-limit failures across those same times.
- All 245 grasp/release-guard samples passing anchor, region-normal, distributed-contact and geometry checks.
- Minimum full-clip sphere clearance 2.069914 mm and floor height 2.001973 mm.

These are sampled vertex and pose guarantees. They do not establish continuous collision freedom, all triangle-interior distances, self-collision, physical grip forces, balance or animator quality. The new region condition remains distinct from the original fixed-point/local-normal fixture, which has not been solved.

## Remaining motion regression

Whole-clip speed and acceleration remain 1.742135 m/s and 46.718854 m/s², above the original V13 values of 1.409751 m/s and 38.516182 m/s². Independent decoded localization places the new speed peak at the right forearm over frames 128–128.25, and the acceleration peak at that forearm over 131.75–132.25. Both occur in the release blend. The original peaks occur at right-hand finger endpoints later in the same release motion.

The next targeted change is therefore the release trajectory. Preserve the passing grasp and approach, evaluate the return from the held pose under the same budgets, and remeasure all geometry and dynamics after any timing/blending change. Do not weaken the acceptance criteria or treat geometry success as natural motion. Broad action/object/rig/partner coverage and real review/cleanup evidence remain required.

## Verification

The extended `audit_region_grasp_track.py` verifies patch hashes, replays the bounded parameters and exact native arrays, checks guidance against the original influenced skin, and confirms unchanged interaction frames. It independently checks the root-only translation and its dense linear constraints before exporting and measuring the actual GLB again. Study and audit source snapshots are retained. Forty-nine frames remain exactly equal to the original V13 clip after the complete sequence of corrections; the larger protected-frame counts above refer to each correction's immediate input.

Twenty-four focused tests pass, including ray-interval overlap cases, initially safe vertices that become obstructing, invalid geometry, subframe floor constraints, locked-frame infeasibility, capacity limits and zero-correction cases. Godot imports both new exports and verifies all 360 actor-frames with 77 bones; maximum joint-position discrepancy is 0.445 micrometres. Import fidelity does not approve motion quality or gameplay events.

Local evidence is retained under `reports/sphere-region-approach-v1`, `reports/sphere-region-floor-v1`, their `-audit` siblings, `reports/sphere-region-dynamics-diagnostic-v1` and `reports/sphere-region-boundaries-engine-v1`. Generated assets remain excluded from Git. No Studio default, model checkpoint, held-out release trial or release capability was promoted.

## Reproduction

Existing local fixtures and separately acquired licensed model/skin dependencies are required. Use fresh output directories.

```powershell
.venv\Scripts\python.exe scripts/correct_region_approach.py reports/sphere-region-track-v2 reports/new-approach
.venv\Scripts\python.exe scripts/audit_region_grasp_track.py reports/sphere-region-track-v2 reports/new-approach-audit --approach-patch reports/new-approach
.venv\Scripts\python.exe scripts/correct_region_floor.py reports/new-approach reports/new-approach-audit reports/new-floor
.venv\Scripts\python.exe scripts/audit_region_grasp_track.py reports/sphere-region-track-v2 reports/new-floor-audit --approach-patch reports/new-approach --floor-patch reports/new-floor
```

Follow-up: [release return experiments](sphere-region-release-v1.md) preserve these geometry checks while measuring remaining speed/acceleration tradeoffs.
