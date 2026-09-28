# Reverse cycle playback and explicit reverse notifications

Reverse playback is implemented in the exported Godot cycle adapter and verified through a real Studio export. This is development evidence under the full Strep goal, not motion-quality or release approval.

`advance(seconds)` retains its forward-only contract. The new `rewind(seconds, notify_crossings=false)` moves backward through nonnegative timeline time, reconstructing the same root and bone transforms as the corresponding saved poses. Both skeleton-space playback and extracted root motion support crossing cycle boundaries and changing direction. Right-composed deltas work in either direction.

Rewind is silent by default. Explicit notifications use the separate `marker_reversed` signal and add `direction=-1`; they never invoke forward marker listeners. Reverse traversal includes the destination, excludes the starting cursor, visits later events first, and reverses metadata order for simultaneous markers. These notifications do not undo audio, spawned objects, attachments, release or physics. Such gameplay policies remain the application's responsibility.

The adapter continues to use an updating, silent seek for pose sampling. Godot documents that `seek(..., update_only=true)` suppresses method, audio and animation playback tracks, which supports keeping Strep marker dispatch explicit. [Godot AnimationPlayer documentation](https://docs.godotengine.org/en/stable/classes/class_animationplayer.html#class-animationplayer-method-seek). The measured behavior below comes from the installed Godot 4.7.2 engine, not documentation alone.

## Endpoint failure retained

`reports/runtime-reverse-v1` failed after a mixed-direction sequence: an independently summed requested duration exceeded the actual remaining floating-point cursor by a tiny amount. The invalid traversal was rejected; no animation or package was approved from that attempt.

To reach zero exactly, the caller now explicitly consumes the exposed remaining cursor with `rewind(adapter.time_s, notify)`, subject to the existing step limit. This resets both time and compensation exactly. No epsilon, early marker or negative-time cycle was introduced. The audit's explicit zero destination uses this API contract; other steps retain their fixed durations and all event/transform expectations are unchanged. The documentation recommends `rewind(min(delta, adapter.time_s))` for an update loop that stops at zero.

Nonfinite or negative durations, steps over 1,024 periods and traversal before zero are rejected before mutation. The engine audit checks unchanged cursor, compensation, root transform, previous delta and both event channels. Zero rewind produces identity delta without duplicate markers. Silent seeks remain silent.

## Actual engine and export evidence

`reports/runtime-reverse-v2/verification.json` covers four existing fixtures: in-place and traveling/turning cycles, an imported locomotion cycle, and a cycle with authored marker provenance. These are development fixtures from two rig families, not four independent action families.

- Forty runs cover skeleton/extracted modes, reverse half-frame steps, 17-frame steps, multi-cycle steps, repeated direction changes and silent reverse traversal.
- All **2,238 transform samples** are checked against immutable three-cycle reference GLBs. Every imported skin bone and independently CPU-skinned mesh is compared at the same timestamp.
- Maximum transform error is 1.156e-5; root/accumulated-delta error is 1.168e-5; CPU-skinned surface error is 7.402e-6 m. The existing 1e-4 tolerance passes without relaxation.
- **276 forward and 722 reverse marker instances** match an independent frame-domain oracle, including simultaneous cues, exact destinations, origin exclusion and original authored payloads. Maximum clock discrepancy is 3.553e-15 s.
- `reports/runtime-forward-regression-v4/verification.json` separately passes the existing **2,118-sample forward regression**, 384 marker instances, silent scrubs and actual packaged demo startup. New portable cycle packs include the updated adapter and instructions.
- Seventeen focused runtime/event tests pass in 11.46 s. Actual Godot execution, rather than Python tests alone, covers the GDScript implementation.

The real Studio `/api/rig-events` request produced job `20260927-231751-70601f00`, preserving the original clip, repeated clip and root track while retaining the previous authored timing and exclusions. `reports/runtime-reverse-export-v2/verification.json` verifies 147 source-backed archive entries, captures the generated README with its hash and caveats, and checks all four HTTP downloads byte-for-byte: metadata, adapter, instructions and animation package. The first export verifier incorrectly assumed the generated README also existed on disk; its failed report is retained in `runtime-reverse-export-v1`. The repaired verifier reused the already-completed job and did not submit a duplicate.

New runtime metadata describes reverse behavior explicitly. New Studio cycle exports copy the updated adapter and contract. Older immutable packages and existing portable installation bundles were not rewritten. The complete offline bundle will need a later refresh and regression pass before release.

GPU rendering, actual game physics, reverse gameplay effects, crossfade policies, other engine versions, broad motion quality and independent animator review remain open. No release gate is approved by these checks.
