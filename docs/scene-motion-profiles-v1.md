# Per-actor movement profiles in scene requests

Scene actor plans now accept the existing optional `motion_profile` alongside `segments`, `seeds` and `guide_plan`. Each actor can use different style, training, current state, numeric stats and custom description rules. Both text-only and contact-guided requests preserve that actor's identical profile, so their comparison changes guidance rather than character direction. Action descriptions remain open vocabulary; profiles apply to every segment without changing its authored duration or contact clock.

Use the schema described in [character movement profiles](motion-profile-v1.md). To add an existing validated profile to actor `A`, assign it as `actor_plan["A"]["motion_profile"]`. Other actors can omit a profile. Omitting profiles preserves the previous request fields and guide-plan report structure. Dense and explicit sparse guide policies both support profiles.

These controls are designer-owned text rules. Three descriptions map stat values into the existing 0–33, 34–66 and 67–100 bands. Custom stats are allowed; unmapped stats such as default endurance retain their values and appear explicitly as unused conditioning metadata. They do not silently become fatigue or force simulations. A profile's generated response remains unvalidated.

Preview without loading model weights, poses or character assets:

```text
python scripts/scene_generation_guides.py scene.json actor-plan.json reports/profiled-guide-preview.json
```

The report includes each actor's original/resolved segment wording, applied and unmapped rules, profile compiler hash and unreviewed status. Actors without profiles appear as null in a mixed-profile report. Input and compiler checksums are bound before reading and rechecked before writing. Preview output cannot overwrite a previous report.

Preparation saves the same briefs in `generation-guide-plan.json` and binds a `motion_profile.py` source snapshot whenever any actor is profiled. Pre-inference checks reject dropped, swapped or changed actor profiles, changed compiler snapshots and rebound resolved wording. Scene assembly verifies every exported generation record's actor request, integer seed, complete batch digest, generated status and exact motion brief before loading scene assets. The scene manifest also retains actor briefs. The existing generator/encoder/export paths already consume and retain resolved profiles; this change connects scene plans to those paths.

Validation: 102 model-free profile/planner/preflight tests pass with zero failures, errors or skips. They cover independent actor controls, multiple arbitrary-action segments and seeds, mixed/absent profiles, object and partner clocks, dense/sparse guidance, invalid rules/values, excessive effective descriptions, preparation snapshots, conditioning provenance and rejected mismatched takes before asset loading. Pose compilation, preparation geometry and preflight are substituted in these integration tests; no production skeleton or inference is tested. An actual metadata-only CLI preview of the saved high-five scene retains separate high/low-agility profiles and frame 60 for both actors. Earlier checks and immutable preview snapshots remain locally retained.

The hosted inventory now contains 389 Python modules across shards of 98/97/97/97 and 36 unchanged Node scripts per operating system. Hosted validation of this commit is pending. No live Studio/browser, inference, training, dependency acquisition, engine playback or human review runs for this change. It does not resolve the retained scene collisions or establish per-stat motion response, physiological control or release quality. All fourteen release evidence arrays remain empty and the whole-project goal stays active. Next connect authoring and interaction initialization diagnostics to this profile-aware scene path, then measure action preservation and distinct motion response before approval.
