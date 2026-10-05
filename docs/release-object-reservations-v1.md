# Reserved primitive object fixtures

Five concrete object assets now complement the reserved prompts and rig proportions. Their dimension sets are fixed before any motion trial, with two boxes, one sphere and two cylinders. This is five geometries across **three primitive families**, not five independent shape classes. Exact historical geometry exposure and checkpoint-training independence are unknown. These fixtures do not complete the release scene package or approve any interaction.

| Fixture | Analytic dimensions, metres | Stored triangles |
|---|---|---:|
| object-held-box-tall | XYZ 0.31 / 0.47 / 0.23 | 12 |
| object-held-box-flat | XYZ 0.64 / 0.18 / 0.37 | 12 |
| object-held-sphere | Radius 0.173 | 2,048 |
| object-held-cylinder-tall | Radius 0.119, full height 0.51 | 128 |
| object-held-cylinder-flat | Radius 0.287, full height 0.136 | 256 |

`benchmarks/release-object-reservations-v1.json` binds the specification and reservation policy. Construction is reproducible from source:

```powershell
python scripts/reserved_object_fixtures.py benchmarks/release-object-reservations-v1.json --output reports/release-object-reservations-v1
```

Use a fresh output directory; earlier assets and evidence cannot be overwritten. The builder accepts explicit unexecuted reservation catalogs, rejects duplicate IDs and exact duplicate geometry, and preserves input and implementation hashes. It constructs static, unskinned, self-contained GLBs with one grey object at its local origin. These procedural objects require no downloaded character, object payload or model.

Each descriptor retains the analytic shape, full asset hash, preview approximation, opposing smooth X-axis anchors and a canonical grounded translation. The translation is a separate placement recipe, **not** baked into the local GLB. Anchors describe surface points and outward normals; they are not reachable-grip or anatomical-contact certificates. Mass, materials for simulation and runtime physics are unbound. Task-specific poses, contact intervals, actor/partner placements and complete scene contexts must still be fixed before release trials.

The preview is an inscribed triangulation of the analytic primitive with a declared nominal inset at most 1 mm, plus recorded Float32 vertex rounding. Collision/contact consumers must use the analytic geometry contract rather than silently replacing it with the preview mesh. The static decoder uses separate primitive-distance arithmetic, checks every stored vertex and normal, triangle winding, exact saved-vertex edge incidence, mesh bounds and four interior samples per triangle. It rejects escaping assets, transformations, nonstatic data and changed geometry. The decoder and triangulation producer are shared source dependencies; the sampled interior check is not an independent continuous collision certificate.

The completed construction contains 7,368 stored vertices and 2,456 triangles. Maximum saved-vertex distance from the analytic surface is 1.2957482843407909e-08 m, approximately 13 nanometres. The largest checked preview inset is 0.0006718526651833534 m on the sphere. These tolerances concern representation, not animation realism. All five saved reductions replay exactly, and a second static construction produces identical GLB bytes while preserving every original file.

Thirty-seven focused Python checks pass in the working tree and a fresh source-only copy without models, downloaded assets or vendor code. They cover all three primitive types, repeatability, preserved inputs, catalog/exposure-flag rejection, changed surface/bounds/normals, inward triangles, external dependencies, invalid scene roots and changed input detection. The first isolated checker omitted dependencies needed by an existing geometry test and failed collection. Its incomplete folder/log remain preserved; a fresh complete-source checker passed. No earlier failure is reused as successful evidence.

Local construction: `reports/release-object-reservations-v1`. Independent saved reductions and repeat construction: `reports/release-object-reservations-check-v2`. The generated assets stay outside Git; source and the dimension catalog are public. Headless engine import, grip reachability, full scene bindings, animation semantics, human review and cleanup measurements are not yet supplied by this work. No reserved action prompt or model seed was sampled or trained. Keep these exact objects out of motion-based tuning and retire/version a reservation if its motion outcomes inform development. All release matrix requirements remain unchanged.
