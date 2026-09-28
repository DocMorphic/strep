# Finger-shape and placement search

Three bounded finger-shape searches pass the earlier necessary rigid-clearance screen, but none yields a passing actual hand placement. Subsequent joint shape/placement searches also fail, with 0.356–0.358 mm overlap remaining. These results distinguish a favorable geometric upper bound from an actual usable grasp.

The unchanged V13 frame-60 fixture and `grasp-pose-restoration-v2` seed remain the reference. All 19 left-finger rotation-norm budgets stay at their original values: 8 degrees at the thumb base, 5 degrees at other bases and 12 degrees at distal controls. Body, root and right-finger parameters remain fixed during shape search. No model training, new checkpoint, held-out trial, anatomical approval or full animation is involved.

## Necessary-bound search

`grasp_shape_bound.py` implements the inward-radial specialization of the general [rigid patch bound](grasp-twist-seeds-v1.md). For an offset with axial component `a` along the measured palm normal and tangential magnitude `b`, the best radial component is `-a*cos(epsilon)+b*sin(epsilon)`, unless the vector can align directly outward inside the normal cone, in which case it is its full length. This avoids the inverse-cosine derivative near the cone endpoints. Tests compare it with the independent general NumPy formula, including zero offsets and 0/90/180-degree cones.

`study_grasp_shapes.py` predeclares starts at the current left-finger edits, half those edits and zero edits relative to the original reference. Each search maximizes a conservative smooth minimum of the per-vertex clearance upper bounds. The temperature is 0.05 mm; every bounded finger shape is checked against all 2,735 hand-patch vertices. This is an optimistic necessary-condition search: different vertices may require incompatible placements to attain their individual bounds.

| Start | Minimum rigid clearance upper bound | Evaluations | Recorded time |
| --- | --- | --- | --- |
| Current | 2.825164 mm | 165 | 3.735 s |
| Half | 2.820673 mm | 148 | 3.469 s |
| Reference | 2.825130 mm | 208 | 4.953 s |

All three cross the 1.999 mm numerical acceptance threshold for this **necessary bound**. None is thereby a pose witness. Their actual unprojected skeleton poses are retained separately and are not inserted into an animation. Independent bounds reconstructed from SciPy/NumPy skin agree within 0.051 micrometres. End-to-end directional objective errors are below 6e-9.

The first invocation, `reports/grasp-shape-seeds-v1`, failed before optimization because in-place normal normalization invalidated Torch's gradient graph. The failure and original source snapshot remain. The corrected invocation is `reports/grasp-shape-seeds-v2`; completed trials were not rerun to erase that failure.

## Actual rigid placement

`study_grasp_placements.py` jointly measures all patch vertices at one placement. Point displacement is bounded by 4.999 mm and normal tilt by 9.999 degrees, leaving a small margin inside the original 5 mm/10-degree limits. Radial sphere symmetry allows axial twist to be removed from this isolated rigid-patch problem. Each shape starts once at centered contact and once near its measured placement, clamped to 90% of the allowed displacement and tilt.

All six local solves fail actual patch clearance. Best minimum signed clearances range from -1.463 to -1.456 mm: the hand still intersects the sphere. Total recorded trial time is 0.859 s. This directly demonstrates why upper-bound passing cannot be substituted for actual geometry validation.

## Joint shape and placement

`study_joint_grasp_patch.py` optimizes finger shape and actual rigid placement together. It differentiates through the measured skin normal, aligns it with the authored normal and applies the bounded tilt/translation. All original finger budgets remain. Three declared starts use the original finger shape with centered placement, the searched shape with its best placement, and reference fingers with centered placement.

| Start | Minimum actual patch clearance | Evaluations | Recorded time |
| --- | --- | --- | --- |
| Original shape, centered | -0.356216 mm | 306 | 6.812 s |
| Searched shape, placed | -0.357816 mm | 318 | 7.047 s |
| Reference shape, centered | -0.357561 mm | 261 | 5.797 s |

The first two hit the 250-iteration limit; the third reports relative objective convergence. None meets the 2 mm outward-clearance requirement. All final placements use almost the full point and normal allowance, while remaining inside their declared limits. Independent patch distances agree within 0.051 micrometres.

The stored `unprojected-shape.npz` files contain finger changes on the unchanged body. The desired rigid hand placement is stored as a separate point/normal/tangent target; it has not been applied to the skeleton. Since the patch itself fails, no arm projection, engine export or clip integration is claimed. These local failures do not prove the full articulated problem infeasible.

## Verification and contact calibration

`audit_grasp_shape_search.py` independently reconstructs all three shapes, six placements and three joint results. It verifies source and input bindings, original finger/point/normal limits, exact frozen parameters and exact saved pose arrays. It recalculates the general rigid bound and actual sphere distances rather than accepting optimizer status or a necessary-bound flag. Ten focused tests pass, including bound equivalence, gradients through the measured normal and independent rotation alignment.

The selected contact remains an unreviewed geometric candidate. Existing [hand-posture evidence](hand-posture-v1.md) already records its 36.105-degree bind-normal difference from a geometric palm-plane hint. An earlier normal-aligned candidate, vertex 7159 at 4.844 degrees, also failed a partner-contact experiment. That is historical evidence, not a new finding or proof that switching points will solve this sphere fixture.

A local review figure at `reports/grasp-contact-calibration-review-v1/contact-patch.png` shows both candidates on the bind mesh. It was inspected for legibility; neither point receives anatomical approval. The figure and asset-derived output remain excluded from Git.

Before further solver variants or larger correction envelopes, evaluate contact calibration explicitly. A sphere comparison using the existing alternate surface binding would be a **new authored calibration condition**, not a success on the unchanged original condition. Preserve the original failure, keep world targets and edit budgets documented, and require full geometry and human review before adopting any binding. The earlier partner failure must remain visible.

## Reproduction

```powershell
.venv\Scripts\python.exe scripts/study_grasp_shapes.py reports/sphere-floor-fit-v13 reports/grasp-pose-restoration-v2 reports/new-shapes
.venv\Scripts\python.exe scripts/study_grasp_placements.py reports/new-shapes reports/new-placements
.venv\Scripts\python.exe scripts/study_joint_grasp_patch.py reports/new-shapes reports/new-placements reports/grasp-pose-restoration-v2 reports/new-joint-patch
.venv\Scripts\python.exe scripts/audit_grasp_shape_search.py reports/new-shapes reports/new-placements reports/new-joint-patch reports/grasp-pose-restoration-v2 reports/new-search-audit
```

The earlier local study artifacts and separately licensed asset are required. Existing evidence is under `reports/grasp-shape-seeds-v2`, `reports/grasp-shape-placements-v1`, `reports/grasp-joint-patch-v1` and `reports/grasp-shape-search-v1-audit`. All processes are terminal. No Studio default or release gate is promoted; all 14 capabilities and the broad action/rig/object/partner evaluation remain open.
