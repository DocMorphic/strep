# Studio scene transfer and bounded calibration

Studio can carry an explicitly authored scene onto completed native character
transfers. This is an authoring workflow for any supplied action/contact scene,
without an action whitelist. It uses the unchanged native transfer and surface
calibration methods. It does not train or sample a model.

## Authoring workflow

1. In **Scene contacts**, assemble the exact characters, selected clips,
   placements, contact patches, targets, timings, limits, object paths and
   declared geometry checks. Turn off the separate object-edit proposal.
2. Finish **Native clip transfer** for each scene actor that needs a new rig.
   Select its actual source clip and saved source/target mappings. These jobs
   must finish their saved-resource and root-playback checks.
3. Open **Transfer a scene to new characters**, load the current scene and
   completed transfers, and choose an actor's matching transfer.
4. Load its required contact vertices. The source population includes both its
   effector patches and every incoming partner target. Supply one distinct
   target reference for every required source reference, with no extras.
   A picked target patch can fill the inputs in its displayed order only when
   its asset digest and complete vertex count match. Review that order yourself;
   neither joint names nor nearest vertices establish anatomical correspondence.
5. Choose the mapped reference rotations that may change, bounded in degrees,
   an optional root offset and the maximum joint-origin movement. Save each
   actor's correspondence and bounds. Multiple actors are supported.
6. Author target normals for every contact: one unit normal per world/object
   contact point in that target's coordinates, or `partner-surface` for an exact
   partner patch. Author the normal angle/side/reliability limits and full query
   budget. Choose a bounded search budget. No normals are guessed from anatomy.
7. Build the separate transferred scene. Review original inputs, the unmodified
   transferred point comparison, candidate contact/surface/geometry measurements
   and motion bounds. Failed searches and incompatible reach preflights stay
   retained. A complete fit does not imply that its conditions pass.
8. Explicitly stage a passing result as a new draft, then build and review
   **Scene contacts** assets for saved-resource engine checks and previews.
   Recheck transition endpoints and animation quality before game use.

The active original draft stays untouched during submission and review. Staging
refetches the exact result and requires the active draft still to match the
submitted source draft. It changes only explicit actor/clip selections and mesh
correspondence. World/object targets, partner identities, placements, timing,
limits, object paths and geometry conditions remain protected. This is an
explicit new rig/clip epoch: the old draft, upstream transfer mappings and
calibration lineage remain in the immutable job. A contact revision's old-rig
receipt stays in provenance rather than being falsely attached to the new rig.
Unchanged context actors keep their original served URL, digest and clip index
in the staged draft, preserving any existing correction lineage. The portable
candidate ZIP also includes their exact unchanged GLB snapshots.

## Backend contract

`POST /api/native-scene-transfer-catalog` takes `{draft, transfers}`; each
selected transfer binds its completed Studio job ID and exact result SHA256.
The catalog rejects another actor, source clip or duration and returns the
complete required source vertices, original target asset digest, saved mapped
roles and output animation index. It never infers correspondence.

`POST /api/native-scene-transfer-assets` takes
`strep-studio-native-scene-transfer-v1`, with `draft`, `transfers` and
`calibration`. Each transfer also contains `vertex_map` pairs of exact
`[mesh node, primitive, vertex]` source and target references. Calibration uses
the existing explicit `actors`, `surface` and `search` contracts.

The same loopback Host/Origin, JSON, 1 MiB and single-worker gates apply as to
existing Studio jobs. Catalog reads do not launch a worker. The worker snapshots
all actors and authoring inputs, binds completed upstream transfers, archives
the complete implementation, checks original files throughout, runs the scene
bridge and then the surface-aware bounded calibration. Stage tools keep their
existing OS worker locks; the orchestration lock is per job and does not nest
those global locks. A failure retains partial evidence and exposes no completed
downloads.

`GET /api/native-scene-transfer-jobs` lists states;
`GET /api/native-scene-transfer-review?id=...` reviews one exact job. Review
replays prepared input/source bindings, explicit correspondence, full common
clock observations, calibration permissions/search, original motion caps,
native transfer fidelity, authored normals, full declared geometry and typed
scope flags. Rehashed summaries alone cannot manufacture a passing result.

