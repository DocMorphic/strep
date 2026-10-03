# Native scene engine diagnostics

This read-only audit imports the selected animation for every actor into Godot,
captures all skinned surfaces and declared joint/object samples, and reconstructs
the imported skin on the CPU. It measures native and imported contacts separately
and can repeat the complete surface geometry audit using actual engine poses.
Original motions remain selected regardless of the sampled result.

## Run

Use the model-free dependencies in `requirements-ci.txt` and an existing Godot
console executable. The reference encoding is validated against Godot 4.7.2,
build `ed1daf0bf001b61586d9930840f2f1394092c079`; other versions require checking
their loader behavior. The default executable path is the local Windows cache.
Models, downloaded characters, the engine and development outputs are not bundled.

```powershell
python scripts/native_scene_engine.py contacts.json reports/my-import --engine C:/tools/Godot_console.exe --geometry-policy geometry-policy.json
python scripts/native_scene_engine.py contacts.json reports/my-authoring --engine C:/tools/Godot_console.exe --geometry-policy geometry-policy.json --playback-mode native-authoring
```

Both output folders must be fresh. Inputs follow the
[native scene contact contract](native-scene-contacts-v1.md); the optional policy
follows [native scene geometry diagnostics](native-scene-geometry-v1.md).
Without a geometry policy, combined sampled conditions are unavailable.
The existing single-worker lock prevents overlapping heavy authoring jobs.

`import` uses ordinary imported AnimationPlayer seeks. `native-authoring`
installs native joint keys into an exported and reloaded Animation resource and
uses the existing manual authoring seek. These are distinct observations;
neither establishes real-time playback. The explicit source animation index is
selected before scene creation, including when the file contains other clips.
Godot's [GLTFState API](https://docs.godotengine.org/en/stable/classes/class_gltfstate.html)
and [GLTFDocument API](https://docs.godotengine.org/en/stable/classes/class_gltfdocument.html)
describe the import state and generated scene used here.

## Identity and measurement

The audit requires one supported skeleton/player per actor, unique named bones
and complete skinned triangle geometry. It checks every original skin function
and triangle across all primitives, with four or eight influences per vertex.
Bone, influence and vertex ordering may change; source function coverage and
triangle multiplicity must remain complete. Exactly equivalent duplicates can
share a representative. Ambiguous matches between distinct source functions,
lost surfaces/faces, altered weights and partial winding changes are rejected.
One global winding reversal is permitted and explicitly reported.

The source import reference reproduces the pinned loader's ordered Float32
weight sum/division, then its existing unsigned-16 encoding. The
[version-pinned Godot loader](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/gltf/gltf_document.cpp)
supplies this algorithm. A NumPy reduction with a different addition tree can
cross a quantization boundary. This reference is used only to establish import
identity: source motion measurements and actual imported weights stay unchanged.
Imported CPU reconstruction uses those raw weights without renormalization.
Authored actor placement is applied after skinning.

The unchanged bind-function identity tolerance is 2e-6 per component. Separate
diagnostics use a 1e-4 joint-matrix element limit, 1e-6 object pose limit and
0.1 mm maximum full-skin position difference. These do not replace or relax
authored contact, speed or penetration limits. Native contacts retain their
source skin convention, making discrepancies visible.

Props are actual sampled engine Node3D transforms, driven by the explicit rigid
position/rotation keys. Analytic geometry uses their measured position and the
proper rotation reconstructed from observed quaternions; raw basis projection
and normalization differences remain reported. These are not physics bodies.

The exact engine clock is the union of clip endpoints, required contact samples
and the optional geometry population. Held contacts retain all twelve frame
populations and their speed checks. Geometry is evaluated only at its declared
times. A sparse policy does not silently expand into continuous collision checks.

Inputs, snapshots, executed scripts, method sources, engine binary, raw engine
observations, exported resources and numerical arrays are hash-bound. A raw
engine receipt is written before CPU validation, preserving successful import
evidence even if later correspondence fails. Runtime failures remain saved.

## Development observations, 2026-10-03

Eight retained humanoid jobs cover sphere source/proposal and high-five
source/proposal in both modes. Each actor has 18,056 vertices and 36,108 faces.
All jobs complete after correcting the import reference; complete bind-function
correspondence agrees within 2.23e-16. The first eight captures imported successfully
but failed CPU correspondence at three weight-boundary vertices. Those captures
remain saved; the fix did not increase identity or motion tolerances.

| Matched motions, both modes | Engine times per job | Result |
| --- | ---: | --- |
| Sphere source/proposal | 1,036 | Pose, full-skin correspondence and sparse geometry pass; grip contacts fail |
| High-five source/proposal | 3 | Joint poses pass; contact, diagnostic plane and full-skin position limit fail |

Sphere grip errors are approximately 2.213–2.348 mm against 2 mm. Right-hand hold
speed remains approximately 10.18–10.22 mm/s against 5 mm/s. Geometry passes only
at the five authored geometry times. High-five hand separation remains about
206 mm for the source and 170 mm for the proposal against 30 mm. The diagnostic
Y=0 plane retains roughly 7–12 mm penetration against 5 mm; this is an explicit
test hypothesis, not a calibrated floor. High-five maximum imported/source skin
difference is roughly 0.130–0.138 mm, exceeding the separate 0.1 mm limit. All
eight jobs fail combined sampled conditions, and none selects a proposal.

A separate actual-engine fixture uses three surfaces, four/eight influences and
animation index 1 from a two-animation file. Both modes pass its authored sampled
conditions across 198 times. This validates import mechanics, not humanoid action
quality or general rig transfer.

Independent replay checks 8,268 contact point samples, all contact frame speeds
and 794,464 vertices at every geometry time. Contact coordinates agree within
2.23e-16 metres, and all 445 study files rehash. Full mesh-error curves between
geometry times are not independently replayed. All 299 focused model-free tests
pass, including corrupt bindings/topology, near-match ambiguity, clock omissions,
actual partner/object poses, Float32 normalization and provenance failures.
Detailed outputs stay local under ignored `reports/native-scene-engine-development-v3`,
`reports/native-scene-engine-multirig-v1` and `reports/native-scene-engine-validation-v1`.

No GPU skin buffers, rendering, physics, gameplay event playback, continuous
collision, self-collision, human review, training improvement or release approval
is established. All release capability gates and formal held-out trials remain
unchanged. Next work must address retained motion failures and extend validation
without treating successful engine import as realistic animation.
