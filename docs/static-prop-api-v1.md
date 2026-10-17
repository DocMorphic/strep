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

## Moving imported meshes: source-bound scene measurements

`scripts/native_mesh_prop_scene.py` now consumes imported static GLBs and saved
grips alongside an existing native actor scene. The prop's complete default-scene
geometry, hierarchy transforms and scale are retained. Explicit rigid pose keys
move that geometry and its exact triangle grip points; translation is linear
and rotation uses Slerp. Winding normals are transported for inspection, without
claiming outward-normal verification or evaluating hand orientation.

The versioned input is `strep-native-mesh-prop-scene-v1`:

| Field | Required content |
| --- | --- |
| `actor_scene`, `actor_scene_sha256` | Existing native V1 actor/contact scene and exact file binding. Its primitive objects and contacts remain intact. |
| `props` | Named GLB path, source SHA, geometry SHA and explicit `keyframes` for each prop. Keys are static at zero or cover the shared duration. |
| `mesh_contacts` | Actor, skin vertex references, explicit individual/centroid reduction, prop, saved grip path/SHA, touch/hold interval and position/relative-speed limits. Use separate rows for separate grips. |

A `strep-native-mesh-prop-geometry-v1` policy binds `mesh_scene_sha256` and
declares `clock`, `limits` and `planes` using the existing geometry conventions.
The native/frame clock also includes exact prop keys and mesh-contact boundaries;
times are not rounded. Open/unavailable outward volumes, degenerate faces and
crossing/boundary/near-surface outcomes remain failed or unresolved conditions.

Run inside the configured project Python environment, with a fresh report path:

```powershell
python scripts/native_mesh_prop_scene.py mesh-scene.json mesh-policy.json reports/my-mesh-check
```

The CLI supervises a single CPU worker with a 512 MiB RSS limit and the unchanged
600 MiB system reserve. Output includes resource replay, source/method bindings,
contact measurements, full geometry reports and a verified streaming observation
archive. Optional `--start`/`--count` selects a declared clock slice; the report
retains the complete clock and says whether every policy time was evaluated.
Inputs are not modified. Bounded intake admits at most 32 props, 64 mesh contacts,
10,000 effective times and 64 MiB of loaded prop geometry/binary data; oversized
populations reject rather than drop triangles, contacts or times.

Measurements include existing actor/primitive/partner/plane conditions, every
actor/mesh-prop and mesh-prop/mesh-prop pair, mesh-prop/primitive pairs, and prop
world-plane checks. Crossings and bidirectional vertex containment are separate:
an intersection with no contained vertices can still fail. Original topology is
preserved; bounding boxes and convex hulls are not substituted for the narrow
phase. Original primitive/primitive and full self/continuous checks remain
separate. This backend measures authored motion; scene fitting, attachment/
release physics, editor/API wiring, engine meshes and human usability still need
integration and validation. The existing intake API does not gain solver or
release approval from these measurements.

## Verified scope and retained real-character failure

