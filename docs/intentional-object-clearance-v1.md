# Intended object contacts and interpolation clearance

Two experimental correction modes retain the authored contact tolerance while separating intended object contact from extra clearance. V14 removes the extra 2 mm buffer for the complete declared hand/foot skin region, only against its named object on contact and immediate release keys. Physical penetration remains constrained. Other objects, regions and keys retain their original buffer. Region membership uses dominant skin joints; it is not anatomical calibration.

The policy validates the physical surface target, full region membership, actor/contact identity, geometry, clock and exact compiled target track before fitting. Contact regions join the object sample population without changing the existing floor sample population. Boxes, spheres and cylinders have numerical policy tests; the actual experiment below uses one box.

## Measured interpolation failure

The retained one-second reference uses the unchanged generated takes for seeds 7103 and 7104, a 1 mm hand-point tolerance and contact keys 10–12 at 30 fps. This is the constructive engineering fixture described in [the preceding experiment](scene-authored-contact-tolerances-v1.md), not a realistic lift or grasp. No checkpoint training or new sampling occurs in this correction study.

| Mode | Seed 7103 maximum contact error | Seed 7104 maximum contact error |
| --- | ---: | ---: |
| V13, authored tolerance and uniform clearance | 1.987 mm | 1.976 mm |
| V14, explicit intended-contact buffer | 0.996 mm | 0.933 mm |

V14 passes the requested point tolerance at all three native keys. Native all-skin box penetration is 0.000455 mm for the first take and zero for the second; floor penetration is zero. These observations do not establish collision-free playback.

Actual headless Godot playback at 120 Hz retains all 77 bones and separately skins all 18,056 original vertices with eight influences. The first V14 take penetrates the moving box by **1.285 mm at 0.05 seconds**, between source keys 1 and 2, before the contact interval. The witness is vertex 1312, the contact anchor dominated by `LeftHandMiddle4`. Its extra buffer was active at that time. The contact-buffer exception does not explain or excuse this failure. Both V14 point tracks still pass the 1 mm requirement on the complete nine-sample contact interval; V13 fails all nine samples in both takes. The V14 failure remains immutable.

## Playback-aware correction

V15 adds object inequality samples at every quarter of every adjacent key interval: 30 native keys plus 87 intermediate samples for this clip, for each declared object and selected vertex. It interpolates shortest local-quaternion arcs and native offsets/root translations, then performs hierarchical forward kinematics and skinning. It never interpolates global joint positions directly. Object poses and buffer tracks interpolate on the same clock. Thus the buffer transitions linearly between its declared key values; it never becomes negative. A 10 micrometre numerical buffer strengthens the object condition, including intended-contact regions.

Matrix-to-quaternion conversion uses the largest well-conditioned component with finite derivatives in unused branches. A test initially exposed NaN gradients at zero square roots; the corrected implementation leaves the selected proper-rotation branch unchanged and passes both float32 and float64 interpolation/gradient checks against SciPy, including identical keys and a shortest-arc crossing.

Both V15 studies complete using the same raw inputs, six outer stages and original root/rotation bounds. Native maximum point errors are **1.000019 mm** and **0.949055 mm**. The first take retains `authored_contact_target_missed`: one of its three requested keys exceeds 1 mm. No tolerance was relaxed. Native box and floor penetration measure zero in both takes. Corrections take 361 and 291 seconds on this machine; these are local timings, not portability or throughput claims.

Actual headless Godot at **240 Hz** compares both V14 and both V15 exports across **932 actor samples**, all 77 bones and all 18,056 vertices/eight influences. The grid includes eighth-key times omitted by the quarter-key fitter. V14's first take reaches 1.536 mm box penetration on this denser grid. Both V15 takes have **zero measured box and floor penetration** on every saved sample. Their complete 17-sample contact intervals reach 1.000020 mm and 0.949063 mm: the first still fails one sample, while the second passes every sample. This is a finite-grid observation, not continuous-time nonpenetration or interaction approval.

All four new GLBs validate with zero errors and warnings. The dense audit verifies imported poses against a separate SciPy/GLB reader before measuring geometry; all input hashes are rechecked afterward. It shares original skin assets and uses CPU skinning of actual engine bone transforms, not GPU-rendered skin, independent physics or a human review. Local evidence includes `reports/scene-reference-correction-v3`/`v4`, `reports/intentional-object-clearance-playback-v1`/`v2` and `reports/intentional-object-clearance-witness-v1`.

All **118 focused Python tests** pass, including native contact compilation/evaluation and solver controls. A separate environment without Torch passes **26 overlapping model-free tests** for policy metadata and release guards. The first interpolation suite retained two NaN-gradient failures; one later command named nonexistent test modules and collected no tests. Neither is counted as validation. Hosted source coverage now declares 393 Python modules in four shards (99/98/98/98) and 37 Node scripts per operating system; validation of this publication is pending.

Next work must preserve the strict contact result while providing numerical headroom for solver/export rounding, then test genuine object actions and partner interactions across additional geometry, timings and rigs. Repeating this fixture alone cannot establish general-purpose motion quality.

## Scope and reproduction

This is a deterministic in-sample correction experiment on two takes, one reference, one native rig and one moving primitive. The full hand region contains 2,847 vertices, giving 3,234 object samples while preserving the original 601 floor samples. Quarter-key sampling is not continuous collision detection. Export quantization, untouched mesh vertices, self collision, forces, balance, attachment, partner dynamics, semantic correctness, retargeting and human quality need separate checks. Passing this fixture cannot approve an action family or release capability.

Use separately acquired pinned vendor assets and the original saved guided collection. Choose fresh output directories so prior results remain immutable:

```powershell
.venv\Scripts\python.exe scripts/run_scene_fit.py <guided-scene-1.json> <guided-scene-2.json> --output reports/<new-correction> --solver-version 15 --preview-base reports/<original-guided-collection>
node scripts/validate_scene_exports.mjs reports/<new-correction>
.venv\Scripts\python.exe scripts/run_godot_scene_import.py reports/<new-correction> reports/<new-engine-audit>
```

The last command checks native keys; a dense playback audit must also supply a complete denser `sample_times_s` clock to `godot_import_audit.gd` and remeasure skin/object geometry. All raw clips, method snapshots, masks, failures and engine witnesses stay in ignored local reports. This repository remains a source snapshot requiring separate dependencies/model/assets. All fourteen release evidence lists remain empty; the whole-project goal stays active.
