# Continued rate fitting and a native motion comparison

The first [contact-preserving rate fit](contact-rate-path-v1.md) hit several
experimental control limits. This continuation uses its actual serialized clips
as the starting path, with the same 36-control parameterization and per-step
component bounds. Original joint-angle references, motion-rate caps, authored
contact, protected spans and collision checks are unchanged. It does not reset
cumulative joint budgets or redefine the original rate comparisons.

## Completed continuation

Both optimizers converge (80 and 47 iterations), but serialized acceptance
requires backtracking. Actor A retains only 1/128 of its proposed correction;
actor B retains half. The weighted rate-violation objectives change from
0.081553251 to 0.081450793 and from 0.077616053 to 0.066297612 respectively.
Full-strength serialized proposals fail the proposal constraints. Halving is
not guaranteed to follow a feasible path through nonlinear skin constraints.

The selected exported clips pass all 53 full inter-actor mesh samples, with zero
detected crossings or contained-vertex depth. Contact gap is 1.000027 mm, and
original joint budgets, clocks, unselected channels and protected/outside poses
pass. Contact matrix drift relative to the preceding source is below 3e-8.
The auxiliary 0.45 mm plane check passes; the separate 0.5 mm comparison remains
false. This is sampled geometry evidence, not continuous collision approval.

| Original rate cap | Failed rows before / after | Maximum excess before / after |
| --- | ---: | ---: |
| Position speed | 143 / 161 | 0.416948 / 0.384053 m/s |
| Position acceleration | 278 / 278 | 65.514376 / 63.120973 m/s² |
| Angular speed | 1,336 / 1,337 | 2.206840 / 2.479271 rad/s |
| Angular acceleration | 228 / 257 | 229.029390 / 229.012917 rad/s² |

All four groups still fail. The angular-speed peak worsens, and several failure
counts increase. The estimated near-contact marker velocity jumps change only
from 0.349037 to 0.348609 m/s for A, and from 0.449183 to 0.412490 m/s for B.
The continuation is retained for comparison, not promoted as an overall quality
improvement or selected for Studio. Floor and human-quality requirements remain
unresolved.

The next solver experiment should provide inward numerical room for serialized
proposal constraints and protect individual rate peaks alongside the scalar
objective. Keep the actual collision and original rate acceptance limits fixed;
do not run repeated weighted-score continuations as a substitute for satisfying
the remaining gates.

## Inspecting the actual clips

The local package `reports/native-contact-review-v2` compares three stages:
native wrist retraction, the first rate fit, and this continuation. It copies
the six GLBs byte-for-byte, validates their input/output hashes, requires matching
contact intent, actor placement and audit times, and displays each version's
contact gap, sampled mesh failures, penetration and four rate-failure counts.

The viewer preserves exact time in seconds across version changes and uses the
actual 3.666666746 s native duration. Contact seeks to 2.091722595 s, without
rounding to a nominal frame. It uses the original grey characters, all eight
skin influences, full-pair and hand camera controls, playback and downloadable
GLBs. It submits no ratings or cleanup-time evidence and changes no Studio
selection. This supplements the existing developer review workflow; it is not
a new blind human-review experiment.

When serving the repository root, open
`/reports/native-contact-review-v2/viewer.html`. Viewer dependencies must already
be installed under `assets/viewer/node_modules`; this is a local workspace
report, not a portable installer. The first package is retained unchanged;
version 2 adds a guard against negative animation-frame elapsed time.

Offline validation loads all six copied GLBs through Three.js, verifies their
recorded durations and complete normalized eight-weight skins, and exercises
start/contact/end/backward seeking with finite bone matrices. Khronos glTF
validation reports **zero errors and zero warnings**. The clock tests preserve
fractional contact time and stop at the actual endpoint. Module syntax and
referenced DOM IDs were checked. **Browser rendering and WebGL shader execution
remain unverified**; these checks do not establish visual fidelity or human
animation quality.

## Reproduction and evidence

```powershell
.venv/Scripts/python.exe scripts/study_contact_rate_path.py reports/contact-rate-path-v1 reports/<fresh-continuation>
.venv/Scripts/python.exe scripts/diagnose_native_contact_turnaround.py reports/<completed-continuation> reports/<fresh-diagnosis>
.venv/Scripts/python.exe scripts/build_native_contact_review.py reports/<fresh-comparison> reports/native-wrist-retraction-v1 reports/contact-rate-path-v1 reports/<completed-continuation>
node scripts/verify_native_contact_review.mjs reports/<completed-comparison> reports/<fresh-check>/verification.json
node tests/test_native_contact_clock.mjs
```

The continuation binds 4,475 inputs, 93 methods and 60 outputs. The read-only
turnaround diagnosis binds 4,629 inputs, 94 methods and two outputs. All were
rehashed without mismatch, including archived/current methods. Result hashes:

- Continuation: `f53721ca7acac20f1fd35a62e351498487f2ae3f240d64b79c35b48fc1135053`
- Diagnosis: `f57832e8cf74dcf61840ed705cd5dbb652fbec38f344de644743d633e03ed7e1`

The unchanged 1,059-test Python source suite passed hosted checks on the preceding
commit; the new viewer-clock test passes locally and is added to CI. This turn
does not claim a newly rerun full Python suite. No checkpoint changes, model
training, reserved held-out prompt use or release-gate approval occurred.

The final comparison binds 4,629 inputs and 17 copied/generated files. Build SHA-256: `9e268912044ba87aae173fbfbb9fd8fba3384f1073778d9a9753174aeb5918d7`. Offline verification SHA-256: `d2420a86f2fba00c4119dcd45bfa23078b41560827932182d655d3e8acf8a4f9`. All copied file hashes match.
