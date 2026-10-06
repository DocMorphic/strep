# Surface checks on completed engine assets

Studio now binds authored surface-facing conditions to a completed **Scene
contacts** or **Root & game-track assets** package. The check applies to the
supplied contact scene rather than an action whitelist. It reuses saved engine
observations and resources; it does not sample, train or edit motion.

## Workflow

1. Finish the scene's existing saved-resource engine job. For root/contact/event
   files, also finish the separate game-track export.
2. Open **Check surfaces & package engine assets**, choose the source kind and
   completed job, and bind its exact scene, selected clips and package.
3. Review the surface declarations. A scene built from one passing Studio scene
   transfer inherits that transfer's declarations only when its complete scene
   intent still matches. Every transfer origin and actor assignment remains in
   provenance. Changed scenes or multiple origins require separately authored
   intent instead of silently dropping their constraints.
4. Supply one unit world/object normal per declared contact point, expressed in
   the target's coordinates, or the exact `partner-surface` declaration for a
   partner patch. Centroid contacts use one normal. Include the opposition,
   facing-side, area/coherence limits and complete actor-pose query budget.
   Changing any inherited surface policy requires explicit revision notes;
   the original policy remains retained.
5. Save the bound request or submit the check. Review every condition and the
   retained audit. The original clips and Studio selection remain unchanged.
   A separate checked ZIP becomes available only when all declared gates pass.

## Decisions and files

The imported surface verifier reconstructs complete imported CPU skin and, for
object scenes, uses the actual saved object-resource observations on the bound
clock. Source-native and native-authoring point and surface conditions must
pass. The parent scene's sampled conditions must pass independently. Game
packages additionally require their existing root-sample and event-helper
dispatch checks. The default-import comparison and its failures remain visible;
they do not replace the native-authoring decision. There is no new engine run.

`checked-assets.zip` preserves every original ZIP member byte for byte,
including scene intent, selected actor assets, animation resources, and any
root/contact/event files or runtime helpers. It adds only `surface-policy.json`,
`surface-audit.json`, and `surface-gate.json`. The portable policy changes only
its scene checksum to bind the packaged `scene.json`; normal intent and limits
stay exact. Root-motion application is unchanged. The audit keeps its original
source bindings; the ZIP is an asset package, not a standalone replay bundle.

Failed completed checks expose the bound request evidence, audit and replay,
but no checked ZIP. Partial or failed workers expose no completed downloads.
Serving and review validate exact member populations, source assets, current
and archived methods, resources, complete observations, typed decisions and
semantic replay. A content-hash cache reuses only unchanged verified evidence
and returns copies; changed source bytes force full verification.

The loopback-only API uses `GET /api/surface-export-source?kind=scene|game&id=…`,
`GET /api/surface-export-jobs`, `GET /api/surface-export-review?id=…`, and
`POST /api/surface-export-assets`. Requests use
`strep-studio-surface-export-v1`, exact `source` kind/job/result checksum,
`surface`, `normal_origins_sha256`, and `normal_revision` (`null` or revision
notes). Submission retains the existing single-worker and offline environment
rules. Stale source bindings and changed normal intent reject before dispatch.

## Validation scope

Generated small skins exercise CPU decoding, complete surface replay, scene
and game package preservation, negative gates, inherited intent, rehashed
tampering and cache invalidation. Parent manifests and engine subprocesses in
the new backend tests are explicit test doubles. Offline mock DOM/API checks
exercise source binding, query limits, revision requirements, stale selections,
submission races and fixed downloads. Existing scene, game-track, imported
surface and desktop build regressions are checked alongside this integration.

These checks are software evidence. This integration has not been loaded in a
live Studio session. Winding normals
do not establish anatomical palms, physical grasps, natural motion or action
correctness. Transition review, dynamics, continuous/self collision, GPU and
real-time playback, production rigs, developer/animator review and cleanup-time
evidence remain separate. Quality, training, human-review and release approval
stay false; the full-project goal remains active.

The initial model-free regression run passed 163 cases and exposed one Windows
ZIP fixture mismatch: `ZipInfo` normalized the intended hostile backslash
header before writing. The fixture now writes the literal header; the backend
also rejects any normalized filename that differs from its original header.
All 50 new backend cases pass after this fix, and four offline Node suites
pass. The 114 unchanged scene, game-track, imported-surface and desktop cases
retain their initial passes. Frozen archives and current source hashes match.
The parsed CI proof adds only the new Python and Node suites, preserving every
other workflow field, pin, dependency, permission, matrix and time budget.

A new serial headless study reuses the preceding generated two-character scene
transfer fixture. The ordinary scene job saves and reloads both actor resources
and the object resource; the game-track job verifies extracted root references
and finite event-helper dispatch. These prerequisites use three owned Godot
processes, all terminal with zero exits and clean logs. The new surface wrapper
then inherits the exact one-degree normal policy, replays complete imported
observations, and produces a checked game ZIP with every original member byte
unchanged. An explicitly recorded half-degree policy fails facing conditions
while scene, point and root/event gates still pass; it exposes five audit files
and no checked ZIP. An unrecorded policy change rejects before preparation.
Neither surface check starts another engine process. The preceding study's
files and all current/archived methods remain unchanged; the worker lock is free.

The moving roots, box, partner/floor contacts and gameplay marker are generated
software fixtures, not production action quality, anatomy, physical interaction,
independent human review or release evidence. The source-check receipt is
`1a68b839211de5f94ef8f3ad40b19c77263d975132c80602622facf112b39849`;
the actual study receipt is
`6e8ce8194c6ef00719598f0a7f3dfb29b9869bb320a6eb0f73637c51cb90fb38`;
the parsed workflow proof is
`f197078b686e1b6ea62e72d9ce218921e32872e89ac7ac89263ae76900d9933d`.
Generated outputs remain local under ignored `reports/`.
