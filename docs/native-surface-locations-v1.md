# Locate self-surface failures before repairing animation

`scripts/native_surface_locations.py` adds read-only location metadata to a
complete native self-surface audit. It retains every supplied flag and degenerate
face, maps triangle IDs to their original mesh node/primitive/material and
vertex IDs, records sampled coordinates, and summarizes mean skin influences.
Joint node IDs remain distinct even when names are identical. Skin influences
are location hints; they are not a verified anatomical classification.

The caller supplies a validated `RigAsset`, complete sampled node matrices and
the corresponding `native_self_surface.audit` result. It must bind the source
clip, animation/time and audit bytes. The helper checks the triangle population
hash, record indices, shared vertex identities and unapproved result contract.
It does not reconstruct the audit's missing candidates or independently certify
that an externally supplied report came from that pose.

The result contains all recorded pairs, all implicated triangle descriptions and
their vertex positions. No ranking limit drops lower-priority records. Unknown
lengths for ambiguous coplanar/boundary cases stay unknown. Crossing-segment
lengths remain distinct from penetration depths.

Exact duplicate loaded position and skin-influence attributes are annotated
per pair. This uses the native `RigAsset` reader's normalized weights and is not
an equivalence claim about raw imported engine skin. No vertices are welded,
no pose is edited and no flags are exempted. A pair with duplicate attributes
can still cross away from its shared point.

## Real wave diagnosis

The [scene export failure](surface-clip-scene-engine-v1.md) is now localized at
all 17 declared times for both the original and corrected native wave: 34
animation observations, plus the original GLB's default-node reference pose.

Each animation population contains 81,329 recorded pair observations across
the 17 poses, including 588 proper-crossing observations. These are observations,
not counts of unique defects. There are 80,750 observations with duplicate
loaded vertex attributes, including **nine proper crossings**. Removing all
such pairs would hide measured crossings.

The proper-crossing region totals are identical between the original and
corrected native clips. The largest groups, classified by dominant skin nodes,
are:

| Skin-joint nodes | Labels | Crossing observations |
| --- | --- | ---: |
| 16 / 21 | Right arm joint 3 / neck joint 2 | 187 |
| 17 / 17 | Left arm joint 4 / itself | 119 |
| 12 / 17 | Torso joint 2 / left arm joint 4 | 74 |
| 13 / 17 | Torso joint 3 / left arm joint 4 | 53 |

The sampled default-node reference pose has 5,002 ambiguous surface records
and zero proper-crossing records. It is not asserted to be the inverse-bind
pose. The animation observations and projections point to the raised hand/head
and shoulder/torso regions for targeted motion diagnosis; they do not establish
that all other mesh geometry is valid. The earlier one-pair engine/native
classification difference remains unresolved.

Evidence is retained in `reports/surface-location-wave-v1/` in the development
checkout, including the complete location tables, original record bindings,
default-pose audit, verifier and `locations.png`. The image projects recorded
diagnostic triangles at the 106-crossing pose alongside the reference pose;
red triangles participate in proper-crossing records. It is a location aid,
not a rendered preview or an occlusion/penetration measurement.

Local validation passes 64 Python cases covering localization and the existing
self-surface screen. The verifier checks every retained record, all output
hashes, both 17-pose populations and the reference audit. All 51 guard resource
observations replay. The full/focused CI source inventories now contain
658/207 Python files; this does not claim a full hosted regression run.

Next, test bounded arm/shoulder corrections against the immutable source,
checking proper-crossing pairs, floor, authored contacts and temporal continuity
together. Preserve legitimate near-body gestures and explicitly authored
contacts. Native and engine comparisons, dense-time validation and human review
remain necessary before accepting any repair. This localization change alone
does not approve a scene, change the collision gate or complete the project.

The subsequent [bounded pose experiment](wave-self-repair-pose-v1.md) reduces
the worst pose from 106 to ten proper-crossing pairs with reference-guided arm
edits. Six pairs are new, so the proposal remains rejected as a complete repair.
