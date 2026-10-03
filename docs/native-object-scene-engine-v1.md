# Combined native object and character engine audit

The corrected sphere hold now passes a matched sampled comparison using
complete imported character skin and actual saved/reloaded object Animation
resources. A reusable CLI combines these producer outputs with source-bound
scene geometry. It preserves the failed default-import comparison and leaves
the original selected; numerical success is not animation-quality approval.

## Reproducible workflow

Start with a strict native scene contact specification and geometry policy,
such as the output of [bounded object fitting](native-object-hold-fit-v1.md).
All actors must share the exact declared duration; retime explicitly first.
Contacts identify actual skin vertices or authored centroids. Actor, object,
partner and plane conditions retain their original meanings and limits.

```powershell
python scripts/native_object_asset.py export contacts.json reports/objects-source
python scripts/native_object_scene_engine.py prepare contacts.json policy.json reports/objects-source reports/objects-common
python scripts/native_object_asset.py engine reports/objects-common reports/objects-engine --engine path/to/Godot_console.exe
python scripts/native_scene_engine.py contacts.json reports/actors-engine --geometry-policy reports/objects-common/common-policy.json --playback-mode native-authoring --engine path/to/Godot_console.exe
python scripts/native_object_scene_engine.py combine contacts.json reports/objects-common/common-policy.json reports/actors-engine reports/objects-engine reports/combined-engine
```

Every output directory must be fresh. Preparation creates a separate derived
object bundle; it copies the GLB bytes, actor snapshots and stored-clock map
unchanged. Its common clock is the union of the complete original geometry
policy, every existing object audit time and every actual stored object key.
The policy mode, limits, planes and contact binding remain unchanged. Additional
Float32 key times are included explicitly, without replacing original times.
An oversized clock fails the existing resource budget rather than returning a
subset. Saved object pose/contact checks are rerun on the prepared bundle.

Preparation binds the original asset, policy and implementation. The producer
commands consume that derived bundle and common policy; users do not edit old
receipts or replace the old asset's clock in place. The combiner rejects mixed
sources, incomplete or different clocks, nonterminal jobs, changed methods,
changed original/prepared snapshots and incomplete resource/script receipts.
Both producers must use the same executable and recorded engine version.

The combiner reconstructs every imported actor vertex at every common time and
checks the source-relative 1e-4 metre skin-position limit. It keeps all raw
imported weights, checks bone poses, and audits contacts against actual object
resource observations. Object source-relative position and basis limits stay
1e-6. Complete scene geometry is queried with those imported surfaces and
object poses; a source-trajectory geometry pass is not reused as that result.
Passing requires native-source contacts, imported contacts, pose preservation,
full-skin preservation, object poses and declared sampled geometry together.
Default object import is retained as a separately measured comparison.

This is headless CPU reconstruction and manual native-resource authoring.
It does not render, bake GPU skin, step physics or dispatch gameplay events.
The resulting numerical decision does not automatically change Studio selection.

## Retained humanoid sphere comparison

The completed development study checks the previously retained 1,266-time
clock. Its actor import covers all 18,056 vertices, 36,108 faces and 18,056
distinct skin functions, including all imported influences. Bone/vertex slot
mapping and globally reversed imported winding are checked against the source.
Raw imported weights are not renormalized.

| Measurement | Result |
| --- | ---: |
| Maximum actor pose-matrix component error | 7.115e-7 |
| Maximum source-relative imported vertex error | 0.0950103 mm |
| Source-relative skin-position limit | 0.1 mm |
| Maximum left/right native-resource grip position error | 1.999534 / 1.996182 mm |
| Maximum left/right native-resource held speed | 3.072727 / 3.086137 mm/s |
| Original contact position/speed limits | 5 mm / 5 mm/s |
| Complete actor/object geometry observations | 2,532 |
| Native-resource contact and declared geometry conditions | Pass |
| Default-import right-hand held speed | 10.209631 mm/s — fail |

The first engine stage also passes its pose, full-skin, original Node3D object,
contact and geometry checks. The combined follow-up substitutes the actual
reloaded GLB-derived native object-resource observations and queries complete
geometry again. Both objects remain outside the closed actor volume; depth
upper brackets remain below the original 5 mm limit at every declared time.
No partner or world plane is declared in this case, so no partner/floor result
follows. Triangle topology is unmodified; self-collision remains unverified.

Independent replay binds raw engine requests, outputs, resources, original
inputs, snapshots and methods. It rederives every full-skin error exactly,
reproduces all imported contact arrays and decisions, and checks every saved
per-triangle depth-array reduction across all 2,532 observations. It does not
unnecessarily repeat the expensive complete geometry query. An early local
prototype mislabeled callback measurements as normalized weights; its original
report is retained and a separate derived report corrects that metadata. The
reusable CLI explicitly labels raw imported weights correctly. Numerical
observations were unchanged.

The common-clock preparation additionally includes stored Float32 object keys.
The retained derived bundle has 2,201 times and passes its saved object pose and
contact audit, with unchanged GLB bytes and original limits. The completed
1,266-time result does not approve this larger population implicitly. Expanded
actor and object engine observations, combined geometry and original-method
replay have since completed; all sampled native conditions pass. See
[the expanded study and streamed producer integration](native-geometry-stream-v1.md).

Ignored evidence is retained in `reports/native-object-combined-engine-development-v1`,
`reports/native-object-scene-engine-validation-v1` and
`reports/native-object-common-clock-development-v1`. Twenty focused cases cover
matched sampled composition, failed default imports, changed and incomplete
producer bindings, actual counterpart use, exact-clock rejection, expanded
policy preservation, unchanged assets and fresh-output isolation. Engine
execution in those small unit fixtures is explicitly mocked; the humanoid
development observations are actual headless Godot output. All 553 related
model-free checks pass in the recorded local run.

One rig, one hold and a finite clock do not establish general manipulation,
action correctness or professional motion. Contact normals, balance, forces,
attachment/release, object/object and self/continuous collision, real-time
playback, event dispatch, GPU rendering, developer/animator review and cleanup
time remain separate requirements. All release capability gates stay open;
no checkpoint, training admission or quality approval is created here.
