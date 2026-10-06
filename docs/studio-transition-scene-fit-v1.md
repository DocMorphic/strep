# Shared-transition correction in Studio

Studio can propose bounded edits to a saved multi-character transition, review original and candidate checks, and explicitly stage the appended clips for further scene editing. Characters, rigid-object paths, contact annotations and gameplay timing remain on the shared timeline. This connects the [offline correction method](native-transition-scene-fit-v1.md) to the native scene and game export workflows.

## Authoring and source binding

The Correct a shared transition panel takes a sealed assembly folder relative to project `reports/` and the SHA256 of its `result.json`. Its catalog exposes existing native rotation and translation channels, their bridge keys and protected tangent intervals. It does not guess anatomy from joint names. Only channels with complete linear bridge endpoint, tangent and interior keys are eligible.

The author selects channels and finite bounds, control times and additional protected ranges per character. Rotation limits use degrees, translations and joint displacement use millimetres. The editable window is the existing bridge; source phases and boundary tangent intervals remain protected. Full-clock pose/skin query preflight and the original floor policy still apply. Prototype limits are 96 complete control components and one million pose/vertex queries; oversized work rejects rather than shortening its sample population.

A job validates its contained source before creating output. Its request, recipe, implementation and source result are hash-bound; a separate owned worker saves a candidate without changing the current Studio selection. The candidate appends an animation to each complete original library. Review checks that its index equals the original clip count, and exposes all original and candidate numerical decisions along with the exact published download population.

Continuation binds a completed correction epoch and retains its original source, actor permissions, geometry, query budget and source-rate caps. Only the label and additional iteration count may change. Ancestor directories and inputs must remain inside project reports, without cycles or an unbounded chain. Continuation does not reset the solver to the latest candidate as a new baseline.

## Explicit Apply and gameplay timing

A completed candidate is never applied automatically. Apply rechecks the selected job and scene draft; a changed scene or stale response rejects. A failed candidate may be staged for further editing, with its failures retained. This is an editing operation, not game-use or animation-quality approval.

The queued root/marker request binds to the exact appended actor hashes and animation indices. The game-track editor loads it only against a matching completed native scene. Every transferred marker stays unconfirmed; contact boundaries supply no automatic gameplay dispatch. Original confirmations survive in historical requests and cannot approve the new timeline.

## Portable history and export

Native scene preparation snapshots selected correction history and carries it into `transition-corrections/` in both scene and game ZIPs. Material includes the complete original clip libraries, original shared scenes and game requests, the original assembly, portable original/candidate scene descriptions, corrected actors, permissions, original source-rate caps, native root/contact/event observations and failed measurement receipts. Subsequent scene edits retain parent evidence, but parent numerical decisions apply only to the parent.

This is selected export history, not a standalone resumable solver archive: all optimization trials, the full continuation chain and implementation archives are not bundled. The local sealed job retains those original artifacts. At most eight origins, 256 complete history files and 768 MiB of binary material are admitted; an excess rejects without a partial history. Verification checks typed decisions, source bindings, exact file populations and payload bytes.

The desktop builder now sources both the previous shared-transition panel and the correction panel from editable templates. Previously, shared-transition markup and initialization existed only in the generated page and would be lost on rebuilding.

## Validation scope

Offline checks cover contained requests, complete separate drafts, appended clip roles, failed source/candidate checks, typed metadata tampering, original libraries and annotations, source-bound scene preparation, portable package history, request origin/content gates, frozen continuation permissions, stale UI responses and explicit Apply. The CI extension adds the new Python and Node suites without dependency changes.

Validation receipts and measured results are recorded below after their workers terminate. Full source-chain replay can be slow, especially when every published download triggers verification. This workflow remains an advanced saved-artifact prototype. Generated closed cube skins and arbitrary gestures establish software behavior only; they do not establish naturalness, action correctness, production rig transfer, physical interaction or animator cleanup performance. Successful export supplies no quality or release approval.

## Completed source checks

