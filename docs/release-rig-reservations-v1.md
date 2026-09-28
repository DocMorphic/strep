# Reserved rig proportions for evaluation

Three concrete fixture assets now complement the reserved prompt set. They derive from the existing Quaternius Universal Base Characters Standard female and male meshes. The official pack page currently lists CC0, matching the retained source license. Original license/provenance/packing records are copied into every fixture folder. Source: https://quaternius.com/packs/universalbasecharacters.html (checked 2026-09-28).

| Fixture | Source | World X/Y/Z factors | Neutral height |
|---|---|---|---:|
| rig-held-01 | Female | 0.90 / 1.10 / 0.95 | 1.953 m |
| rig-held-02 | Male | 1.12 / 0.90 / 1.08 | 1.638 m |
| rig-held-03 | Female | 1.15 / 1.00 / 1.00 | 1.775 m |

Construction scales default-pose mesh and joint positions together in world coordinates, grounds the mesh, retains rigid rotation bases, rebakes the mesh and recomputes inverse binds. Normals/tangents are transformed, materials and influence data retained, and node transforms remain rigid with unit scale. The generated character files have no animation; both source files also had no animation. Profiles retain the original 19 neutral role mappings and foot alignments, with new character hashes and no motion-based tuning.

An independent decode checks transformed surface and joint coordinates, unchanged hierarchy/influences, normalized normals, profile validity and the binding to engine evidence. Maximum surface error is 0.674 micrometres and joint-position error is 0.551 micrometres. All three fixtures retain 65 skin joints. Godot checks two identical neutral poses per fixture: six static actor-frames, with three skinned surfaces each. This is construction/import evidence, not retargeting or animation quality evidence.

`benchmarks/release-rig-reservations-v1.json` binds each character/profile to its hash and reserves three directed partner pairings. Actual scene placements and contact targets remain unbound. These are new proportions within one known topology/skinning family and two source meshes; do not claim independent artist-rig or topology generalization. No reserved action prompt or model seed was run. Keep these assets out of correction/transfer tuning and retire/version them if motion outcomes inform development.

The full release fixture package is still incomplete: task geometry, placements, fixed metrics and method/baseline choices must be bound before trials. No release approval or universal-rig claim follows from these static checks. The production character catalog is unchanged.
