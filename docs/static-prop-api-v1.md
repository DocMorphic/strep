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

## Scene-aware local prop fitting

`scripts/native_mesh_prop_scene_fit.py` proposes original-relative rotations
using both characters and every other mesh prop, rather than only the selected
contact's normal. It keeps character-motion tracks, geometry, grip
definitions, frozen prop keys and edit permissions unchanged. The clearance
fraction stays at its explicitly supplied starting value.

```powershell
python scripts/native_mesh_prop_scene_fit.py pose-permissions.json mesh-policy.json warm-start.json reports/my-scene-fit --maximum-evaluations 96 --maximum-iterations 12
```

Guidance samples the three vertices, three edge midpoints and centroid of every
selected triangle at the editable key. A conservative sphere around the
**original** grip pivot encloses every permitted rigid prop orientation and
clearance. Every actor/other-prop triangle whose box intersects that envelope
contributes its fixed samples; no changing nearest-face subset replaces it.
Full prop samples are also queried against each non-disjoint complete entity,
so containment remains measurable even when an enclosing object's surfaces are
outside the envelope. Declared primitives use the existing analytic triangle
depth bounds; prop plane terms retain the original physical limits.

Complete-entity boxes reject only impossible positive guidance residuals.
Signed queries use batches of 16; exceeding 250,000 owned samples or requiring
an unavailable outward volume rejects guidance instead of truncating it.
Source normals/topology are not repaired. Seven samples per triangle are still
a sampled objective, not complete triangle crossing detection.

