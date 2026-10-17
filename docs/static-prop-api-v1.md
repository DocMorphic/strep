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
1 micrometre grip-position limit are unchanged.

The finite table now has **80 completed candidate decisions**. The original run
stopped at its unchanged 900-second execution limit after 70 decisions, with a
partial next probe retained. A separate versioned continuation verified the
closed prefix, source/method hashes and every saved decision, then evaluated
only the remaining ten proposals. It kept the original source, baseline,
condition identities, permissions and thresholds. The first run remains marked
failed; the continuation does not rewrite its history or claim it completed.
Resource replays verify both runs: first 900.172 s / 240,918,528 bytes / 895
observations, continuation 134.437 s / 223,690,752 bytes / 149 observations.
Memory did not cause the stop.

All 80 satisfy the sampled pose-edit bounds and declared point contacts, but
**none passes all three-time geometry conditions**. Fifty-nine introduce a
previously passing condition failure; ten meet the source comparison rules.
Best admissible probe 5 reduces peak sampled penetration from 81.464129 mm to
27.208295 mm and surface crossing records from 247 to 113. Both still fail the
collision policy. A small finite orientation table without a passing candidate
does not prove that the authored constraints are infeasible. No character motion
was changed, and the original scene stays selected.

Independent replay imports neither new backend. It reconstructs the edited
key from the original grip and permissions, verifies both frozen endpoints and
all other scene content, and reproduces all **2,017** native/frame pose-change
samples byte for byte. Peak centre displacement is 0.114805271 m and rotation
45 degrees, within the explicit prop edit bounds. The grip error is about
0.5 micrometres, within its original 1 micrometre limit. Every world-vertex
array and all 15 complete mesh pairs across the three declared times reproduce;
the same geometry failure remains. Original passing-condition identities and
all source collision metrics are independently checked. Guard: 15.390 s /
204,976,128 bytes / 33 observations.

This replay independently checks composition and saved transport using the
existing rotation/interpolation/collision libraries. It is not a separate
collision algorithm. The 2,017 pose-bound samples do **not** imply 2,017 geometry
samples: geometry here covers only the three declared times. Continuous
collision, grasp dynamics, action semantics, engine import and human quality
remain unverified.

A subsequent diagnostic evaluates **both** original and candidate at the
endpoints and original native keys 62 through 68: nine times per scene, all
90 actor/prop and prop/prop pair queries, plus the existing actor scene and
ground conditions. Source binding, geometry thresholds and ground planes stay
unchanged. The candidate removes the source collision at key 64 without
introducing any newly failed condition in this population:

| Nine-time measurement | Original | Probe 5 |
| --- | ---: | ---: |
| Failed geometry times | 2 | 1 |
| Failed conditions, including whole-sample decisions | 4 | 2 |
| Surface crossing records | 293 | 113 |
| Peak vertex penetration | 81.464129 mm | 27.208295 mm |

The remaining failure is at key 65. This expanded comparison uses the producer's
geometry stack; it has not had a separate geometry replay. Its resource replay
confirms completion (72.812 s / 330,895,360 bytes / 89 observations). Nine explicit
times remain sparse coverage of the 2,017 native/frame sampling times.
Passing the non-regression comparison does not make either scene collision-free
or approve a box pickup. All outputs and the interrupted probe remain retained
locally; no scene is promoted.

## Surface-guided orientation proposals

`scripts/native_mesh_prop_surface_seed.py` adds geometry-informed proposals to
the same bounded, source-relative prop editor. It uses every triangle incident
to the selected contact vertices at the editable key, suggesting orientations
that oppose the prop grip's winding normal to each incident actor normal and
their area-weighted mean. Explicit twist samples explore orientations around
that world normal. The full actor mesh stays in the collision evaluation;
incident faces supply guidance, not a replacement collision surface.

```powershell
python scripts/native_mesh_prop_surface_seed.py pose-permissions.json mesh-policy.json reports/my-surface-search --maximum-candidates 32
```

The editable key must lie in the selected contact interval. Guidance rejects
degenerate incident faces and unsupported populations instead of silently
dropping them. A cancelling mean is reported as unavailable while both opposed
face directions remain. Winding normals are not certified outward normals;
neither matching them nor fitting the selected point proves a grasp.

The table begins with the original pose and optionally a saved starting point.
`--warm-start warm-start.json` accepts only an explicit
`strep-prop-source-relative-warm-start-v1` document containing
`permissions_sha256` and four cumulative `controls` relative to those exact
original permissions. Its geometry and contacts are remeasured. It does not
create a new source or reset any angle/displacement limit. Invalid proposals are
retained as rejected controls, never clipped into the permitted domain.

Every admissible proposal checks all native/frame sampled pose-change bounds,
all declared point contacts and all geometry policy conditions. A newly failing
condition remains a rejection even if the total failure count stays unchanged.
Source collision metrics cannot worsen; best proposals require componentwise
improvement. Candidate limits and incomplete tables are explicit. No finite
normal/twist table proves global infeasibility or complete action coverage.

All **40** focused tests pass locally and on Windows/Ubuntu at `cc3a032` in
[run 39079181801](https://github.com/DocMorphic/strep/actions/runs/39079181801).
They include exact/opposed/general normal alignment, world twist composition,
incident-face identities and area weighting, cancelling/degenerate guidance,
strict caps and locked rotation, original source bindings, remeasured starting
points, and complete contact/geometry repair of a generated convex fixture.
The local guard records 23.625 s / 125,390,848 bytes / 41 observations. These are
source tests and generated fixtures, not real-action or release approval.

The retained real-character trial records the complete 22-entry table: the
original, the remeasured previous best, and 20 proposals from four incident face
normals plus their area-weighted mean, each with four twists. One guided
proposal fails its strict native pose bound and is retained without export.
The other 19 pass all sampled pose budgets and point contacts but introduce a
previously passing partner/box condition failure. None is accepted; the previous
best remains unchanged at 27.208295 mm peak penetration. Guard: 272.718 s /
239,104,000 bytes / 284 observations, with an independently replayed resource
trace. No source/cap/threshold changes or scene promotion occurred.

This is useful failure evidence: probe 2 clears the box from actor A but moves
it into actor B. The total failed geometry-time count remains one, and its
41.504893 mm peak is below the original 81.464129 mm. Those aggregate numbers
cannot justify accepting a new collision with the partner. The stable condition
identities reject it. The finite table is not a proof that no valid orientation
exists, and this authored contact demonstration is not a generated pickup.

A separate replay imports none of the three new mesh/pose/guidance backends and
independently reconstructs **rejected probe 2**. It reproduces all 2,017 sampled
pose-budget values and world-vertex arrays and freshly recomputes every one of
the 15 complete three-time mesh pairs. Actor A's condition is repaired; actor
B's previously passing condition newly fails. All declared point contacts and
original edit bounds still pass. Guard: 13.344 s / 192,659,456 bytes / 31
observations. Existing collision/interpolation libraries are reused, so this is
independent composition/transport rather than a separate collision algorithm.

The unchanged best's earlier independent qualification is inherited through
its byte-identical complete scene manifest and every geometry/contact/pose-budget
observation array, with the earlier replay's inputs rehashed. Its geometry was
not freshly recomputed in this replay. That best still fails collision checks.
Full native/frame geometry, continuous collision, dynamics, action correctness,
engine imports and human acceptance remain open. Next fitting work must use
partner collision witnesses when proposing edits, while retaining the original
source, frozen keys and all prior passing conditions.
