# Source-bound native prop runtime package

`scripts/scene_prop_runtime.py` exports an existing native game asset ZIP with
explicit source-joint grips and per-prop ownership modes. The Godot main scene
imports the original actor GLBs, installs their saved native resources and binds
the shared prop owner automatically. Applications supply a world, floor/colliders,
camera and gameplay listeners. Studio authoring for these bindings remains open.

Every source actor retains its chosen embedded/extracted root mode. Every source
prop explicitly chooses `authored` playback or `grip-physics`. Authored props keep
their native tracks and visible meshes. For a physical prop, the original animated
mesh stays hidden as an authored reference; a separate rigid body uses a copy of
its imported mesh resource, matching centered primitive collision geometry and
uniform inertia. The source mesh never receives a physics transform. Source
contact measurements describe that unchanged reference, not the physical copy;
they cannot certify physical grip/contact success.

## Author and export

Use a `strep-native-scene-game-package-v1` input from the existing native game
asset export. Supply the complete source ZIP SHA256 and explicit root modes for
all actors and ownership modes for all props. Choose existing source GLB skin
joint **node indices**; bone names, actor file hashes and animation indices are
resolved and bound to those choices rather than guessed from prompt text. Each
commanded grip/prop pair needs a rigid 4x4 bone-to-prop-center offset in meters.
Different props can have different offsets for the same grip.

An example request structure follows; replace its hash, joint node, offset and
event IDs with choices from your actual source:

```json
{
  "schema": "strep-scene-prop-runtime-request-v1",
  "source_game_zip_sha256": "REPLACE_WITH_COMPLETE_SOURCE_ZIP_SHA256",
  "root_modes": {"A": "embedded", "B": "extracted"},
  "object_modes": {"item": "grip-physics", "reference": "authored"},
  "grips": {
    "left": {
      "actor": "A",
      "joint_node": 0,
      "prop_offsets": {"item": [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}
    }
  },
  "commands": [
    {"event_id": "marker:grasp", "object": "item", "grip": "left", "action": "acquire"},
    {"event_id": "marker:drop", "object": "item", "grip": "left", "action": "release"}
  ],
  "physics": {
    "item": {
      "mass_kg": 2,
      "friction": 0.6,
      "restitution": 0,
      "linear_damping": 0,
      "angular_damping": 0,
      "collision_layer": 1,
      "collision_mask": 1
    }
  },
  "physics_fps": 120,
  "history_capacity": 1800,
  "position_tolerance_m": 0.001,
  "rotation_tolerance_rad": 0.001
}
```

```powershell
python scripts/scene_prop_runtime.py GAME_ASSETS.zip OWNERSHIP_REQUEST.json FRESH_OUTPUT_DIRECTORY
```

The original events must already contain timing-confirmed gameplay intent for
these exact IDs/actors. Contact boundaries never create ownership commands.
Acquisitions/handoffs must be continuous within the chosen pose bounds; offsets
are authored bindings, not an alignment solver or an anatomical grasp model.
Set all desired source markers and timing first using native game track authoring.

The output includes `prop-runtime-assets.zip`, a source ZIP snapshot, a complete
staged `project/` and packaging/failure receipts. The portable ZIP retains every
original source file byte-for-byte; the original manifest is renamed
`source-game-package.json`. It adds the exact original authoring request bytes,
compiled source-bound configuration, frozen runtime scripts, a main scene and
project settings under `ownership-v1/`. ZIP paths/hashes/population are checked
before extraction and after readback; there is no partial resource fallback.
Original ZIP limits are 256 entries/1 GiB, and complete output is bounded to
fewer than 512 entries/1 GiB. Fresh output and reserved-entry conflicts reject.

The public repository does not bundle models, character assets, engine binaries
or dependency environments. Existing third-party model/asset licenses still
apply. This packaging CLI needs the established model-free NumPy/SciPy/Trimesh
environment and available source assets; it does not run Godot, a model or new
motion generation and cannot grant physics or quality approval.

## Game startup and ownership

Extract the ZIP as a Godot project or copy its complete relative layout into your
game. Instance `ownership-v1/scene.tscn` under a rigid, stationary world placement
node. The generated project configures Jolt and the chosen 60/120/240 Hz step
before startup. In an existing project, explicitly configure the matching step
before engine startup; unsupported rates/changed steps reject.

The child imports and binds in `_ready()`. Connect from the parent's `_ready()`
to `gameplay`, `actions_applied`, `sampled` and `faulted`; the initial marker
arrives on the first physics callback after parent readiness. The boot scene has
no wall-clock/process animation driver: only the shared owner advances actors
and native authored references. Root transforms are already applied in extracted
mode; do not apply them a second time. `sampled.physics_root_deltas` covers the
complete boundary, including intermediate marker visits.

