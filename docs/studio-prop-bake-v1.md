# Studio offline prop animation bake

Studio source now connects a completed [prop runtime package](studio-prop-grips-v1.md)
to [offline editable animation baking](scene-prop-bake-v1.md). The new **Bake prop
animation** panel provides scene placement, an explicit world ground/no-ground
choice, a saved request, an asynchronous bake and verified fixed downloads.
It preserves the selected source clips and original source failures. It does
not generate new character motion or infer a successful grasp.

## Authoring flow

1. Build a prop runtime with explicit grips, ownership events and physical
   settings, then select its completed job above the bake panel.
2. Choose **Use selected prop runtime**. The server binds the exact completed
   result and runtime ZIP; incomplete or changed sources are rejected.
3. Set a stationary rigid scene position/rotation and explicitly choose a world
   ground plane or no ground collision. Ground height, friction and restitution
   are bounded values. The ground plane stays in world space.
4. Choose **Save bake request** for a portable Studio request or **Bake editable
   animation** to start the existing offline CLI pipeline in a worker.
5. Refresh bakes and show its results. Download the editable asset ZIP, standalone
   bake request and provenance results only after complete verification.

Scene/root failures from the original reference remain visible. Review reports
configured engine import fidelity, exact physical timing and maximum delay,
sampled baked grip agreement, sampled ground conditions, and the separate
default 30 FPS import diagnostic. No-ground results remain N/A. Successful
export or import does not approve animation quality, anatomical hand contact,
body collision, continuous collision or partner reactions.

Requests and replies are bound to the selected job and hashes. Changing the
source while binding or submitting cannot silently select a different source.
Changing the review job rejects a stale reply. Concurrent submissions stay
disabled until their request completes. Failed jobs preserve their requests
and error receipts and expose no partial download.

## Backend and integrity

`scripts/studio_scene_prop_bake.py` uses the existing single-worker gates and
the baker's lock, pinned headless Godot binary, finite clock and bounded asset
budgets. Preparation snapshots the exact source ZIP, request and complete
implementation archive. The worker records source conditions separately from
new bake observations; it changes no Studio clip selection or release flags.

Completed review/serving verifies preparation, source lineage, archived methods,
execution artifact fingerprints, fixed download hashes and complete portable
ZIP membership. It also checks every original capture-project/reference file,
unchanged mesh/material bytes, original authored prop channels, complete exact
capture clocks/events/ownership applications, the physical audit, decoded
tracks, Float32 clock storage, baked grip/floor conditions, engine sample clocks,
configured/default import requests and observations, and composition/end/root
policies. Rehashing changed output receipts does not authorize changed original
assets, composition, sampled conditions or storage/import decisions. These
saved-data checks do not rerun the engine while serving; native resources are
bound to the recorded execution fingerprints and package checksums.

Read APIs are `/api/scene-prop-bake-source?id=...`,
`/api/scene-prop-bake-jobs` and `/api/scene-prop-bake-review?id=...`. Source/review
queries require exactly one ID. `/api/scene-prop-bake-assets` accepts local
same-origin JSON under the existing 1 MiB limit and worker gates. It starts a
separate worker instead of running engine capture on the HTTP handler.

Only these completed downloads are served:

- `bake/baked-assets.zip`
- `bake-request.json`
- `bake/result.json`
- `result.json`

Source snapshots, raw capture, implementation archives, arbitrary asset paths
and traversal paths are not individual public download endpoints. The portable
asset ZIP includes the original reference assets described by the baker.

## Development evidence and limits

A real serial headless worker case uses the existing two-second generated
native package: two duplicate test rigs, one physical sphere, one authored
sphere, artificial root-joint grip offsets, partial release and handoff. Its
upstream saved Studio job boundary is explicitly doubled; native GLBs/resources,
headless physics, baking, saved-resource import and full completed-review
verification execute for real. This is neither live HTTP/browser proof nor
production humanoid interaction quality.

The final worker completes 241 physical records and 492 baked query times.
Configured 120 Hz import and saved native tracks pass the unchanged pose bound.
The default 30 FPS import still fails near impact, and exact physical timing
still fails with a **6.25 ms** maximum delay. Sampled grip/floor screens pass in
this fixture, while its deliberately failed upstream scene-condition flag
remains false. All four downloads pass completed serving validation. Three
owned engine stages exit zero, with unchanged core methods and no retained
engine process or busy worker. No quality/release approval is inferred.

Model-free source tests use generated fixtures, an explicit upstream Studio
boundary double and an engine double. Offline UI tests use a DOM/API double.
These checks are separate from the actual engine case. The live Studio/server
has not loaded or verified this update, and no model sampling/training,
production skin/anatomical query, rendered/GPU evidence, human ratings/cleanup
or held-out release approval is created. All fourteen release requirements
remain unapproved.

Final local worker receipt SHA256:
`83787e3fa08d65c17a5d24a66a49aefdd786dd666e9a11345ca1bfad651f7fec`.
The standalone bake result SHA256 is
`00ed1879662e9be093cffe639edd77732cedacc4552c65d56a404129f9760024`.

The final frozen public-source run passes 74 Python tests, including all
28 new bake-job contracts, plus four offline editor suites. Request/source and
method drift, fixed downloads, failed jobs, rehashed output changes, HTTP handler
gates, generated Studio preservation and stale/busy UI replies are covered.
Source/copy hashes remain unchanged. Local source-result SHA256:
`750abf2b932a1baccea49c74592f9d62bd00e4222cd669ee14b09e5589fd0631`. Parsed workflow proof SHA256:
`8586fb56ffa839ffae55628508dbdaeb94d0318252f4692e2dfa7589cfbfbd8f`.
