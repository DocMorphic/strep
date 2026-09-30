# Refreshed partner bindings with clear-time protection

This matched comparison starts from the earlier [eight-step pair](coupled-pair-continuation-v1.md), which has 24 failed sample times. It does not start from the later [12-step continuation](coupled-local-reserve-v1.md), which lowered maximum penetration but lost the clearance pass at frame 69. This study changes two things together: closest-surface bindings and protection of already-cleared times. It does not isolate their individual effects.

## Method

The original 3,045 source vertex/time identities remain fixed. Fresh queries against the exact starting exported partner meshes select current closest triangles, barycentric points and outward normals. Norm constraints apply to the 2,338 currently penetrating witnesses, rather than forcing previously penetrating but now exterior points to remain near an old surface location. Scalar signed-plane constraints still include every selected row. The closest triangle changes for 1,134 rows.

All **33 previously clear sampled times** receive a 5 mm cap. Other times retain the original source-depth allowance, with 5 mm as its minimum. No original ceiling increases. The existing 1-micrometre geometric comparison tolerance remains explicit; strict and tolerance-based clearance-loss counts are reported separately. This is a new stricter comparison policy, not a retroactive reinterpretation of earlier runs.

The original total edit reference, source per-joint motion caps, 0.2-degree knot trust radius and local empirical fitting margins remain unchanged. Margin compatibility checks compare the exact motion vectors, Jacobians, radii and row kinds at the calibrated start. Surface arrays intentionally differ. One coupled proposal is tried at the existing descending line factors, with every attempted export preserved.

Acceptance requires an actual signed-distance improvement of at least 1 micrometre at the matched selected vertices. A lower conservative distance caused solely by rebinding cannot count as motion progress. Complete sampled mesh queries and engine checks remain separate mandatory evidence before interpreting the candidate.

## Proposal and export checks

The proposal solves in 37 iterations. The full step reduces the selected-vertex penetration peak but fails four actor-B motion comparisons and one actual per-time depth allowance by 1.255 micrometres; its fixed-point bound excess is 2.048 micrometres. It is rejected and preserved.

The half step passes the original exported motion, edit, finger and protected-time checks. Its selected-vertex peak falls from **22.753871 to 22.586846 mm**, a reduction of **0.167025 mm**, with no selected-vertex clearance losses or allowance failures. Final original-reference edits remain 5.000001780 and 5.000000278 degrees, within the existing 0.0001-degree export tolerance. The run finishes in 66.44 seconds with two retained trials and 11,088 independently replayed motion peak values.

Fresh Godot validation passes **600 actor-frame observations**, retaining 77 bones, a skinned surface per clip, the original duration and nonlooping behavior. Maximum position error is below 4.16e-7 m. This does not establish natural-looking motion.

## Complete geometry and independent replay

The complete audit covers **57 quarter-frame times and 114 directional queries**, considering all 18,056 vertices per actor with conservative broadphase filtering. The selected-vertex peak matches the complete sampled peak. All 33 previously clear times remain clear under both strict and numerical counts; no new cap or floor failures occur.

| Pair | Peak penetration | Times above 5 mm |
| --- | ---: | ---: |
| Fixed original source | 23.556264 mm | 25/57 |
| Eight-step comparison start | 22.753871 mm | 24/57 |
| Previous 12-step alternative | 22.503084 mm | 25/57 |
| Refreshed half-step candidate | 22.586846 mm | 24/57 |

Frame 69 improves from **3.939619 to 3.683939 mm**, retaining the pass that the previous alternative lost. Eight times nevertheless deepen relative to this comparison's start, by up to **0.090604 mm**, within the unchanged original ceilings. The policy protects clearance passes and lowers the worst depth; it does not require every already-failing depth to decrease at every step. No sampled depth increases relative to the fixed original source.

The event remains unchanged: 21/17 regional vertices within 3 mm, 5.199358-degree opposing-normal error and 1.896658 mm penetration. Full-clip inherited floor defects remain outside this edited interval. The candidate passes this local comparison policy but still has **24 failed times** and is not promoted as a release-ready animation.

Independent replay reconstructs **all six starting/trial GLBs byte-for-byte**, rechecks the exact calibrated motion center and original edit angles, and verifies all 11,088 motion peak values and both trial decisions. Full CPU skinning reconstructs **9,135 retained witness vectors** within 1.12e-15 m and the stored fresh source/closest points. Stored signed distances are replayed for trial decisions; the separate complete final mesh queries supply the independent collision evidence. Rebinding alone is never credited as animation progress.

The next experiment can use this better-cleared pair for bounded repeated refreshes, preserving total controls and the original edit/motion reference. Updated motion fitting margins must be calibrated or treated explicitly as empirical estimates at the new center; the old exact-center artifact cannot silently be relabeled. Recheck complete sampled geometry before selecting another candidate. This one-step result does not establish convergence or show that the remaining 22.6 mm penetration can be removed within the present control/edit budget.

## Reproduction and limits

Sixty focused tests pass, including ten new policy cases covering preserved clearances, unchanged original ceilings, strict versus numerical counts, invalid inputs, and the prohibition on counting rebinding alone as improvement. The new policy tests join model-free Windows/Linux CI.

```powershell
.venv\Scripts\python.exe scripts/study_coupled_refreshed_pair.py reports/coupled-pair-continuation-v1 reports/coupled-pair-continuation-geometry-v1 reports/paired-approach-witnesses-v1 reports/coupled-pair-local-reserve-v1 reports/<new-comparison>
.venv\Scripts\python.exe scripts/run_godot_rig_import.py --study reports/<new-comparison> --output reports/<new-engine>
.venv\Scripts\python.exe scripts/audit_coupled_pair_geometry.py reports/<new-comparison> reports/paired-approach-witnesses-v1 reports/<new-engine> reports/<new-geometry>
.venv\Scripts\python.exe scripts/verify_coupled_refreshed_pair.py reports/<new-comparison> reports/paired-approach-witnesses-v1 reports/<new-geometry> reports/<new-review>
```

Use fresh output directories. Local evidence uses the `coupled-pair-refreshed-v1`, `coupled-pair-refreshed-engine-v1`, `coupled-pair-refreshed-geometry-v1` and `coupled-pair-refreshed-review-v1` folders under ignored `reports/`. Reproduction needs the separately acquired licensed fixture, pinned solver and preceding evidence. The full source and method snapshots, original and failed candidates remain local; weights and character payloads are excluded from GitHub.

This is one development high-five pair, with vertex-sampled geometry at declared quarter-frame times. It is not continuous triangle or self-collision certification, a learned animation model, a human/animator rating, or broad action qualification. Held-out prompts remain unused; all fourteen release capabilities remain unapproved.
