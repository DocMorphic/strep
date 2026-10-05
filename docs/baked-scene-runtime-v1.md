# Saved actor and prop scene playback

This workflow turns a completed [offline prop bake](scene-prop-bake-v1.md)
into a standalone Godot project. Original actor GLBs, saved actor Animation
resources, contact measurements, root references and confirmed event intent
remain byte-for-byte unchanged. Baked prop tracks play on the same finite
clock as the actors. There are no live prop bodies or collision nodes in the
loaded scene; physics was recorded during the preceding bake.

## Package and audit

From the repository, using its configured Python environment:

```powershell
python scripts/baked_scene_runtime.py package path/to/baked-assets.zip reports/my-saved-scene
python scripts/baked_scene_runtime.py audit reports/my-saved-scene/baked-runtime.zip reports/my-saved-scene-audit
```

Both destinations must be fresh directories. Packaging needs the complete
original baked ZIP and source dependencies, but does not run Godot. Auditing
requires the existing pinned Godot 4.7.2 console binary and acquires the shared
worker lock. There is no automatic model download, inference or training.
The repository remains a source snapshot, not a bundled offline installer.

The ZIP preserves all original baked files, including their manifest, and adds
`project.godot` plus `baked-runtime-v1/`: a main scene, exact runtime bindings,
source helpers and a separate package manifest. Complete populations, portable
paths, unique names, size limits, original decisions and file hashes are
checked. The audit snapshots the whole input ZIP, validates all current method
hashes before executing trusted scripts, and checks input/assets/methods again
after engine execution. A changed or partial source cannot produce a completed
audit. Failures retain their request, raw output, pipeline status and terminal
process receipt locally.

## Clock and integration contract

The stationary world placement comes from the bake. Actors retain their
original embedded root motion; root references are not applied again. A caller
can consume each actor's local root delta, while the saved actor clip continues
to contain that movement. Applying the delta to the visible actor again would
duplicate movement.

The original source clip and event clock can end before the final complete
physics boundary. Actor sampling and event traversal stop at the original end;
props continue on their saved baked tracks until the finite baked end. The
original actor resource lengths, keys and event bytes are preserved.

glTF prop key times are Float32. At some physical endpoints the final stored
key lies slightly beyond the exact Float64 resource length. The loader clones
the prop Animation in memory and extends only its length to the larger of the
exact end and its Float32 representation. No saved file, key time or value is
changed. Playback still rejects times beyond the exact baked end.

The player exposes monotonic `advance_to(seconds)`, silent arbitrary-order
`seek_preview(seconds)` and explicit `restart()`. Every crossed confirmed
marker dispatches with all actors and props sampled at its original exact
time. A repeated advance does not redispatch events or accumulate root motion,
including after preview. Reentrant sampling, backward advance, nonfinite or
out-of-range time and moving the stationary scene container reject. Restart
resets traversal; it does not blend the end into the start.

The exported main scene binds automatically and advances from an elapsed-time
clock. A game can supply its own scene, rendering, camera and event consumers,
or use the loader/player directly with its own finite clock. Automatic startup
binding and deterministic advances are audited; real-time rendering and frame
performance are not measured here. Dynamic parenting, motion blending, looping,
physics interaction during playback and gameplay interruption are outside this
finite saved-scene contract.

## Validation and limits

The headless audit compares every imported skeleton bone by name, every prop,
actor root motion and root deltas against original CPU samplers at complete
physics boundaries, midpoints, original native event times and the exact source
end. It separately checks ordinary, skipped, restarted and exported-main-scene
callbacks; complete populations and exact Float64 clock bytes are required.
The pose-component bound remains `3e-5` for translations and matrix elements.

Actual generated fixtures include a two-second grid-aligned source and a
`2.000999927520752`-second source with explicit moving root keys, a rotated and
elevated stationary parent, two duplicate rigs, one physical and one authored
sphere. The non-grid source holds its original actor end for
`0.007333405812581351` seconds. Its final prop key envelope is
`2.008333444595337` seconds; the public baked endpoint remains
`2.0083333333333333` seconds. These are small software fixtures with artificial
root-joint grip offsets, not anatomical interaction or independent-rig
generalization.

The non-grid bake still fails exact physical event timing by 6.25 ms and
default 30 FPS import by approximately 9.985 mm. Its sampled grip error is
approximately 0.703 mm and sampled floor depth approximately 0.000048 mm;
these screens pass only their stated fixture bounds. Successful saved playback
does not repair those preceding failures or approve action correctness,
collision safety between samples, realistic partner response or animation
quality. No live Studio/browser, production skin query, new model sampling,
rendered/GPU evidence, human ratings, cleanup times or release approval is
created. The single full-project goal and all release gates remain open.

Final frozen checks pass **197 tests**, including **38 new saved-scene tests**,
with no skips. Complete-source/decision/clock/root/end policies, rehashed
tampering, snapshot drift, complete current methods before execution,
every participant/event/root delta, startup and transport rejection are tested.
Upstream Studio jobs and engine resources in CPU tests are explicit doubles;
the two actual headless cases above provide separate engine evidence.

The final grid/non-grid cases complete **987 pose-query frames**, **48 marker
callback observations** and **24 rejected malformed bindings** without leaked
participants or collision nodes. Both exported main scenes bind and advance.
Largest actor/root component error is `2.593656560634372e-7`; largest prop error
is `2.2721984693774289e-7`, under the unchanged `3e-5` limit. Both final engine
processes exit zero with clean logs. Source and frozen-copy hashes agree with
the final engine method manifests; the shared worker lock is free afterward.

Early packaging attempts failed on a Python list conversion and Godot JSON
numeric membership check. A first CPU check exposed incomplete-reference
validation occurring after resource access; it now rejects before binding.
Those attempts remain locally retained. No timing or pose guard was relaxed.

Local immutable receipt SHA256 values:

- Combined final engine cases: `4de38d9a87ae65f8af28cea80df856920202f467174fba9c2434cc89b5401e8a`.
- Grid result: `21dd12c0655a7f412ba2c5f27735e9d2b66aee135da06dd97b2262dc5fcab56f`.
- Non-grid result: `9defa9b486e194fd5dfc07bcadf8cd3be89ad07905a6af9aed071e841aac9f2f`.
- Frozen source result: `276db045d7b6b156f5bd98baac176961bad03c84e8176de5db3141c9d814d28b`.
- Parsed workflow proof: `501c9fb1492723042d7c56655c9b80b7bd82e4b1c003f779f7319b55dec29cb4`.

The parsed workflow adds only the new source suite; dependencies, action pins,
matrix, permissions, environment and budgets remain unchanged. Hosted CI for
the preceding Studio commit is queued at the recorded snapshot; hosted success
for this update is not claimed.


Follow-up: [Studio saved-scene export](studio-baked-scene-v1.md) adds selected-bake binding, an asynchronous package/audit job, verified fixed downloads and preserved failure review. Its headless generated fixture supplies workflow evidence; its upstream Studio selection is explicitly doubled and no live browser is claimed.
