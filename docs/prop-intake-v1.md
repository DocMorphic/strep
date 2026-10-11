# Static prop intake and source-bound grip authoring

`scripts/static_prop_asset.py` loads self-contained static GLB triangle geometry.
`scripts/studio_props.py` stores original payloads locally and creates immutable,
source-bound surface selections. This is an authoring backend; Studio upload
controls, mesh contact solving and engine export are not integrated yet.

Intake retains the selected scene hierarchy, mesh instances, scale and reflection
in glTF metre/Y-up asset coordinates. It does not recenter or resize objects.
Valid parent/child TRS composition can produce world shear, which is retained.
Local matrix shear is rejected. Skins, animation, morph targets, sparse accessors,
external image/buffer references and unsupported compressed geometry are rejected.
Limits are 32 MiB, 512 nodes/surfaces, 200,000 instance vertices and 400,000 faces.

Every surface selection names the source and transformed geometry hashes, the
exact triangle index and three nonnegative barycentric weights summing to one.
The store recomputes its position and winding normal. Winding does not certify an
outward normal, watertightness or collision. Grasp validity, mass, inertia, force
balance, scene support and animation quality remain unverified.

For a local authoring client, add `scripts` to the Python import path and call:

```python
from pathlib import Path
import studio_props

asset = studio_props.import_bytes(
    Path("my-prop.glb").read_bytes(), "my-prop.glb",
    license_note="My own asset",  # User assertion; rights are not inferred.
)
# Select an actual triangle and location from this asset's geometry.
draft = dict(asset_id=asset["id"], geometry_sha256=asset["geometry_sha256"],
             face=selected_triangle, barycentric=selected_barycentric_weights)
point = studio_props.surface_preview(draft)
saved = studio_props.save_grip({**draft, "label": "Left-hand grip"})
verified = studio_props.grip(asset["id"], saved["grip_id"])
```

Assets live under ignored `reports/prop-assets/<source-hash>`. Stored GLB bytes
remain unchanged. A changed selection creates another record; old selections
remain available. Exact duplicate uploads retain original metadata. Reads verify
the payload, reconstructed inventory and grip hash/triangle. Served-file lookup
permits only the original GLB and verified grip JSON; HTTP routes are not added
by this module. Filenames do not grant third-party provenance or license rights.

Generated-fixture checks cover hierarchy and instances, nonuniform scale,
reflection, world shear, payload preservation, unsupported representations,
budget rejection, corrupted assets/grips, false hashed landmarks, serving
allowlists and failed-write cleanup. Staged intake and store checks pass 39 and
23 cases respectively. These are source checks, not real-object interaction,
engine or human approval. The public import-layout check passes all 62 cases;
its completed resource trace independently replays 21 observations. Both suites
are registered in the 444-module Python / 41-suite Node source-check inventory.

The existing scene solver still accepts analytic boxes, spheres and cylinders.
It must be extended and validated against actual triangle props before these
selections can drive motion corrections. See [the glTF coordinate and transform
specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html).
