# Studio character correction and preserved source epochs

The Character window's **Correct character motion** panel connects scene drafts
to bounded native character correction. It supports body patches against world
points, declared moving objects and partner patches. Action labels are unrestricted;
this workflow edits supplied clips, rather than generating motion or demonstrating
that arbitrary actions are realistic.

## Authoring and review

1. Assemble the clips, placements, contact patches, timing, object trajectories
   and geometry policy in Scene contacts. Turn off the separate object-edit
   request: this character solver uses the declared object paths. Simultaneous
   character/object optimization is still unfinished.
2. Load scene joints. Every skin-joint rotation/translation path is listed.
   Editing requires one existing LINEAR native channel with at least three keys;
   unavailable paths carry a reason. The interface makes no automatic anatomical
   selection and does not truncate the joint population.
3. Select tracks and explicit rotation bounds in degrees or translation bounds
   in millimetres. Set the edit window, ordered control times, protected time
   ranges and maximum world-space joint displacement. Save bounds separately for
   each character to edit. Unselected characters remain unchanged.
4. Save the complete request or propose a correction with 1–16 primary iterations.
   The backend limits the request to 96 control components, 16 tracks per actor
   and 3–12 control times. Each interior time contributes three components per
   track. Invalid permissions are rejected before job creation.
5. Refresh jobs and inspect source/proposal downloads and measured failures.
   The selected source remains unchanged. Staging requires recorded native and
   sampled geometry checks to pass and replaces all scene actor references
   together, only after an explicit click. This creates a new draft; it does not
   approve animation quality. Build its scene/game assets for engine checks.

The numerical configuration uses storage-vector proposals, central differences
at 0.001 normalized units, unit quaternion storage, a 0.02 trust bound, three
candidate-centered restoration models and at most 64 serialized ray probes.
These are proposal settings, not realism thresholds. Decoded contact conditions,
original source-rate limits, edit bounds and protected keys remain authoritative.
The existing solver retains every trial and accepts only measured safe improvement.

## Continuation and provenance

Load a completed correction to continue its original source epoch. Ordinary
continuation preserves exact actor bytes, permissions, contact intent, geometry
clock/planes/limits and original source-rate cap arrays. It replays the prior
final controls before attempting more correction. Changing edit freedoms requires
a separately authored experiment; continuation cannot silently widen them.

Explicit source/partner patch revisions can continue within that same epoch.
Their receipt permits only the declared mesh-reference/reduction changes; contact
timing, targets, limits and every other scene field remain protected. Both prior
and revised contact intents are audited on the proposal. A fresh draft with
revision provenance also retains and audits its baseline contact intent.
Patch changes are not anatomical approval or evidence of improved animation.

Each fresh job snapshots submitted clips, contacts, permissions, geometry,
implementation, source hashes and request options. Per-job and shared worker
locks prevent concurrent duplicate execution. Failed partial jobs remain intact;
completed requests are revalidated and reused rather than overwritten. Serving
checks source snapshots, fitter archives, probe receipts/exports, original cap
archives, contact observations, geometry observations/receipts and the complete
fixed download population. These integrity checks establish file provenance,
not independent semantic or physical correctness.

Jobs use the configured local Python runtime and offline dispatch environment.
The optional conic solver must already be available. No model inference, training,
remote execution, dependency download or automatic Studio source promotion occurs.
The new routes and editor are included in the checked-in desktop build; this
implementation has not been exercised through the currently running Studio server.
Its existing process remains untouched.

## Development crawl: expanded controls still fail

A separate finite control-completeness experiment added rotation permissions for
four distal leg nodes (6, 7, 10, 11) to the retained crawl: 78 components across
13 tracks, versus the earlier 54 components across nine tracks. Both use the
same previously floor-restored first native actor, original source-cap arrays,
contact intent, 1.3–2.3 second window, 20-degree added rotation bounds, two primary
iterations and three recentered restoration models. The expanded contract does
not replace or claim to pass the older permission contract.

All 160 complete exports were independently decoded, byte-replayed and audited.
No correction was accepted. Native conditions still fail; sampled floor conditions
pass. Added shin-channel skin weights on the two selected shin patches average
approximately 0.0175; the added foot channels have zero direct weight there.
More permitted joints alone did not resolve this example.

The final container hash is
`7d5db64eb3c245055ac5b6409e7ecea88ac0bdae75b2f56adf8647ed9b5fb6c3`.
It differs from the earlier container because additional channels were rewritten;
zero controls preserve the complete decoded native pose population. No new engine
run verifies this container, and earlier engine evidence for different bytes is
not reused as proof. The original benchmark and permission files remain unchanged.
An earlier preparation failed on a nonexistent actor metadata key before fitting;
that failure and the repaired immutable trial are retained locally.

Local study records: `reports/native-crawl-distal-control-completeness-v2/checks.json`
and `reports/studio-native-scene-fit-validation-v1/`. Public documentation contains
methodology and scope; generated clips, observations and local paths stay ignored.
This is development evidence only. All release acceptance gates remain open;
humanoid semantic ratings, animator cleanup, held-out coverage and realistic
interaction success still require evidence.

## Software validation

On 2026-10-04, the final backend/build group passed 152 Python cases. Six
subsequent actor-admission/integration cases passed, including two new cases;
the union is 154 unique cases. They exercise actual procedural CPU correction,
ordinary and patch-only continuation, world/object/partner targets, frozen source
caps, unchanged actors, malformed requests, duplicate workers, failure retention,
modified observations/archives and inconsistent or rebound decisions. HTTP tests
use offline handler stubs, with no live server connection. The initial malformed
saved-draft test exposed a KeyError; the corrected implementation rejects it
explicitly and the final suite passes. Earlier logs remain locally retained.

Four Node DOM workflows and two syntax checks passed. They cover existing scene,
patch-revision and game-track editors as well as the new correction editor.
New coverage includes explicit bounds, stale requests/responses, failed proposal
retention, atomic actor staging and continuation. The generated desktop HTML
matches its editable source and contains each control once. This establishes
source/workflow checks, not a rendered or live Studio UI review.

An actual wrapper canary also completed on the retained humanoid crawl, with six
explicit root-only controls and one primary iteration. It resolved the original
saved scene clip through the existing file-serving validator without HTTP,
snapshotted current methods, completed native fitting and contact/geometry audits,
revalidated every fixed download, and reused the completed job without rewriting
it. Original source bytes and all original source-rate arrays remain exact.
The fitter retains 140 exports; native contact conditions fail and sampled floor
conditions pass. This is a small integration canary, not a successful crawl repair,
held-out action, engine import or semantic benchmark. Its six-control permissions
are explicit and separate from the earlier 54/78-control experiments.
