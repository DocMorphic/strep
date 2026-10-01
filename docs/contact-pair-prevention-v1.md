# Prevent new contact-pose triangle intersections

The previous combined vertex/triangle correction reduced maximum depth but
introduced 130 proper crossing pairs relative to the original joint-ball pose.
This experiment makes those known regressions explicit hard constraints and
requires the unchanged complete mesh-regression guard before retaining a pose.

## Frozen source constraints

All 130 pairs are separated in the original source. Their smallest selected-axis
gap is 0.008222 mm and the largest is 1.825910 mm. For every pair, choose a
separating axis from that source geometry and require all nine vertex-pair gaps
to remain at least 1e-8 m. This preserves separation, not the original distance.
Both triangles follow their actual moving skins. Axes and gap floors are frozen
to the original pose and never rebased to a later candidate.

Each batch is validated before it changes the accumulated constraint set. A
pair whose source is not strictly separated is rejected instead of receiving
a fictitious separation constraint. Duplicate pairs are ignored. Source arrays
and exported records cannot mutate the stored reference or axes.

## Bounded solve and full-mesh checks

Start from the original joint-ball pose, where all new constraints are feasible,
not the previous candidate that already violates them. Retain the original
authored contact thresholds, per-joint rotation balls, native-key envelope,
reference clips and motion checks. The coupled objective still includes actual
crossing-triangle witnesses and penetrating-vertex exit witnesses.

Run at most three 40-iteration proposal rounds. Keep previously observed
crossing pairs in the objective across rounds, even after they separate.
Every full-mesh candidate audit can discover additional pairs; add those as
preventive constraints using their original separated geometry. Each local
solve has a fixed constraint population. If adding a constraint makes a retained
iterate infeasible, restart from the original feasible pose and record that
reset rather than rebasing or dropping the constraint.

Full, half, quarter and eighth proposals undergo the unchanged complete source
mesh guard: no new proper/uncertain pairs or degenerate faces, and neither
directional maximum depth may increase beyond its 1e-8 m numerical allowance.
Retaining a proposal also requires the hard contact and joint limits plus a
strict depth/count improvement. Known-pair constraints never substitute for
the full audit. After export, decode and check the preventive constraints,
contact pose, complete mesh guard, original edits, native clocks, unedited
channels, outside-window poses and original motion caps again.

Passing this guard does not remove existing source intersections or approve the
animation. Full-interval geometry, self-collision and human review remain
separate requirements. No result is automatically selected for Studio.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_contact_triangle_pose.py reports/contact-plane-ball-v1 reports/<fresh-output> --with-vertices --prevent-from reports/contact-triangle-vertex-pose-v1
```

The original rigs and prior diagnostic are hash-bound local inputs, excluded
from Git. Six new model-free tests cover actual triangle-crossing rejection,
accumulation without rebasing, transactional rejection of invalid source pairs,
duplicate/empty populations, invalid indices and immutable exported records.


## Measured result

The completed local study is `reports/contact-pair-prevention-v1`. Three rounds
accumulate 130 -> 150 -> 156 -> 157 preventive pairs (1,413 scalar constraints
at the end). Each proposal exhausts its 40-iteration budget; convergence and
infeasibility are not established. Round 0 retains no proposal, round 1 retains
an eighth step and round 2 a quarter step. No reset to the original pose occurs.
The round-2 half step fails serialized hard constraints and is not mesh-audited.

After independent export and decoding:

| Measure | Source | Final |
| --- | ---: | ---: |
| Proper crossing pairs | 220 | 220 |
| Maximum vertex penetration | 10.212648 mm | 10.106972 mm |
| New proper/uncertain pairs | - | 0 / 0 |
| Authored marker gap | 1.068067 mm | 1.164547 mm |

The fixed-source mesh-regression guard passes. Directional maximum depths
improve by 0.104213 and 0.105676 mm, respectively. Marker anchor errors are
0.160216 and 0.133280 mm; normal errors are 16.570186 and 16.602104 degrees.
All original joint-angle bounds pass, native clocks and unselected channels
are exact, and outside-window poses remain unchanged. The minimum decoded
preventive margin is 0.004748641 in the solver's millimetre-normalized units.

Original motion caps still fail: position speed 253 rows (maximum excess
0.096065 m/s), position acceleration 134 (5.904053 m/s^2), angular speed 630
(0.733016 rad/s), and angular acceleration 183 (170.954305 rad/s^2).
Existing penetration remains substantial. This is a conservative contact-pose
nonregression result, not a collision-free pose or validated animation. No full
interval geometry rerun or Studio promotion is justified by this result.

All 1,022 model-free source tests pass. Rehashed 3,419 bound inputs, 79 archived
and matching current methods, and 29 outputs. Result SHA-256:
`633f372eecf1a57c8496a4626157b2f7d93ed2f45c3dccada3eb15a07fb65e1b`.
Raw evidence remains local and immutable; no model training or reserved held-out
prompt use occurred.

## Next decision

The guard prevents new intersections but has not untangled the existing pose.
Do not keep extrapolating these small depth changes into a release claim.
Assess a collision-free initialization or rig-space untangling prototype that
preserves the character, authored contacts and original angle limits. Test its
feasibility independently before spending on longer trajectory optimization.
The old pair-preservation guard remains a reported comparison; it is not a
proof that all useful untangling paths must preserve each pair identity.
Published free-mesh untangling is only research precedent: see the dated
[source ledger](source-ledger.md). Any separate search protocol must be explicit,
with full-mesh/contact/motion checks and unchanged release criteria.
