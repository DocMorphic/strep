# Static prop authoring API

Studio now routes the existing source-bound GLB prop store through its loopback
API. It preserves source scale and original payload bytes. These endpoints
start no model, fit worker, server or browser themselves.

| Request | Input and result |
|---|---|
| `POST /api/props/import` | Raw GLB, `application/octet-stream`, explicit Content-Length up to 32 MiB. Optional percent-encoded `X-Filename` and `X-License-Note`. Returns source digest, inventory and original-file URL. |
| `GET /api/props/{asset_id}` | Exact SHA-256 identifier; verifies the saved payload, geometry and inventory before returning details. |
| `POST /api/props/surface-preview` | JSON with `asset_id`, `geometry_sha256`, `face`, `barycentric`. Returns the source triangle's point and winding normal. |
| `POST /api/props/grips` | Same selection plus a nonempty label. Stores an immutable source-bound selection and returns its digest and file URL. |
| `GET /api/props/{asset_id}/grips/{grip_id}` | Reconstructs the saved point from the exact source triangle before returning the selection. |

Mutation requests require the existing loopback Host and matching local HTTP
Origin. JSON selection bodies are bounded at 16 KiB; duplicate fields, nonfinite
JSON constants, chunked transport, oversized and incomplete bodies reject. GET
selection URLs accept no queries or extra path components. Original GLBs and
saved grip JSON are served through the existing artifact handler only after
store validation. Source corruption rejects reuse and downloads.

A saved triangle point is an authored geometric target. It does not establish
outward normals, a physically valid grasp, collision safety, object mass or
strength requirements. License notes remain user statements rather than rights
verification. Responses retain the store's negative solver/quality flags. Mesh
props are not yet connected to the scene solver, runtime or graphical prop
picker; current primitive object workflows remain separate.

The [focused Windows/Linux CPU run](https://github.com/DocMorphic/strep/actions/runs/38146696339)
at commit `964f062` passes **262 checks on each platform**: Linux in 13.66 seconds,
Windows in 36.14 seconds. This includes 28 new route cases and the 62 existing
static-prop/store cases, plus the earlier 172 contact/rig regressions. Route tests
use the real Studio handler in process with generated GLB fixtures, including
binary/JSON serving, complete import-to-grip roundtrip and rejection paths.
No socket, running Studio instance, browser, model or downloaded asset is used.
This is API evidence, not a live UI demonstration. Local captured-motion
validation remains deferred for RAM. All release criteria stay unchanged.
