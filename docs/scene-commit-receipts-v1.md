# Complete committed ownership receipts

The native prop SDK already waits for all owned body callbacks before emitting its action list. It now also emits `transaction_committed`, a recursively read-only, detached receipt containing the complete assigned prop states, memberships, modes, incoming tracking, actor root motion/extraction modes, original event contracts, source clock and action/application clocks. Game code can consume one coherent snapshot for a simultaneous pickup, partial release, handoff or multi-prop release.

This adds a game-integration contract; it does not generate or correct motion. Actor source clips, grip providers, physics configuration, ownership selection and physical acceptance limits are unchanged. The receipt explicitly labels its prop observations `assigned_before_force_integration`, preserving their actual phase instead of presenting them as settled collision results. The [integration guide](../integrations/godot/SCENE-PROP-OWNERSHIP.md) describes the signal and transport behavior.

## Numerical and callback contract

Nested collections must each be made read-only: Godot's [Dictionary contract](https://docs.godotengine.org/en/stable/classes/class_dictionary.html#class-dictionary-method-make-read-only) does not recursively protect their children. The emitter copies the complete receipt, freezes every nested dictionary/array and preserves actor/body value transforms. It emits only after all owned callbacks have supplied states. A failure suppresses the failed boundary's receipt; earlier successful transactions remain recorded.

The receipt groups all actions at a physics boundary and lists each referenced source event once in original order. Two hands or props commanded by one event therefore do not require duplicate gameplay effects. Legacy action-list notifications continue. Read-only snapshots do not prevent unrelated gameplay effects or roll them back.

Owner IDs remain exact strings, including signed RefCounted IDs beyond the floating-point integer range. Commit IDs distinguish owner, session and tick. They identify a live binding rather than a persistent network entity. Restart establishes a new session; pause/preview/resume do not redispatch a commit.

Binary little-endian Float64 triples bind every action's source time, physical application time and delay. The independent verifier requires exact source bytes, the original expected physics rate, `application = tick / rate`, and `delay = application - source`. Full-precision engine JSON keeps its descriptive numbers consistent with the wire. No event time is shifted or rounded to conceal a physical delay.

## Engine population and limits

Final fresh study `reports/scene-commit-receipts-v3/` runs the existing six scenarios at each of 60, 120 and 240 Hz: ordinary/reversed body order, incompatible grips, outside clock mutation, missing body callback and a clock-changing provider. Actual Godot 4.7.2/Jolt participants are two procedural three-bone skinned triangle rigs and cylinder/sphere bodies. They are software fixtures, not production humanoid assets, mocap or visual-quality evidence.

The first signal listener checks recursive immutability and changes its own writable serialized copy. The second checks that every body has reported, that owner membership/modes/direct-state observations and actor roots match, and that its receipt is unaffected. Python independently matches every new committed group to the original plan, full live record, complete actor/prop populations, recorded roots, source event contracts, exact clock triples and legacy action population. It rejects missing, extra, duplicated, failed or transport-only commits and resealed state/timing changes.

All eighteen cases pass these integration checks: 4,287 complete records, 60 commit receipts and 96 prop action observations, including the successful acquisitions preceding the twelve intentional faults. All 60 receipts are observed by both listeners. The original physical failures remain: exact physical event timing fails in all six positive cases, with maximum delays 11.667 ms at 60 Hz and 3.333 ms at 120/240 Hz. The 60 Hz cylinder floor-depth screen still fails at approximately 63.229 mm under the original 10 mm limit. Higher-rate boundary samples do not prove continuous collision safety. Held props remain prescribed targets with collisions disabled; characters do not respond physically.

146 source checks pass in a fresh asset-free fixture without Torch, covering 34 new receipt checks plus existing ownership/package/native actor/scene regressions. The declared model-free inventory is 413 Python modules and 41 Node suites; workflow fields and dependencies are unchanged. The owned engine-study supervisor exits zero after 13.516 seconds, with sampled process-tree peak RSS 346,066,944 bytes under the existing hard limits. Independent replay verifies all 27 resource observations. Executed runtime and verifier method hashes match their frozen copies and current source.

| Final engine study | SHA-256 of result.json |
| --- | --- |
| engine-60 | `ebe971caba94cc2f9234a35b672473f764ddf3e6151059a78b54a84c106e577b` |
| engine-120 | `7de9cda8eccc21643293edbc141a68b60236fef5317397b802273f5a3eae94df` |
| engine-240 | `485a3d0c0adf40df30d8eb3abe793c1dc8c64e8e959a589daa7be5d69761247b` |

Initial attempts remain immutable under `reports/scene-commit-receipts-v1/` and `-v2/`. Verification first rejected valid negative RefCounted IDs, then exposed default JSON rounding. Signed-string validation, binary action clocks, full-precision study serialization and explicit pre-force phase labeling resolve those representation defects. The final study binds current runtime and verifier sources without replacing earlier raw output.

No model run, training, production rig/skin review, rendered appearance, game-specific response logic, human score, cleanup record or release approval was produced. All fourteen release capabilities remain unapproved and the single full-project goal remains active. Further work includes actual game consumers and production scenes, crossfade/interruption ownership, contact realism, continuous collision, held-out rigs/actions and actual developer/animator review.
