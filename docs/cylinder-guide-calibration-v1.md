# Cylinder guide calibration and bounded pose

One native pose passes both regional hand contacts, full-skin cylinder clearance, floor clearance and original source-relative edit bounds under **explicit alternative guide vertices**. The unchanged original guide condition still fails. No clip or release capability is approved.

## Separate authored condition

The [isolated hand-placement study](cylinder-hand-placement-v1.md) retained original-guide failures despite relaxing arm reach. This follow-up enumerates alternatives inside exactly the same authored palm regions. It changes only guide identity; patch faces, area-weighted normal definitions, object targets, numeric contact gates and original finger budgets remain fixed. It does not overwrite a scene or default binding.

`probe_regional_guide_points.py` uses two declared frozen shapes per hand: the whole-body iterative control's shape and the best-clearance shape from the previous four-start local search. Every region vertex is tested at 72 orientations (eight axial twists, each with centered normal and eight 9.5-degree tilt directions) and three outward guide offsets: 2.1, 2.9 and 4.9 mm. The full 2,735-vertex pure-hand skin is checked before regional contact. Arm reach, body/floor/self/partner collision and temporal constraints remain relaxed during this stage.

| Hand / shape | Placements | Full-hand clearance passes | Complete alternative contact passes | Original-guide passes |
| --- | ---: | ---: | ---: | ---: |
| Left / original | 41,256 | 194 | 22 | 0 |
| Left / searched | 41,256 | 534 | 31 | 0 |
| Right / original | 40,824 | 198 | 10 | 0 |
| Right / searched | 40,824 | 404 | 12 | 0 |

The completed grid has **164,160 placements, 1,330 clearance passes and 75 complete alternative contact passes**. It took 78.609 seconds with peak observed process RSS 645,468,160 bytes. Independent replay verifies every row with a separately written analytic cylinder-distance calculation; maximum distance discrepancy is 1.666e-16 m. Original guides failing this finite grid is not an infeasibility certificate.

Passing alternatives are ranked first by the smallest rigid orientation change from their unprojected shape, then contact centroid error, descending triangle area, guide ID and stable enumeration index. The frozen rank-zero candidates are left vertex **7148** from the original shape and right vertex **11538** from the searched shape. Their original guides were **14712** and **16974**. Guide changes still require anatomical/developer review; a numerical contact pass cannot supply that review.

## Arm projection and combined pose

`project_regional_guides.py` turns each rigid hand placement into a target wrist position and orientation. It fits only the corresponding shoulder, upper arm, forearm and wrist using the original source-relative rotation-norm mapping. Each hand's selected finger shape remains frozen during projection. Other parameters remain fixed. The two disjoint arm/finger blocks are combined, and the full **18,056-vertex** skin is reconstructed and audited under both original and alternative guides.

Both projections reach their targets with position errors below 0.032 micrometres and orientation errors below 1.4e-6 degrees. Each stops at the 160-evaluation limit (solver `success=false`), taking 6.875 / 6.828 seconds. Acceptance comes from the independently reconstructed geometry and bounds, not convergence status.

| Combined-pose measurement | Result | Original numeric gate |
| --- | ---: | ---: |
| Minimum full-skin cylinder clearance | 2.035614 mm | ≥ 2 mm, existing 1 micrometre allowance |
| Minimum full-skin floor height | 2.588736 mm | ≥ 2 mm, existing 1 micrometre allowance |
| Alternative left / right guide error | 2.900017 / 2.099981 mm | ≤ 5 mm |
| Left / right patch clearance | 2.342087 / 2.053352 mm | ≥ 2 mm, existing allowance |
| Left / right region normal error | 9.499987 / 9.500008° | ≤ 10° |
| Left / right triangle centroid error | 3.741627 / 2.868636 mm | ≤ 5 mm |
| Left / right triangle area | 79.005190 / 33.736614 mm² | ≥ 25 mm² |
| Left / right triangle spacing | 13.049453 / 8.198725 mm | ≥ 6 mm |
| Maximum rotation edit | 23.647860° | Every original per-joint norm passes |

The original guides miss by **30.453204 / 26.074695 mm** and still fail their 5 mm requirement. This distinction is retained in the combined result. Root lift remains 0.587197 mm and all parameters outside the disjoint arm/finger blocks remain unchanged. The minimum cylinder-clearance margin is only about **36 micrometres**; this pose must not be assumed safe between frames or after retargeting.

## Verification, scope and next work

Independent projection replay reconstructs source-relative parameters, exact serialized pose arrays, target wrist transforms, disjoint-block composition, original and alternative contact audits, and the full-skin cylinder minimum. All input/method/output hashes replay. Directional derivative errors are below 7.3e-8 in scaled residual units. **34 focused tests pass**, covering batched versus individual clearance, explicit cylinder orientation sampling, rigid wrist transforms, placement derivatives and prior bounded solver checks. Public model-free CI is separate from these Torch/asset-dependent tests.

This is sampled skin-vertex geometry at frame 96. It does not establish anatomy, triangle-interior or continuous collision safety, self-collision, balance, force, clip smoothness, engine compatibility or animator quality. No checkpoint, Studio default, original source scene, reserved evaluation case or release approval changes.

Next, freeze guide vertices 7148 / 11538 for the entire grasp interval and evaluate a bounded moving trajectory against the same patch definitions. Measure native and intermediate times, approach, attachment and release. Retain failed frames and original-condition comparisons. Do not choose a new guide independently at every frame or treat this development pose as coverage of other objects, actions, rigs or partners.

Local evidence: `reports/cylinder-guide-points-v1`, `reports/cylinder-guide-points-review-v1/verification.json`, `reports/cylinder-guide-projection-v1`, and `reports/cylinder-guide-projection-review-v1/verification.json`. With separately acquired assets and retained source studies, use fresh output directories:

```powershell
.venv\Scripts\python.exe scripts/probe_regional_guide_points.py reports/cylinder-hand-placement-v1 reports/<new-guide-probe>
.venv\Scripts\python.exe scripts/project_regional_guides.py reports/<new-guide-probe> reports/<new-guide-projection>
```

All fourteen project release capabilities remain unapproved.
