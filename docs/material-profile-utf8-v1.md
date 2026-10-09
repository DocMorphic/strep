# Preserve uploaded rig-profile bytes during region authoring

Contact-region authoring previously rejected a valid UTF-8 rig profile with a leading byte-order mark (BOM). The browser decoded the file with the default BOM-stripping behavior but retained the SHA-256 of its original bytes. The backend therefore received different bytes from the uploaded file. Submitting the BOM explicitly also failed because backend validation parsed a Python string, whose JSON parser rejects a leading BOM.

The browser now decodes strictly while preserving the BOM in the submitted text. The backend validates JSON from the re-encoded UTF-8 bytes, which supports a single leading UTF-8 BOM. The saved profile remains byte-for-byte identical to the supplied file. No normalization, reserialization, hash rebinding or relaxed source checks are introduced. Invalid UTF-8 remains rejected before a browser request; profile byte-size, exact SHA-256, object/mapping, character, topology, ownership and complete-triangle checks remain in effect.

The regression was reproduced before the fix: both BOM variants failed real preview/save/load tests, and the browser's actual callback failed the uploaded-byte equality assertion. After the fix, plain UTF-8, UTF-8 with BOM and BOM with CRLF profiles pass through a tiny animated GLB's preview, portable bundle creation, complete replay and explicitly ordered native point loading. The tests check exact saved profile bytes and unchanged actor animation, source hashes and false approval fields. Browser callback checks verify exact posted text/hash/re-encoded bytes and refusal of invalid UTF-8.

This repairs supplied-rig contact authoring for object and partner workflows. It does not select an anatomical palm, generate motion, fix contact geometry, provide human ratings or grant release approval. Existing running Studio servers are not restarted by this work; live browser/HTTP delivery of the revised backend is not claimed.

## Validation and remaining work

The related four-module NoTorch suite passes **170 checks** in 281.75 seconds. Four Node suites pass for the actual region-author callback, saved-region loader, explicit animation-pose inspection and complete orientation display. Five Studio build/preservation checks also pass; the separately served module change needs no generated-HTML edit. Existing exact-hash/tamper, stale selection, ownership, point-ordering and false-approval tests remain passing.

```powershell
python -m pytest -q tests/test_studio_material_region.py tests/test_studio_material_region_pose.py tests/test_studio_material_patch.py tests/test_material_patch_bundle.py
node tests/test_material_region_author.mjs
node tests/test_material_patch_loader.mjs
node tests/test_material_region_pose.mjs
node tests/test_material_region_orientation.mjs
python -m pytest -q tests/test_desktop_build.py tests/test_desktop_build_preservation.py
```

The latest native contact retry still defers without a child under the unchanged 2 GiB plus 600 MiB admission requirement. Its second V8 guard records 61 admission observations over 60.640 seconds; independent replay verifies all bindings and the unmet resource requirement. V7 stage 1 remains the latest independently verified state; fifteen windows remain and complete physical/keyed passes remain 0/62. No reserved motions are generated or tuned. Hosted CI remains queued behind an earlier run whose ten completed jobs pass while two Windows shards are still running. All fourteen release capabilities remain unapproved and the full-project goal stays active.
