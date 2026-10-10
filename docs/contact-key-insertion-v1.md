# Contact key-insertion pilot

The nine-key wrist-guide insertion pilot is rejected. Every inserted pose passes the existing contact and source-cap checks, but the exported motion loses 46 previously passing sampled conditions. Successful poses and preserved original keys do not establish successful interpolation.

## Frozen population and method

Use the [previously frozen selection](pose-continuation-v1.md): three quarter keys in each of native intervals 79–80, 78–79 and 80–81, sorted by time and quantized to float32. Preserve all 180 existing native quaternions exactly in each of eleven edited channels. The new rotation clock contains 189 keys. Preserve the original binary prefix, mesh, skin, nonedited channels and other asset data.

Interpolate the fitted endpoint wrist guides in object coordinates, fit with the public previous-pose helper, and evaluate the actual five skinned contact points per hand and their complete incident faces. Keep eight 45-degree arm caps, three 15-degree torso caps, original translations/fingers/other local transforms, 5-mm position, 5-mm/s relative speed, 15-degree opposition and 0.5-mm side limits. Caps describe source-relative edits, not anatomical joint limits.

All nine inserted poses pass. A separate Rodrigues/FK/scalar-skin/complete-incident-normal replay verifies 99 source caps and 90 contact correspondences; original feet differ by at most 4.45e-16 in their world matrices. All 180 original quaternions remain exact in all eleven channels.

## Actual exported motion

The full original/added clock has **1,041 times per contact**, 10,410 normal correspondences and the unchanged **16,960 rate/phase point-velocity pairs**. Eight of the nine added times are distinct from the original contact-clock union; the remaining time already belongs to it. Independent replay checks the clock, complete face incidence, scalar contact arithmetic, normal availability/coherence, opposition, side, speed and pass decisions. Asset parsing, native interpolation and skin-weight loading are shared and remain outside its independence.

| Contact | Old worst speed | Pilot worst speed | Previously passing conditions lost | Selected failures repaired |
| --- | --- | --- | --- | --- |
| Left center | 12.2230 mm/s | 20.6028 mm/s | 2 | 13 |
| Right center | 8.2666 mm/s | 10.5545 mm/s | 7 | 2 |
| Left neighbors | 12.2544 mm/s | 20.8524 mm/s | 9 | 80 |
| Right neighbors | 8.4028 mm/s | 10.6168 mm/s | 28 | 8 |

Of the 46 losses, 45 are velocity-pair failures and one is a left-neighbor side failure. All original position conditions remain passing, and no original opposition condition loses its pass. Every original sampled position/opposition/side value outside the selected intervals is identical; original velocity pairs without positive-duration overlap are also unchanged. The pilot repairs 103 conditions but still fails the predeclared zero-loss rule. Do not expand this candidate to all 135 proposed keys or admit it as a generation guide.

A separate scalar comparison reconstructs **30,990 original position/opposition/side conditions** and all 16,960 velocity pairs. At the added poses, the maximum contact-error departure from the original endpoint-error chord is only 0.309 / 0.849 / 0.320 / 0.866 micrometres for left center, right center, left neighbors and right neighbors. These small departures do not prevent larger excursions between joint keys. They motivate testing joint-curve consistency rather than assuming more independently fitted poses will solve sliding. This is an inference from this fixture, not a proof about every character or action.

The first scalar auditor completes its assertions but fails while serializing a NumPy integer. Preserve that failure and its 112 resource observations. A new auditor casts receipt counts explicitly and caches saved arrays instead of repeatedly decompressing them; it repeats the same scalar calculations and passes. Numeric thresholds and comparison decisions are unchanged.

## Next bounded experiment

Use the same nine keys, original native quaternions and acceptance limits. Initialize from the failed pilot. Fit all ten actual skinned points toward the baseline endpoint contact-error chord while anchoring selected local rotations to the baseline interpolant at the current inserted-key time. Explicit objective weights: 1,000 for world point residuals, 0.002 for source rotation vectors, 0.2 for local rotation departure from that baseline interpolant. Enforce source-norm caps and interior 14.99-degree opposition / 0.49-mm side solver constraints, with at most 200 SLSQP iterations per pose. Those interior solver margins do not relax the original acceptance limits.

This is a finite pilot, not a continuous-time or globally optimal motion solver. Preserve failures, independently replay actual poses/export, evaluate the full original/added clock, and require zero lost original passing conditions before expansion. Whole-body geometry, forces, engine imports, held-out actions/rigs and real human ratings/cleanup remain separate release work. No new model training is admitted.

