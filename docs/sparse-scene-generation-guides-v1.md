# Explicit sparse scene-generation guide planning

Scene generation previously expanded sustained hand/foot contacts into a pose guide at every contact frame. Developers can now choose a sparse temporal plan per actor while retaining complete authored intervals for reference and generated-scene checks. Prompts remain open vocabulary. This change does not resolve the measured object/partner collision failures.

Add a `guide_plan` member to each selected actor in its existing actor-plan JSON:

```json
{"mode":"sparse","maximum_frames":19}
```

The planner preserves every contact interval endpoint and both sides of changes in the active effector set. It fills remaining capacity with the temporally farthest available contact frame, choosing the earliest frame on ties. Simultaneous hands/feet share one pose guide, preserving the existing implicit-root convention. A partner contact contributes guides to both actors, even when only one directed contact is authored. No new pose or interpolated target is inferred.

The 1–19-frame budget follows [NVIDIA's sparse-constraint guidance](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/limitations.html), which recommends fewer than twenty constrained frames per type. It is an explicit planning policy, not a motion-quality guarantee or upstream hard limit. A budget too small for required events fails with an explanation. Optional `frame_indices` select exact frames within that budget and must preserve every required boundary/change. Omitting `guide_plan` preserves historical dense requests; their plan reports whether they meet the sparse recommendation.

Preview the temporal plan without loading pose arrays, weights or character assets:

```text
python scripts/scene_generation_guides.py scene.json actor-plan.json reports/guides-preview.json
```

The preview retains every actor's complete contact clock, selected guides, required events and effector memberships. It checksums input JSON and planning methods before reading, rechecks them before writing, and creates its output exclusively. Existing previews are preserved. Previewing does not evaluate pose geometry or generated motion.

The existing `scene_generation.py prepare` path compiles the selected actual fitted poses and saves `generation-guide-plan.json`, its checksum and a planner source snapshot. Before encoding/generation and scene assembly, the preflight rebuilds the plan and verifies complete actor/request populations, exact guide frames/effectors, prompt schedules, seeds and provenance. New plans cannot drop their binding or the complete reference-preflight contract. Original reference/model-projection contact and geometry checks still evaluate every authored contact frame.

Validation: 70 model-free planner/integration/preflight tests pass, with zero failures, errors or skips. They cover sustained intervals, simultaneous hands, one-direction partner contacts, insufficient budgets, invalid/manual selections, changed or rebound populations, dropped artifacts, changed requests/seeds, source snapshots, legacy compatibility and input-read races. Pose compilation is substituted in request tests; no production skeleton or model is loaded. The standalone CLI also previews the saved high-five metadata, preserving frame 60 for both actors. Earlier development checks/previews remain locally retained. The hosted manifest expands from 387 to 388 Python modules, four shards of 97 per operating system; its 36 Node scripts remain unchanged. Hosted validation of this new commit is pending.

No inference, training, dependency acquisition, live Studio/browser, engine playback or human quality review runs for this change. All fourteen release evidence arrays remain empty; the whole-project goal remains active. Next improve interaction initialization diagnostics and assess source/target representation failures before broad motion-quality validation.
