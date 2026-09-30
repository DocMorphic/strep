# Runtime release checklist refresh

2026-09-30. This is an integrity check of existing development evidence, not a new engine run or release approval.

The release matrix still described latest-blend reversal and physical attachment/release as entirely outstanding. Retained studies already cover narrower versions of those behaviors:

| Retained study | Verified development scope | Remaining scope |
| --- | --- | --- |
| `runtime-reverse-blend-v3` | 144 runs across three cases; latest-transition rewind/replay with two rigs, explicit event policies and both root modes | Older transition history, interruption into a third clip, gameplay undo and physics |
| `runtime-chained-blends-v2` | 18 runs across three cases; three successive forward handovers with reused donors | Interruption, shared gameplay ownership and physical interactions |
| `godot-finite-events-v4` | Eight finite scenarios and eight clock checks; one-prop attach/release, terminal release, recorded preview/resume/restart, continued gravity and floor contact | Multiple props, shared scene clocks, two hands/actors, crossfade attachment ownership and convincing grasp motion |
| `godot-event-object-small-angle-v1` | Four cycle scenarios with the corrected release-spin consumer | General scene ownership and motion/contact quality |

The refresh verifies each completed pipeline, request/output hash, implementation snapshot and declared GLB/metadata binding. Finite source-report bindings also match. The saved observations remain historical: no held-out action, human rating or cleanup time was added. The local integrity inventory is `reports/release-runtime-evidence-refresh-v1.json`.

The two blend studies' implementation snapshots match current source. The finite study predates the added hash-bound legacy corrected-clip metadata path in `rig_runtime_finite.py`; its runtime adapters and object consumer still match. The cycle study retains earlier audit/verifier versions; its actual cycle adapter and object consumer match. These distinctions prevent treating a historical test as proof of every current export path.

The matrix now identifies interrupted blends, scene-level object ownership and broader game integration as remaining work, while retaining all release statuses as unapproved. Original numerical/semantic failures, held-out requirements, additional rigs and animator review requirements remain.

Implementation and study details: [crossfade and reverse playback](runtime-crossfade-v1.md), [single-prop runtime behavior](godot-event-object-v1.md), and [finite action runtime behavior](godot-finite-events-v1.md).