The first skin-chord producer is interrupted by the original available-RAM guard after 114.359 execution seconds, one passing reported pose and no completed export. All 114 resource observations replay. Its partial solver report is retained; it is not a resumable full-array checkpoint or completed pose/clock proof. A fresh retry uses the same numerical method and records partial observation arrays and their hash after each completed pose. Neither memory budgets nor contact acceptance limits are reduced to obtain a run.

## Completed skin-chord pilot

The checkpointed retry completes in **486.235 execution seconds**. All nine actual skin poses pass, all original native quaternions remain exact, and independent replay again verifies 99 caps and 90 point correspondences. Four optimizations report convergence; five reach the 200-iteration limit. Preserve those statuses: actual feasibility does not establish optimality.

At the complete exported clock, the revised pilot repairs **150 original sampled failures with zero previously passing conditions lost**. Per contact, it repairs 21 / 3 / 114 / 12 conditions for left center, right center, left neighbors and right neighbors. All 31 selected opposition/side failures disappear. Selected failing velocity pairs decrease from 23 / 3 / 91 / 12 to **2 / 0 / 8 / 0**. Worst selected speeds become 6.931 / 3.191 / 7.080 / 3.229 mm/s. Thus the finite pilot meets the predeclared expansion rule while still failing the original 5-mm/s speed threshold in ten selected point pairs.

Full-clip worst speeds are 7.538 / 8.267 / 7.638 / 8.403 mm/s; unselected intervals retain failures. Both neighbor rows still fail the full-clip side test. Do not describe this as a completed contact correction or usable generation guide. Full-clock scalar preservation replay again checks 30,990 contact conditions and 16,960 velocity pairs. An additional original-source comparison verifies **11,451 rotation-cap conditions at 1,041 times**, with zero cap failures, protected-local differences below 7.78e-16 and preserved translations. It uses the previously explicit serialized-quaternion allowance of 1e-5 degrees; the unexported candidate allowance remains 1e-8 radians. Shared native samplers remain outside independence, and finite clocks do not establish continuous-time behavior.

The next experiment expands the already frozen 45-interval/135-key population with this actual-skin/baseline-curve method, preserving the nine verified candidates and all original keys. Evaluate every remaining pose and the complete export clock, preserve failures and passing conditions, and assess geometry/force only after contact completion. More keys alone are not an acceptance condition.

Expansion preflight verifies 135 distinct float32 interior times, all 45 selected intervals, exact inclusion of the nine verified candidates, a 315-key rotation clock and the original 192-added/512-total budgets. The first launch rejects a requested 7,200-second runtime before starting a worker because the unchanged supervisor permits at most 3,600 seconds. Preserve that policy rejection. A revised preflight and bounded first stage keep the complete population frozen while fitting at most eighteen new keys; immutable per-key NPZ/JSON checkpoints retain candidate arrays and hashes. Subsequent stages require separate candidate replay before carrying those keys forward. No partial stage is a completed 135-key asset.

## Verified staged expansion

The first four stages complete with **72 passing inserted poses** in the frozen population. Each stage independently replays every accumulated candidate against the original source, actual partial skin, complete incident normals, contact decisions and source caps. The fourth stage includes all nine verified pilot candidates; the other 63 poses are new fits.

| Stage | Accumulated passing poses | Replayed source caps | Replayed contact correspondences | Producer execution | Resource observations |
| --- | --- | --- | --- | --- | --- |
| 1 | 18 | 198 | 180 | 299.437 seconds | 284 |
| 2 | 36 | 396 | 360 | 241.578 seconds | 231 |
| 3 | 54 | 594 | 540 | 225.687 seconds | 216 |
| 4 | 72 | 792 | 720 | 356.797 seconds | 337 |

All producer and pose-audit resource traces replay. The source foot-matrix difference remains below 6.67e-16. Separate continuation replay checks every carried array, report and numerical-policy field: stage 2 preserves 594 arrays / 124,182 scalar values from its eighteen-key predecessor exactly; stage 3 preserves 1,188 arrays / 248,364 scalar values from its thirty-six-key predecessor exactly. A separate stage-3 pilot comparison verifies all 99 arrays / 20,697 values for the three pilot keys included at that stage. Source/previous transforms, targets, all weights, caps, margins, iterations, clocks and original input hashes remain unchanged.

