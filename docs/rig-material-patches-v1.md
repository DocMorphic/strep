# Material hand regions on supplied rigs

Partner and object contacts need points on the character's skin. A mapped hand bone origin does not identify a palm, fingertip or grip surface. `scripts/rig_material_patch.py` now preserves explicitly selected GLB triangles and provides their material vertex references to the existing native contact reader. This is an authoring primitive; it grants no anatomical, interaction or motion approval.

## Source and topology contract

`MaterialSurface` requires the exact character and profile SHA256 values, a default-node reference profile with zero world offset, distinct mapped skin joints and a fully skinned surface supported by `RigAsset`. Every original indexed or nonindexed triangle retains a `[mesh node, primitive, local face]` reference. Material points use the native `[mesh node, primitive, vertex]` references, including multiple mesh nodes/primitives and up to eight influences. Triangle winding and vertex order are preserved. Coincident seam vertices are not welded.

Candidate ownership is the sum of the selected mapped bone's normalized influences, optionally including its actual hierarchy descendants. Bone names do not select a hand. The ownership fraction divides by the resummed complete influence weight, so an entirely owned vertex remains exactly one when floating-point sums differ from one by an ULP. A threshold below one explicitly includes blended boundary vertices. This is deformation ownership, not a classifier for palms or contact suitability.

Candidates classify every owned triangle: eligible nondegenerate faces and excluded degenerate faces are both recorded. Complete populations exceeding the explicit face budget fail instead of returning a subset. The fixed source limits are 250,000 vertices and 500,000 triangles.

An authored patch requires distinct existing triangles, one component connected by shared triangle edges, declared ownership at every selected vertex, and nondegenerate reference triangles. Its complete population must fit an explicit limit of at most 512 faces and 256 vertices. The vertex limit matches the native point-contact reader. A whole hand inventory may exceed that limit and is not automatically an applicable patch.

Area-weighted normals follow the selected triangles' winding. The report retains area, coherence and degeneracy; cancelling winding produces an unavailable normal rather than a replacement axis. A computable normal is not a claim about anatomical palm direction or the outward surface of a volume. Pose measurements rebuild selected material triangles from complete supplied node transforms, report posed degeneracy, and require unchanged source bytes and patch payloads.

## Authoring API

```python
from rig_material_patch import MaterialSurface

surface = MaterialSurface(character, profile,
    character_sha256=expected_character_sha256,
    profile_sha256=expected_profile_sha256)
inventory = surface.candidates("LeftHand", include_children=True, minimum_weight=1.)

# Select original triangles explicitly after inspecting the intended surface.
patch = surface.patch("LeftHand", selected_face_references,
    include_children=True, minimum_weight=1.)
posed = surface.posed(patch, complete_node_world_matrices)
```

`patch["vertices"]` feeds a native contact's `vertices` field. Partner target references must be authored separately, with explicit correspondence for distributed contact. Sorted material vertex IDs do not establish matching locations between different characters. The existing `individual` and `centroid` reductions retain their original semantics; a vertex centroid can lie off a curved or concave skin surface. Creating references does not create a timing schedule or resolve collisions. All original native, contact, geometry and engine checks remain necessary.

Appending animation changes a GLB's full-file hash. A patch is therefore rejected against changed asset bytes, even when references appear identical. The separate [explicit bundle transfer](material-patch-authoring-v1.md) checks the complete static deformation identity and creates new source-bound patches with retained parent evidence; it does not relax this API's source checks. Material ownership also does not supply finger articulation, grip intent, a partner response or an animator review.

## Complete reserved neutral inventory

```powershell
python scripts/reserved_partner_materials.py build reports/release-partner-reservations-v2 reports/release-partner-materials-v1
python scripts/reserved_partner_materials.py verify reports/release-partner-materials-v1
```

The separate builder copies the complete already verified neutral fixture bundle and archives bound methods. It prepares both hand inventories for every directed pair and actor: three pairs, six instances and twelve hands. Repeated rig instances share identical default-pose topology; their separately bound scene placements remain unchanged. Every original attachment and neutral observation remains present. Replaying a moved bundle rebuilds every candidate and reduction without requiring the original asset paths. Changed candidate data is rejected even if its JSON hash is rebound; complete population, source, methods, settings and false approval fields remain checked.

This neutral step neither generates nor tunes reserved motions, selects a palm patch, binds an interaction target, changes a scene's empty contacts/animations, executes the engine, or fills release evidence. The rigs still share the known topology and two source meshes described in the [neutral import results](reserved-partner-engine-results-v1.md). They cannot establish generalization to independently authored rigs.

## Validation status

An isolated public-source copy passes 149 checks: 82 new material/portable-inventory checks and 67 existing neutral-fixture/native-contact checks. They cover actual tiny GLB decoding, all eight influences, indexed/nonindexed primitives, different mesh nodes, repeated slots, both hands, explicit mixed ownership, cancelled winding, source mutation, complete budget rejection, patch-payload integrity, native partner-contact sampling, moved bundles and rebound/tampered evidence. No model, vendor or character payload was copied into that source check.

The actual twelve-hand inventory and complete portable replay also pass. The [reserved inventory results](reserved-partner-materials-results-v1.md) report the populations, hashes, corrected read-denial harness and remaining anatomical/interaction limitations. No human or interaction-quality result is claimed by these source checks.