The exported scene exposes `pause_playback()`, `resume_playback()`,
`restart_playback()` and `preview_tick(tick)`. Their queued command/history and
saved-live-cursor semantics match the
[shared ownership SDK](../integrations/godot/SCENE-PROP-OWNERSHIP.md). Other world
objects, contact caches and external gameplay side effects are not rolled back.
All physical grips must agree; conflicting providers or missing callbacks fault.
Failed imports/late bindings free only the staged container, leaving existing
game nodes intact. `last_error` identifies the failed binding stage.

Node indices and original names are cross-checked against the source GLB at
runtime using Godot's [GLTFNode metadata](https://docs.godotengine.org/en/stable/classes/class_gltfnode.html).
Physically controlled bodies are separate from the immutable native reference
graph; source contact events/measurements must not be treated as measurements of
their simulated poses. Held/parked/paused/previewing bodies have disabled collision
masks. Characters and their grips remain prescribed and cannot physically react
to props. Moving/scaled parents, competing pose/physics drivers, blending,
continuous collision certification and arbitrary world rollback are unsupported.

## Current evidence and failures

The serial headless `scripts/study_scene_prop_runtime.py` study builds tiny
procedural skinned GLBs and saves actual native Animation resources in Godot.
Two copies of one generated rig, one physical sphere and one authored sphere
exercise the complete native game ZIP → explicit binding ZIP → imported
actor/resource/mesh → actual body path. Grip joints are explicitly chosen root
nodes with artificial offsets; this is an integration fixture, not evidence of
anatomically plausible hands, partner reaction or successful motion generation.

Two cases at 120 Hz use elevated identity and translated/rotated rigid parent
placements. Each completes 533 boundary records, eight prop transactions across
two traversals, two-hand acquisition, partial release, A-to-B handoff, physical
release/floor contact, silent preview, saved-state resume and restart. All actors,
the visible authored prop and the hidden source reference stay on the native
clock while the physical copy simulates. Twenty malformed staged bindings reject
without leaving participant nodes behind. Maximum held/visible-authored pose
matrix-element errors are 2.091e-7 and 1.572e-7; the original 3e-5 limits stay
unchanged. Root-delta checks here include the fixture's static root; the prior
ownership study separately exercises moving roots across marker substeps.

The actual exported `.tscn` boot is also instantiated under a parent listener,
with 361 additional physics records, all six confirmed markers, initial parent
readiness, four prop transactions, floor contact and source pose held at 2 s
while physics continues to 3 s. Every callback's source and visible pose time is
checked against the original Float64 clock **bytes**, including the 1/480 s
marker; equal rounded JSON decimal strings cannot satisfy that check. Total:
**1,427 recorded boundaries, 20 prop transactions and 28 exact-clock callbacks**.

**Exact physical event timing still fails.** The 1/480 s partial release applies
6.25 ms late at 120 Hz, even though native callbacks retain exact binary timing.
Both new positive cases have zero observed sampled floor depth, which does not
erase the earlier 60 Hz 63.229 mm failure or establish general collision safety.
There is no fractional physics solver or hidden source-time rounding. The mesh
copies retain imported geometry; fresh GPU appearance has not been checked.

Final local result: `reports/scene-prop-runtime-engine-v9/result.json`, SHA256
`64528f950ea63a1e761deb8a0ebce974185086f1fc3a604bb2322c1ed0d0cada`.
Executed GDScript and package/study Python method hashes match frozen copies.
Every packaged original file and runtime helper is checked after engine runs.
All owned study commands are terminal/accounted. Earlier failed attempts remain
preserved: Float64-vs-integer homogeneous-row array comparison, an existing
multi-object loader indentation defect and a verifier that incorrectly expected
a terminal marker in the intentionally shorter second traversal. Diagnostics and
corrected runs do not alter source event clocks, pose limits or collision screens.

The loader fix assigns a prop ID only to its matching imported mesh. Previously
the assignment was outside the matching-name branch, so the first mesh populated
every ID and the next mesh was rejected as a duplicate. The actual mixed two-prop
import and complete-population checks now cover this path.

No production anatomical/skin query, model sampling/training, GPU rendering,
live Studio/server/browser access, human rating, cleanup measurement or held-out
release evidence was created. All source contact failures remain in exported
files. All fourteen release evidence arrays are empty and the full-project goal
remains active. Next work is explicit Studio joint/offset authoring, review of
production contact intent and improvement of the measured physical limits.

Final isolated public-source regression: **281 passed, four explicit engine
skips in 48.64 s**, including 29 package/binding/binary-clock tests and the
existing native scene/root/ownership and cylinder regressions. This source run
uses tiny generated fixtures and engine doubles where indicated; actual import
and physics evidence comes from the separate engine study above. Source result
SHA256: `e7a7ffe43aefe3cd86342785e55332cfe143ed159fd114e17e6b5112f9e1acf1`.