Stage 4 independently preserves all 1,782 arrays / 372,546 scalar values and reports from its fifty-four-key predecessor. Separate pilot replay verifies **all nine** retained pilot candidates, comprising 297 arrays / 62,091 scalar values, exactly. No interpolated asset or guide is admitted from these pose-only results.

The first stage-3 continuation auditor fails on a flat-manifest assumption: six ancestor inputs are carried through the exact bound parent-plan hash rather than duplicated directly in the child map. Preserve its source, log and all ten resource observations. The corrected auditor verifies that exact parent-plan binding, rechecks every ancestor file/hash, and repeats the full saved-array/report/policy comparison; all eight successful observations replay. Later stages also copy the parent's input mapping explicitly. This is an ancestry-accounting repair; no candidate, numerical condition or source artifact is altered to obtain a pass.

The 135-key asset has not yet been exported or assessed at its full contact clock. Keep interpolation, geometry, force, model guidance, engine, human review and release approval unset while the remaining stages run.

## Evidence

Immutable local inputs, raw candidates, assets, clock arrays, method snapshots and receipts remain ignored under `reports/central-hand-dense-pilot-v1`; the next experiment and its checkpointed retry are `reports/central-hand-skin-chord-pilot-v1` and `reports/central-hand-skin-chord-pilot-v2`. These machine-specific payloads are not distributed in GitHub.

Pose producer/replay take 16.203 / 2.266 supervised execution seconds, with 21 / 8 independently replayed resource observations. Complete clock producer/replay take 14.594 / 2.203 seconds, with 27 / 8 observations. Comparison producer/repaired scalar replay take 0.125 / 1.141 seconds, with 6 / 13 observations. The failed receipt serializer takes 114.812 seconds and retains all 112 resource observations. Actual pose/incident-surface jobs keep the 1,024-MiB budget plus 600-MiB reserve; saved-array comparisons use 512 MiB plus the same reserve. Sampled resource admission does not certify motion or guarantee RAM availability between observations.

Receipt SHA-256 identifiers:

- Pose/export: `3e458362e2959fe9f46e0833e77751f8524ead9568b6eacd24836f1e0f3c1929`.
- Complete clock: `f3354c794d41996effce45435a30e54e945eb48989a8d58f6bb154027d4e2fce`.
- Scalar preservation comparison: `14125bf02e29443615fd7901dce9b53790da668f7835a24853c1bdf6ad5f887b`.

Completed skin-chord retry receipts:

- Pose/export: `36f738b05e165678c752975092cb41f8e06f06e162732097b0a3a340835bfaae`.
- Complete clock: `4bed474bd3a8eba9744228f56da01967d70da8e3e51ae5b354c9b48e515802b1`.
- Scalar preservation comparison: `08400cd280240cd4ec6e3a5676755e6ddb7d8b233337ca4ae7bb070755ad4fc0`.
- Complete clock caps/protected transforms: `287254aea7123b7940eca68131787ca07e9eace6964af78572649200ef364f3a`.

All 453 retry resource observations replay. Pose replay takes 2.219 seconds/eight observations; complete clock producer/replay take 8.641 / 4.359 seconds with fourteen / ten observations; scalar comparison producer/replay take 0.078 / 0.063 seconds with six / six observations; complete cap/protected replay takes 13.016 seconds/eighteen observations. All resource traces replay; their successful supervisor exits do not approve motion, the engine or human quality.

Staged outputs remain under ignored `reports/central-hand-skin-chord-hold-v1` through `central-hand-skin-chord-hold-v3`. Stage-3 receipt identifiers:

- Complete accumulated pose replay: `8547130873cd1283d145fae90f642f9caaaee9682be3a492c7ece680969f1ebd`.
- Exact continuation and ancestor bindings: `7e0cab78e2cbed41978fe2845ad42f4fa3551736446d441671b260e0c0391393`.
- Included pilot preservation: `6f7a877ba2b0fbfa1e29f5617c72cc0b2c08f84229484b4f98a53bd38b5b7ccb`.

Stage-4 receipt identifiers:

- Complete accumulated pose replay: `280959d13121dfb9120ce13cb29c465e157f4a27779187860329254ffde63c34`.
- Exact continuation and ancestor bindings: `48aeefa4f6183deaa49dd2b6c8e99da7dc866d927cfc07ade34b54710624a24c`.
- All nine pilot candidates: `a42f2fb9816078d2f96b5136e65ac920e7755ab4e6c8579703a3e5427ce8bbf1`.

The single full-project goal remains active. This contact fixture is one release dependency; action families remain evaluation categories rather than a prompt whitelist.
