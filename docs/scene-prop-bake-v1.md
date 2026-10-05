# Offline editable prop motion bake

`scripts/scene_prop_bake.py` captures a finite, explicitly bound native prop
runtime and saves the resulting prop motion as editable GLB tracks and a Godot
Animation resource. Playback of those tracks does not need live prop physics.
The original actor clips, embedded root motion, mesh payloads, confirmed marker
intent and authored contact references remain available alongside the bake.
This is an offline CLI workflow; Studio selection and the live server are not
changed. It does not generate motion or repair an unsuccessful interaction.

## Run

First prepare a complete [native prop runtime ZIP](scene-prop-runtime-v1.md),
including explicit joint/offset bindings, root choices, physical settings and
confirmed ownership events. Only the current trusted runtime scripts execute.
The source ZIP, original files and compiled bindings are verified in full.

Use a request with exactly these fields, replacing the digest with the SHA256
of that ZIP:

```json
{
  "schema": "strep-scene-prop-bake-request-v1",
  "source_runtime_zip_sha256": "<64-character source ZIP SHA256>",
  "parent_world_transform": [[1,0,0,0],[0,1,0,2],[0,0,1,0],[0,0,0,1]],
  "floor": {"enabled": true, "height_m": 0, "friction": 0.6, "restitution": 0}
}
```

The parent must be a stationary rigid transform. The optional floor is a world
Y plane, independent of the parent. No additional scene collisions are inferred.
The command uses the shared worker lock and the existing pinned Godot 4.7.2
binary at `.cache/godot/4.7.2-stable/`; that binary is not distributed here.
Use the configured project Python environment and a fresh output directory:

```powershell
python scripts/scene_prop_bake.py path/to/prop-runtime-assets.zip path/to/bake-request.json reports/my-prop-bake
```

The finite physics clock uses the package's selected 60, 120 or 240 Hz rate.
If the original clip ends between boundaries, capture continues to the first
complete boundary and holds the original actor end pose. Exact source clocks
and physics clocks are separate. The complete capture is bounded to 14,400
physics steps and the portable input/output files to 512 entries and 1 GiB;
oversized work is rejected without truncation. Failed logs and raw outputs stay
in the fresh directory. Owned engine processes are stopped on timeout.

## Outputs and checks

`baked-assets.zip` contains:

- `objects.glb`: physical prop TRS tracks with the original mesh/material bytes;
  authored prop channels remain unchanged.
- `objects.res`: saved and reloaded Godot Animation tracks.
- `composition.json`: original actor paths and placements, embedded-root/end
  policy, baked prop path, stationary parent and optional world floor.
- `reference/`: complete original game assets, native resources, root tracks,
  event/contact intent and original package manifest.
- `bake-storage.json`, `bake-audit.json`, `import-audit.json` and
  `baked-motion-audit.json`: storage, physical application, engine fidelity and
  sampled grip/floor observations, each with separate approval flags.

The private output directory also retains the original runtime ZIP, exact
request, implementation hashes, raw capture, engine logs and terminal receipts.
All original file hashes and current implementation copies are checked again
before completion; the complete final ZIP and manifest are read back.

glTF animation clocks and poses use Float32 storage. The bake resamples at the
stored timestamps and reports rounding; collapsed timestamps are rejected.
Original event intent and capture clocks keep their Float64 binary evidence.
See the [Khronos glTF specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)
for animation accessor storage.

Engine evaluation covers every physics boundary, midpoint and original native
event/key time. Both the configured GLB import and saved native resource must
stay within the unchanged `3e-5` pose-component bound. A separate 30 FPS import
diagnostic is retained. Godot's
[GLTFDocument.generate_scene](https://docs.godotengine.org/en/stable/classes/class_gltfdocument.html#class-gltfdocument-method-generate-scene)
accepts an explicit animation bake rate, with a 30 FPS default; the exported
track must be imported at its declared bake rate or revalidated.

Ownership event intent and physical application time are compared separately.
Between-boundary grip observations use all explicitly active bindings on the
physical application timeline. Sampled analytic prop-floor depths use the
existing 10 mm screen. These are recorded conditions, not continuous collision,
anatomical hand contact, body clearance, partner reaction or quality approval.
Original authored contacts describe the source reference, not the new dynamic
trajectory. The SDK uses Jolt direct-state callbacks; see
[RigidBody3D integration](https://docs.godotengine.org/en/stable/classes/class_rigidbody3d.html#class-rigidbody3d-private-method-integrate-forces).

## Development measurements

Three actual serial headless cases use the same tiny two-second generated
package: duplicate test rigs, one physical sphere, one authored sphere,
explicit root-joint offsets, two holds, partial release and handoff. Parent
transforms are elevated identity and elevated 30-degree Y rotation; the latter
also runs with its floor disabled. These are software fixtures, not anatomical
hands, independent rigs or production animation evidence.

Each case completes 241 physical boundary records and evaluates 492 baked
sample times. Across all three cases the configured 120 FPS GLB import stays
within `3.745e-7` pose-component error and saved native tracks within `1.076e-7`.
The 30 FPS diagnostic fails in every case: about 9.985 mm near floor impact and
1.361 mm without the floor. The original failed 30 FPS pipeline remains saved;
the bound was not relaxed. All nine final engine stages exit zero with clean
logs and unchanged source/method hashes.

The maximum physical event delay remains **6.25 ms** in all cases, so exact
physical event timing fails. Sampled explicit grip agreement passes with a
maximum 0.06001 mm positional error. Enabled-floor samples pass the existing
screen; disabled-floor results remain N/A. These results do not replace the
earlier 60 Hz floor failure or prove broader interaction success. All quality
and release approval flags remain false.

The focused model-free suite passes 28 tests. Synthetic trace/engine doubles
test incomplete capture rejection, exact clocks, source preservation,
box/sphere/cylinder track export, non-grid clip ends, malformed imports,
timeouts and retained grip/floor failures. Those doubles are not actual
physics evidence. The full-project release requirements remain unmet.

Local final engine result SHA256s:

| Case | Result SHA256 |
| --- | --- |
| Elevated identity, floor | `3c57bc6f52e8b3c4b515213257c3f0e7e2239fa651b89b014489c4f28ee6868b` |
| Elevated rotation, floor | `519a2efe91c45ad42624f9cf5dc86b43a2e569b76faea85c0016e7918c677303` |
| Elevated rotation, no floor | `bb4612c9dfbee6e3f15ccfbc9d0a7d50a15074b210d581559337e54fc822a658` |

The combined local receipt SHA256 is
`e7902e6101890e8f5399abbea1c32793e7c7d4f1d1a1166e71c7943786e08586`.

The final frozen regression covers 231 passing tests and 0 explicit
engine skips across prop bake/runtime/ownership, native scene/clock/object
assets and Studio grip packaging. All source/copy hashes remain bound. Its
local result SHA256 is `ce59b02418d1892f9edf383d088e52516390d974e800b3fc35641cd6d32b2888`.

Follow-up: [Studio prop animation baking](studio-prop-bake-v1.md) connects this
CLI to source-bound asynchronous authoring and completed download validation.
Its headless worker fixture adds workflow evidence while retaining the timing,
import and interaction-quality limits above; live browser verification remains
separate.
