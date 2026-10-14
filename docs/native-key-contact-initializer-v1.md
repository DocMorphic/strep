# Rig-aware initialization on existing animation keys

The transferred kick has a spatially feasible support-leg pose, yet the preceding eight-knot correction cannot retain a changed clip under its original motion limits. This experiment fits existing native rotation keys directly, using the supplied rig's complete skin and declared point targets. It substantially reduces floor error but still fails both between-key geometry and motion-rate checks. The original remains selected.

This is an explicitly different temporal proposal representation, **not a passing revision of the earlier bounded-knot contract**. Original failures and the earlier correction are retained. Rotation, joint-displacement, root, endpoint, contact, floor and original motion-rate limits are not enlarged.

## Public workflow

```powershell
python scripts/native_key_contact_initializer.py contacts.json geometry.json initializer.json fresh-output
python scripts/audit_native_key_initializer.py fresh-output fresh-replay --expected-result-sha256 <trusted-result-digest> --expected-request-sha256 <trusted-original-request-digest>
```

The `strep-native-key-contact-initializer-v1` request binds the original contacts digest, actor and fixed root. It declares rotation nodes and degree limits, a native-key-aligned edit window, frozen key times including both clip endpoints, maximum joint displacement, complete-key/iteration/time budgets and an inward floor reserve smaller than the unchanged geometry tolerance. Inputs may contain arbitrary supported clips and scene contacts; actions are not enumerated by the solver.

Current limits are one selected actor, 1–16 existing LINEAR rotation tracks with identical native clocks, 30 degrees per track, 22 cm joint displacement, 4,096 keys, 32,768 skin vertices, 100,000 scalar pose conditions, 150 iterations per key and a 600-second key-initialization budget. The existing resource supervisor separately bounds the whole job. Unsupported populations reject rather than being sampled or truncated. Proper rigid source locals are required. Root channels, local translations, unselected channels, skin payload and the original animation library remain preserved. A separate appended animation is selected explicitly.

Every key includes all triangle-referenced vertices against every declared plane, all skin-joint displacement conditions, rotation-vector norm constraints and every active affected point contact. Outgoing world/object/partner targets and incoming partner targets retain their authored coordinates, reductions and timing. Other actors and objects stay fixed to their source trajectories. A single-key guide does not enforce hold-slip, collision or between-key motion conditions.

Analytic derivatives account for all skin influences, hierarchy ancestry, actual inverse-bind homogeneous coordinates, actor placement and rotation-vector Jacobians. The joint origins and full mesh share the same articulated pose. The objective favors smaller edits. Failed pose solves retain the original key; solver success alone never permits adoption. The normalized `1e-7` proposal-inequality guard is only a numerical initializer check. Final decoded rotation/displacement bounds are strict, and the root must match exactly.

After export, complete contact and geometry audits use the actual appended animation. A separate full-clock check measures decoded edit bounds and root identity. All four original motion-rate arrays are recomputed from the unchanged original clip at 120 Hz, in the existing four bins with `1e-5` tolerance. Candidate rates are compared against those original arrays, rather than becoming a new reference. Every failed decision is retained.

## Complete development result

The Kenney kick trial preserves the original transferred clip, 30-degree left hip/knee/foot/toe permissions, 22-cm joint bound, root node 21 and both endpoints. It retains the separately declared right-foot position at 0.733333349 seconds within 5 mm. That target is at Y=1.586907 m; it is a raised-foot preservation example, **not inferred ground support** or anatomical approval. Baseline contact intent remains separate.

All 120 per-key continuous pose checks pass. Maximum decoded joint displacement is 185.338012 mm and maximum rotation edit is 9.077956 degrees. The root matches exactly on the complete decoded clock; the declared contact audit passes. Original rate-cap arrays match the earlier source epoch exactly.

| Full decoded measurement | Original transfer | Key-initialized proposal |
| --- | ---: | ---: |
| Floor samples | 2,017 | 2,017 |
| Triangle-referenced vertices / faces | 1,029 / 1,604 | 1,029 / 1,604 |
| Times failing the unchanged 5-mm floor screen | 234 | 32 |
| Maximum floor depth (mm) | 49.727615 | 6.509660 |
| Failed original motion-rate rows | 0 | 58 |

The remaining worst floor depth occurs at 0.65 seconds, between native keys. The 85,590 original rate rows are all evaluated. The candidate remains rejected: neither a collection of feasible keys nor a large numerical improvement establishes a usable animation. No prior fit, engine or quality approval is inherited.

The actual initializer takes 29.343 seconds with 47 resource observations. Its first complete fresh replay takes 34.468 seconds with 52 observations and reconstructs exact GLB bytes, every key-pose decision, full contact/geometry observations, complete source/candidate worlds, original cap arrays and all numerical decisions without executing the optimizer. Shared readers, skin and pose arithmetic are explicit; this is not independent physics or human review.

The public auditor subsequently strengthens provenance by requiring both trusted original request and result digests. It also checks exact original authoring, animation index, method snapshots and typed result fields. Added or forged approvals, changed bounds, altered arrays and rehashed numerical summaries reject. A separate fresh replay through this strengthened contract passes in 27.328 seconds/45 resource observations, reproducing all complete arrays and failed decisions. Both actual replay resource traces pass.

## Software and evidence scope

All 18 initializer checks pass, including complete finite-difference skin/constraint comparisons for incoming/outgoing contacts and non-unit homogeneous terms, source/clock/library preservation, strict input bounds, native window alignment, complete population sizing and failed/frozen-pose rejection. All 45 auditor and compatibility checks pass, including eight new audit cases and the existing geometry/support-rate suites. This verifies 63 selected software checks, without motion-quality approval. Final initializer checks take 22.266 seconds/40 resource observations; auditor/compatibility checks take 53.594 seconds/71 observations. Their resource traces replay.

An initial syntax/setup failure occurs before any numerical worker starts and is retained. The first audit-test driver names a nonexistent test file, performs zero tests, and exits; all 18 resource observations of that failure replay. Corrected checks use a fresh output directory. Neither failure changes numerical limits or acceptance.

Private evidence remains under ignored `reports/native-key-contact-validation-v1` / `v2`, `reports/kenney-native-key-contact-v1`, `reports/kenney-native-key-contact-replay-v1` / `v2`, and `reports/native-key-initializer-audit-validation-v1` / `v2`. Character payloads and bulky outputs remain excluded from public Git.

All eight [focused hosted jobs at dae4cc6](https://github.com/DocMorphic/strep/actions/runs/38601904140) pass on Windows and Linux for the preceding public paired-repair change. This new source needs its own hosted result. No model generation, training, reserved held-out cases, engine execution, new human ratings or timed cleanup measurements occur here. All fourteen release capabilities and calibration gates remain unchanged and unapproved.

Next, enforce clearance over the interpolated segments and restore the original temporal conditions jointly. The method must then be exercised on broader actions, rigs and scene/partner constraints, with complete import/runtime, style, semantic and developer-review evidence. The entire-project goal remains active.