Verification of an identical completed result may be reused within the server
process. Its cache key hashes the complete job payload, archived/current methods,
live original actor files, complete upstream job payloads and their original
saved assets/profiles. It does not use modification times or trust an on-disk
verification claim. A changed or added file, live dependency or method invalidates
the cache and requires full replay. The upstream pipeline state is included,
because the selected transfer must still be complete. This job's mutable
pipeline/worker/supervisor state files contain no measurements and are excluded
from that identity. Entries are
bounded to 32 and are never shared as mutable result objects.

Only a fixed download population is served. It includes the exact result,
original authoring draft, correspondence, authored conditions, native comparison
and, when a candidate exists, every actor GLB, relative-path scene JSON, separate
stage draft, audits/bounds and an exact-member ZIP. Input snapshots, method
archives, raw solver/engine evidence and arbitrary paths are not download routes.
Failed numerical conditions can retain candidate files for review, but expose
no passing stage draft. A necessary reach conflict exports no candidate.

## Scope and remaining work

The staging gate requires strictly true decoded contact, source-rate,
joint-displacement, common-clock normal, sampled surface and declared geometry
checks. It keeps engine, anatomical, human-quality, continuous-collision and
release flags strictly false. The candidate ZIP contains authoring assets; it
is not a final game-engine release package. This Studio job does not run its
own engine stage. The separate scene asset workflow must check saved resources;
imported surface-facing evidence remains separately measured and is not implied
by the basic scene import check.

Whole-clip reference changes can alter start/end poses. Self-collision,
continuous-time contact/collision, dynamics, physical grasp, natural action
semantics, arbitrary production rigs and timed human cleanup remain open.
Numerical success on generated closed cube skins does not resolve those tasks.
The full project goal remains active; no release evidence is admitted here.

No live Studio HTTP calls, browser/rendering, server restart, GPU checks,
production anatomical queries, new model sampling or training are needed for
the model-free source validation.

## Validation

The frozen final source check passes 98 Python cases with zero skips, including
47 scene-transfer contracts plus existing scene and desktop-build regressions.
All four selected Node editor suites pass. Coverage includes multiple selected
transfers, incoming partner references, authored unit normals, explicit bounds,
stale responses, fixed downloads, protected staging, unchanged context lineage,
rehashed published tampering, cache copy isolation/dependency invalidation,
read-only catalog access, loopback/worker gates, retained failures, negative
geometry and a necessary reach conflict that exports no candidate. These tests
use explicitly labelled upstream engine doubles and generated skins; they are
not actual engine or motion-quality evidence. All archived/current checked
source hashes agree.

Source receipt SHA256:
`18a627dbaa646bc532812472b0639b6a66172bbb54610b3821960cab3a7a31b6`.
The parsed workflow proof adds only one Python and one Node suite, preserving
all other fields, pins, dependencies, matrices and time budgets. Proof SHA256:
`a96155182871208ed212f363ff74295a8f6b9c67f07c0fb3ccc6bec252f50e16`.

A separate actual CPU/headless study runs the complete Studio character-transfer
and scene-calibration workflow on independently generated closed skins, moving
roots/box, reciprocal partner contacts and a floor. Both upstream engine stages
pass, and the packaged candidate saves/reloads two actor resources and queries
416 complete scene clock times. Imported pose, raw skin, object transforms,
contacts, declared geometry and winding-normal conditions all pass unchanged
limits. Maximum imported opposition error is 0.9990157 degrees under the authored
1-degree limit; skin error is below 3.84e-7 m and pose component error below
3.46e-7. All three owned engine processes exit zero with clean logs. Inputs stay
unchanged, archived/current method hashes match, and the worker lock is free.
The isolated study's imported surface audit remains separate from the Studio
staging gate and basic scene export checks.

Actual study SHA256:
`b7e69d87210b90423bd1e104de0d18e40d49daef64a09c0d9d955dcbca3eba21`.
Retained outputs are under ignored `reports/stj-engine-v1/`; source validation is
under `reports/studio-scene-transfer-source-check-v1/`. No live HTTP/browser,
server restart, rendering/GPU check, production anatomical query, model run,
training or human review was performed. This is software integration evidence,
not realistic motion, physical interaction or release approval.
