# Explicit skin-region authoring and contact revisions

The material API now has a file workflow: inventory a supplied rig, explicitly select original triangles, verify a portable patch bundle, transfer that selection across animation edits with an unchanged rig and mesh, then apply explicitly ordered points to existing native contacts. This is a CLI/API workflow. Studio has no new selection UI and has not been visually verified for these changes.

## Inventory and selection

```powershell
python scripts/material_patch_bundle.py inventory CHARACTER.glb PROFILE.json FRESH_INVENTORY --roles LeftHand RightHand
```

`inventory.json` records complete deformation-owned candidates and excluded degeneracy. `selection-template.json` binds the exact character/profile bytes and starts with an empty `patches` array. Empty selections cannot create a patch bundle. Inspect the intended surface and explicitly add entries such as:

```json
{
  "id": "left-contact-surface",
  "role": "LeftHand",
  "face_references": [[6, 0, 0]],
  "selector": {
    "include_children": true,
    "minimum_weight": 1.0,
    "minimum_twice_area_m2": 1e-12,
    "maximum_faces": 512,
    "maximum_vertices": 256
  }
}
```

The references above illustrate the format; they are not a palm selection for your rig. Each entry needs a unique ID, actual original triangles, explicit ownership settings and one connected component. Keep the exact `schema` and `source` fields from the template. The bounds remain 1–64 patches, at most 512 faces and 256 vertices per patch, and 128 MiB per character/profile file. The complete source limits remain 250,000 vertices and 500,000 triangles. Oversized populations fail rather than being truncated.

```powershell
python scripts/material_patch_bundle.py create CHARACTER.glb PROFILE.json SELECTION.json FRESH_BUNDLE
python scripts/material_patch_bundle.py verify FRESH_BUNDLE --expected-result-sha256 RESULT_SHA256
```

The bundle contains copied character/profile/selection inputs, all patches, static identity, archived method bytes and bound manifests. Verification rebuilds every selected patch and checks exact file population, inputs, methods and false approval flags. It uses matching current implementations; archived Python is not executed. Failed builds preserve their partial output with a failure record. A bundle can move without its original asset paths.

## Transfer after animation editing

```powershell
python scripts/material_patch_bundle.py transfer ORIGINAL_BUNDLE ANIMATED.glb ANIMATED_PROFILE.json FRESH_TRANSFER --character-sha256 NEW_CHARACTER_SHA256 --profile-sha256 NEW_PROFILE_SHA256
```

Transfer requires exact equality of the complete node graph and default transforms, raw primitive attributes and indices, skin joint order and bind matrices, scene selection, and every profile field except the character hash. Raw weight values and zero-weight joint slots are compared before normalization. Animation and accessor packing may change. Geometry, skinning, default pose or mapping changes require fresh explicit authoring; this command is not retargeting.

Every original selection is preserved, newly bound to the target asset bytes and regenerated. Each transfer includes the full verified parent bundle and a comparison record. Recursion is limited to three transfers. Verification requires a valid parent result hash and rechecks the complete chain. Material/texture payloads and animation validity are outside this static deformation comparison; motion/export audits remain separate.

## Apply to an existing native scene draft

`scripts/material_patch_revision.py` accepts an original Studio native draft and a separate specification:

```json
{
  "schema": "strep-material-patch-revision-v1",
  "baseline_sha256": "EXACT_ORIGINAL_DRAFT_SHA256",
  "edits": [{
    "id": "existing-contact-id",
    "source": {
      "bundle": "animated-regions",
      "result_sha256": "EXACT_BUNDLE_RESULT_SHA256",
      "patch_id": "left-contact-surface",
      "vertex_indices": [2, 0, 1],
      "reduction": "individual"
    },
    "partner": null
  }]
}
```

Use actual lowercase 64-character SHA256 values. `vertex_indices` explicitly select and order entries in the saved patch's `vertices` array; sorted IDs do not establish correspondence. Partner bindings use the same format and require an actor target. Distributed contact counts must match. `centroid` is available only when explicitly requested and can lie off a curved surface. A null side preserves that side; an edit changing neither side is rejected. Bundle paths resolve relative to the specification. Patches must bind the exact animated actor file; transfer first if only animation has changed.

```powershell
python scripts/material_patch_revision.py ORIGINAL_DRAFT.json SPECIFICATION.json REVISED_DRAFT.json
```

Save the fresh revised draft beside its original to preserve relative actor paths. The existing native revision validator protects the complete original draft, timing, contact limits, actors, objects, geometry and other settings. A separate `.material.json` receipt binds inputs, methods, patches and native revision lineage. Source and target contacts receive only explicit material references and reductions. The command edits no animation, samples no contact motion and claims no anatomical, quality or release approval.

## Validation and current limits

An isolated public-source copy passes **171 checks in 168.05 seconds**: 84 new bundle/revision checks and 87 existing material/native-contact checks. Synthetic fixtures exercise portable creation, full parent replay, added animation, actual native edit exports, storage repacking, native skin-point sampling and protected contact revisions. Tamper cases include changes outside selected patches, raw weight changes hidden by normalization, rebound evidence, missing hash pins, false approval flags and invalid point correspondence. No model, vendor or downloaded character payloads were copied, and original/copied source hashes remain unchanged. CI now includes both new test modules on Windows and Linux; the new revision's CI result is not yet available.

The new inventory command also reproduces both complete hand inventories for all three reserved default-pose rigs. Hand populations remain 1,351 faces/893 vertices on rigs 01 and 03 and 1,544 faces/1,004 vertices on rig 02. Their templates are empty; reserved selections, anatomical reviews and targets remain zero. These are known-topology proportion fixtures, not independently authored rig generalization. Choosing useful palms/grips, animated object and partner tests, engine checks and human cleanup review remain required. No reserved motion has been generated or tuned by this work.

Local source-check receipt: `reports/material-authoring-source-check-v1/result.json`, SHA256 `ee3a9976a7bdcf60b7291973045591a0d2bb1b7c7a743855dfab75f842ecbf6f`. Complete unchanged-inventory comparison: `reports/material-authoring-templates-v1/result.json`, SHA256 `992e9d7019ae89a1193b901ddc8b2ea866d0941ce0a862f621b90f77d464147f`. These private outputs remain excluded from Git.
