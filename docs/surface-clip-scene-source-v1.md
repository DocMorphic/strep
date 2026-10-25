# Use a completed ground-contact correction in a scene

Completed Ground-contact cleanup candidates can now enter the existing native
scene workflow. Previously their served URLs were accepted for comparison and
download but excluded from scene authoring. The original character selection
still stays unchanged; adding the candidate is an explicit authoring action.

## Workflow

1. Inspect a saved Ground-contact cleanup job that has completed its whole clip.
2. In the scene editor, choose a new actor name and placement.
3. Click **Add completed candidate to scene** in the correction results.
4. Author the scene's contacts, objects, partner targets and geometry checks,
   then build scene assets using the existing workflow.

Existing scene actors and objects remain in the draft. Duplicate actor names,
more than eight actors, different clip durations, active contact revisions and
a scene that changed while loading are rejected. Different durations require
explicit retiming; adding an actor does not silently trim clips or move targets.
Correction point targets remain recorded historical intent and are not silently
converted into scene contacts or declarations of foot planting.

The source endpoint binds the exact job, attempt, candidate hash, animation
index, request and result. It requires a completed whole-clip result with every
native key finalized and validated. Partial checkpoints, unresolved/rejected
outputs, changed originals and altered publication receipts are rejected.
Original and rejected preview downloads retain their existing comparison roles.

## Preserved history

A scene selecting these candidates snapshots a `surface-correction-lineage`
record. Each distinct source job/attempt contributes the original and candidate
GLBs, authored correction request, preparation record, result, publication,
guard completion and resource replay. Multiple actors can share the same source
without duplicating those eight artifacts. The complete snapshot is bounded to
768 MiB; exceeding it fails without dropping files.

Scene exports include the record and artifacts under `surface-corrections/`.
The existing game-package transport preserves all source-package entries and
binds the additional source methods. Changing source bytes, historical settings,
selection, snapshot population or receipt hashes invalidates the history.
Recorded parent decisions apply to that original job only. Scene placement,
new contacts, transitions and engine behavior must be measured separately.

The real saved wave has been checked through the new metadata and history
functions. Its candidate hash remains
`7678f1bafd355cf3f368c0d2d263e033f1a65ecb657553fa5517871f48d748f0`.
All nine portable history files, including the record, survive ZIP transport
byte-for-byte. Evidence is retained in `reports/surface-clip-scene-wave-v1/`
in the development checkout. That check does not run a new scene engine job or
establish live browser behavior.

Local validation passes 136 distinct Python cases across the source adapter,
scene snapshots, correction routes/continuation and game packaging, plus three
Node editor/comparison suites. The first run passed 133 cases; the final source
adapter follow-up passed all 25 cases, including three added cases for strict
counter types and complete scene-to-game history transport. The earlier source
bytes are archived for the original run's bindings. Engine output is explicitly
mocked in packaging fixtures; they establish transport, not Godot motion quality.
The real saved-wave source/history check was replayed against the final code.

Both guarded test traces replay. Receipts and the combined verifier are in
`reports/surface-clip-scene-tests-v1/`, `reports/surface-clip-scene-tests-v2/`
and `reports/surface-clip-scene-publication-v1/` in the development checkout.
The full/focused CI inventories now contain 657/206 Python files. These local
results do not assert that the full hosted regression or live browser run passed.

The scene/transition requirements remain open: this source adapter creates no
transition, loop, contact solution or quality approval. In particular, the
[wave connection-pose screen](studio-surface-wave-playback-v1.md) still has an
approximately 109 mm direct-repeat gap and failing original destination floors.
The existing edited endpoints continue to require transition review.
