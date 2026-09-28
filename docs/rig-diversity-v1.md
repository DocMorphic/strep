# Rig diversity and neutral height calibration

2026-09-26. Development evidence only; the full-project goal remains active. The 42 retained outputs are not production-approved animations.

## Assets and provenance

The transfer matrix uses CesiumMan (19 skin bones) plus Quaternius Superhero Female and Male (65 skin bones and three skinned surfaces each). These are **three assets across two rig families**, not three independently authored skeleton designs. The Quaternius bodies have different proportions, but share naming and hierarchy conventions. Their source is the free Standard edition of [Universal Base Characters](https://quaternius.com/packs/universalbasecharacters.html), downloaded through its [official itch.io page](https://quaternius.itch.io/universal-base-characters). The archive's included license specifies CC0 1.0. No paid edition was acquired.

The original 128,968,391-byte archive, selected original glTF/buffer/textures, license and provenance remain in `assets/characters/quaternius-base`. The upstream glTF files reference missing `T_Eye_Normal_png.png` and, for the male model, `T_Hair_1_Normal_png.png`. Packing explicitly substitutes the corresponding existing `T_Eye_Normal.png` and `T_Hair_1_Normal.png`; the substitutions and every resource hash are recorded in each `.packing.json`. Original files remain unchanged.

`pack_local_gltf.py` embeds buffers/images while verifying every original bufferView byte and preserving node, skin, mesh, accessor, material, texture, scene and animation definitions. It rejects external-network/path-traversing resources and existing output files. This is container conversion, not mesh simplification or re-rigging. The project catalog matches exact asset hashes, loads a saved mapping and retains license/provenance/packing records in Studio job snapshots. Uploaded filenames alone cannot confer provenance.

Two other assets were inspected and retained:

- [RiggedFigure](https://github.com/KhronosGroup/glTF-Sample-Assets/tree/c6a6bd13ab2b3c685c7903d03561b8a9392f38b8/Models/RiggedFigure) imports, but shares Cesium's rig family and is not counted as independent validation. Its license is CC BY 4.0 in the pinned upstream README.
- [RobotExpressive](https://github.com/mrdoob/three.js/tree/1af6de5bd8cd481993483dc6127eba668e818dfd/examples/models/gltf/RobotExpressive) is CC0 per its pinned README. It is unsupported: two 43-joint skins, three facial morphs, non-unit scales and a different leg hierarchy. The original also has 752 `ACCESSOR_WEIGHTS_NON_NORMALIZED` validation errors. No stripped/normalized substitute is counted as success. See its `compatibility-audit.json`.

## Frozen baseline

`reports/rig-diversity-transfer-v1/request.json` freezes the asset/profile/source-motion hashes before the batch. Seven existing raw Kimodo seed-77 motions are transferred to all three assets: jump/land, crawl, dance/turn, wave, kick/recover, get-up, and run/roll/stand. There is no new generation or training, and no per-motion profile fitting. All 21 jobs ran through the real Studio API and retained source snapshots, target transforms, GLBs, root/contact sidecars and packages. Every job completed export/round-trip verification; that is not a contact or semantic pass.

Quaternius mapping suggestions now understand `pelvis`, `spine_02`, `spine_03`, `neck_01`, and `ball_l/r` names while leaving ambiguous matches unmapped. Neutral calibration v1 and v2 are retained under `reports/rig-diversity-v1`; v2 explicitly keeps reference foot/toe orientation, as previously done for Cesium. The female file was imported through the actual browser file chooser, mapped, saved and previewed.

The baseline exposed hovering: Quaternius standing motions can have zero penetration while the weighted foot region is 8–10 cm above the floor. The female mesh also fails the strict flat-reference-sole heuristic, so exact sole patches are unavailable until authored explicitly. Missing patch measurements stay unavailable, rather than being reported as zero.

## Neutral-only calibration experiment

`calibrate_rig_height.py` computes a constant Y offset from source and transferred target neutral **skin geometry** with the source root at zero:

`deltaY = source neutral mesh minY * leg-length scale - target neutral mesh minY`

It adds that offset to the explicitly authored placement and changes no bone mapping, orientation, timing or per-frame control. The calibrated profiles record the source SOMA skin hash, input/profile hashes, measured heights and formula. No motion frames are used to fit the offset. These profiles are experimental and are not promoted into the default catalog or user's active mapping.

The offsets are +5.034 cm for Cesium, −9.409 cm for Quaternius female, and −9.109 cm for Quaternius male. `reports/rig-diversity-height-v1` reuses the same 21 inputs with these profiles through the supervised Studio worker. This diagnostic reuse is not a new held-out study. Source/input bytes remain preserved, and all candidates are visible in Characters.

| Character/action | Floor depth before → after | Foot-region hover before → after |
| --- | --- | --- |
| Cesium wave | 5.94 → 0.90 cm | 0.00 → 0.00 cm |
| Quaternius female wave | 0.00 → 1.02 cm | 8.87 → 0.00 cm |
| Quaternius male wave | 0.00 → 0.85 cm | 8.61 → 0.00 cm |
| Quaternius female get-up | 19.89 → 29.30 cm | 9.98 → 0.57 cm |
| Quaternius male get-up | 27.57 → 36.68 cm | 8.93 → 0.00 cm |

The experiment removes standing hover but worsens other poses. Neither profile choice solves support/contact transfer generally. Constant root calibration is not promoted as the default correction, and all failures remain visible.

## Independent measurements and verification

`audit_rig_ground.py` reloads each actual GLB and skins every frame. It records whole-mesh floor depth/worst vertex, explicit sole-patch heights/sliding when draftable, and a coarse per-foot lower-envelope height. That envelope uses vertices with at least 65% combined foot/toe weight during unchanged source-predicted foot or toe support. It is not a calibrated heel/toe contact patch, an independent contact annotation, a force/balance check or semantic review.

Studio now displays the inspection for the exact export hash and provides **Worst floor** / **Worst foot hover** jumps plus a JSON download. Future transfer jobs automatically include these audits in their packages; the 42 study jobs were audited post hoc, so their immutable original packages remain unchanged and the audits are separate files. Corrected jobs can be audited with the original mapping/source report and corrected output hash. Exact clip links load the requested character/result without changing its active editable profile.

- All **42 derived GLBs** have zero Khronos validation errors. Each Cesium output has one inherited skinned-mesh-parent warning; each Quaternius output has six inherited warnings (three skinned-mesh-parent and three generated-tangent-space). Source-asset validation confirms those warnings were already present. RobotExpressive's separate source validation fails as recorded above.
- Actual Godot 4.7.2 import checks **6,120 frames**, 19/65 bones and all skinned surfaces across both studies. Maximum position discrepancy is 3.30e-6 m and maximum basis-element discrepancy 7.68e-7. This does not prove GPU skin rendering, gameplay physics, blending/root extraction or animator quality.
- An independent all-frame paired GLB audit confirms unchanged rotations/horizontal movement and only the declared constant Y displacement under the mapped pelvis. Maximum skin displacement error against that constant is 2.16e-8 m.
- All **42 ZIPs and 42 GLBs** were downloaded through the local server, SHA-256 checked, and every archived non-README entry compared with the saved file. Licenses/provenance are included. Packages do not contain model weights or the entire inference environment.
- **242 tests pass**, with four upstream Torch deprecation warnings. New tests cover lossless packing/resource repair, traversal rejection, mapping ambiguity, neutral calibration preserving authored placement, immutable inputs and hash-bound Studio ground inspections.
- Browser verification confirmed the 65-bone neutral preview, exact-job links, report filtering, baseline female-wave hover jump to frame 102, and calibrated female-wave floor jump to frame 54. These are developer checks, not independent human ratings.

Review: http://127.0.0.1:8767/reports/rig-diversity-height-v1/review.html . Evidence lives in both study folders, `reports/godot-rig-diversity-v1`, and `reports/godot-rig-height-v1`.

## Next work under the existing goal

Author target-mesh contact patches on curved/non-flat soles and extend support beyond feet to hands, knees, torso and head. Preserve hard edit budgets, infeasibility diagnostics and independent collision/contact checks; do not compensate for a head collision merely by shifting the entire clip. Add another independently authored rig family and preserve unsupported inputs rather than weakening the declared checks. Continue the outstanding rough-clip editing, transitions/style, scene/partner coordination, offline installation and independent animator cleanup-time/release work. The seven motions are measurement strata, never a whitelist of supported prompts.
