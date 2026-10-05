# Studio grip authoring

The character workspace includes **Grips & physical props**, beneath **Root &
gameplay tracks**. It authors bindings around an existing completed game-track
package. Original animation clips, contact measurements and recorded failures
remain unchanged. A successful package export is not physics or motion approval.

## Authoring

1. Select a completed game-track job and choose **Use selected game package**.
   The draft binds its result hash and complete source ZIP hash.
2. Choose embedded or extracted root motion for every actor. Choose authored
   animation or grip/physics playback for every prop, including reference props.
   At least one prop must use grip/physics playback.
3. Choose an actor, an actual source skin-joint index, a prop and a grip ID.
   Enter a rigid offset from that joint to the prop center. Translation uses
   meters; rotation uses degrees applied X, then Y, then Z. Nothing maps a joint
   to a hand automatically. Each grip can carry separate offsets for multiple
   props; different joints require separate grip IDs.
4. Optionally select a confirmed event for that actor and choose **Align offset
   at selected event**. This evaluates only the selected source joint at the
   exact event clock and aligns it to the parked source prop pose at time zero.
   This can supply a starting offset; it does not establish anatomical contact
   or a believable grasp. Inspect and adjust the offset before saving it.
5. Save the grip and add acquire/release changes using confirmed events belonging
   to its actor. Partial releases keep remaining grips. For a handoff, both
   actors need confirmed events at the same native time. The server compiler
   validates complete ownership membership and atomic handoffs.
6. Choose an explicit 60, 120 or 240 Hz physics rate, finite history capacity,
   grip agreement tolerances and physical settings. **Save grip request** saves
   the source-bound draft. **Build prop runtime package** snapshots and packages
   it asynchronously, subject to the existing single-worker lock.
7. Refresh the job list and show its results. Only completed, validated jobs
   expose the fixed download population. Failed jobs retain their request and
   failure receipt without offering a partial package.

Changing the selected game package invalidates the binding. An alignment reply
cannot overwrite fields edited while it was pending, or fields belonging to a
different binding. Rebinding clears the old draft. This initial editor saves
drafts but does not yet restore saved draft files into its controls.

## Source integrity and local API

`studio_scene_prop_runtime.py` archives the request, source game ZIP and complete
implementation population. It rechecks them before and after packaging. Reviews
verify completed receipts, fixed downloads, ZIP members, original source bytes,
archived runtime helpers and compiled configuration against the bound request.
Rehashing a changed exported helper, source asset or joint configuration does not
turn it into the approved source-bound package.

Read endpoints are `/api/scene-prop-runtime-source?id=...`,
`/api/scene-prop-runtime-jobs` and `/api/scene-prop-runtime-review?id=...`.
Source and review requests require exactly one ID. Same-origin local JSON POSTs
use `/api/scene-prop-runtime-align` and `/api/scene-prop-runtime-assets`; both
retain the existing body budget and worker gates. Neither alignment nor
packaging invokes the motion model, engine, renderer or anatomical skin search.

Completed download entries are `runtime/prop-runtime-assets.zip`,
`runtime-request.json`, `runtime/result.json` and `result.json`. Source snapshots,
implementation files and arbitrary project paths are not served. Runtime
behavior and the portable standalone request are described in
[the native prop package documentation](scene-prop-runtime-v1.md).

## Limits and validation scope

This editor does not repair the motion, synthesize partner reactions or make
prescribed character motion respond to forces. Original scene contact results
describe the unchanged authored reference, not the dynamic prop trajectory.
The earlier exact physics timing failures remain, as does the 60 Hz collision
depth failure. Those results are documented in
[shared prop ownership](scene-prop-ownership-v1.md).

Validation uses tiny generated fixtures, explicit upstream saved-job/engine doubles,
offline handler stubs and a JavaScript DOM double. It checks request integrity,
source preservation, event/joint selection, alignment math, stale replies,
ownership drafts, failed-job serving and generated Studio source integration.
It is not live browser, production character, new engine, rendering or human
review evidence. The full-project release criteria remain unmet.

The broad frozen run passes 223 tests and four offline editor suites. Final
source checks after the method-archive and nonrigid-alignment guards pass 75
targeted tests, including all 42 new backend cases, and the same four editor
suites. Only the backend and its test file changed between these snapshots;
shared regressions retain their original result. Canonical startup files use
identical UTF-8 bytes across platforms and remain bound to the selected rate.
The first upstream test fixture omitted native keys and was rejected; replacing
it with a complete-clock fixture did not relax the runtime contract.