The focused correction, shared-transition, scene-fit, lineage, native scene/game and desktop-builder regression run passed 201 Python cases with no failures or skips in 1,820.00 seconds. The new correction suite contributes 21 cases. All 95 snapshotted product methods and 20 Python test sources still matched at terminal completion. The checkpoint snapshot was taken during the run; it is not claimed as a pre-launch archive.

After that worker terminated, only the new editor's six garbled punctuation instances were changed to valid Unicode. Python product methods and Python tests stayed unchanged. Four final offline Node suites pass: bridge correction, shared transition, native scene fit and native game tracks. The final implementation snapshot records that one display-only method difference.

An earlier Node aggregate call exposed a newline-sensitive assertion in the existing shared-transition source-inclusion test. Its failure remains in the turn output. The test now normalizes CRLF/LF before comparing the editable partial with the generated page; a focused rerun and the final four-suite run pass. That correction changes no product behavior.

Local receipts remain under ignored `reports/`: source/UI validation `studio-transition-fit-source-check-v1/result.json`, SHA256 `9e6045dcff8b7cee45160be06f7ac3a46abcf490833c605bdc939e9d2858f21e`; parsed workflow proof `studio-transition-fit-workflow-v1.json`, SHA256 `613477fa36c0d9a5bb31ee3f6bc133f53ac4a811b4b62b3be4f867ffaffc414f`. The workflow adds only the new Python and Node suites, with other parsed fields and dependencies unchanged. Hosted CI success is not inferred from these local checks.

## Completed saved-resource scene/game study

The serial CPU/headless Studio study completed with an exit-zero driver on 2026-10-06. It continued the original bounded correction by one iteration, reaching 18 total, then exported both appended actor resources, the object resource, native root/contact/event tracks and the portable scene/game packages. Original libraries have four clips and the selected appended index is four. The original source and prior correction files, current/archived methods and worker-lock state were checked at completion.

The core correction audit uses 1,707 times. The imported scene and root-track checks use a distinct 1,688-time population per actor; these populations are not conflated. Both actors pass saved-resource pose component fidelity with a maximum error of `3.0303e-7`, full CPU-skin position fidelity within `2.3266e-7 m`, and root-reference fidelity within `1.1681e-7 m`. These are serialization/import fidelity checks, not evidence of realistic movement.

All three owned engine processes exit zero with clean logs and stopped process trees. The event helper produces exact traces for four full/skipped/repeated-seek scenarios. The exported tracks retain 14 events, including seven gameplay markers whose timings remain unconfirmed; no exported event permits runtime dispatch. Root motion remains embedded in the character clips and its separate track is reference-only.

All 38 selected correction-history members are byte-identical in the local lineage, scene ZIP and game ZIP. The game ZIP retains all 46 source package members except its intentionally updated package manifest. Earlier confirmations remain visible in historical requests; they do not confirm the transferred markers. The complete optimization-trial/resume archive is still not bundled.

The 18th iteration leaves the partner-contact gap unchanged at about `20.2577 micrometres` against the original `20 micrometre` limit. Native motion/contact and whole-scene geometry checks remain failed, as do the inherited near/coplanar geometry and default object-import conditions. Actor transition conditions pass. Failed motion can be reviewed and exported for further correction without acquiring a quality, physics, training or release approval.

Final local receipt: `reports/studio-transition-fit-engine-v1/result.json`, SHA256 `09153877ff9079500bb25827ecf47ee20b69efb135fcd60b0c492a4cc3c5b393`. A separate read-only root audit recomputes both saved root comparisons and delta reconstruction, checks all seven binary arrays against the complete JSON population and ZIP payloads, and retains unconfirmed event timing; receipt SHA256 `25b2b23fd20e6718631ddc5c4919fae96f25373d15b3d87cfb7a54b5bf819e33`.

Repeated full-chain verification makes this small generated study slow: the driver ran for roughly 87 minutes, while the engine processes had already stopped before the final replay finished. [Verified-read cache groundwork](verified-transition-read-cache-v1.md) is being checked against the unchanged full verifier before transport integration. No live HTTP/browser, rendering/GPU, physics, production anatomy, new model sampling/training or human review occurred. All fourteen project release evidence arrays remain empty, and the full-project goal remains active.
