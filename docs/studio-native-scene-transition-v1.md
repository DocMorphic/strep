# Shared transitions in Studio

Studio can inspect a sealed `strep-native-scene-transition-v1` assembly and save it as a separate scene draft. Applying that draft is explicit. Actor clips, rigid-object motion, placements and remapped contact intent enter the existing native scene editor together. The original scene selection stays active until Apply.

## Source and staging contract

The Shared transitions panel takes a folder relative to project `reports/` and the SHA256 of its `result.json`. Inspection replays the assembly and checks its original inputs and archived/current implementation. Absolute paths, traversal, external inputs and extra request fields reject. This is an advanced saved-artifact workflow; it does not generate or search for a transition automatically.

The author explicitly selects geometry limits and an optional floor. The exact assembly root clock is retained in the draft. Ordinary scene geometry limits still apply, including the 10,000-time explicit clock limit; an oversized population rejects rather than being shortened. An empty plane dictionary declares no floor. Staging copies the whole assembly, including negative measurements, without changing its actor GLBs. The snapshot budget is 256 files and 1 GiB; excess populations reject before copying. Only the published result, draft, timing, actor and root/contact/event artifacts are served.

Staging success means the separate draft was saved and verified. It does not mean the source contacts, motion quality, import, physics or release conditions passed. Those decisions remain separate and visible.

## Gameplay timing and export history

Apply queues the remapped root choices and markers in Root & gameplay tracks. They load only after a completed native scene has the exact selected actor hashes, animation indices, actor population, known root nodes and audited marker times. All transferred or bridge markers remain unconfirmed. Confirmation uses the existing explicit marker authoring workflow; a matching clock never confirms gameplay intent automatically. Contact boundaries never dispatch gameplay actions automatically.

When staged actors are exported, `transition-lineage/` contains portable original scene descriptions, original clip libraries and game-track requests, the candidate scene and actor clips, and assembly/staging/root/contact/event results. Original marker confirmations remain in the historical requests; transferred confirmations remain reset. Historical numerical decisions apply to the parent assembly, not to subsequent scene edits. The original scene package and game package carry identical lineage bytes. Existing game packaging also copies every other source package member unchanged, with the source manifest retained separately.

The lineage material budget is eight complete origins, 128 files and 768 MiB of binary material. Verification replays origins, checks exact physical file populations and current source bindings, and compares JSON with typed equality. Rehashing an integer in place of a boolean does not make it valid. Methods are included conditionally for selected transition actors, preserving the archive population of older jobs.

## Validation and limits

Offline checks exercise separate staging, retained contact failures, unchanged source bytes, path containment, complete downloads, portable original libraries/annotations, source-bound scene preparation, origin/content request gates, typed tampering, stale UI selections and exact-clip timing transfer. The CI extension adds one Python suite and one Node suite; dependencies and all other parsed workflow fields stay unchanged.

The initial staging/scene/game regression run passed 90 Python cases in 518.65 seconds. After adding typed JSON equality, the final staging suite passed 15 cases in 217.15 seconds, including four additional rehashed boolean/population cases. Both runs had zero skips. Four offline Node suites also passed. Source archives were taken after terminal checks, not claimed as a pre-run freeze; archived/current methods match the passing staging fixture.

A real serial headless study staged the prior two-actor/moving-box assembly, saved scene assets, exported root/contact/event tracks and created both scene and game ZIPs. The common object/actor clock contains 1,688 times, extending the retained assembly clock without changing authored marker times. Imported actor poses and CPU skins pass existing limits; the maximum skin error is below 2.890e-7 m. The saved box native resource passes pose checks at 1.4894e-8 m position error; default GLB import still fails at 1.04401 mm under the unchanged 1e-6 m limit. Incorrect object/partner contacts remain failed, so both object mode summaries and whole-scene conditions remain false. Root samples pass. All 15 lineage files and every original package member survive byte-identically in the game package. Original confirmations remain in historical requests; seven transferred markers and all 17 contact/game events are unconfirmed and dispatch nothing across four seek scenarios. Three owned Godot processes exit zero with clean logs and stopped trees; originals and archived/current methods agree and the isolated worker lock is free.

The study harness exited one at its final assertion because it looked for request-schema `markers` in the event-plan document instead of `events`/`timing_confirmed`. Its failure and raw outputs remain preserved. A separate read-only receipt rechecks completed workers, exact packages and empty dispatch traces without starting another engine.

Local receipts, retained under ignored `reports/`:

- Source checks: `studio-transition-source-check-v1/result.json`, SHA256 `3d57b265a0dcd5fe629caba056d6ce5d3d357317b826d2b017f1f0be37508598`.
- Actual engine/package receipt: `studio-transition-engine-v1/result.json`, SHA256 `f647e3bc5dbb4ac25de18e7a5716abf6777210d55e8255ad85e2f1c967b6698e`.
- Parsed CI proof: `studio-transition-workflow-proof-v1.json`; only the new Python and Node suites differ from the previous workflow.

Verification intentionally replays the full source chain. Larger assemblies can make inspection, staging and export slow; no performance or live-browser claim is made here. Generated closed cube skins establish software behavior only. Production anatomy, action correctness, naturalness, coupled articulated contact correction, dynamics and developer/independent animator cleanup remain open. Successful packaging supplies no animation-quality or release approval.
