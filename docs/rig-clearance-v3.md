# Geometry-aware clearance transfer, 2026-09-26

An experimental correction now reduces foot penetration caused by transferring a generated motion to a differently shaped character. It preserves every frame outside the prompt-edit envelope, limits root/joint changes, and penalizes changes to horizontal foot-surface motion. It is not promoted to the default: failed raw guides, existing frozen-frame defects, sliding and sharp motion still prevent release acceptance.

## Diagnosis and method

`reports/rig-clearance-v1/diagnosis.json` locates the worst point in jump seed 205 at a vertex fully weighted to Cesium's right toe. Native SOMA mesh penetration was 0.95 mm, versus 70.71 mm on the target rig. Scaling pelvis motion by leg length and transferring rotations does not preserve clearance for a different foot shape. The matched native and target joint/vertex positions are retained; no input/model data was changed.

New `scripts/rig_clearance_fit.py` accepts an existing finite prompt-edit job and an unused output folder. The experiment derives each foot region from vertices with at least 65% influence from mapped foot/toe joints. Native clearance uses all eight SOMA skin weights. Target foot minimum height follows native minimum height scaled by leg length plus the profile's vertical offset, clamped to zero inside full-weight replacement frames. Boundary blends mix with the original supplied clip's height. This is a surface-height correspondence, not a contact or flight classifier. It neither pins a foot to a world location nor asserts support.

The fitter adjusts world pelvis translation and mapped leg, shin, foot and toe local rotations. Existing correction limits apply, multiplied by the regeneration envelope; envelope-zero samples remain exact. Adjacent corrections have hard 15 mm root and 5° rotation-vector norm bounds, verified again as decoded geodesic edits. Alternating forward/backward frame updates use bounded least squares and SLSQP when neighbor bounds become active. A feasible segment safeguard and non-increasing local objective check retain a feasible candidate. Up to six sweeps; at most 80 evaluations/iterations per local subproblem. Reaching a small update is not a stationary-point or global-optimum proof.

V1 finite-difference fitting was deliberately stopped after verifying live PID 9896 because it was too slow for interactive work; no quality result exists. V2 added analytic rotation/skin derivatives and optimized height only. It cleared the editable floor but worsened sliding. V3 additionally penalizes all selected foot vertices' horizontal displacement from the pre-correction target motion, normalized by region size. This preserves existing horizontal trajectories rather than claiming to solve their original sliding. Weights are explicit in the frozen implementation: height 12, horizontal surface 30, floor 4, with existing pose/root/temporal priors. Defaults in the production Studio transfer path remain unchanged.

The analytical skin Jacobian includes descendant influence weights and the SO(3) right Jacobian. Tests compare it against independent `RigAsset` finite differences in all three axes and check the full objective derivatives, fixed samples and neighbor bounds. Seven focused tests passed in 3.78 seconds. No production-path edit or full-suite rerun is claimed this turn.

## Matched saved failures

No new inference or training. Two descriptions, two existing rig families; these are retained development failures, not held-out evaluation. All raw model guide screens still fail unchanged.

| Case | Editable floor, before → V3 | Editable half-frame floor | Whole-clip floor after | Preserved samples |
|---|---:|---:|---:|---:|
| Cesium jump, seed 205 | 70.71 → 1.52 mm | 2.48 mm | 24.06 mm | 14 |
| Cesium jump, seed 204 | 62.57 → 0.24 mm | 1.20 mm | 24.06 mm | 14 |
| Quaternius dance, seed 203 | 14.38 → 2.35 mm | 2.36 mm | 3.00 mm | 24 |

Both jumps have 13 frozen samples failing the 5 mm screen. Keeping those frames unchanged proves whole-clip floor compliance impossible under this edit envelope. All remain preserved to less than 4e-9 maximum world-matrix error. A clean full clip requires an explicit broader edit or another source; no implicit root lift is applied outside the selected range.

On seed 205, right-foot predicted-support centroid speed p95 went from 0.118 m/s to 0.563 m/s in V2, then 0.118 m/s in V3. The corresponding V3 left values are 0.104 → 0.104 m/s, but there is only one left support step and 15 right steps. Seed 204 has one left and nine right steps. Dance has 94/87 steps, with approximately 0.213/0.199 m/s unchanged. These model predictions are not confirmed contacts. Preserving a centroid statistic is insufficient: the verifier also reports every foot vertex's horizontal displacement and velocity change. Maximum V3 horizontal edits are 4.88/6.05/0.95 mm for the three cases, and peak vertex velocity changes can still reach 0.127/0.139/0.016 m/s.

Maximum root rises are 73.84/61.87/10.76 mm. Adjacent local-joint rotation peaks worsen from 23.68° to 25.85° and 24.52° to 28.46° for the jumps; dance stays 28.66°. Five and two jump subproblems reported unsuccessful solver termination, and both hit the six-sweep cap. Dance stopped at five sweeps with zero final update; that is not an optimality certificate. These are concrete remaining limitations, not approved realistic animations.

## Files, validation and review

- `reports/rig-clearance-v2`: height-only controls retained, including their sliding regressions.
- `reports/rig-clearance-v3`: three input/candidate pairs, solver logs, implementation snapshots, independent all-vertex/half-frame audits, comparative data and packages.
- `scripts/verify_rig_clearance.py`: independently decoded GLBs, fixed-frame preservation, envelope-scaled edit and adjacent geodesic bounds, unchanged bone translations/uneditable local transforms, root track, contact/timeline bytes, floor, foot-surface changes and predicted-support speed.
- `reports/godot-rig-clearance-v3`: actual Godot 4.7.2 import of eight GLBs (six V3 input/candidate files plus two V2 controls), 606 joint-pose samples, maximum position error below 4.6e-7 m. All surfaces retained. This does not verify GPU skin, physics or naturalness.
- glTF validation: zero errors across eight files; inherited one-warning Cesium and six-warning Quaternius assets. Three candidate packages have every entry byte-checked, retain the full original authoring package with licenses, and match their served HTTP hashes. All eight served GLBs also match hashes.
- [Local synchronized viewer](http://127.0.0.1:8767/reports/rig-clearance-v3/viewer.html): before, height-only regression where available, and V3 correction at a shared frame. Original grey geometry remains visible when switching stages and at the dance terminal frame. Candidate packages and audits are linked. This is an experimental review artifact, not a new default Studio operation.

## Next work

Establish feasible model boundary conditioning and transition timing; inspect common root/heading errors before attributing all guide failures to model ability. Reduce remaining sharp joint motion while maintaining surface trajectories and edit bounds. Extend clearance/correspondence tests to additional actions and rigs before production integration. Independent support intent, action completion, partner/object contacts, style diversity, offline installation, held-out reviews and animator cleanup time remain essential release gates under the same project-wide goal.