The local optimizer uses the pinned SciPy 1.15.3 implementation of
[SLSQP](https://docs.scipy.org/doc/scipy-1.15.3/reference/optimize.minimize-slsqp.html)
with explicit difference/iteration/evaluation limits. Its score uses
[Trimesh signed distances](https://trimesh.org/trimesh.proximity.html), scaled by
0.01 m for optimization. That scale is not a collision tolerance. Optimizer
termination and score improvement never grant acceptance. Every evaluation is
retained; exhausting its budget is reported explicitly. No controls are clipped
into author permissions or rebased onto a corrected scene.

The original, remeasured starting point and four explicit line proposals
(full, half, quarter, eighth of the guidance step) undergo the complete original
pose/contact/geometry checks. Those line values remain cumulative controls
relative to the original source. Every original passing condition and all
source collision metrics are protected; best proposals require componentwise
improvement. Full collision/contact/pose-budget archives are separate from the
guidance score and surface probes.

All **25** focused tests pass locally and on Windows/Ubuntu at `2db6c4a` in
[run 39080086249](https://github.com/DocMorphic/strep/actions/runs/39080086249).
They cover both actors influencing the score, conservative far-entity rejection,
containment without nearby faces, primitives/planes, source limits/locks,
bounded interrupted optimization, actual objective reduction, positive-residual
screening against complete queries, and full export checks of a known generated
repair. Local guard: 24.937 s / 124,383,232 bytes / 42 observations. The earlier
24-test source snapshot is retained. This is source evidence, not real-action or
whole-suite approval.

The real-scene preflight retains 151,732 fixed guidance probes: 101,017 from
14,431 reachable actor A faces, 50,631 from 7,233 actor B faces, and 84 from all
12 prop faces. Both actor meshes still have 36,108 complete faces in final
geometry checks. The other box is provably outside the reachable envelope.
Four preflight evaluations take 0.514–0.724 s each; the guarded run and its
resource replay complete at 4.125 s / 150,642,688 bytes / 22 observations.

The first actual fit performs 51 score evaluations and reaches its explicit
12-iteration limit; the optimizer does **not** report convergence. Energy falls
from 0.154930703026 to 0.004294257171, but all four line proposals create a new
actor B collision. Full-step peak penetration falls to 10.120663 mm while the
crossing count grows to 209 and a previously passing pair fails. No proposal
replaces the retained 27.208295 mm / 113-record candidate. All six complete
original/warm/line checks finish, with a replayed guard of 99.578 s /
260,218,880 bytes / 115 observations.

Independent diagnostic replay reconstructs rejected full-step probe 2 from the
original permissions and exact recorded line formula. All 2,017 sampled pose
budgets, every world-vertex array and all 15 complete three-time mesh pairs
reproduce; the new partner collision is confirmed. Neither the new mesh/pose
backends nor the scene fitter is imported. Existing interpolation/collision
libraries are reused. Guard: 17.484 s / 210,653,184 bytes / 35 observations.

An additional **experimental**, locally retained study adds signed surface-probe
constraints for originally passing edited-prop pairs during optimization.
Actor B's sampled clearance is initially 0.272803 mm; the other prop is outside
the complete reachable envelope. These are guidance constraints, not new author
permissions or substitutes for full collisions. It retains all 128 unique
evaluations at its evaluation limit, then checks eight explicit line fractions
from full to 1/128, as well as the original and remeasured starting point.
The full proposed step still creates an unsampled partner collision and is
rejected, demonstrating that surface-probe constraints alone are insufficient.

Experimental probe 5 (the eighth step) reduces peak sampled penetration to
24.266305 mm, about 10.8% below the retained candidate, with the same 113 crossing
records and no newly failed condition at the three declared times. This is an
internal numerical improvement; the actor A/box collision remains. Full study
guard: 202.078 s / 257,912,832 bytes / 215 observations. A separate replay of
that probe freshly recomputes all 15 three-time pairs, reproduces every world
array and all 2,017 pose-budget samples, and verifies the exact original-relative
line formula and non-worsening incumbent metrics. Source-relative maxima are
0.118851621 m centre displacement and 46.022441 degrees rotation. Replay guard:
15.406 s / 194,666,496 bytes / 33 observations. It uses existing collision
libraries, not an independent geometric algorithm. This experimental guard is
not yet exposed by the public CLI.

The expanded comparison freshly evaluates all 45 actor/prop and prop/prop pairs
at nine times: endpoints and native keys 62 through 68, plus the existing
actor-scene and ground checks. It protects **both** original passing conditions
and the retained candidate's prior repair at key 64. Reference source/incumbent
reports are inherited after rehashing current inputs and verifying observation
receipts; their geometry is not recomputed. The new candidate has no new failed
condition relative to either reference and retains both prior repaired
condition identities (mesh pair and whole sample).

| Nine-time measurement | Retained candidate | Experimental probe 5 |
| --- | ---: | ---: |
| Failed geometry times | 1 | 1 |
| Failed conditions | 2 | 2 |
| Surface crossing records | 113 | 113 |
| Peak vertex penetration | 27.208295 mm | 24.266305 mm |

This comparison passes with strict metric improvement, but both candidates still
fail the collision policy. The new nine-time queries use the producer backend;
they are not an independent nine-time replay. Guard: 44.219 s / 223,707,136 bytes
/ 61 observations. Complete 2,017-time geometry, continuous collision, dynamics,
engine imports, action semantics and human cleanup/review remain open. The
original Studio scene remains selected. Next: make the experimental guard a
supported, tested fitting option before broader scene/action/rig evaluation.

## Supported guarded fitting, version 2

`scripts/native_mesh_prop_scene_fit_v2.py` is the supported guarded entry point.
It reuses the unchanged v1 geometry/guidance code, preserving the exact source
used by earlier studies. It accepts the same original pose permissions, scene
policy and permission-bound cumulative starting controls:

```powershell
python scripts/native_mesh_prop_scene_fit_v2.py pose-permissions.json mesh-policy.json warm-start.json reports/my-guarded-fit --maximum-evaluations 128 --maximum-iterations 20 --backtrack-steps 8
```

The original and starting candidate receive complete policy pose/contact/mesh
checks **before** optimization. A starting candidate qualifies for preservation
only if it satisfies the original pose budgets, all point contacts, original
passing conditions and non-worsening source collision metrics. The fitter then
protects the union of original passes and that qualified candidate's passes
across every measured time. A previously repaired condition cannot be traded
away to repair a different source failure. An unqualified starting proposal
does not become an authoring reference or gain new permissions.

If the edited key is absent from an explicit geometry clock, v2 adds it while
retaining every requested time. The requested/effective clocks and effective
policy are saved separately; the supplied policy file and physical thresholds
remain unchanged. Exceeding the existing sample budget is an error rather than
an excuse to drop times. This prevents an endpoint-only clock from hiding a
known bad edited pose.

At the edited key, passing mesh pairs from the original and qualified starting
candidate supply signed surface-probe constraints. Both query directions and
complete target volumes are used, with conservative box bounds outside the
query region. Provably disjoint entities remain explicitly recorded. These
constraints guide proposals; they do not certify complete triangles, contacts,
other times or continuous motion. Primitives, ground, all mesh pairs and all
declared contacts still receive the full original postchecks.

Optimizer requests and unique measured controls have separate counts. Every
unique evaluation and its guard margins are retained. The budget stop and a
failure to find any guard-feasible proposal are explicit; a fallback is not
labelled feasible. Eight line fractions, from full to 1/128 by default, remain
controls relative to the original source. Frozen keys, geometry and character
motion are unchanged; neither optimizer output nor export success grants
selection or release approval.

All **27** focused tests pass locally and on Windows/Ubuntu at `3d501bc` in
[run 39081465684](https://github.com/DocMorphic/strep/actions/runs/39081465684).
They exercise conservative signed bounds, invalid/duplicate pair selection,
guarded versus colliding poses, cached evaluation limits, an explicit infeasible
fallback, actual objective reduction, complete generated-fixture export checks,
preserving qualified repairs, rejection of an injected repair-breaking proposal,
and adding a missing edited key without dropping supplied times. Local guard:
26.719 s / 136,466,432 bytes / 44 observations. These are source/fixture checks,
not whole-system, real-action or human quality acceptance.

The supported v2 real-scene run starts from the independently checked
24.266305 mm candidate, bound to the **original** permissions. Its policy covers
all nine nearby times from the outset. Both earlier repaired conditions at key
64 are protected: 95 original passing identities become a 97-identity protected
union. All ten candidates receive complete nine-time policy checks, including
450 actor/prop and prop/prop pair evaluations in total, plus actor-scene and
ground conditions. All declared contacts and 2,017 sampled pose-budget times are
checked for each candidate.

The search retains 128 unique measured controls from 278 requests and stops at
its explicit evaluation limit, without claiming convergence. A full step with
16.099732 mm peak penetration introduces a new partner collision and is rejected.
Several smaller steps preserve all prior passing conditions but have more
crossing records than the starting candidate, so they do not replace it.
Probe 7, a 1/32 step, improves every required comparison without a new failure:

| Nine-time measurement | Starting candidate | Supported v2 probe 7 |
| --- | ---: | ---: |
| Failed geometry times | 1 | 1 |
| Failed conditions | 2 | 2 |
| Surface crossing records | 113 | 113 |
| Peak vertex penetration | 24.266305 mm | 23.627057 mm |
| Earlier repaired identities retained | 2 | 2 |

The approximately 2.6% reduction is numerical progress, not a collision-free
grasp. The producer completes under its unchanged guard at 486.422 s /
401,629,184 bytes / 492 observations; the resource trace independently replays.
Character clips, original prop source, frozen endpoints, author limits and
physical thresholds remain unchanged. Nothing is promoted into Studio.

Two separate independent replays reconstruct the complete starting reference
and the selected v2 proposal. Each freshly recomputes all 45 complete mesh pairs
at all nine declared times and reproduces every world-vertex array and all
2,017 pose-budget samples. The second inherits the first's verified reference
bindings, reconstructs the original/qualified-initial condition union and checks
exact original-relative line provenance and componentwise improvement. Neither
imports any new mesh/pose/fitting backend; existing collision/interpolation
libraries are reused, so these remain independent composition/transport replays,
not separate geometric algorithms. Reference guard: 42.016 s / 299,122,688 bytes
/ 59 observations; selected-proposal guard: 41.062 s / 303,878,144 bytes /
58 observations.

This closes the missing independent nine-time replay for the starting reference
as well as the current proposal. It does not cover complete 2,017-time geometry,
continuous collision, self-collision, dynamics, action correctness, engine
imports or human review/cleanup. The actor A/box collision still fails, and the
full-project release criteria remain open.

## Exact crossing diagnosis and a fixed-scene obstruction

`scripts/native_mesh_prop_crossing_witness.py` connects completed fitter probes
to the existing `exact_triangle_crossing_witness.py` rational construction. The
plane/intersection-interval approach is described in
[Möller's original paper](https://fileadmin.cs.lth.se/cs/Personal/Tomas_Akenine-Moller/pubs/tritri.pdf);
the repository's rational implementation is independent code, not copied C.

```powershell
python scripts/native_mesh_prop_crossing_witness.py pose-permissions.json reports/my-guarded-fit/fit/probe-007 reports/my-crossing-witnesses
```

The collector verifies the original producer permission/input hashes, archived
implementation, completed history/decision, exact cumulative scene manifest,
complete geometry condition populations and every ordered policy time. It
reconstructs all complete actor/prop world-vertex arrays from the source and
checks them byte for byte against the transport archive before using triangle
IDs. Every selected-prop surface record is retained; exceeding its explicit
budget rejects collection instead of truncating it. Each record's floating
classification is replayed, then the represented binary-float triangles receive
an exact rational interior witness when possible. Boundary, coplanar and other
unproved outcomes stay unresolved. Float barycentric approximations are exported
for later fitting, with their reconstruction error reported separately.

All **24** focused tests pass locally and on Windows/Ubuntu at `66ec672` in
[run 39082774483](https://github.com/DocMorphic/strep/actions/runs/39082774483).
They cover strict rational witnesses, unresolved outcomes, altered triangle IDs
and classifications, complete generated producers, original permission epochs,
missing pairs/times, changed source snapshots, no record truncation, and altered
world arrays even when given a new internally valid archive receipt. Local guard:
35.922 s / 123,240,448 bytes / 53 observations. These are source/fixture tests.

For the retained v2 probe 7, **all 113 recorded actor A/box crossings receive
exact strict-interior proofs**, with no unresolved record. All nine-time world
arrays reproduce. This proves intersections of the represented triangles after
skinning/transform rounding; it does not certify earlier arithmetic, continuous
motion or whole-scene clearance. Collection guard: 3.094 s / 152,588,288 bytes /
21 observations. No correction is applied.

A local diagnostic uses all 113 pairs on both sides (226 moving-plane rows), two
finite-difference steps and four angular trust boxes. Its eight affine solves
find no common positive separating margin. Those numerical local models alone
are **not** a nonlinear or global infeasibility proof.

A separate, locally retained obstruction study then finds a stronger geometric
witness for this particular locked scene:

- The source prop is verified to be an eight-corner, twelve-triangle box whose
  triangles exactly cover its six faces. Its selected face grip admits an inward
  half-ball of radius 99.000004 mm, independent of the box's rigid orientation.
- Four fixed source vertices, three from actor A and one from actor B, surround
  the required contact point. Exact rational barycentric and face-plane checks
  verify that their tetrahedron contains a ball of radius at least 0.173408 mm
  centred at that point. The original grip position tolerance is 0.001 mm.
- Each of those vertices is close enough to the grip that any box orientation
  contains at least one of them strictly inside its inward half-ball. Its mesh
  component also contains a vertex outside every permitted rigid box placement.
  Verified source edge paths connect each inside candidate to its outside
  witness, so a character surface must intersect the box boundary.

An independent verifier reconstructs the source inputs and checks exact box
face coverage, positive tetrahedron weights, **squared** plane-distance bounds,
near-vertex bounds and four explicit mesh paths. It uses no hull, triangulation
or LP construction solver. The builder uses Qhull only to find candidate source
vertices; acceptance depends on exact rational checks. Builder guard: 2.063 s /
123,084,800 bytes / 20 observations. Independent verifier: 2.063 s /
151,367,680 bytes / 20 observations.

This is a sufficient obstruction for the **fixed represented geometry and ideal
rigid-grip model at the mandatory contact time**, including arbitrary rigid
orientations and grip displacement within the original positional tolerance.
It does not rule out solutions that edit a character pose or change authored
grip/asset constraints, and it does not certify earlier skinning or all floating
rigid-transform errors. The source decoder is shared; rational geometry and
connectivity checks are independently composed. This diagnostic is not yet an
automatic fitter preflight.

Further box-only rotation tuning on this exact locked fixture cannot produce a
collision-free result under that model. Keep the original constraints and failed
outputs; do not enlarge tolerances to call it solved. Next work is an explicit
obstruction preflight and body-aware scene fitting under the original body/prop
permissions, alongside broader action/object/rig evaluation. This is a limitation
of one constrained fixture, not evidence that the full animation objective is
unachievable. The full-project goal and all release requirements remain active.

## Supported sufficient preflight for fixed box/grip scenes

Run the standalone preflight before attempting box-only fitting:

```powershell
python scripts/native_mesh_prop_obstruction_preflight.py pose-permissions.json reports/my-box-preflight
```

It uses the existing permission-bound original scene, prop grip and edited key.
The key must lie inside the authored required contact interval. Character world
geometry is fixed for this diagnostic; its conclusion never blocks a domain
that permits character edits. Neither existing fitter implementation changes.

`fixed_grip_box_obstruction.py` recognizes exact axis-box corner/face coverage
and strictly interior face grips on all six faces. Floating Delaunay proposes
tetrahedra from original actor vertices. Acceptance requires exact positive
barycentric coordinates, a contained ball larger than the original grip
tolerance, strict half-ball reach, and explicit original mesh-edge paths to
vertices outside every ideal rigid box placement. The direct verifier uses
squared rational face distances and validates paths without calling Delaunay.
Construction and verification share elementary rational helpers and source
decoders; this is not a separate geometry library or arithmetic pipeline.

The default search permits 10,000 nearby candidates and 128 tetrahedron checks;
explicit caps cannot exceed 10,000 and 512. Exceeding the vertex budget returns
unknown without truncation. Unsupported boxes/grips, keys outside the contact
interval, unavailable triangulation and absent verified witnesses also return
**unknown**, never clearance or feasibility. The search omits vertices within
twice the grip tolerance of the contact centre: a vertex exactly at that centre
makes incident discovery tetrahedra have zero barycentric weights. This is only
candidate screening; exact acceptance conditions remain unchanged.

The initial actual-scene attempt retained an unknown result after 128 checks
because that exact contact vertex poisoned discovery. Its raw output is retained.
The corrected search sees 3,105 candidate vertices and proves the same previously
independently checked four-vertex obstruction on its first tetrahedron. The
contained radius remains 0.173408 mm against the original 0.001 mm grip tolerance.
Source bindings and author permissions remain unchanged. Guard: 3.094 s /
126,812,160 bytes / 21 observations; resource replay matches archived bindings.

All **37** focused cases pass locally: exact construction/direct verification,
all six grip faces, altered weights/ball/source references/geometry/connectivity,
invalid box coverage/winding, missing outside paths, discovery budgets and
unknown outcomes, exact-contact-vertex screening, and source-bound CLI backend
fixtures. Local guard: 17.453 s / 122,183,680 bytes / 35 observations. These are
source fixtures plus the separately recorded actual-scene diagnostic, not
animation quality, movable-body feasibility, continuous/physics or engine and
human approval. Next correction work must include permitted body motion rather
than repeat box-only fitting on this locked scene.

The same **37** cases also pass on Windows (2.47 s) and Ubuntu (1.14 s) at
`74acc70` in [run 39084446325](https://github.com/DocMorphic/strep/actions/runs/39084446325).

## Coupled moving-grip pose map

`native_coupled_mesh_prop_pose.CoupledGripPose` maps a supplied, caller-authorized
moving hand point to an edited prop pose. The prop's original permission file,
source pose, angle/centre-translation caps and authored clearance direction and
amount remain fixed. It does not replace the original source with the current
character or prop candidate. A moved target that exceeds the original centre
translation cap is rejected in the report, never clipped or rebased.

For target `c`, source-local grip `g`, authored direction `d`, clearance amount
`h` and source-relative rotation `R`, the centre is `c + R*(h*d - g)`. Supplied
body derivatives occupy every original body column, followed by the original
three rotation controls and one clearance control. The rotation/point chain is
analytic and uses the existing SO(3) right Jacobian. Complete point and column
budgets reject before output allocation instead of truncating. The exact source
zero pose keeps its original translation/quaternion bytes.

```python
mapping = CoupledGripPose(original_permission_bound_edit)
vertices, jacobian, pose = mapping.points(
    prop_controls, authorized_hand_world_point, complete_prop_local_vertices,
    target_jacobian=complete_hand_body_jacobian,
)
```

The map deliberately reports body/target permissions, saved-motion checks and
full sampled pose bounds as unverified. Those are caller-owned gates; matching
a hand point or returning an analytic Jacobian does not approve a body edit,
grasp, scene or animation. Existing independent prop fitters remain unchanged.

All **21** focused tests pass locally and on Windows/Ubuntu at `88187f8` in
[run 39084988054](https://github.com/DocMorphic/strep/actions/runs/39084988054).
They compare complete body/rotation/clearance pose and point derivatives against
independent finite differences, test the final supported body column and duplicate
points, source-zero bytes, source hash changes, unchanged original caps, locked
prop components and incomplete/invalid/budget inputs. Local guard: 27.687 s /
121,131,008 bytes / 45 observations. Windows: 10.68 s; Ubuntu: 1.29 s.

A separately retained actual-rig experiment composes all **135** original-relative
local character controls with the four prop controls. Every one of the 113 exact
crossing pairs supplies all three opposite-triangle vertices: 339 moving-plane
guidance rows. Two independent perturbation directions in the 138 variable
proposal columns check the composed 139-column map; clearance stays fixed in
these actual-rig comparisons and is checked separately in source fixtures.
Maximum point differences are 3.10e-10 m and 3.32e-10 m, and scaled plane-row
differences are below 1.90e-8. Original character nodes, caps, cumulative native
balls, source clocks and frozen keys remain unchanged. The supplied world/skin
map keeps all native skin influences; a rigid wrist substitute is not used.

The first solve is retained as rejected: its explicitly fixed clearance delta
drifts outside the exact zero-width proposal box by 2.16e-16. No tolerance is
enlarged and no output is clipped. A second study eliminates that declared fixed
search value algebraically, solves the other 138 columns and restores its exact
zero. This is a local search restriction, not a new permanent author lock. All
5,400 native character norm constraints, the prop rotation and original centre
translation norm constraints, and all 199 key-pose rows remain represented.
The source implementations of the existing conic solver and prop fitters stay
unchanged. First study guard: 50.218 s / 231,006,208 bytes / 67 observations.

The second proposal passes native and stored-time pose/pair checks, then
completes **all 944,562 existing raw/saved character-motion scalars**. It is still
rejected. In both raw and saved modes, five previously failing rows pass but
one previously repaired row fails again: **20295**, an actor A displacement
condition. Its raw margin changes from +5.7822e-5 to -0.00169288. Total world
failures decrease from 6,093 to 6,089, yet peak normalized error increases from
44.323721 to 44.802310 and squared error also increases. A lower count or local
collision objective cannot buy a new displacement failure or lose a repair.

A separate read-only audit rehashes trial inputs and compares complete archived
scalar populations, identifying the same failed/repaired row IDs in both modes.
All 177,328 other motion scalars pass. It performs no new geometry or motion
sampling. Trial guard: 146.547 s / 274,694,144 bytes / 161 observations; rejection
audit: 3.094 s / 50,151,424 bytes / 21 observations. Resource replays match.

No coupled candidate is promoted, no whole-scene collision result is claimed,
and no release or human score changes. The next solver stage needs refreshed
full-timeline passing displacement/rate guards (including all 29 prior repair
witnesses) and motion-error guidance alongside the object-plane rows. A sampled
key-pose guard is insufficient for between-key motion. The full-project goal,
broader actions/objects/rigs and engine/human validation remain open.

## Experimental full-timeline guard integration

A fresh local world model is built at the last independently replayed body
candidate, not at the rejected coupled proposal. All **383,617** registered raw
world values match that candidate byte for byte. All 319 groups retain their
135 body columns; two complete directional comparisons have maximum differences
2.204e-7 and 1.247e-7 with zero failed numerical comparisons. One uncached
perturbation reproduces every value and group exactly. These derivative checks
are numerical evidence, not new physical tolerances. Guard: 276.531 s /
285,593,600 bytes / 288 observations.

The refreshed guard population includes all 29 prior repair witnesses, including
displacement row 20295, and every temporally affected passing displacement/rate
row. Selection uses the union of passing raw and saved modes; a row's proposal
reserve uses the smaller margin among its passing modes. The current incumbent's
pass masks happen to be identical. Raw derivatives guide the exported mode;
exported-motion acceptance still requires the complete independent value gates.
There are **6,425** guards across 7,238 temporally affected scalar conditions.
Contact and original pose/pair conditions proven independent of this local basis
stay represented with exact zero derivatives. No small nonzero temporal weight
is dropped. Both guard-direction checks pass; maximum differences are 3.649e-7
and 2.245e-7. Guard: 46.188 s / 339,689,472 bytes / 63 observations.

The resulting experimental solve combines 339 object-plane rows with 1,106
complete motion-guidance groups, 7,722 extra guards and 5,402 source-bound body/
prop norm constraints in its local model. The fixed clearance delta is substituted exactly as
before. Original source epochs, caps, clocks and frozen keys stay unchanged.

Its full-step character correction completes all **944,562** raw/saved motion
checks with no newly failing row and no loss of any prior repair. Six world rows
are repaired in both modes: failures fall from 6,093 to 6,087. Raw peak normalized
error falls from 44.323721 to 43.887751 and squared error from 56,878.826 to
56,818.723; exported results agree in direction. This is a numerical improvement
within an already failing source-budget study, not a realism or release score.

The combined scene is nevertheless rejected. All 2,017 sampled prop pose bounds
and declared contacts pass, but fresh full geometry at all nine policy times
finds a new actor B/box collision. Peak penetration drops from 23.627 mm to
18.998 mm while surface records increase from 113 to 162 and failed conditions
from two to three. A smaller peak cannot buy the new failed condition. Trial
guard: 176.375 s / 456,933,376 bytes / 190 observations.

A separate prop-only line search keeps that motion-qualified body byte-identical
and tests fractions 1/2, 1/4, 1/8, 1/16 and zero from the old original-relative
prop controls toward the failed direction. Every candidate receives all nine
geometry times, contacts and sampled original prop bounds. The first three keep
the new partner failure; the last two preserve all 97 previously passing geometry
conditions but still have 115 surface records versus 113. All five remain
rejected under the declared componentwise comparison. Body motion checks are
inherited by immutable file identity, not freshly sampled in this search. Guard:
228.312 s / 372,019,200 bytes / 241 observations. All resource replays match.

A further bounded study scales the **entire** original coupled direction by
1/8, 1/16 and 1/32, including both character and prop controls. It does not rerun
the optimizer or use a corrected clip as a new authoring epoch. Each step
receives all 944,562 raw/saved motion checks, the 29 repair checks, all nine
geometry times, contacts and original sampled prop bounds. All three preserve
the prior passing motion rows and improve peak/squared motion error. None passes
the geometry comparison:

| Joint step | Surface records | Peak penetration | New failed geometry conditions |
| --- | ---: | ---: | ---: |
| Previous numerical reference | 113 | 23.627 mm | — |
| 1/8 | 123 | 23.035 mm | 1, actor B/box |
| 1/16 | 115 | 23.330 mm | 0 |
| 1/32 | 115 | 23.479 mm | 0 |

The last two preserve all 97 previously passing geometry identities but retain
two additional crossings. Keep them as tradeoff evidence rather than changing
the declared metric rule. All three raw/exported motion populations complete;
there is no successful combined-scene selection. Guard: 494.657 s /
522,768,384 bytes / 495 observations, below the unchanged 512 MiB process cap.
The original Studio selection and release declarations remain unchanged.

This separates two demonstrated needs: full-timeline motion guards prevent the
earlier displacement regression, while the next coupled scene guide must also
represent the second character and newly discovered surface pairs. Repeating
smaller steps of the same local direction is not a substitute for that missing
scene information. Existing source-rate failures, other geometry policy times,
self/continuous/dynamic checks, engine validation and human review remain open.

Independent export replay confirms the **motion-only** full-step result without
importing the local basis/context helper. It reconstructs the cumulative native65
insertion from the already verified parent under the original authoring domain,
freshly reproduces all 383,617 saved world values byte for byte, independently
checks 5,400 raw and 5,400 saved native rotation balls, and verifies all 177,328
other archived motion scalars. Static assets, uncontrolled channels, clocks and
original frozen keys are unchanged. Both modes repair the same six rows:
56647, 56716, 93134, 93211, 93288 and 276878, with no new failed row. Guard:
47.203 s / 194,859,008 bytes / 64 observations.

Only one pose changes within the previously verified 232-pose body-geometry
population. A separate body-only replay checks its complete 36,108-face meshes
per character, partner intersections, all-vertex floor depths and original
rotation/joint-displacement limits afresh. The other 231 poses inherit their
previous results only through exact full-hierarchy byte identity and the same
physical geometry policy. This closes a 232-sample/all-120-native-key body
composite with zero geometry or pose-budget failures. Guard: 60.594 s /
190,275,584 bytes / 77 observations. All bindings and resource replays match.

The body result still has 6,087 source-rate failures and 1,785 other geometry
policy times unverified. It does not approve mesh-prop interactions, self or
continuous collision, dynamics, semantics, engine import or human cleanup time.
Future fitting from this body must protect the union of the 29 previous repairs
and these six new repairs while retaining the original authoring epoch. The
combined scene and all rejected steps remain separate; no Studio selection or
release capability is promoted.

## Complete triangle-pair projection rows

`native_triangle_pair_projection.py` provides a general coupled guidance kernel
for supplied triangle pairs, independent of an action label or character rig.
`choose_directions(left, right)` proposes unit directions using projection
intervals, face/cross-edge axes and in-plane edge axes for coplanar triangles.
The projection method is described in
[Eberly's primary note](https://www.geometrictools.com/Documentation/MethodOfSeparatingAxes.pdf).
The implementation is independent code, not copied pseudocode.

Freeze those directions, then call `projection_rows(left, right, directions,
left_jacobian=..., right_jacobian=...)`. Each pair retains all **nine** signed
vertex-combination rows, in pair/left-vertex/right-vertex order. Both sides'
complete derivative columns participate. A fixed side needs an explicit zero
Jacobian; a missing side is rejected. There is no entropy correction that would
turn a tiny positive source gap into a negative smooth constraint. Positive
projections imply separation in real arithmetic only; floating input/rounding,
other pairs, mesh containment and continuous motion still need separate checks.
Negative projection gaps do not prove intersection or general infeasibility.

Complete pairs, points and derivative columns must fit the declared 64 MiB
budgets. Evaluation projects each side before forming the nine differences,
avoiding an additional pair/left/right/xyz/column workspace. No pair or vertex is
discarded to fit the budget. Source hashes, topology IDs, clocks and edit
permissions remain caller-owned.

All **27** focused source tests pass locally and on Windows/Ubuntu at `193701a`
in [run 39087765112](https://github.com/DocMorphic/strep/actions/runs/39087765112).
They cover all nine rows, duplicate points, parallel/coplanar separation,
crossing/touching outcomes, complete analytic derivatives against independent
perturbations, shared-motion cancellation, the final supported column,
transform/side-reversal consistency and invalid/incomplete/budget inputs. Local
guard: 25.672 s / 82,333,696 bytes / 43 observations. Windows: 0.54 s; Ubuntu:
0.37 s. These are source fixtures, not motion or scene approval.

### Complete pair guide trial (2026-10-18)

The next experimental guide retains all 1,245 crossing occurrences in ten
named prior geometry reports as **267 distinct pairs: 226 for actor A and 41
for actor B**. It produces 2,403 projection rows without dropping duplicate
vertex combinations. The unchanged original author epoch, native clocks,
frozen keys, 5400 body norm bounds and prop permissions remain in force.

A fresh model reproduces all 383,617 incumbent world conditions byte for byte.
Two independent directions check its derivatives. Fresh timeline guards cover
6,431 passing conditions, including **35 previous repairs**; every one of the
7,262 affected/required derivative rows is checked. A total squared-error
directional guard is verified against complete-world finite differences.
The coupled 139-column map passes two point/projection perturbation checks.
The solve retains all 41 second-character pairs as projection guards.

Four declared joint steps (1, 1/2, 1/4, 1/8) each complete all **944,562**
raw/exported motion checks, with zero newly failing world rows and no lost
repair. This means nonregression, not that all conditions pass: pre-existing
source-rate failures remain. The full step lowers raw normalized peak error
43.887751 to 43.473433 and squared error 56,818.723 to 56,141.241.

Each step also receives the full nine-time mesh query, all 2,017 sampled prop
permission checks and declared contact checks. All 97 previously passing
geometry conditions remain passing, including the second character. However,
**every step retains 115 crossing records against the previous best 113**;
none is selected. Full-step maximum penetration is 23.262 mm versus 23.627 mm.
Better depth or motion error cannot waive the crossing-count criterion.
The trial finishes in 584.703 s, peaks at 519,151,616 bytes under the unchanged
512 MiB cap, and its resource replay matches all 588 observations.

The ledger covers its named prior reports, not unseen pairs, and fixed source
directions need full nonlinear mesh postchecks. Continuous contact, self
collision, dynamics, broader rigs/actions/objects, engine behavior and human
ratings remain separate open release requirements. Original Studio selection
and all release declarations remain unchanged.

The subsequent representation check identifies a shared actor vertex, 11639,
in four recurring actor-A/box-face-0 pairs; the authored grip uses vertex
17039. Full-mesh and support-skin paths agree within 9e-16 m. Raw versus saved
full-mesh positions differ by less than 2.8e-8 m. The source projected gap is
already -1.34521e-7 m and the original proposal still predicts a negative gap.
Thus these four crossings cannot be attributed solely to export rounding.
The corrected diagnostic finishes in 22.562 s / 248,016,896 bytes; its earlier
incorrect six-pair precondition stops without conclusions and is retained.

The expanded ledger includes the four completed proposals: 14 named reports,
1,705 occurrences, 269 pairs (A 228 / B 41). A fresh bounded subproblem adds
all 36 vertex-combination rows of the four recurring pairs as hard repair
targets. Its requested 1 micrometre extra directional separation is a stronger
**proposal target**, not a changed geometry/contact tolerance. With all 35
motion repairs, 6,431 passing motion guards, 154 protected pairs and original
norm bounds retained, the solver returns `PrimalInfeasible`; no direction or
candidate is accepted. The 48.219 s / 317,038,592-byte run and 65-observation
resource replay finish normally. This status does not establish infeasibility
of nonlinear motion, a larger permitted search region or the action itself.

A repair-focused follow-up targets those 36 rows in its objective, retaining
the same passing-motion/35-repair guards, all 154 protected triangle pairs,
original norm bounds and total-world squared-error directional cut. All 2,421
pair derivatives are still observed, but 111 other known pairs with overlapping
source projections are outside this focused objective. Full raw/saved peak,
sum-squared and failure-count gates remain unchanged. The solver returns a
usable step and all 944,562 motion checks complete without regression. Full
nine-time geometry still gives 115 records, all 97 prior passes preserved;
the candidate is rejected. The 207.219 s / 447,164,416-byte run has 220 matched
resource observations. This limited step motivates inspecting proposal
constraint conflicts rather than repeating smaller line steps or relaxing
physical tolerances.

The full labeled solver witness identifies actor-A triangles 28752 and 28753
against prop face 0 as the strongest conflicting proposal guards. The first
labeling worker stops after the completed solve because 106 grouped world
descriptors were mistaken for 6,431 scalar labels. A fresh recovery expands
every group, verifies the original model/proposal byte identities and archives
all 8,053 extra-row labels without rerunning the solver. Its floating dual is a
diagnostic, not an exact infeasibility certificate.

An independent row comparison then finds **exactly opposite stored normals
and all 139 stored Jacobian columns** between each of those two guard rows
and the repair row for triangle 28404. Their margin-sum identity differs by
1.28e-21. Keeping half of either positive guard margin limits the repair's
predicted geometric gap to **at most -72.2604 nm**. Thus these fixed source
directions prohibit even clearing that repair in this local model. This is a
conflict between proposal restrictions, not proof of a physical impossibility.
Recovery: 15.391 s / 85,737,472 bytes / 33 resource observations. Row comparison:
9.250 s / 55,341,056 bytes / 27 observations. Both resource audits match.

An explicit direction branch can test alternatives for those two pairs while
retaining their complete 18 value/derivative rows in the full objective. It
must still retain all original motion, author, prop and full-mesh postchecks,
including the 97 passing geometry identities and crossing-count/depth limits.
Changing a conflicting projection restriction cannot itself approve a clip.

The explicit two-direction branch completes the same full 3,527-row objective
with all 269 pairs, 2,421 projection rows, 6,431 motion guards/35 repairs, 5,402
norm cones and 36 hard repair targets. It completes all 944,562 raw/saved motion
checks with no new failed rows or lost repairs. Raw peak decreases 43.887751
to 43.533073 and squared error 56,818.723 to 56,297.638. All nine scene times,
2,017 prop-bound samples, contacts and 97 previously passing geometry identities
are checked. Crossing count returns to **113**, equal to the previous best;
maximum depth decreases 23.627057 to **23.531278 mm**. Therefore the unchanged
componentwise numerical comparison accepts this partial improvement. This is
**not collision-free motion**: the two failing geometry conditions/one failing
sample remain. Original Studio selection, quality and release flags stay
unchanged. Trial: 191.578 s / 437,751,808 bytes / 205 matched resource
observations. Independent export/body/scene replay is required before treating
it as a verified fitting incumbent.

Those independent replays now complete under the same resource/source guards:

| Replay | Fresh verification | Time / peak RSS / observations |
| --- | --- | --- |
| Body export | All 383,617 saved world rows byte-identical; 5,400 raw and 5,400 saved native bounds; 177,328 other archived scalars passing; original cumulative source/caps/static content/frozen keys/clocks retained | 37.969 s / 195,616,768 bytes / 55 |
| Changed body pose | One fresh complete mesh/partner/all-vertex-floor query; 231 exact full-hierarchy pose identities inherit the prior policy, closing 232 samples and all 120 native keys with zero body failures | 35.859 s / 187,277,312 bytes / 53 |
| Combined scene | All 45 mesh-pair queries and full world-array bytes at nine times, 97 prior geometry passes, all 2,017 prop bounds and contacts; no new mesh-prop/coupled backends imported | 83.047 s / 223,850,496 bytes / 99 |

Both raw and saved motion audits identify exactly five additional repaired
world rows: 93688, 93691, 93696, 240146 and 276877. Existing failures decrease
6,087 to **6,082**, with no new failing row. Together with the earlier 35,
**40 repair witnesses** must be protected in future warm fits. The original
actor/quaternion source and permission epoch remain authoritative. Existing
geometry/skinning/collision libraries are shared by the replays; these are
independent composition and artifact checks, not independent algorithms.

The new fitting reference remains a **partial experimental improvement**:
113 crossings, two failing scene conditions and one failing scene sample,
6,082 source-rate failures, 1,785 unclosed body geometry times, self collision,
continuous motion, dynamics, semantics, broader rigs/actions/objects, engines
and human cleanup evidence remain open. It does not replace the Studio's
selected clip or approve any release capability. The next fit must refresh
the complete timeline/scene guide around this reference, include discovered
pairs and preserve all 40 repairs without relocking temporary search anchors.

### Reusable projection-guard conflict check

`scripts/native_projection_guard_conflicts.py` exposes
`find_equal_row_conflicts(guard_matrix, guard_upper, repair_matrix, repair_lower)`.
It compares the supplied inequalities `A x <= upper` and `B x >= lower`.
Exactly equal stored coefficient rows with `lower > upper` have contradictory
bounds in that linear proposal. Every supplied column and duplicate row
identity participates. Signed zero compares equal; near-equal or proportional
rows are outside this detector. An empty result says nothing about general
feasibility. The helper reports conflicts; it never removes guards or changes
author/contact/geometry permissions.

Inputs are explicit finite real NumPy arrays with coefficients/bounds within
1e12 in magnitude. Complete row/column, comparison,
output and workspace admission occurs before the owned copies and comparison
blocks. A budget failure rejects the call instead of truncating rows, columns
or matching identities. Default limits are 1,048,576 row-pair comparisons,
16,384 conflicts and 64 MiB estimated array workspace, with up to 768 columns.
The process/interpreter and caller-owned assets need separate resource guards.
Results
retain row IDs in repair-row/guard-row order and positive bound gaps. Caller
labels, source binding and all nonlinear raw/exported/mesh postchecks remain
necessary; this is not a scene-infeasibility certificate.

All **34** focused fixtures pass locally, covering duplicate and empty
populations, strict/touching/one-ULP bounds, signed zeros, mixed numeric types,
strided immutable inputs, all 768 columns, exact scaling/permutation,
near-equal/proportional exclusions, invalid values and complete budget
rejections. Local guard: 16.421 s / 79,343,616 bytes / 34 observations.
The supplied-guide replay checks **all 49,896 combinations** of 1,386 guards
and 36 repair rows in all 139 columns. Its **24 contradictory row pairs**
identify exactly actor-A triangles 28752 and 28753 against prop face 0, matching
the earlier independent diagnosis. All identities are archived; no character
candidate or automatic guard removal is performed. Replay: 9.265 s /
57,835,520 bytes / 27 matched resource observations. These are source and
linear-guide checks, not animation-quality or release approval.

### Moving-frame point map

`scripts/native_inverse_rigid_frame.py` exposes `inverse_rigid_frame_points`.
For a rotation mapping local coordinates into world coordinates, it computes
row-vector local points as `(world - position) @ rotation`. Its full Jacobian
includes derivatives of the points, frame translation and frame rotation;
fixed sides need explicit zero arrays. A non-rigid/reflected frame or
inconsistent rotation derivative is rejected rather than repaired. All supplied
points and columns remain; complete array budgets reject without truncation.
Caller assets and interpreter/process memory need their own resource guard.

This supports evaluating triangle projection guidance in a prop frame while
the prop rotates. It changes the proposal's coordinate formulation and
derivatives, not physical edit permissions or collision/contact tolerances.
The imported prop geometry remains fixed in that frame. A full scene trial
must still verify the supplied rig motion, saved files, all required clocks,
contacts and meshes; a coordinate-map fixture cannot approve an animation.

All **31** focused fixtures pass locally: independent homogeneous inversion
and rigid finite perturbations in every supplied column, common rigid motion
cancellation, the 768th column, global rigid re-expression, projection
composition, immutable strided inputs and incomplete/invalid/non-rigid/budget
rejection. Local guard: 16.422 s / 104,902,656 bytes / 34 observations. The
coordinate convention is documented in the primary-source ledger; the array
implementation and product-rule composition are independent code.

Both new helpers now pass their focused Windows/Ubuntu workflows at the tested
source revisions: guard conflicts **34 per OS** at `250b431`
([run 39090873333](https://github.com/DocMorphic/strep/actions/runs/39090873333)),
and inverse rigid frames **31 per OS** at `63d860a`
([run 39091231807](https://github.com/DocMorphic/strep/actions/runs/39091231807)).
Windows/Ubuntu durations are 0.36/0.28 s and 0.56/0.42 s respectively. These
focused source passes do not imply a complete repository or release pass.

### Refreshed guide around the verified partial incumbent

The new world model reconstructs all 383,617 current conditions byte for byte,
checks two full directions in its 319-group/135-column representation, and
repeats one perturbation without the invariant-pose cache. The original source
epoch, cumulative controls, clocks and frozen keys remain authoritative. Guard:
271.516 s / 288,546,816 bytes / 283 matched observations.

The refreshed timeline model verifies all 7,262 affected/required derivative
rows, retains **6,436 passing guards and all 40 repairs**, and checks its total
world squared-error gradient against complete-world perturbations. Invariant
original contacts, pose/pair observations and all native coefficient bounds
remain represented. Guard: 50.265 s / 341,393,408 bytes / 67 observations.

The named geometry ledger now covers 16 reports/1,933 crossing occurrences,
still 269 unique pairs (A 228 / B 41). The prop-local composition evaluates
all 2,421 vertex-combination rows and all 139 columns. Two actual directions
check 627 world and 627 local scalar point rows plus every projection row;
the fixed source clearance is held constant in those perturbations. Maximum
point error is 3.021e-10 m and scaled projection error 1.702e-8. Complete prop
self-frame reconstruction agrees with local geometry within 2.776e-17 m, and
its full 139-column derivative cancels within 2.221e-16. Projection values
agree with transported world directions within 1.066e-14 scaled. Guard:
46.156 s / 227,012,608 bytes / 63 observations. This qualifies the coordinate
guide, not a saved clip, full scene or animation quality.

The complete prop-local trial uses all 269 pairs/2,421 projection rows in its
3,527-row objective, 6,436 passing motion guards, 40 repaired witnesses, 156
protected triangle pairs and 5,402 norm cones. Every declared step completes
all 944,562 raw/saved motion checks, preserves every repair and passing row,
improves peak/total motion error, and repairs row 56719 in both modes. Every
step also completes nine-time mesh queries, all 2,017 sampled prop bounds and
contacts, retaining the 97 previously passing geometry identities.

However, **all four candidates are rejected** against the current incumbent's
113 crossing records and 23.531278-mm maximum depth:

| Joint fraction | Raw normalized motion peak | Crossing records | Maximum depth (mm) |
| --- | ---: | ---: | ---: |
| 1 | 43.033387 | 115 | 23.626764 |
| 1/2 | 43.283110 | 115 | 23.578343 |
| 1/4 | 43.408062 | 115 | 23.554635 |
| 1/8 | 43.470560 | 115 | 23.542923 |

The underlying run fails **only during final report writing**, referencing
undefined inherited-direction metadata after all four checkpoints and source
checks. That raw failure remains unchanged: 584.547 s / 522,432,512 bytes /
589 observations, under the unchanged 512 MiB cap. A fresh recovery rechecks
every archived scalar, repair witness, geometry condition/metric table,
observation receipt and source binding without rerunning the solver, motion
or geometry. Recovery: 24.641 s / 119,574,528 bytes / 42 observations. It
qualifies the completed rejected checkpoints; it does not relabel the original
failed run as successful. No new incumbent is selected, row 56719 is not added
to the selected 40-repair reference, and the conditional independent candidate
export replays are not run.

### Interior-depth coverage diagnosis

A fresh depth study evaluates **all 18,056 actor-A vertices** against the
complete 12-face represented convex box for the incumbent and all four saved
candidates: **90,280 vertex queries**. It verifies saved world-array identity,
convex/closed-wound preconditions, and every triangle signed distance against
independent facet-slack depth. Values agree within 2.568e-16 m; all depth and
missing-vertex ID arrays are archived. Guard: 11.266 s / 132,612,096 bytes /
29 matched observations. The original 5-mm penetration tolerance is unchanged.

The crossing-derived guide directly observes only **177 actor-A vertices**.
In the incumbent, 373 vertices exceed the existing penetration limit, of which
**324 are outside that direct point population**. The deepest vertex, **12006**
(`0/0/12006`), is absent from that population in all five cases. Trial counts
are 373–375 vertices over tolerance, with 324–325 outside the direct guide.
The full-mesh acceptance check correctly catches these failures; successful
coordinate derivatives cannot compensate for missing metric observations.

The next guide must add complete streamed interior-depth observations and
gradients while preserving the original source/clock/contact/cap and full-mesh
gates. This particular value agreement is for the verified convex box; it does
not extend a facet model to arbitrary concave props or approve an animation.
The original Studio selection, entire project scope and all release criteria
remain unchanged.

### Complete convex interior-depth field

`scripts/native_convex_depth_field.py` provides `ConvexDepthField` for a supplied
closed, outward-wound convex triangle mesh. It rejects unsupported/open/inward/
concave geometry, retains every supplied facet, validates every vertex against
the supporting planes and never repairs the mesh or substitutes its hull.
Construction and evaluation use explicit complete array/comparison budgets.
This is an opt-in convex-target guide, not a replacement for arbitrary-mesh
collision queries.

For each supplied point it returns positive interior plane depth (zero
outside), a smooth upper approximation, its point gradient and every supplied
point-Jacobian column. The approximation uses corrected soft-min and softplus;
the real-arithmetic error is at most `temperature * log(2 * facet_count)`.
No claim of a floating-point collision certificate follows. Points, facets
and derivative columns are never removed to fit memory; a budget failure
rejects the call. Existing author/contact/mesh acceptance limits stay fixed.

All **30** focused fixtures pass locally, including independent box and
non-box convex triangle-distance values, every supplied derivative column,
the 768th column, rigid re-expression, reordered facets, duplicate points,
streamed chunk equivalence, smoothing ties/bounds and invalid target/budget
rejection. Guard: 31.953 s / 120,528,896 bytes / 49 observations. Source
fixtures do not approve character motion or a scene. The primary mathematical
reference and independent-implementation notes are in the source ledger.

The exact published source `096b56e` also passes all 30 focused fixtures on
Windows and Ubuntu ([run 39092990783](https://github.com/DocMorphic/strep/actions/runs/39092990783));
test times are 0.70 and 0.89 seconds respectively. This is focused source
validation, not a full-product test result.

### Complete interior-depth composition and coupled trials

The actual original-rig study composes native skinning, the moving prop frame
and the depth field for **all 36,112 vertices**, 12 facets and 139 control
columns, in 512-point chunks. Both actors retain all 18,056 vertices, including
deepest vertex 12006 and every previously missing deep vertex. Two independent
directional comparisons cover every point and both conservative complete-max
groups. Maximum point derivative error is 1.957e-8 m/control and grouped
normalized error is 7.434e-7/control. The fixed source clearance column is held
constant in those perturbations; all 139 composition columns are retained.
The real-arithmetic point-plus-group approximation budget is below 0.328
micrometres, without changing the physical penetration limit. Maximum estimated
chunk-array workspace is 10,377,504 bytes. Guard: 46.172 s / 268,152,832 bytes /
63 observations. No motion or geometry approval follows from derivative checks.

The first coupled trial uses the 269 known triangle pairs plus both complete
interior-depth groups: 3,529 objective rows, 8,042 extra rows, 5,402 native
norm cones, 6,436 passing motion guards and all 40 repaired witnesses. Every
declared fraction completes all 944,562 raw/saved motion scalars, nine-time
full scene geometry, 2,017 sampled prop bounds and declared contacts. There
are no new motion failures or lost repairs, and all 97 prior geometry passes
remain intact. Nevertheless, **every candidate is rejected**:

| Joint fraction | Raw normalized motion peak | Crossing records | Maximum depth (mm) |
| --- | ---: | ---: | ---: |
| Original comparison | 43.533073 | 113 | 23.531278 |
| 1 | 43.033387 | 115 | 23.453963 |
| 1/2 | 43.283110 | 115 | 23.491909 |
| 1/4 | 43.408062 | 115 | 23.511410 |
| 1/8 | 43.470560 | 115 | 23.521309 |

Depth improves but crossing count regresses. Guard: 580.125 s / 522,145,792
bytes / 584 observations, under the unchanged 512 MiB cap. The failed
comparisons remain archived; they are not animation-quality successes.

Discovery across 24 named completed reports retains 2,853 crossing occurrences
as **273 unique pairs** (A 232 / B 41), preserving all previous identities.
Four newly observed A/box-face-0 pairs use actor triangles 26588, 26589, 26778
and 26779. The expanded guide checks all 2,457 projection rows, all 139 columns
and 636 world/local scalar point rows in two directions. All 269 old pair
values/Jacobians, full prop-world values/derivatives, body basis and grip frame
match exactly, permitting reuse of the complete depth model at the same
control point. Guard: 36.859 s / 226,344,960 bytes / 54 observations. The
observed-pair ledger is not exhaustive future or continuous collision coverage.

The expanded full step retains 3,565 objective rows, 8,078 extra rows and
5,402 norm cones. Its complete raw/saved motion checks reject it before
geometry: actor A's linear-acceleration row 93696 loses a protected repair in
both representations. Its raw margin changes from +0.035049838 to -0.000190245;
the saved margin changes from +0.035052858 to -0.000188688. Lower overall error
does not waive this failure. Trial guard: 197.563 s / 318,488,576 bytes / 210
observations. A separate complete archived-scalar/source diagnosis verifies
the identity without rerunning motion or fitting: 4.125 s / 50,151,424 bytes /
22 observations.

One explicitly declared half-step reuses that recorded direction, with no
solver rerun, clipping or changed permissions. All 944,562 motion scalars
complete with zero new failures and all 40 repairs intact; raw normalized peak
43.533073 → 43.283007 and squared error 56,297.638 → 55,891.856. Nine full scene
times, all 2,017 sampled prop bounds, contacts and 97 prior geometry passes
remain intact. Crossing count stays 113 while maximum depth improves to
23.475561 mm. This qualifies a **partial numerical comparison only**: two
scene conditions still fail at one sampled time. Guard: 213.031 s / 441,720,832
bytes / 226 observations. Independent export, changed-pose body and combined
scene replays are required before adopting this as the next fitting reference.
The original Studio selection and release declarations remain unchanged.

The three independent replays now qualify this half-step as the next
**experimental fitting reference**, relative to the original author epoch:

- Export/body replay reconstructs cumulative native controls without the local
  fitting context, reproduces all 383,617 saved world values byte-identically,
  checks 5,400 raw and 5,400 saved native bounds plus 177,328 other archived
  scalars, and verifies unchanged static channels, clocks and frozen keys.
  Both representations confirm an additional repaired linear-speed row,
  **56719**: 6,082 → 6,081 remaining source-rate failures, with no new failures.
  Future fits must protect **41** repaired witnesses. Guard: 40.000 s /
  194,273,280 bytes / 57 observations.
- Changed-pose body geometry freshly checks the sole changed native pose at
  key 65, including both complete 36,108-face actors, partner geometry and all
  floor vertices. Together with 231 exact full-hierarchy pose identities from
  the previous verified reference, this closes the 232-sample body composite
  and all 120 native keys with zero body geometry/motion failures. Another
  1,785 policy times remain open. Guard: 35.890 s / 186,564,608 bytes /
  53 observations.
- Combined-scene replay independently reconstructs the original-relative body,
  grip and prop line, freshly reproduces all 45 mesh-pair queries and every
  world-array byte at nine declared times, and verifies the 97 prior passes,
  2,017 sampled prop bounds and contacts. It imports no fitting, inverse-frame
  or convex-depth backend. Existing geometry libraries are shared, rather than
  independent collision algorithms. Guard: 82.047 s / 266,977,280 bytes /
  98 observations.

Every source/archive/resource binding matches. This reference still has
**113 crossing records, two failed scene conditions and 23.475561-mm maximum
penetration** at one sampled time. It is neither collision-free nor approved
for realism or release. Continuous collision, self-collision, dynamics,
semantics, engine import and human cleanup requirements remain open. The
original Studio selection, broader action scope and fixed release requirements
remain unchanged; rejected trials are preserved locally.

### Complete temporal failure coverage

Continuing only the key-65 correction cannot finish this clip. A source-bound
classification covers all **383,617** raw/saved world rows in the independently
verified half-step reference. Only 7,238 rows are possibly affected by that
block's exact native endpoint support; **376,379 are temporally invariant**.
Of the 6,081 remaining failures in each representation, **825 are possibly
affected and 5,256 are invariant**. The invariant raw normalized peak is
16.322134 and its squared-error floor is 21,123.972. These are obstructions
for this declared temporal block, not infeasibility claims about the rig or
action. Nonzero temporal support is a conservative superset, not evidence of
spatial controllability or a nonzero derivative.

All invariant raw/saved values match the previous reference byte for byte;
four archived complete directional perturbations also preserve every invariant
raw value. Authored contact endpoints remain outside the block, and all 41
repaired witnesses still pass. Guard: 18.500 s / 217,669,632 bytes / 36
observations. The first diagnostic run incorrectly compared a joint-refined
319-group partition directly with the 15-block oracle layout and stopped at
that assertion. That failure remains unchanged: 12.281 s / 185,573,376 bytes /
30 observations. The fresh run validates the complete refinement, including
every boundary and row label; no fitting or motion checks are repeated.

`scripts/native_temporal_failure_coverage.py` supplies a bounded, complete
planner for explicit sampled failure stencils. Each candidate changes one
existing native key, anchoring its neighbours while retaining original frozen
keys. Stored LINEAR interpolation weights determine temporal dependence; exact
keys and adjacent representable timestamps are not rounded. The returned
matrix retains every supplied candidate and row, including unselected blocks.
Oversized populations are rejected without pruning. Weighted greedy scheduling
uses complete marginal sums with a deterministic key-order tie rule. Explicit
initial peaks describe scheduling context, not successful repairs.

All **55 focused fixtures** pass locally: independent scalar-impulse
interpolation on irregular clocks, one/three-sample stencils, original frozen
keys, exact and adjacent representable times, weighted/tied/initial scheduling,
unselected candidates, unchanged inputs and invalid/complete-budget rejection.
Source guard: 15.406 s / 82,247,680 bytes / 33 observations. No new dependency,
model inference, training or data acquisition is involved.

Actual-rig composition retains all **6,081 failed sampled-rate stencils** and
all **117 eligible native peaks**, yielding **711,477 dependency cells**.
Raw/saved failure masks agree; weights use the squared maximum normalized
violation between representations, without changing any physical cap. Every
candidate is independently constructed against both original-domain cumulative
native bases and checked through scalar interpolation. All 234 block/basis
constructions preserve the zero control grid and original frozen keys 0, 60
and 119; every candidate/stencil dependency agrees. Guard: 28.703 s /
204,779,520 bytes / 46 observations.

With key 65 explicitly retained as initial context, the greedy schedule has
**31 blocks and zero temporally uncovered failure stencils**. The first new
peak, **74**, covers 656 failures outside the initial block. This is neither
an optimal schedule nor 6,081 repaired conditions: no new clip is generated,
and temporal coverage does not prove a spatially feasible correction. Future
blocks must preserve all 41 repairs, the original author/cap epoch and every
raw/saved/contact/mesh gate. Newly changed poses need geometry checks beyond
the previous nine scene times. The verified partial fitting reference and
original Studio selection remain unchanged.

The initial hosted suite run at `6c6dcd4` fails collection on both platforms
because the new test omitted its standalone scripts-folder import path; its
local wrapper had provided that path. The failed hosted logs remain archived.
Only that test setup is corrected in `2defbd9`; the planner module is unchanged.
All **55** fixtures now pass on Windows (0.39 s) and Ubuntu (0.34 s),
[run 39095673022](https://github.com/DocMorphic/strep/actions/runs/39095673022).
A fresh local interpreter with empty `PYTHONPATH` independently passes all 55
in 0.78 s. Guard: 15.375 s / 106,541,056 bytes / 33 observations. The previous
55-case local snapshot is historical and retains its original test binding.

The first scheduled new block, **[73, 74, 75]**, now has a qualified complete
world model about the unchanged half-step reference: all 383,617 values match
byte for byte, with 319 groups and 135 columns. Both complete directional
comparisons pass (maximum differences 7.485e-10 and 8.451e-10), including one
complete uncached perturbation replay. There are five complete value
perturbations. Guard: 283.844 s / 286,343,168 bytes / 295 observations.

Its complete 1,106-group guide retains all 448,401 world/native/original-pose/
pair scalars, all **41 repaired witnesses** and **5,852 passing motion guards**.
Both directional checks cover every 6,508 affected/required derivative row;
maximum difference is 3.283e-7. The complete-world squared-error derivative
also passes its declared numerical comparisons. Authored contacts and all 120
original pose/pair observations are temporally invariant for this block; those
conditions remain represented. Original cumulative bounds, source curves,
clocks and frozen keys are unchanged. Guard: 50.219 s / 348,782,592 bytes /
67 observations. No solver, new saved clip or geometry approval follows from
these model checks.

A supplemental full-scene baseline at native key **74** (2.4666666984558105 s)
now freshly checks both complete 36,108-face characters, partner/floor geometry
and all five actor/prop/prop pairs. The selected pose passes, with **zero
mesh-pair crossing records and zero measured containment depth**. Guard:
25.672 s / 146,509,824 bytes / 43 observations. This is a baseline to preserve
during fitting, not a repaired clip or continuous scene approval. The original
nine-time scene policy and its remaining key-65 failures are unchanged.

The first supplemental query correctly stops before geometry because its
one-time explicit clock omits required clip endpoints: 6.156 s / 121,921,536
bytes / 24 observations. That rejected run remains immutable. A fresh run
retains both endpoints in its declared clock and explicitly queries only the
middle native-key-74 index, with identical source assets and physical limits.
Its complete observation archive and receipt verify; the endpoint requirement
and original scene policy are not relaxed.

### Paired motion progress across temporal blocks

`scripts/native_motion_progress.py` compares every supplied raw/saved signed
world margin with the same caller-bound row population and original caps.
Both representations must strictly reduce total squared violation beyond a
declared progress threshold, with no increase in peak or failure count, no
newly failed row and no lost required repair. An unchanged global worst row
outside the edited block is allowed. Nonnegative margins pass exactly; the
helper adds **zero physical acceptance tolerance**. Native bounds, other
pose/pair rows, source/static content, contacts, geometry and release acceptance
remain separate mandatory checks.

All **34 focused fixtures** pass in a fresh standalone local interpreter
(0.65 s), including improvement with a fixed worst row, rejection of new
failures despite lower total error, lost zero-margin repairs, a worse peak,
one representation failing to improve, exact repair identities, signed zero,
strict progress thresholds, complete input budgets and invalid populations.
Guard: 14.359 s / 104,448,000 bytes / 32 observations. No source cap or past
failed study is reinterpreted by this helper.

The predeclared first key-74 trial uses the complete 1,106-group guide, all
5,400 cumulative native cones, 5,852 passing motion guards and 41 repaired
witnesses. It permits two fractions, 1 and 1/2, of one bounded proposal.
Each attempted candidate must finish all 944,562 original raw/saved checks;
motion-qualified candidates then receive fresh full scene queries at all nine
previous times plus key 74. Props remain fixed, original sampled prop bounds
and contacts are rechecked, and every prior passing scene identity and the
supplemental baseline are protected. Proposal or coverage success alone is
not a repaired animation or a new fitting reference.

All 34 paired-motion fixtures also pass on Windows (0.47 s) and Ubuntu
(0.19 s) at exact source `05b7c91`,
[run 39096519682](https://github.com/DocMorphic/strep/actions/runs/39096519682).
These are focused source checks, not full-product validation.

### Grouped-objective limitation and complete individual rows

The first key-74 run completes all 944,562 motion scalars and preserves all
41 repairs with no new failures. Its tiny proposal changes raw squared error
by only 0.019048 and saved error by 0.007433; failure counts and peaks do not
change. Validation then stops before geometry: the worker mistakenly supplies
the original-prop bounds checker with the current candidate's scene-bound
policy. The checker correctly rejects that binding. The **failed** run remains
immutable: 101.375 s / 278,884,352 bytes / 117 observations. Its completed
motion checkpoint is not promoted or relabelled as a completed scene study.

A fresh stored-model/scalar diagnosis finds **12 violating grouped terms with
exactly zero Jacobian entries** in this temporal block. The grouped hinge
gradient is zero, although 656 individual affected rows fail and their
Jacobian contains 10,497 nonzero entries. Their hinge-gradient norm is
6,725.141 and the complete-world squared-error gradient norm is 84,559.757.
The proposed maximum control component is only 2.324e-7, with exactly zero
predicted grouped-hinge change. A maximum over worse errors elsewhere can
hide useful derivatives for this block. These are stored linear-model facts,
not nonlinear invariance or infeasibility claims. Diagnosis: 17.453 s /
73,445,376 bytes / 35 observations; fitting and geometry are not rerun.

The next trial retains all original 1,106 groups and appends **every 6,508
qualified affected/required individual row**: 7,614 objective rows and all 135
columns. The 6,951 extra proposal rows, 5,400 native cones, 5,852 passing guards,
41 repairs and original physical limits remain intact. No top-error slice or
row pruning is used. The prop bounds checker is supplied its original bound
policy in the fresh worker; neither candidate reaches that stage because
motion rejects both first.

| Fraction | Raw squared error | Raw improvement | Remaining failures per mode | New failures per mode | Repairs newly passed per mode |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | 55,891.855644 | — | 6,081 | — | — |
| 1 | 50,149.450587 | 5,742.405057 | 6,067 | 16 | 30 |
| 1/2 | 52,630.005096 | 3,261.850547 | 6,085 | 8 | 4 |

Both complete raw/saved checks preserve the 41 required repairs and all
177,328 other scalars. The global peaks remain unchanged. Nevertheless,
**both candidates are rejected** for newly failed source-rate rows, regardless
of improved total error or repaired rows. Geometry is not run; no independent
candidate replays or new fitting reference are claimed. Trial:
218.093 s / 335,224,832 bytes / 231 observations.

A second complete archived-value/source diagnosis verifies that every newly
failed row was present in the original passing guard set, and its linear cut
was satisfied. The full step breaks 12 angular-speed, three angular-acceleration
and one linear-acceleration condition; the half-step breaks eight actor-A
angular-speed conditions. For example, row 133035 starts with margin
+0.007748724 and predicts +0.005811543 at the half-step, but measures
-0.034047500. Its derivative norm is nonzero (7.334941), so this is not a
zero-gradient invariance claim. Diagnosis: 8.219 s / 78,761,984 bytes /
26 observations. Original outputs, caps and rejected decisions are unchanged.

The next constraint model should retain the underlying rate vectors and
their norms, then repeat the same full raw/saved gates. An affine vector-norm
cone can retain information lost by a scalar tangent, but does not certify the
nonlinear rotation, forward kinematics or saved animation. The primary SOCP
reference is recorded in the source ledger. The verified half-step fitting
reference, original Studio selection, broad action scope and all release
requirements remain unchanged.

### Complete sampled rate vectors

`scripts/native_motion_rate_vectors.py` retains all three components of linear
and angular speed/acceleration, their complete supplied world-to-rate Jacobian,
the caller's original caps/tolerance and the unchanged validator's scalar
values. Its vector norms must match canonical rate arithmetic byte for byte.
Angular acceleration preserves the validator's divide/difference order;
angular derivatives use the existing matrix decoder in bounded 16-column
batches. No source rotation, clock or cap is reconstructed or replaced.

The local constraint is `norm(v + J delta) <= original_cap + original_tolerance`.
It retains transverse components and nonzero vector derivatives at zero speed.
It is an affine local model, not a certificate for nonlinear rig motion or
saved Float32 files. Canonical scalar arithmetic and all subsequent physical
checks remain authoritative. Complete input-plus-output Jacobian budgets are
checked before copying; no supplied joint or column is dropped to fit memory.

All **63 fixtures** pass in a fresh standalone local interpreter (4.03 s),
including every column of independent nonlinear pose fields, exact legacy
scalar/norm agreement, known-axis rates, zero-speed vector derivatives, a
transverse angular change missed by a scalar tangent, 768th-column retention,
batch equivalence, near-orthogonal decoder behavior, rigid re-expression,
unchanged inputs, zero caps/tolerance, exact budget boundaries and invalid/
ambiguous-branch rejection. Guard: 33.078 s / 157,159,424 bytes / 50 observations.
This adds no dependency, inference, training, asset or data acquisition and
does not approve a new clip.

The exact published source `62203aa` also passes all 63 fixtures on Windows
(0.65 s) and Ubuntu (0.80 s),
[run 39097928396](https://github.com/DocMorphic/strep/actions/runs/39097928396).

### Complete passing-row norm composition

The actual rig pair now has a local vector-norm model for **all 5,852 passing
world guards**, including all 41 repaired witnesses, with all 135 columns.
The population contains 1,081 uniform displacement rows, 155 additional-time
displacement rows, 1,036 linear-speed, 1,241 linear-acceleration, 1,099 angular-
speed and 1,240 angular-acceleration rows. Every original guard identity and
column is retained; constant constraints remain explicitly represented.

All canonical anchors match the previous scalar guide byte for byte. Projecting
the vector derivatives onto the rate direction reproduces its complete scalar
Jacobian within 9.632e-15. Two independent nonlinear directions check all
17,556 vector components, with maximum normalized derivative differences
3.604e-7 and 7.093e-7. The complete vector Jacobian uses 18,960,480 bytes;
maximum pose-cache storage is 22,134,528 bytes under its 64 MiB bound.
Guard: 68.640 s / 248,061,952 bytes / 85 observations.

For the previously rejected full and half proposals, these norm constraints
predict **all 16 and all eight newly failed rows**, respectively, which the
scalar tangent guards missed. This checks stored proposals at the measured
linearization; it is not a guarantee about future nonlinear motion. The
unchanged baseline lies inside every represented norm bound, with maximum
initial norm excess -7.118e-8 in normalized units.

The next proposal retains the complete 7,614-row objective and 6,951 scalar
cuts and stacks **5,400 original native rotation cones plus all 5,852 world
norm cones**: 11,252 total. Its world proposal radii retain half of the available
local norm slack, a search restriction only. Original physical cap/tolerance
arrays, strict raw/saved gates and output values are unchanged; no clipping
is introduced.

The full step completes all 944,562 raw/saved conditions with **zero newly
failed rows and all 41 prior repairs intact**. Both modes repair the same 23
additional rows: 6,081 → 6,058 source-rate failures. Raw squared violation
55,891.855644 → 50,237.206349; saved 55,891.848214 → 50,237.208111. The global
peaks remain unchanged because their worst rows are outside this block.

Fresh complete geometry at all **ten** scene times retains **108** passing
condition identities, passes native-key-74 geometry, rechecks all 2,017 sampled
original prop bounds and declared contacts, and changes no collision metric.
The source-bound prop-policy path that stopped the earlier run is now exercised
successfully. The scene still has 113 crossing records, two failed conditions
and 23.475561-mm maximum depth at the earlier time. Trial:
194.891 s / 451,338,240 bytes / 208 observations, below the unchanged 512 MiB
tree-RSS cap. This qualifies a partial numerical comparison; independent
export/body/combined-scene replays remain required before adopting it as a new
fitting reference. No realism, engine, continuous/self/dynamics or release
approval follows from these results.

The independent replays now qualify this candidate as a new **partial fitting
reference**, relative to the same original source epoch:

- Export/body replay reconstructs the native-key-74 insertion directly into
  the independently verified cumulative parent controls, without the fitting
  context. It reproduces all 383,617 saved world values byte for byte, checks
  5,400 raw and 5,400 saved native bounds, and verifies all 177,328 other archived
  scalars plus static assets, source caps, clocks and frozen keys. Both modes
  confirm the same **23** repaired rows and zero new failures: future fits must
  protect **64 total repaired witnesses**. Guard: 41.047 s / 218,812,416 bytes /
  58 observations.
- Changed-pose body geometry freshly checks key 74 with complete 36,108-face
  actor meshes, partner queries and all floor vertices under the unchanged
  policy. Together with 231 exact full-hierarchy pose identities, it closes the
  232-sample body composite and all 120 native keys with zero body failures.
  Another 1,785 policy times remain open. Guard: 30.766 s / 168,816,640 bytes /
  48 observations.
- Combined-scene replay freshly reproduces all **50** mesh-pair queries and
  every complete world-array byte at all **ten** times. It independently checks
  original-relative fixed prop controls, contact targets, 108 prior passing
  identities and all 2,017 sampled original prop bounds, without importing
  rate-vector, motion-progress, solver or high-level mesh-prop backends.
  Existing interpolation/skinning/collision libraries remain shared, not
  independent physical algorithms. Guard: 79.937 s / 275,484,672 bytes /
  96 observations.

All source/archive/resource bindings match. The new experimental reference
still has **6,058 source-rate failures, 113 crossing records, two failed scene
conditions and 23.475561-mm maximum depth**. No collision-free, realism,
continuous/self/dynamics, semantic, engine or human-cleanup approval is implied.
The original Studio selection and every fixed full-project release requirement
remain unchanged. Future blocks must regenerate their derivatives around the
current cumulative controls and retain all 64 repairs; old-point models are
not current-point evidence.

### Refreshing the correction schedule and objective roles

A complete schedule refresh at the independently verified 64-repair reference
retains all **6,058 failed stencils**, all 117 eligible native peaks and
**708,786 dependency cells**. With peaks 65 and 74 recorded as initial editing
context, 1,458 failures have temporal support there and 4,600 lie outside both.
The 31-block coverage schedule still has zero uncovered stencils and selects
**63** next. Every candidate is replayed against both original-domain cumulative
bases; no frozen key, source curve or physical cap changes. Coverage is not a
repair or a spatial feasibility proof. Guard: 28.766 s / 208,670,720 bytes /
46 observations.

The new **[62, 63, 64]** world model reproduces all 383,617 current baseline
values byte for byte, retains 319 groups and 135 columns, and passes both full
directional checks plus an uncached perturbation. Maximum directional
differences are 3.035e-8 and 5.384e-8. Exact native timestamps are retained,
including small nonzero interpolation weights near uniform-sample boundaries.
Original 120 pose/pair observations remain invariant for this block. Guard:
297.672 s / 289,144,832 bytes / 308 observations. No new clip is generated.

`scripts/native_world_objective_partition.py` keeps every original group and
every supplied affected/required row. Rows failing either raw or saved mode
receive objective terms using the lower baseline margin. Rows passing either
mode are returned as hard constraints, with their smallest passing baseline
margin. A mixed-mode row receives both roles; every required repaired witness
must be present and already pass both modes. Passing rows are not discarded
to meet the soft-objective budget, and original groups are never truncated.
The caller must enforce every returned hard row and retain native/world norms
and full raw/saved/geometry postchecks. A shared raw Jacobian is guidance for
both modes, not a derivative of Float32 quantization.

All **43 fixtures** pass locally in a fresh standalone interpreter (0.76 s):
complete role/order preservation, mixed raw/saved rows, repaired witnesses,
exact zero margins, 768th-column retention, complete-budget rejection and a
case where 8,072 affected rows remain represented despite a smaller objective
row budget. Random feasible local directions verify equality with the
unreduced hinge objective when every returned passing-row hard constraint is
retained. This is a local linear-model equivalence, not nonlinear motion
approval. Guard: 16.406 s / 99,745,792 bytes / 34 observations.

### Complete key-63 guards and rejected numerical proposals

The 43 objective-partition fixtures also pass on both Windows and Ubuntu at
`ae9d9b6` ([focused run 39099756189](https://github.com/DocMorphic/strep/actions/runs/39099756189)):
0.55 s and 0.33 s, respectively. No engine or motion approval follows from
these source tests.

The fresh **[62, 63, 64]** composed guide retains all 1,106 groups, 135 columns
and **8,069 affected/required scalar rows**: 8,008 temporally affected rows plus
61 additional repair witnesses. Every required witness remains present. The
passing raw/saved masks agree; all **7,152 passing rows** receive hard guards,
while all **917 failing rows** receive objective terms. Thus the objective has
**2,023 terms**, without selecting a top-error subset. Every original group
remains, including constant groups. Native, scalar-guard and full squared-error
directional checks pass. Original contacts and the 120 pose/pair observations
are invariant for this block. Guard: 71.688 s / 354,705,408 bytes / 72 observations.

The complete vector model retains **7,152 world norms, 21,456 components and
135 columns**. Its canonical anchors match the scalar guide byte for byte;
maximum scalar projection difference is 4.719e-15. Both full nonlinear vector
directional comparisons pass, with maximum differences 7.872e-7 and 5.396e-7.
The complete vector Jacobian uses 23,172,480 bytes and the bounded pose cache
peaks at 27,605,760 bytes. Guard: 95.250 s / 261,980,160 bytes / 95 observations.
These local models remain guidance for mandatory nonlinear and saved-file gates.

The actual proposal retains all **5,400 native plus 7,152 world norm constraints
= 12,552 norms**. All 8,251 original scalar cuts are archived. Exactly 6,352
have every stored coefficient equal to zero and a nonnegative upper bound:
their affine inequalities are explicit tautologies. The other 1,899 scalar
cuts enter the solver. This uses exact equality, never a small-coefficient
threshold. A zero scalar gradient does **not** establish physical invariance;
every corresponding vector norm is retained, including its transverse motion.
The complete row-role and scalar-cut partitions are recorded for replay.

One initial worker fails before solving because two report dictionaries supply
the same `scope` keyword. Its raw exception and resource trace are preserved;
a fresh worker corrects only that report construction. The subsequent three
numerical proposals all fail the existing **1e-8** norm-residual admission:

| Fresh proposal | Trust bound | Maximum norm excess | Outcome |
| --- | ---: | ---: | --- |
| Original norm scaling | 0.02 | 5.510121e-8 | Rejected despite `Solved` |
| Positive per-cone unit-radius scaling | 0.02 | 5.981269e-8 | Rejected despite `AlmostSolved` |
| Same scaling, quarter trust bound | 0.005 | 2.031963e-8 | Rejected despite `Solved` |

The positive scaling is algebraically equivalent in exact arithmetic. It
retains every cone, records all positive scales and checks two complete
reconstructions (maximum differences below 4.45e-16). The original-unit residual
gate is retained as an additional check; neither normalization nor a smaller
search box changes physical caps, tolerances or saved-file acceptance.
The solver's status alone is insufficient. No direction is admitted, no new
clip is exported, and conditional full motion/geometry/independent replays and
reference registration are **not executed**. These numerical admission failures
are not proofs that the action or rig is infeasible.

The three completed proposal guards use 313,450,496 / 315,920,384 / 316,112,896
peak bytes and finish in 65.469 / 65.437 / 60.344 seconds. The initial report
failure uses 221,343,744 bytes and finishes in 36.765 seconds. All resource/source
bindings replay under unchanged 512-MiB tree RSS and 600-MiB free-RAM policies.
The memory retry therefore permits this work; it does not certify motion quality.

The verified fitting reference remains **64 repaired witnesses, 6,058 source-rate
failures, 113 crossing records, two failed scene conditions and 23.475561-mm
maximum depth**. Studio selection and all original release requirements remain
unchanged. Next diagnose the norm conditions responsible for numerical admission
failure and improve feasibility handling without relaxing the gates, then run
all mandatory motion, contact, prop, mesh and independent saved-file checks on
any admitted candidate. Broader action/rig/scene coverage and developer/animator
cleanup evidence remain requirements of the same entire-project goal.
