# Bounded continuation of the coupled partner correction

The first bounded continuation accepts eight additional corrections, retains 15 rejected attempts, and stops when its ninth line search exhausts all five step sizes. It makes measurable progress under the original limits but does not solve the high-five or establish convergence.

## Fixed origin, limits and acceptance

The starting pair is the fully audited [full-vector candidate](coupled-surface-norms-v1.md). The study requires its completed 57-time mesh proof and exact candidate identities before running. Each subsequent proposal relinearizes kinematics around the accumulated 72 control values. The edit origin, source per-joint motion caps, original 5-degree edit limit and export tolerance, source-or-5-mm per-time depth allowances, event/release keys and original fingers remain fixed.

The run allows at most 12 additional steps, with a 900-second cooperative time guard and a 0.2-degree trust radius per three-dimensional knot update. These step radii **do not accumulate into a new total edit allowance**. The original penetrating-witness population retains its full-vector constraints, and all existing scalar gaps remain screened. Barycentric bindings remain fixed to the original target triangles; both actors' surface points continue to move.

Every exported trial checks all 77 joints over six windows at 597 quarter-frame times per actor. The existing motion tolerance remains 1e-5, original edit acceptance remains 5.0001 degrees, and surface allowance comparison retains its 1-micrometre tolerance. At least 1 micrometre of improvement in the largest retained fixed-point distance is also required. A lower global value cannot excuse a separate motion, edit, finger or retained-surface failure.

Trial factors are 1, 1/2, 1/4, 1/8 and 1/16. Each accepted step updates the accumulated controls; rejected exports remain on disk. A line search with no passing trial stops rather than silently accepting a failed clip. Final complete-mesh validation remains separate because retained witnesses do not cover every possible collision.

## Completed continuation and independent replay

The run completes in **141.22 seconds** with **eight accepted steps out of 23 attempts**. Accepted factors are 1/2, 1/2, 1/2, 1/4, 1/2, 1/2, 1/4 and 1/2. The ninth proposal fails exported motion checks at every declared factor. Larger earlier trials also have retained-surface failures. All rejected attempts and the last passing pair are preserved.

The worst retained distance to a fixed barycentric surface point falls from **23.052382 to 22.804379 mm**, an improvement of 0.248004 mm. This conservative distance is distinct from the actual nearest-surface penetration reported by the complete geometry audit below. Maximum final retained-constraint excess is 0.149 micrometres, below the unchanged comparison tolerance. Final original-reference edits are 5.000001780 and 5.000000278 degrees, within the existing export tolerance; total edit limits were never reset.

Independent history replay checks every accumulated control update, trust radius, unchanged cap layout, retained trial-vector array and acceptance decision. It accounts for **88,704 independently replayed peak values** generated across the start and all trials. The final pair is reconstructed byte-for-byte from its total controls, and a separate final decoded-motion replay checks another 3,696 peak values with maximum discrepancy 5.69e-14. Complete CPU skin evaluation independently reconstructs all 3,045 final witness vectors within 1.12e-15 m of the selected-vertex evaluator.

Fresh Godot import validation passes **600 actor-frame observations**, with maximum position error below 4.16e-7 m. Original duration, 77 bones, a skinned surface and nonlooping import behavior are retained for all source/candidate clips. Neither successful import nor these relative motion checks constitutes an animator rating.

## Completed full sampled geometry

The final complete-mesh audit covers all **57 quarter-frame times and 114 directional queries** from frames 63-77. Each direction considers all 18,056 source vertices with conservative broadphase filtering; original source queries are reused only with exact identity, placement and time-population bindings.

| Measure | Fixed original source | Continuation start | Final retained pair |
| --- | ---: | ---: | ---: |
| Maximum partner penetration | 23.556264 mm | 23.023948 mm | 22.753871 mm |
| Times exceeding 5 mm | 25/57 | 24/57 | 24/57 |

Maximum depth improves by another **0.270077 mm** relative to the continuation start and by 0.802393 mm relative to the fixed original source. No sampled pair depth increases against that original source, and no per-time allowance or floor regression is observed. The contact event retains 21/17 regional vertices within 3 mm, a 5.199358-degree opposing-normal error and 1.896658 mm penetration.

The fixed original source is the comparison reference. Relative to the continuation start, frame 66.5 increases by 0.183341 mm while remaining below its original-source depth allowance; per-sample monotonic improvement over intermediate candidates is not enforced. **The animation remains unapproved:** 24 times still fail clearance and inherited full-clip floor defects remain. Sampled vertex checks also do not certify continuous collisions, triangle intersections, self-collision, force balance or naturalness.

## Why the sequence stopped

The exhausted ninth direction is replayed with both ideal float64 kinematics and actual serialized GLBs. Actor A passes at all five factors. Actor B has six ideal and six exported rate failures at the full step, then three ideal and three exported failures at every smaller step. These include repeated ring-finger acceleration peaks across overlapping windows. The problem cannot be attributed solely to float32 rounding.

The motion-fitting reserves were deliberately held at their first-step empirical values for this comparison. At the later direction, observed positive exported-minus-affine norm error exceeds them by up to **0.000090752 m/s** and **0.006533097 m/s2**. Serialization alone shifts individual norm values by at most 0.000002318 m/s and 0.000395489 m/s2. These are local approximation measurements, not new thresholds or proof that another correction is impossible.

Next compare refreshed local fitting margins using these retained failures, while keeping the original acceptance gates, control layout and source limits. Increasing the iteration count alone would repeat the exhausted direction. The existing empirical reserve must not be treated as a universal error bound across relinearizations.

## Evidence and reproduction

Local evidence is under `reports/coupled-pair-continuation-v1`, `coupled-pair-continuation-review-v1`, `coupled-pair-continuation-limits-v1`, `coupled-pair-continuation-engine-v1` and `coupled-pair-continuation-geometry-v1`. The raw start, final pair, all trial clips, local linearizations, solver steps, recorded rejection reasons and implementation snapshots remain preserved. The current runner also writes an empty trial ledger before a time guard can stop an iteration; this does not change the observed completed trial population.

**45 focused tests pass.** New model-free policy tests join Windows/Linux CI and cover total-budget creep, a lower worst distance hiding another failure, stagnation and nonfinite evidence. The public repository contains code and summaries; reproducing the study requires the separately acquired licensed fixture, pinned solver and preceding evidence. Use new output paths.

```powershell
.venv\Scripts\python.exe scripts/study_coupled_pair_continuation.py reports/coupled-pair-surface-norms-v1 reports/coupled-pair-surface-norms-geometry-v1 reports/paired-approach-witnesses-v1 reports/<new-continuation>
.venv\Scripts\python.exe scripts/verify_coupled_continuation.py reports/<new-continuation> reports/paired-approach-witnesses-v1 reports/<new-review>
.venv\Scripts\python.exe scripts/audit_coupled_continuation_limits.py reports/<new-continuation> reports/paired-approach-witnesses-v1 reports/<new-limit-audit>
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/<new-continuation> --output reports/<new-engine>
.venv\Scripts\python.exe scripts/audit_coupled_pair_geometry.py reports/<new-continuation> reports/paired-approach-witnesses-v1 reports/<new-engine> reports/<new-geometry>
```

No learned checkpoint, held-out generation, human review or release approval is claimed. All fourteen release capabilities remain unapproved.
