# Native rig-to-rig animation transfer

Strep can now transfer an existing rigged GLB animation to another rigged humanoid GLB using explicit checksum-bound profiles. The path needs NumPy/SciPy and the existing CPU dependencies, without Torch, Kimodo or a checkpoint. This extends the SOMA77 transfer path; no action whitelist is involved.

The output is a separate candidate with a new appended editable animation. Original source/target files, the target's prior clips, mesh/material/skin payload and default transforms remain intact. The report retains input and implementation hashes, copied inputs, reference calibration, exact timing, decoded transforms and measured fidelity. A fresh output directory is required; failed candidates and their measurements remain available.

## Usage

Use the existing `strep-rig-profile-v1` format with `reference_pose: default_nodes` and explicit humanoid role mappings. Both profiles must bind their own GLB checksum. The source profile has zero world offset and no axis overrides; target placement/axis overrides are explicit author choices. Every requested target role must exist in the source profile, including optional roles that the author chooses to map.

```powershell
python scripts/native_rig_transfer.py --source source.glb --source-profile source-profile.json --target target.glb --target-profile target-profile.json --animation-index 0 --rate 120 --output reports/my-transfer
python scripts/audit_native_rig_transfer.py reports/my-transfer reports/my-transfer-engine
```

The optional second command uses the project's separately provisioned, checksum-pinned Godot executable. It saves and reloads a native Animation resource, checks all imported bones and raw CPU skin, and exercises embedded/extracted root playback and silent preview under rotated placement. It checks source-bound candidate hashes and method versions before running. The generated resource is `animation.res` in the audit folder; this does not bundle an offline installer or select the candidate in Studio.

## Reference and timing policy

The [Khronos glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) defines local joint TRS, parent-composed world transforms, quaternion rotation channels and Float32 animation storage. The transfer rule below is our deterministic policy, not a property guaranteed by the file format.

For each role, source motion is rebased as `R_source_world(t) @ R_source_reference_world.T`. The resulting world rotation delta multiplies the target calibration. This accounts for nonidentity source rest-joint axes. Calibration aligns target reference bone directions to source reference directions, with explicitly supplied target axis overrides taking precedence. It may change the target's default pose; joint positions alone do not determine anatomical twist.

Root position is `target_default_pelvis + leg_scale * (source_pelvis(t) - source_default_pelvis) + target_profile_offset`. Scale is the mean of left/right leg-length ratios. Trajectory axes remain in world space; reference rotation alignment does not silently rotate displacement. Local translations below the target pelvis and unmapped target local transforms retain the target reference. Helper twist is not distributed automatically.

The candidate clock combines every original source key, zero, exact source duration, and dense ticks at 60, 120 or 240 Hz. Ticks are converted to Float32 before evaluation/export; original Float32 keys are not snapped or merged by tolerance. The last key equals the source duration, with no extra end frame. Maximum supported duration is 30 seconds, node count is 512 per rig, and stored key population is capped at 8,192.

Readback checks every node at every stored key plus quarter, midpoint and three-quarter samples of each interval against newly evaluated source transfer. Fixed limits are `1e-5` for key matrix components, `1e-4 m` for sampled position error and `1e-4 rad` for sampled rotation error. Failed fidelity does not gain approval by raising these limits. These finite probes are not continuous-time bounds.

## Supported limits

- Explicit humanoid mapping, rigid unit-scale nodes, one skin, embedded GLB data, and LINEAR source channels.
- Animated source ancestors of the pelvis contribute their world motion. Other source local translations must remain at reference; stretch is rejected.
- Animated source helper rotations that influence mapped roles are included through source world rotations. Animated accessories/unmapped leaf bones are rejected; optional source roles absent from the target are reported as unused.
- STEP/cubic channels, animated scale beyond the numerical unit tolerance, morphs, compression and multiple skins are rejected. Existing rig-import restrictions remain in effect.
- Contacts and gameplay events are not inferred. Root tracks describe authored pelvis movement before extraction. Foot/hand sliding, anatomy, collisions, object/partner contacts and motion quality require separate validation/correction.

## Development evidence

The model-free tests use self-generated humanoid hierarchies and trivial weighted test triangles. They cover source rest-rotation rebasing, root anchoring/placement, different role populations, helper bones, reversed node ordering, non-grid clocks, preserved target clips/materials, matrix-to-TRS conversion, explicit axis overrides, invalid/lossy contracts, rehashed corruption, source mutation, and retained interpolation failures. Engine failures in these unit tests are doubles; actual engine evidence is recorded separately.

The final frozen source check passes **126 Python tests, zero skips**, including 42 new transfer/binding contracts. It runs from a copied source/test snapshot with the CPU-only environment; every copied/current source hash matches afterward. Only the two new source suites were added to parsed CI; dependencies, action pins, permissions, matrices and budgets are unchanged. Frozen result SHA256: `1f4123947079308ac4e148f174188e47b118dd259bab55919571c54fedea0bf5`. Workflow proof SHA256: `f0977beedb9f2a7b6085d29a86225cec82e065eee77e4570ee82f3aa2a9248bc`.

Two actual serial headless Godot studies exercise separately generated rigs:

| Case | Source/target skin joints | Clock samples | Maximum imported pose component error | Embedded/extracted CPU skin difference |
| --- | --- | --- | --- | --- |
| Independent rest axes, target elbow helpers, reversed target node order | 19 / 17 | 969 | 1.142e-6 | 1.096e-6 m |
| Animated source helper, asymmetric target reference, explicit hand-axis override | 21 / 15 | 1,933 | 1.254e-6 | 1.623e-6 m |

Both preserve the prior target clip and every mesh/material/bind payload byte, reload a saved resource, retain non-grid source duration/keys, and pass the existing runtime pose/skin limits of `1e-4`. Preview, exact complete clocks, all bones, root deltas, rotated placement, malformed bindings and invalid time rejection are checked. All four owned engine processes have zero exits and clean logs; complete Float64 observations round-trip exactly. Transfer readback probes stay below `1.5e-7 m` position and `1.6e-7 rad` rotation error in these cases. Method manifests match the frozen/current implementation.

The accelerated 60 Hz undersampling trial fails at **0.4338 mm** sampled position error versus **0.1 mm** allowed, and **0.002069 rad** sampled rotation error versus **0.0001 rad** allowed. Its original inputs, derived candidate, transforms and failed report remain saved; no limits were loosened. This demonstrates why key-only agreement is insufficient.

Complete generated evidence stays locally under ignored `reports/native-rig-transfer-final-v1`; final study receipt SHA256: `97663d626268450176c2d2169f490d92c8cc9b993521c7eca76cc37cca58a8d7`. Initial collection exposed a Torch import dependency; the pure numeric transfer helper now imports without it. Earlier generated development studies remain retained. The pure direction-alignment function has the same numeric AST body as the legacy correction helper, whose file remains untouched; model imports are deferred to the original SOMA export entry point.

These fixtures are software evidence, not independent production-character coverage, realistic motion, successful contact retargeting or animator approval. No live Studio/server/browser, rendered/GPU checks, production skin/anatomical queries, new model sampling/training or human ratings/cleanup were performed. Every project release gate remains open. Next work is exposing this source-bound path in the authoring workflow, then testing contact retention and separately licensed production rigs with developer/animator review.
