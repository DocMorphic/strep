# Motion-bounded paired path search

The native waypoint search now enforces sampled joint speed and acceleration
while selecting a path. On the existing coarse lattice, all six directions
return only the unchanged source. The collision-clearing experimental path is
rejected rather than accepted with an abrupt return. This is a useful negative
result, not a successful collision correction or a general infeasibility proof.

## Constraints and search

The input is the completed nine-time native lattice from
`scene-pair-native-path-v1`: 100 states per time, six signed axes, 20 mm wrist
increments and 15-degree swivel increments. The original guide-rate limits,
45-degree native pose budget, source clips, edit window, protected poses, and
source-relative motion caps remain unchanged.

`decoded_motion_edges.py` reconstructs the actual native arm quaternion keys,
including float32 quantization and retained source signs. It samples each
candidate segment through the regular `AnimationSampler`, using all 77 joints
of each actor. Tests compare these segment transforms exactly with separately
baked GLBs, including shared samplers and states that edit only one actor.

`sampled_motion_caps.py` builds per-joint source maxima in the original time
bins on the original 148-time uniform clock. Checks include positional speed
and acceleration, world-angular speed, and world-angular acceleration, with the
existing 1e-5 numerical tolerance. The two actors' joint populations stay
separate. Constant scene placement does not affect these vector norms.

`motion_lattice.py` retains the two endpoint states of the incoming segment.
This is necessary because acceleration at a join depends on both segments.
The search rejects segments with internal rate violations and rejects joins
with crossing velocity or acceleration violations. Two unchanged samples
before and after the editable support check entry and return transitions.
Every native interval must contain at least two uniform samples. Selected
segments are decoded again and checked as a concatenated trajectory including
the frozen samples; unchanged motion outside that interval retains its source
values. No limit is increased when a path is rejected.

The same node and guide-transition objective as the preceding planner is used.
Costs select among motion-feasible paths; they cannot override a motion failure.
This is a finite sampled search, not a continuous-time dynamics certificate.

## Completed result

| Direction | Segments checked | Internal rejections | Join rejections | Nonzero path |
|---|---:|---:|---:|---|
| Xminus | 190 | 182 | 0 | No |
| Xplus | 190 | 178 | 4 | No |
| Yminus | 190 | 182 | 0 | No |
| Yplus | 190 | 182 | 0 | No |
| Zminus | 190 | 172 | 10 | No |
| Zplus | 181 | 173 | 0 | No |

Across reachable search states, 1,131 segments are checked, 1,069 are rejected
internally, and 14 additional joins fail. Only the zero state remains reachable
at every layer. All six selected trajectories pass concatenated motion replay
and contain zero controls. Their cost is 33.935183; the deterministic tie-break
selects Xminus. A selected route name does not imply motion was changed.

No new GLB or Studio replacement is published, and no redundant mesh or Godot
audit is run for this unchanged result. The starting correction retains its
previously measured 37 failing samples and 22.426395 mm peak. The rejected
collision-clearing experiments and their 15 later failures remain separate
evidence; their clearance cannot be combined with this search's motion pass.

The coarse state increments cannot leave the source while satisfying these
constraints. Next investigate finer or continuous controls under the same
decoded motion checks; do not infer that all physically plausible approaches
are impossible, or weaken the limits silently. Later contact collisions and
human motion-quality review remain unresolved.

## Reproduction and verification

Local ignored native-lattice, character and prior evidence files are required.
Use a fresh output directory.

```powershell
.venv/Scripts/python.exe -u scripts/plan_motion_bounded_path.py reports/scene-pair-native-path-v1 reports/scene-pair-motion-bounded-path-v1
```

Tests cover exhaustive second-order path agreement, rejected edges, terminal
joins, acceleration-only and angular-direction-reversal failures, malformed
clocks/poses, partitioned versus whole-track checking, agreement with existing
independent replay, and exact decoded-edge versus exported-GLB transforms.
The expanded focused suite passes 129 tests in both development and minimal
runtimes. The worker is terminal. No training or model/data acquisition occurred, and
all 14 release capabilities remain unapproved.

| Artifact | SHA-256 |
|---|---|
| Request | `97e07aceb7e89baac26bdc13b5acf53a31ac0097085fe239d97a653409e33d09` |
| Routes | `5d82e8f65c9635865ddbfb0c2a580a6f6d71882a860f0f8fc2e2ea361a2fb2ce` |

See [the preceding native-key experiment](paired-native-path-v1.md).
