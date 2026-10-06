# Tightened local depth guidance

The [preceding segment study](native-affine-surface-restoration-v1.md) improves affine surface excess but loses actual penetration feasibility. This experiment tests a **20 micrometre reserve in local guidance**: 4.98 mm, with original external acceptance still **5 mm**. It neither relaxes acceptance nor changes source/native/contact/rate/reference/edit budgets. The reserve is a measured experiment parameter, not a proved universal nonlinear-error bound. Production selection is unchanged.

## Complete saved-model measurement

The already independently replayed sixty-control model retains all 29870 native norms, 276815 scalar surfaces, 2873 depth witnesses, original inputs and matrices. No model/Jacobian or witness population is rebuilt. Separate guidance-policy bytes and both phase points remain archived. Both phases return `Solved`; the surface point violates the original 1e-9 native check tolerance at about 8.707e-9 and is rejected. The primary native margin is about 3.772e-6.

The existing bounded helper measures 32 intermediate probes plus endpoints and selects fraction **0.9999973045196384**, with affine surface excess **2.454209507160 → 2.333154686449**. Every trial checks all original affine native norms strictly at zero tolerance, the original delta box and the tighter local depth-priority bound. Original external geometry checks remain unchanged.

All requested fractions receive every 1707 native and 1673 geometry sample:

| Fraction | Stored failures | Centered failures | Contact failures | Depth, mm | Triangle records | Contained vertices | Failed geometry samples |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1.0 | 8 | 4 | 0 | 4.978978 | 30113 | 0 | 1605 |
| 0.5 | 0 | 0 | 0 | 4.989988 | 30271 | 0 | 1603 |
| 0.25 | 0 | 0 | 0 | 4.995283 | 30382 | 0 | 1603 |
| 0.125 | 3 | 0 | 0 | 4.998034 | 30419 | 0 | 1603 |

All original reference bounds pass. The half and quarter steps pass native/contact/reference/depth checks. Every overall geometry fails its persistent triangle intersections; the full step also fails nonlinear native conditions, so storage alone cannot fix it. All failed probes and source/earlier outputs remain immutable. No numerical success approves quality or release.

A consumer imports no restoration/job/model/proxy/solver and reconstructs every scalar segment trial, bisection decision and selected direction from frozen full matrices. The tested public observation API then reproduces every actual payload, decoded world and native observation, original rate array and all-native original static/animated reference bound. Saved collision clocks/limits/scores and observation transport match. Collision predicates and producer auxiliary centered observations are not independently reimplemented.

## Appended diagnostic and remaining failure

Among fractions that pass original motion/reference/depth checks, the half step has the fewest recorded triangle intersections. It is kept as an unapproved diagnostic, with depth **4.989988 mm**, **30271** triangle records, zero contained vertices and **1603** failed samples. The preceding native-feasible depth-passing candidate has approximately 4.975307 mm, 30454 triangle records and 1606 failed samples; this trades some penetration margin for fewer intersections. Both remain. No selected production asset changes.

Separate index6 variants preserve all six source animation clips and original binary prefixes. A second consumer imports no job/storage/restoration API and verifies original scene metadata, complete library/binary preservation, identical saved controls and every appended native world against the independently replayed raw fraction. All five CPU workers exit zero. Runtime code is unchanged; the prior seventeen focused helper tests remain applicable. Hosted CI success is not claimed.

Next implement a pinned offline command for these saved-model reserve/restoration experiments with complete raw outputs and original decoded acceptance. Persistent crossings, broad action/rig/object/partner validation and human cleanup evidence remain unresolved. These generated cube-skin fixtures provide no production humanoid, inference/training, engine, physical, rendering or human release evidence. All fourteen release evidence arrays remain empty.

Immutable ignored local receipt SHA256 identities:

- capture: `ffd3cca81e036c02fa8cd789d7bf44d79a79eb3f1b3bac54509398fd2d262f9c`.
- study: `74d21ac9a3b55a747fd2c441e5b869f1246e1ccf964d0edda69e3415e4780f11`.
- replay: `4722faaba12c1ea299fec4c32b3d84bc311b80be618f32ac4e90685c4a509ce1`.
- appended: `72b00b6fc29f9dcd33f34a9b382bca7cb07fa97e8af9c9f94cf6d4a99ab8f7d2`.
- appended_replay: `2d3dbc00f46d2560ccc823eb7d4311ef009f8f41affe0f5b73e3a101cc21f864`.
