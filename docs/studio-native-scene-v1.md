# Studio scene drafts and native asset jobs

The Character window now exposes **Scene contacts & game assets**. It connects
the existing native scene authoring job to selected character clips, explicit
object geometry, mesh patches and saved results. Action names are unrestricted;
this addition assembles supplied motion rather than generating motion from a
prompt or automatically solving every interaction.

## Authoring

1. Select an exported character clip. Enter its scene name and position, then
   add it. Add another clip the same way if needed. Each clip must have exactly
   the shared duration; retime clips explicitly beforehand. Their animation
   indices, bytes and timing are preserved.
2. Add a box, sphere or cylinder with explicit dimensions and placement. The
   quick controls create a static object. A saved JSON draft can also supply the
   existing schema's complete moving object trajectory and rotated placements.
3. Open Mesh contacts and select an actual patch. Choose the effector character,
   object-local grip point, world point or partner patch, timing and position
   limit. A hold also requires a relative speed limit. Partner targets are saved
   from the selected partner's patch before selecting the effector patch.
   Every picked vertex maps to its original mesh node, primitive and vertex;
   no anatomy or nearest-point guess replaces the selection.
4. Declare a horizontal world plane only when appropriate. No plane is inferred
   from the preview grid. Imported nonhorizontal planes and complete clocks
   remain intact. Set penetration limits explicitly.
5. Optionally request the existing bounded object edit using two declared
   object holds, an edit window, translation/rotation bounds and a key budget.
   This edits the object trajectory; it does not edit the character clips.
6. Save/open the scene draft, then build assets. Refresh the job and show its
   results. Numerical failures remain downloadable and never replace the
   selected Studio character or approve animation quality.

## Reproducibility and downloads

The `strep-studio-native-scene-v1` envelope contains the existing contact scene,
explicit geometry clock/limits/planes and an optional object-edit request.
Character GLBs must resolve through permitted local Studio asset namespaces and
match their recorded hashes. Remote URLs and arbitrary executable choices are
rejected. Jobs use the configured local Godot runtime; missing setup produces a
specific error rather than downloading or using a remote machine.

Drafts are validated before creation. A fresh job snapshots complete character
bytes, draft, contacts, policy, optional edit, recipe and implementation hashes.
The current local request gates permit one worker, with offline environment
settings. The worker runs the existing seven-stage audit or eight-stage edited
pipeline, retaining partial evidence on execution failures. A completed job
binds every stage result, original/derived input, method archive, actor
observation, geometry archive, replay and fixed downloadable asset population.
Serving rejects modified artifacts. No raw tokens, logs or implementation
folders are offered by the new download route.

A worker starts only in a fresh prepared job. Repeated dispatch against a
completed or failed folder is rejected before altering its status or evidence.

Downloads include unchanged character GLBs, object GLB, reloaded Godot character
and object animation resources, measured results, geometry and replay records.
The ZIP additionally provides a portable `scene.json` with relative actor paths
and a contact-hash-bound geometry policy. Its manifest records each file hash
and selected animation index. Complete ZIP entries are read back and compared
to their source hashes before publication; neither clips nor thresholds are
changed to make packaging pass.

These files are development assets, not a finished engine project. Root/event
sidecars are explicitly absent from this package version. Playback integration,
physics/attachment, semantic correctness, animator cleanup, human review and
release approval remain separate. Character and engine licenses still apply.

[Root/contact/gameplay packages](native-scene-game-tracks-v1.md) add explicit
sidecars and a finite tested Godot event helper to completed scenes while keeping
this original package and its source observations unchanged.

## Validation scope

Python checks cover exact preparation, rejected input/URL/clock/limit changes,
offline request-handler stubs, source snapshots, partial failures, numerical
failure retention, complete receipt-bound downloads, artifact tampering and
portable paths. Node DOM checks cover source selection races, duration mismatch,
complete patch conversion, object/world/partner targets, explicit edit bounds,
imported planes/clocks and completed/failed results. These checks make no claim
about a live browser or GPU render.

On 2026-10-03, 104 existing/new source and orchestration checks passed, followed
by all 47 final Studio backend checks. The new Node workflow and the existing
mesh-contact playback workflow passed. The first actual-run preparation used a
fixture's relative path incorrectly and stopped before engine execution; that
attempt was retained. The repaired preparation ran the unchanged fixture through
the Studio worker with the configured Godot 4.7.2 executable. All eight stages
completed at all 1,101 times. Original contacts fail; the explicitly bounded
object edit and native sampled scene conditions pass. Complete replay passes.
The ZIP's exact population and bytes pass readback; its extracted scene and
geometry policy load with relative paths and matching receipts. All original
character bytes remain unchanged, and every fixed download passes its manifest
checks.

The actual canary consists of two procedural closed-cube articulated rigs, a
sphere, two grip constraints and a declared remote plane. It tests integration,
not realistic humanoid motion or floor-contact quality. Ignored local records
are `reports/native-scene-jobs/procedural-canary-v2` and
`reports/studio-native-scene-validation-v3/checks.json`. The final worker guard
was verified again with 51 backend/build checks and a fresh complete actual
eight-stage run. Node additionally checks that displaying metre limits as
millimetres preserves untouched imported limits exactly, including values whose
unit-conversion round trip would change one binary floating-point bit. Prior measurements,
release capability evidence, held-out trials and acceptance gates stay intact.
