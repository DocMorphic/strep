# Held-object mass response: a measured missing behavior

Changing a physical prop's mass does not currently change the character animation while that prop is held. The shared owner parks held props at the authored grip pose, disables their collision layers/masks, and directly sets the body state. It uses the original actor clips and performs no inverse dynamics, load-based reposing, exertion synthesis or strength-capacity check. Released props participate in their configured physics simulation. This is the current SDK's fixed-motion baseline; it is **not** a test of how the unchanged generative checkpoint responds to a prompt describing a heavy object.

Godot documents direct state access through [`RigidBody3D._integrate_forces`](https://docs.godotengine.org/en/stable/classes/class_rigidbody3d.html#class-rigidbody3d-private-method-integrate-forces). Its [`PhysicsDirectBodyState3D`](https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate3d.html) exposes the applied gravity vector and inverse mass. The experiment records those native values instead of inferring body settings from a successful import or confusing a prop's mass parameter with an animator's strength control.

## Matched experiment

The same source game ZIP, original actor/prop assets, grips, event clock, earlier CCD profile, 60 Hz rate, 16 ms timing contract and scene placement are used for both cases. Only the selected prop's mass changes, from **2 kg to 200 kg**. Inertia is recomputed from the same uniform source geometry. Both requests are fully source-bound and boot through the current SDK's normal native binding checks.

The actual pinned Godot 4.7.2-stable runs return **121 complete records each**, of which **79 are held records**, with both actors present. Actual masses are 2 and 200 kg. Native inertia changes by a factor of **99.99999674**, reflecting engine precision. All 79 held prop matrices and both actors' complete bone populations have **zero component difference** between the two cases. Collision layers and masks are zero while held. The measured gravity force magnitudes from the body states are **19.620000839 N and 1962.000083923 N**; the nominal project-gravity weights are 19.62 and 1962 N.

Those force magnitudes are gravity loads, not measured muscle forces or a certificate that an actor can lift either object. Acceleration, torque, grip friction, load sharing, balance, external contacts, fatigue and anatomical capacity are not evaluated. The benchmark does not require every change of mass to produce a visibly different pose: a deliberately held pose may remain the same. It establishes that this SDK performs no feedback from mass to the saved actor motion. A requested heavy/weak/strained performance must be explicitly generated or edited and then checked; changing mass alone does not create it.

The Studio grip panel now states that held props follow saved grip motion and that changing mass does not add strain, change posture or check lifting capacity. No nominal strength-to-kilograms conversion is invented. Semantic and animator review remain necessary to establish believable effort. This is a demonstrated development gap for the general-purpose system, not a new contact-quality pass or a reason to train immediately.

## Reproduction and scope

With separately acquired source assets and the pinned engine, run the public study under the project's owned resource supervisor:

```powershell
python scripts/run_guarded_job.py --worker scripts/study_scene_prop_mass.py --output reports/my-mass-study-guard --expected-rss-mib 512 --stable-seconds 3 --admission-seconds 60 --max-seconds 180 --poll-seconds 1 -- source-game-assets.zip ownership-request.json reports/my-mass-study --prop item --masses 2 200
```

The study requires a fresh directory under ignored `reports/`, two distinct masses within the existing 0.001–10000 kg SDK range, complete bounded native clocks, successful current SDK binds, exact input/method hashes and complete ZIP preservation. It archives both requests, packages, methods and raw native observations. It stops at the complete source duration, rather than taking a favorable subset. The public runner is a development experiment, not a production deformation or physics solver. No models, rigs or engine binaries are included in the public source snapshot.

**33 focused comparison tests and four Studio preservation tests pass** in 2.12 s. After adding the panel text, all four preservation tests pass again in 0.63 s, and the existing offline grip-editor suite passes. Tests cover no-response and changed-response cases, matching populations, malformed clocks/masses, missing actors, invalid matrices/gravity/inertia, native inverse-mass mismatches and unchanged false quality/release fields. They are synthetic guards, not engine proof. The separate native experiment provides that evidence.

The final native guard exits zero in **7.312 s**, sampled peak **182366208 bytes**, with **nine independently replayed resource observations**. The earlier unextended experiment is preserved separately: ten observations, exit zero, 8.375 s, peak 104353792 bytes. Its source snapshot predates complete-clock/body-gravity checks; it is not treated as the final method. Independent replay verifies every final raw response, native mass, held tick, actor pose and complete package/source binding. This small procedural 512 MiB plus 600 MiB admission does not lower full native fit/audit profiles.

The explicit model-free inventory becomes **420 Python modules / 41 Node suites**, preserving all previous entries. No acceptance gate, capability status or release approval changes.

Local final raw SHA-256 values under ignored `reports/prop-mass-response-v1/matched-final/`:

| Artifact | SHA-256 |
| --- | --- |
| `case-0/engine.json` | `a658cdbaac98a38cdf51ec7a6d1781157a979bd280cf6342e6f3a78804814bb0` |
| `case-1/engine.json` | `abf6b26bc51f4bba38bd46c5220e88468c352483cf1cff36aff97c71c957e1e4` |
| `protocol.json` | `3e722afd2995b7ad6f28668c7adfe7ec773bd18f10bf98f79304bd350e43878b` |

Two fresh full V8 contact geometry replay admission windows each defer without a child: **61 observations per attempt**, unchanged **2776629248-byte** requirement. The first was launched with the native venv rather than the auditor's required Torch-free interpreter; no worker starts, and no geometry result is produced. The corrected isolated runtime also lacks sustained headroom. Both deferrals are preserved and independently replayed. V7 therefore remains the latest verified contact state at 0/62 complete physical/keyed passes; V8 is not adopted. No unrelated applications or servers are stopped.

Next work is explicit load-aware authoring and correction with measured force/torque, contact and effort evidence, alongside the pending native contact replay and broad action/rig/style/transition validation. Saved poses are not silently altered and no arbitrary capacity rule is made a release gate. The developer review packet still lacks actual ratings and cleanup trials. All fourteen release capabilities remain unapproved and the single project-wide goal stays active. The running Studio backend is not restarted; live delivery is unverified.

## 2026-10-10 update

The [native prop-load integration](native-prop-load-v1.md) now saves and independently verifies complete sampled force/torque demand and pose/velocity discrepancies, with actual gravity, native custom-zero COM settings and separate ownership phases. The mass-to-animation feedback gap remains. [V8 contact replay](isolated-contact-replay-v1.md) is now independently complete; its full contact checks still fail and no release approval changes.
