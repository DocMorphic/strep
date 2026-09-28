# Gameplay event authoring and periodic playback — 2026-09-26

Studio now supports adding, removing and reviewing gameplay markers on an existing target-rig clip. A marker-only save creates an immutable job: the selected GLB, root-motion and contact tracks remain byte-for-byte unchanged. Event names describe author intent. Confirming timing does not certify a physical contact or correct action.

## Authoring and mapping

The Gameplay markers panel exposes name, frame, current-frame placement, navigation, removal and explicit timing confirmation. Saves bind to the selected GLB hash; changing sources invalidates the panel. Up to 128 authored markers are supported. Structural cycle/transition boundary names are reserved, including after whitespace normalization. Existing structural markers remain separate from authored markers.

Loop and transition exports map each source event through the actual positive-weight pose contributors. Same-name simultaneous events and occurrences from both transition inputs are retained with distinct IDs, source frames, weights and lineage. Zero-weight and unselected occurrences are recorded as omitted. Partial-blend occurrences require timing review and are excluded from runtime dispatch until explicitly confirmed. Retime uses the existing nearest output-frame mapping with half-up rounding and records dropped events. Immutable input/history snapshots retain the originals.

Periodic runtime metadata includes timing-confirmed authored events in the first period, plus the generated cycle boundary. The duplicate terminal sample is excluded. Every emitted authored event carries its source event and provenance. The existing Godot adapter supports forward multi-cycle dispatch, simultaneous markers, silent seeks and optional phase-zero dispatch through `restart(true)`. The demo does not request initial dispatch automatically. Reverse playback, crossfade dispatch policy and physical gameplay reactions remain outside this implementation.

## Reproducible development study

`scripts/run_event_study.py` exercised the real Studio API, followed by an actual UI-authored save. Requests, responses, source snapshots and packages are retained in `reports/event-authoring-v1` and the individual rig jobs:

| Case | Job | Evidence |
| --- | --- | --- |
| Eight source markers | 20260926-222238-f477afb4 | Geometry unchanged |
| 45-frame loop | 20260926-222246-21daa174 | Two partial-blend markers require review; zero-weight/outside markers omitted |
| Confirm one blended marker | 20260926-222349-89b1b9df | One review flag remains; both single/repeated GLBs unchanged |
| Trim and retime | 20260926-222358-c6235aed | Seven markers retained; source frame 40 maps to output 8 |
| Join two marked excerpts | 20260926-222407-17897918 | Both source occurrences survive; 11 events, four requiring review |
| Studio review cue | 20260926-222539-831f5a06 | UI add/remove/navigate/save/reopen verified; geometry unchanged |

The first orchestration attempt encountered HTTP 409 while a completed job's worker process was still exiting. Its failure remains in `previous-attempt.json`. Resume reused completed matching requests; bounded busy retries followed the real server worker state. No finished job was overwritten.

`scripts/verify_event_study.py` independently reconstructs contributor occurrences, retime frames and runtime eligibility; verifies all package entries against saved files and HTTP hashes; and checks geometry/root/contact preservation. All six jobs pass. These are development intent cues on one wave source, not six new action-quality samples.

## Actual Godot evidence

`reports/runtime-authored-events-v2/verification.json` covers the loop, confirmed edit and UI edit in Godot 4.7.2. Skeleton and extracted-root modes, three update strides, nonzero initial actor placement and three periods produce 18 runs and 1,680 transform samples. Each run emits respectively 29, 32 or 35 expected events, including clearly separate synthetic dispatch probes. All payload IDs, names, frames and review flags match. Silent seek, zero advance and restart behavior also pass. The three standalone demo projects start and reach the first real cycle boundary.

Maximum transform-element discrepancy is 4.12e-6, independently reconstructed CPU-skinned vertex discrepancy 4.14e-6 metres and root discrepancy 8.51e-6. These pass the existing 1e-4 tolerance. This is headless runtime evidence, not GPU, physics or animator approval. Ready-to-run projects are saved as `reports/runtime-authored-events-v2/<job>/godot-cycle.zip`.

The first authored-event engine audit failed exact payload equality because Godot JSON rounded a blend weight by approximately 2.22e-16. `reports/runtime-authored-events-v1` retains that failed audit. The verifier now compares JSON floating values within 1e-12 while requiring identical keys and exact non-floating IDs, strings, frames and flags. The final maximum floating serialization error is 3.34e-16. No event timing or pose tolerance was changed, and the runtime adapter did not change.

311 full tests passed with four upstream Torch warnings after core integration. The final reserved-name whitespace guard has its own focused regression run. No model inference or training ran. Existing motion-quality failures remain: event correctness does not fix penetration, foot sliding, source motion defects, scene interaction or action semantics.

Next: contact correction across the period boundary while preserving cycle closure, then the remaining scene/partner, semantic editing, style, offline installation and held-out/animator release gates. The single full-project goal remains active; all release approvals remain open.
