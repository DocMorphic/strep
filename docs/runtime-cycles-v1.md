# Godot cycle playback and root extraction — 2026-09-26

This is development evidence under the same full-project goal. A working runtime consumer now repeats one exported cycle, accumulates its placement, and emits explicit authoring markers. It does not fix the motion-quality failures in those clips.

`godot_cycle_adapter.gd` supports skeleton-space playback and full pelvis extraction. In skeleton mode it applies the cycle transform only to the mapped pelvis subtree. In extracted mode it holds that pelvis at its initial clip transform and reports the relative transform for the game's actor. Applying the reported transform once reconstructs the same weighted mesh motion. This includes vertical movement and tilt: it is not a planar CharacterBody controller. Weighted bones outside the pelvis subtree and rigid mesh primitives are rejected by metadata generation. Unsupported runtime export leaves the ordinary loop intact and records its reason.

The contract uses a finite single-cycle GLB with P+1 samples, its terminal sample at P/30 seconds, exact source hash, named root and rigid yaw cycle transform. It deliberately leaves Godot's automatic looping off. The caller chooses forward update timing and owns physics, actor placement and pause. Absolute transforms and right-multiplied local deltas are available. Do not apply both or combine this driver with AnimationTree, another AnimationPlayer driver, or SkeletonModifiers. Full instructions are in `integrations/godot/CYCLES.md`.

Markers use phase frames and first-cycle indices. Generated metadata currently supplies only `cycle_boundary`, starting at cycle 1. Semantic source markers remain in the authoring package and are not automatically mapped or declared physical contacts. Forward updates dispatch every marker in the open-left, closed-right interval, including simultaneous events and updates spanning multiple cycles. Silent seeks and restarts reset the delta; optional explicit initial dispatch supports authored phase-zero markers. Negative/nonfinite updates and steps over 1,024 cycles are rejected before mutation. A 1,000,000-period clock ceiling is a guard, not evidence of tested precision across that duration.

## Failure retained and fixed

`reports/runtime-cycles-v1` failed: repeatedly adding 1/60 second left the clock fractionally below the exact third wrap, omitting its two test markers. The full engine output and failure remain. The adapter now uses compensated clock accumulation. The passing runs keep exact event expectations; no early-event epsilon, relaxed tolerance, or extra final advance was added. Zero advance is a no-op with identity delta.

## Actual engine evidence

`reports/runtime-cycles-v3/verification.json` checks four exported jobs representing three distinct cycles and two rig families: in-place wave, traveling/turning wave, imported locomotion, and the same wave exported through the new Studio path. This is a development regression set, not four independent action families.

Across skeleton/extracted modes and half-frame, 17-frame and multi-cycle strides, the engine supplied **2,118 transform samples**. Every skinned bone and independently CPU-skinned mesh reconstructed from observed engine bones was compared with the immutable three-cycle reference GLB. Initial actor placement includes nonzero translation and yaw. Maximum transform-element discrepancy was 1.10e-5; CPU-skinned vertex discrepancy was 9.81e-6 metres. Right-composed root deltas matched the absolute transform within 1.11e-5. The unchanged 1e-4 numerical tolerance passed.

Each of 24 runs emitted the same 16 expected marker instances, including initial, simultaneous, last-phase and exact-wrap cases. Except cycle boundaries, these are explicitly synthetic dispatch probes and are not written into shipped motion metadata. Silent scrubs, repeated restarts, zero updates, duplicate binds, bad source hash and invalid update rejection were checked. Actual Godot 4.7.2 ran the standalone main scenes headlessly for 240 fixed 60 Hz frames and confirmed startup plus the first real cycle-boundary marker. This establishes headless transform/dispatch behavior; GPU appearance, game collision response, crossfades, reverse playback and long-running drift remain unverified.

Audited portable packs are under `reports/runtime-cycles-v3/<job>/godot-cycle.zip`. Unzip and open `project.godot`, then Run Project (F5). Each contains the single GLB, metadata, adapter, runnable scene/script, instructions, engine verification and original authoring archive with source provenance/licenses. Every archive entry was checked against its source bytes. `.godot` caches are excluded. Earlier v2 and Studio-only audit evidence remains separate.

## Studio integration

New loop jobs include runtime metadata, adapter and instructions in `transfer/` and the ordinary animation ZIP. Studio exposes three download links. Job `20260926-220650-1da442bb` is the actual API-created example; its 66 archive entries, HTTP files, decoded transforms and both GLBs were independently verified in `reports/runtime-cycle-export-v1`. Both GLBs have zero validator errors and six inherited asset warnings. The same new job was included in the v3 actual engine runtime study. Existing jobs and their immutable packages were not modified.

303 full tests passed with four upstream Torch deprecation warnings. Subsequent runnable-demo packaging was checked by the actual engine; the final UI-only unavailable-reason message passed JS syntax validation. No new inference or training ran. Existing wave wrist speed, turning foot sliding and imported locomotion penetration remain unapproved.

Next: periodic semantic event mapping with explicit source/blend provenance and contact correction that preserves cycle closure. Continue scene/partner reliability, semantic rough editing, meaningful style controls, offline packaging and held-out/animator evaluation under the full goal.

References consulted: [Godot AnimationPlayer seek](https://docs.godotengine.org/en/stable/classes/class_animationplayer.html#class-animationplayer-method-seek), [Skeleton3D pose API](https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html#class-skeleton3d-method-set-bone-global-pose), [root motion concepts](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html#root-motion). Runtime evidence, rather than documentation alone, supports the tested implementation above.