All **45** focused tests pass locally and on Windows/Ubuntu at `690f81d` in
[run 39076084765](https://github.com/DocMorphic/strep/actions/runs/39076084765).
They use the real prop store and generated GLBs/rigs to verify moving grips,
exact clocks/transforms, original-file preservation, full pair/plane populations,
surface crossings without vertex containment, enclosed volumes, open-volume
rejection, malformed bindings, admission limits, unambiguous observation names,
streaming output and guarded CLI paths. Local guard: 38.797 s / 124,416,000 bytes /
40 observations. This is focused source evidence, not a whole-suite or release
pass; earlier 40/44-case source snapshots remain immutable.

`reports/native-mesh-prop-scene-actual-v1` uses the retained two-character clip,
**36,108 original faces per actor**, and two instances of a self-created 0.3 m
box, **12 faces each**. One box stays clear; the other has an explicitly authored
grip target. No model was run and no pickup action or new character motion was
generated. Geometry is assessed at exactly **0, 2.1666667461395264 and
3.9666666984558105 s**, retaining the prior geometry limits/planes. The CLI
completes in 28.531 s / 207,360,000 bytes / 30 observations.

The grip point matches within its declared 1 micrometre position limit and all
declared point contacts pass, but the contact-time mesh geometry **fails**:
one pair crosses, with **81.464129 mm** peak sampled vertex penetration. The
other two assessed times pass. Matching an authored point does not establish
a valid object interaction; the failure is retained and nothing is selected.

`reports/native-mesh-prop-scene-replay-v1` independently reconstructs every
actor/prop world-vertex array byte for byte and recomputes all **15 declared mesh
pairs** across the three times without importing the new backend. Original
crossing/containment kernels are reused, so this is independent composition and
transport replay, not an independent collision algorithm. Point error and
geometry decisions agree exactly: 27.516 s / 182,136,832 bytes / 29 observations.
These are three authored diagnostic times, not complete 2,017-time, continuous,
physics, semantic, engine or human qualification. The earlier character motion's
6,093 source-rate failures and every project-wide release gate remain open.

## Explicit grip-centred prop pose edits

`scripts/native_mesh_prop_pose.py` adds a source-bound prop pose operator and a
bounded finite search. A `strep-native-mesh-prop-pose-edit-v1` permission file
binds the original mesh scene, prop, existing key index and authored contact ID.
It explicitly declares frozen keys, maximum rotation in degrees, maximum centre
displacement in metres, maximum intentional clearance and its unit direction in
prop-local coordinates. No boundary permission or clearance direction is inferred.

The four controls are a cumulative, source-relative local rotation vector and a
clearance fraction. Rotation uses a strict normalized unit ball; excessive
rotation or centre displacement rejects export without clipping. The chosen grip
is the rotation pivot at the edited key; clearance moves it along the explicitly
authored local direction. Actual grip errors are still checked against the
original contact limits. A pivot at one key does not guarantee other grips or
whole hold intervals, so every contact is re-evaluated.

Zero controls reproduce the original poses exactly. Only the declared prop key
may change; actor clips, prop geometry, grips, key times, frozen and unrelated
keys remain intact. Derived manifests relocate source paths explicitly without
changing source payloads. Repeated calls use the original permission origin,
not the previous correction as a new reference.

```powershell
python scripts/native_mesh_prop_pose.py pose-permissions.json mesh-policy.json reports/my-pose-search --maximum-candidates 80
```

The guarded CLI retains all proposals and failures. Its finite table includes all
three rotation axes: 26 directions at quarter, half and full authored angle,
plus the original and a clearance-only proposal when those components are
unlocked. A declared numerical interior fraction keeps proposed rotations inside
their original bounds; it is not output clipping. A finite search is neither a
global feasibility proof nor an exhaustive orientation search.

Every natively admissible candidate checks the complete native/frame sampled
pose-change clock, **all** original and mesh point contacts and **every declared
geometry policy time/condition**. No original passing geometry condition may
newly fail. Failed-condition/sample counts, crossing records and peak penetration
also cannot worsen relative to the source. Intermediate best proposals use
componentwise improvement, so fewer crossings cannot conceal deeper penetration.
`sampled_feasible_probe` identifies a candidate passing those declared conditions;
`best_admissible_probe` may still be an invalid diagnostic. Originals remain
selected; neither field grants continuous, physical, engine or human approval.

All **34** focused tests pass locally and on Windows/Ubuntu at `2cf6736` in
[run 39077460300](https://github.com/DocMorphic/strep/actions/runs/39077460300).
They verify source/frozen/unrelated-key identity, all rotation axes, separate
displacement limits, malformed/locked permissions, repeated source-relative
edits, exact zero changes for nontrivial source rotations, multi-grip rejection,
finite-search limits and a generated scene with a known collision repair.
Local guard: 55.250 s / 134,209,536 bytes / 56 observations. The earlier passing
31-case source snapshot is retained. These are generated-fixture source tests,
not real-action or release evidence.

The retained real-character pilot explicitly permits editing only the middle
`authored_box` key: up to 180 degrees and 0.5 m centre displacement, with at most
0.5 micrometres of intentional clearance along the declared local direction.
Both endpoints and all character assets stay fixed. These are new, explicit prop
edit permissions for this diagnostic; prior geometry thresholds and the original
1 micrometre grip-position limit are unchanged. Its result remains pending until
the guarded search and independent source/pose/contact/geometry replay finish.
