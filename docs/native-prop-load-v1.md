# Recorded prop motion to sampled load demand

The native mass-response study now saves complete force/torque diagnostics for each physical prop case. It uses the recorded body gravity, native mass/inertia settings and the actual observed ownership clock. This advances load-aware authoring without assigning an invented lifting capacity to a designer's strength slider. Actor motion still does not respond to prop mass; effort generation/editing and human review remain necessary.

The existing rigid-body diagnostic uses **F = m(a − g)** and **τ = I_world α + ω × (I_world ω)** about the COM. See the primary [Modern Robotics rigid-body dynamics explanation](https://modernrobotics.northwestern.edu/nu-gm-book-resource/8-2-dynamics-of-a-single-rigid-body-part-1-of-2/). These are required net non-gravity force and COM torque under the recorded settings, not measured hand/muscle forces. [Godot's direct body state](https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate3d.html) supplies gravity, inverse mass/inertia and the physics step. Native startup metadata confirms the current SDK's custom-zero COM setting; the diagnostic therefore uses body origins as COM positions. It rejects missing/automatic/nonzero COM settings instead of guessing a mesh centroid. This is startup-setting provenance enforced by the bound SDK, not an independently recorded per-tick COM sensor.

`object_dynamics.py` now also accepts a complete `(frame_count, 3)` gravity track. Constant-vector inputs preserve their original complete output; recorded variable gravity uses the central sample without smoothing. `scene_prop_load.py` validates the complete live clock, source times, physics steps, rigid matrices, native inverse settings and ownership. Every change of grip membership splits the support phase, even if the prop remains held. All central samples and boundary values remain in the report; phase summaries exclude stencils crossing ownership changes. Released phases stay **unknown**, including collisions; an empty contact list never becomes a free-flight certificate.

Reports also compare COM/angular velocity estimated from poses against recorded body velocity/spin. Their native body metadata is detached from input captures, so editing a returned report cannot mutate the original. The source clock is `tick / physics_fps`; actual float-precision native step values are retained separately. No resampling or smoothing hides jumps, quantization, transfer boundaries or impacts.

## Matched native evidence

The same procedural two-actor source ZIP and original grip/ownership request are evaluated at 60 Hz with 2 kg and 200 kg. Each pinned Godot 4.7.2/Jolt run captures **121 complete records**, **119 central estimates**, four ownership phases, **79 held records** and **74 held phase-interior estimates**. Boundary frames 1, 47, 48, 78 and 79 are retained but excluded from phase summaries.

| Held-motion diagnostic | 2 kg | 200 kg |
| --- | --- | --- |
| Peak required net non-gravity force | 23.223173 N | 2322.317314 N |
| Peak required COM torque | 0 Nm | 0 Nm |
| Maximum pose-derived vs recorded COM velocity difference | 0.060002804 m/s | 0.060002804 m/s |
| Maximum pose-derived vs recorded spin difference | 0 rad/s | 0 rad/s |

All held force vectors scale by 100 under identical trajectories; all held prop matrices and both actor bone populations remain exactly unchanged. The 6 cm/s velocity discrepancy reflects the current held-pose controller moving the body while recording zero velocity. This establishes a missing feedback/state behavior, not proof that either mass is liftable or either performance looks believable. These are tiny procedural integration rigs, not production humanoid or held-out animation evidence. This native fixture has no rotation and therefore does not establish nonzero torque behavior. A separate analytic test rotates an anisotropic body about a nonprincipal axis and verifies its nonzero gyroscopic torque and complete independent replay.

`verify_scene_prop_load.py` independently reconstructs every force/torque/vector sample, support phase, boundary mask, peak/percentile/mean and velocity discrepancy from raw native data without importing the producer. Numeric populations use a 1e−12 absolute/relative replay tolerance; engine inverse-setting comparisons retain native float-precision tolerance. Machine-precision ties may name any original phase frame with a maximal reconstructed value within that numeric tolerance; a nonmaximal or out-of-phase peak is rejected. This is arithmetic/provenance verification, not a derivative-error bound, sensor measurement, force-allocation solution or quality review.

**91 focused checks pass in 2.26 seconds**: 39 native-load/replay tests, 19 rigid-body diagnostic tests and 33 existing mass-comparison tests. Coverage includes analytic support/ballistic/gyroscopic dynamics, variable gravity, complete clocks/settings, support boundaries, detached metadata and changed force/torque/peak/evidence rejection. Initial checks exposed zero-comparison roundoff, an overly strict native-inertia comparison and reordered constant-torque peak ties; corrections keep numerical replay tolerance separate from engine precision. No physical acceptance gate is relaxed. Inventory is **422 Python modules / 41 Node suites**, preserving previous entries.

The final native guard exits zero in **7.328 s**, sampled peak **197767168 bytes**, with **nine independently replayed resource observations**. The earlier completed source version is preserved separately: 7.312 s, peak 95129600 bytes, nine observations. It precedes detached returned metadata; final methods, raw outputs, packages, original inputs and both load reports are independently bound and replayed. These tiny 512 MiB-plus-600 MiB studies do not lower full native fit/audit estimates.

## Reproduce

With separately acquired source assets and the pinned engine, use a fresh output directory:

```powershell
python scripts/run_guarded_job.py --worker scripts/study_scene_prop_mass.py --output reports/my-load-guard --expected-rss-mib 512 --stable-seconds 3 --admission-seconds 60 --max-seconds 180 --poll-seconds 1 -- source-game-assets.zip ownership-request.json reports/my-load-study --prop item --masses 2 200
python scripts/verify_scene_prop_load.py reports/my-load-study/case-0/engine.json reports/my-load-study/case-0/load.json --prop item
python scripts/verify_scene_prop_load.py reports/my-load-study/case-1/engine.json reports/my-load-study/case-1/load.json --prop item
```

Use the project's pinned CPU SciPy/NumPy environment; no Torch or model inference is required. Public source does not bundle character assets, weights or the engine. Original motion/scene/intent and complete packaged members remain unchanged; the study adds separate diagnostics only.

Local final evidence under ignored `reports/native-prop-load-v1/`:

| Artifact | SHA-256 |
| --- | --- |
| 2 kg raw capture | `280af5ac36c01918384170f99602ea3d38c4181b6865009379ae86eff5966cc0` |
| 200 kg raw capture | `60e063e923d2dd3d18fe37ad433d5e0e8a9e08134e6c26a0c28387ea24483e24` |
| 2 kg load report | `9d0413dfcb4899e8903620baaf62678695c24181ffbb4a97b51b796d78a3c656` |
| 200 kg load report | `32a1aefe6c112ef0c2ba568b48b6f1931ec4de011e7edfe31f4c93347d9cf46d` |
| Final independent verifier | `0b1607194fec55f91f961bc266b20c63d2ca0d4ac951da09df6608f19c19a033` |

A fresh full alternative-solver admission attempt also defers without a child after60.672 seconds, with61 independently replayed observations. Its 2 GiB-plus-600 MiB requirement and fifteen-second stability remain unchanged. [Verified V8](isolated-contact-replay-v1.md) stays trusted at0/62 complete contact passes; no conic fit/adoption is claimed. Human ratings and timed cleanup remain absent, every release capability remains unapproved and the single full-project goal stays active. Continue explicit effort authoring, actual contact correction, broad action/rig/scene/partner/edit/style/transition/engine evaluation and developer review.
