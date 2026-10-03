# Stored object assets and native engine authoring

Declared rigid object tracks can now be exported directly from a native scene
contact specification into a GLB. Every object keeps its analytic primitive
description, an explicitly approximated visual mesh and complete translation,
quaternion rotation and unit-scale tracks. Actor clips and placements remain
separate, with byte-identical source snapshots. No model or downloaded asset is
needed by the exporter itself.

## Float32 storage and unchanged audits

The [glTF specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#animations)
requires strictly increasing floating-point animation timestamps. Distinct
double-precision native/frame times can round to the same stored Float32 time.
Blindly casting the authoring clock would therefore produce invalid tracks.

The exporter records every source time, its stored index, all collision groups
and the maximum timestamp rounding. It creates the unique stored Float32 clock
and resamples the source rigid interpolation at those times. Source endpoint
clamping is explicit when an endpoint rounds slightly outside its domain.
It does not arbitrarily choose the first or last pose in a collision group.
A static object gets two constant poses spanning the shared clip duration.

Translation and quaternion values are actually saved as Float32 accessors.
The reopened GLB is the authority for subsequent measurements. Complete TRS,
unit-scale values, normalized-range quaternions, accessor bounds and strictly
increasing times are checked before sampling. Saved quaternion interpolation
normalizes its stored values; the original authoring track is preserved.

Audit times retain the original actor native keys, object keys, clip endpoints
and all authored point/hold clocks, including all twelve absolute frame
populations. Those times are not rounded or replaced by the asset clock.
All original contact caps remain unchanged. Separate object pose checks use
1e-6 metre position and 1e-6 basis-component limits; they do not override contact
failures. Large quantization or an incompatible sharp pose change stays a
recorded failure. Export success alone does not select or approve the asset.

```powershell
python scripts/native_object_asset.py export contacts.json reports/new-object-assets
python scripts/native_object_asset.py engine reports/new-object-assets reports/new-object-engine --engine path/to/Godot_console.exe
```

Each command requires a fresh destination. Export records exact source and
actor snapshots, archived implementation, GLB, clock mappings, contact arrays
and receipts. Engine auditing rejects implementation drift before launching.
It rechecks the saved input and implementation bindings after completion.

## Actual Godot observations

The headless engine audit imports the actual object GLB and observes both
ordinary import and native-resource authoring. [Godot's GLTFDocument API](https://docs.godotengine.org/en/stable/classes/class_gltfdocument.html#class-gltfdocument-method-generate-scene)
has a fixed-rate scene-generation option; the recorded default comparison uses
30 Hz, with trimming and immutable-track removal disabled.

The alternative builds typed object TRS Animation tracks from the reopened GLB,
saves a binary `.res` resource, reloads it and verifies every native key time
and count. Authoring samples use that loaded resource's track interpolation on
the imported mesh nodes. This is explicit manual authoring evaluation; it does
not prove real-time AnimationPlayer stepping, gameplay events or physics.
The loaded objects' actual engine transforms feed the original contact audit.
Actor points still come from the source CPU skin decoder, so this isolated
object test does not establish complete imported-actor contact correctness.

## Matched humanoid sphere result

The input is the explicitly corrected object trajectory from the
[two-grip hold study](native-object-hold-fit-v1.md), with the same unchanged
actor, contacts and other object. Its 1,266 sphere keys become 1,182 stored keys
through 84 collision groups. Maximum timestamp rounding is 0.222524 microseconds.
The second object has two keys with no collision. All 1,266 original audit
times remain included.

| Measurement | Reopened Float32 GLB | Godot default import | Reloaded native resource |
| --- | ---: | ---: | ---: |
| Sphere maximum source-relative position error | 0.0000416 mm | 0.0430891 mm | 0.0000595 mm |
| Sphere maximum basis-component error | 2.17e-8 | 2.46e-4 | 1.21e-7 |
| Maximum right-hand held speed | Below 5 mm/s | 10.194265 mm/s | 3.076894 mm/s |
| Original contact and object pose checks | Pass | Fail | Pass |

The native resource has maximum left/right grip distances of approximately
2.001216 mm, below the original 5 mm cap. Its other object's maximum position
error is 0.000417 mm, also below the independent 0.001 mm pose limit. No limits
or phase populations are relaxed to obtain these results.

Two retained runs reproduce the same GLB bytes. The second adds stricter
implementation bindings without changing the object fitting/export values.
Independent saved replay regenerates the GLB byte-for-byte, checks the complete
clock mapping, reproduces every asset/engine contact array and rechecks both
pass/fail decisions from raw engine transforms. An initial verifier compared
original-path metadata with snapshot-path metadata and stopped; that failed
verification directory remains retained. The corrected replay separately binds
the original-source and snapshot-source scenes rather than suppressing the
path distinction. No source study output is rewritten.

Ignored raw evidence is under `reports/native-object-asset-development-v1` and
`reports/native-object-asset-development-v2`. Seventeen focused regressions
cover collision mappings, invalid clocks, three primitive shapes, exact repeat
export, unchanged actors, original contact populations, visible sharp-motion
storage failures, static tracks, malformed assets and pre-launch method drift.

All 533 related model-free regressions pass in the recorded local run.

Complete geometry must still be checked using the saved/imported object poses;
the earlier authoring-trajectory geometry pass is not transferred implicitly.
Imported actor skin, whole-scene geometry, continuous contact/collision, normals,
attachment/release, physics, runtime event dispatch, human review and release
acceptance remain unapproved. This experimental CLI path does not change
Studio defaults or claim a newly trained model or general manipulation quality.
