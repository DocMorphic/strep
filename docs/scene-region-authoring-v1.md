# Authored distributed scene contacts

Scenes can now declare a hand patch and measure distributed contact against a moving box or sphere. A point touching an object is insufficient when the author requests a separated contact area. These requirements are additional to the explicitly selected anchor constraint; choosing a different anchor creates a new authored condition.

## Scene format

An existing scene contact may include `region_contact` with these required fields:

| Field | Meaning |
| --- | --- |
| `schema` | `strep-scene-region-contact-v1` |
| `mesh_sha256` | Canonical content fingerprint returned by `scene_region_contact.mesh_fingerprint(skin)` |
| `hand` | `LeftHand` or `RightHand`, matching the effector |
| `face_ids` | Unique triangle indices in this exact skin mesh |
| `limits` | Explicit clearance, contact gap, spacing, area, centroid distance, local radius and normal-angle limits |

The limit keys are `clearance_m`, `contact_gap_m`, `spacing_m`, `area_m2`, `centroid_error_m`, `local_radius_m`, and `normal_degrees`. No implicit acceptance defaults are supplied. The anchor must belong to the patch, and all positive skin influences must belong to the declared hand. Patches contain 3–256 vertices. Changed bind geometry, topology, skin weights, joint names or bind transforms invalidate the fingerprint.

The target must name a scene primitive and a point on its smooth surface. The desired patch normal is the inward primitive normal at that point, transformed with the object. Partner targets and separate normal/tangent overrides are rejected by this version, rather than interpreted as equivalent primitive contacts. They remain required future workflow capabilities.

## Compilation and measurement

```powershell
.venv\Scripts\python.exe scripts/compile_scene_regions.py path/to/authored-scene.json --actor A --contact left-grip --contact right-grip --output reports/new-region-compilation --evaluate
```

This saves the authored scene, an actor-native region package, source provenance and optional source-motion measurements. The package preserves object geometry and sampled poses, patch bindings, normal tracks, inclusive intervals, and a separately labelled anchor subproblem. Actor placement inversion follows the existing yaw-only grounded actor convention. Compilation produces no new animation and claims no solver success.

The scene evaluator searches for three patch vertices within the declared object-gap and target-radius limits. Every pair must meet the spacing limit, their triangle must meet the area limit, and its centroid must be near the authored grip. All patch vertices must satisfy clearance, and the area-weighted patch normal must satisfy the angle limit. Collapsed normals fail. An exhaustive search uses fixed-size batches to bound memory. Each successful frame records a witness triangle, gaps, spacing, area and centroid error.

The anchor is still measured independently. `anchor_all_requested_frames_within_tolerance` records that result; `all_requested_frames_within_tolerance` requires both the anchor and the distributed region. Full-body object penetration remains a separate scene measurement. These native integer-frame checks do not replace the prior decoded quarter-frame export audit.

Legacy point compilation, solver-context compilation and vertex-normal auditing reject region requests with an explicit explanation. Feeding just the anchor subproblem into those tools is not an implementation of the authored region condition. The [experimental V14 fitting path](scene-region-fitting-v14.md) now consumes the package explicitly, with independent exported-motion validation. Current compilations record `solver_supported: true` and `solver_version: 14`; this denotes an available experimental consumer, not successful fitting. Studio editing controls remain pending.

## Validation and limits

Focused tests exercise rigid-placement invariance, passing anchor/failed region cases, single-point contact, penetration, collinear contact, reversed normals, mesh changes, malformed bindings, actor-space conversion, source immutability and rejection by unsupported consumers. Existing point and primitive tests remain included.

The focused suite passes 45 tests. A development replay of the [corrected sphere animation](sphere-region-upper-return-v1.md) through the new scene evaluator passes both hand regions on all 62 requested native frames (60–121 inclusive), with the independently declared 5 mm anchor and 10-degree normal limits. Maximum normal errors are 9.520553 and 9.524751 degrees. The two scene objects have zero sampled skin-vertex penetration. This reroutes an existing development result through the authoring contract; it is not an additional generated action or held-out trial.

The original scene and motion remain unchanged. The explicitly authored variant records the changed anchor IDs (14814 and 17076), patch definitions, original protocol hashes and release-guard endpoint. Evidence is retained locally under `reports/scene-regions-development-v1/compiled-final`, including implementation snapshots. Native scene checks pass; the previous exported quarter-frame audit remains separate evidence, not a result of this compiler.

This is an incremental scene-authoring contract and measurement path. It does not establish successful generation, general interactions, forces, continuous or triangle-interior collision, self-collision, anatomical validity, animator approval or cleanup time. All release capabilities remain unapproved.
