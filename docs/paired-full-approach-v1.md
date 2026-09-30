# Full permitted pre-contact approach

Planning through the full existing pre-contact support reduces failing mesh
samples from 37 to 5. The remaining failures are near contact and the deepest
vertices belong to the thumbs. The current forearm-only ranking model misses
that geometry. Original-relative motion limits also fail, so this candidate
is not accepted or published as a correction.

## Preserved authoring constraints

`--full-approach` selects the largest interval around the original peak bounded
by the authored edit window and its nearest protected spans. For this request,
the interval is 1.4083333333333334 to 2.0917225950783 seconds. The original
authored end is 2.5917225950783; the protected contact truncates the approach.
No authored window is widened and no contact protection is moved.

The shared native clock has 14 keys from 1.4402683973312378 through
2.0917224884033203 seconds. The latter key lies just before contact and remains
frozen. Evidence consumers independently recompute both the interval and the
native clock from bound authored inputs. Unknown policies, changed guards,
changed peak times and changed authored bounds are rejected.

The continuous replay helper can now directly address more than 12 native keys.
It uses the existing rotation-edit object's source/key cache, not that object's
curve basis; the unused basis remains small. Tests compare these longer direct
native controls with independently exported GLBs for both actors.

## Search and decoded motion

All six fixed-axis routes remain connected on the 100-state-per-time lattice.
The lowest declared proxy cost is Xplus, 9.587283. It holds a 60 mm symmetric
wrist offset through most of the approach, briefly uses 15-degree elbow swivels,
then returns through a 40 mm offset at 2.041611 seconds to zero at the frozen
boundary. Guide-rate limits remain 0.8 m/s and 300 degrees/s per swivel; the
experimental native pose budget remains 45 degrees.

Native clocks, frozen quaternion keys and protected/outside-window world poses
remain exact. Maximum rotation edits are 16.934896 degrees for A and 17.029541
for B. Maximum sampled wrist-guide errors are 1.096393 and 1.366099 mm.

| Actor | Positional failures | Angular speed failures | Angular acceleration failures |
|---|---:|---:|---:|
| A | 348 | 85 | 66 |
| B | 372 | 86 | 64 |

Godot verifies four clips / 444 sampled actor-frames / 77 bones. Maximum
position discrepancy is 5.366924e-7 m and basis-element discrepancy is
6.851266e-7. These import checks do not approve motion quality.

## Completed full-clock geometry

| Measurement | Starting correction | Short native path | Full approach |
|---|---:|---:|---:|
| Samples over 5 mm | 37 / 148 | 15 / 148 | 5 / 148 |
| Peak vertex depth | 22.426395 mm | 21.433380 mm | 21.203789 mm |

The full approach audit performs 158 fresh directional mesh queries and reuses
69 times only after exact equality of both decoded actor worlds and verified
geometry bindings. Maximum floor increase is zero. Thirty-two original failing
times clear, with no newly failing sample times.

The five failures occur at 2.050000, 2.058333, 2.066667, 2.075000 and 2.083333
seconds. Depth at 2.058333 seconds worsens from 19.084295 to 20.450441 mm, a
1.366146 mm regression. Fewer failing times therefore does not imply that every
remaining collision improved.

At the worst time, 2.066667 seconds, both directional audits identify vertex
14682. Its skin weights are 99.748921% LeftHandThumb1 and 0.251080% LeftHand.
The forearm capsule objective does not model these hand surfaces. The selected
last segment runs from native time 2.041611 to the frozen contact-adjacent key;
the failing times occur between its endpoints. Node-only ranking is insufficient
even if both endpoints appear acceptable.

Next include hand geometry and between-keyframe collision checks in path
selection, with direction-changing or diverse route candidates where needed.
Do not run another long projection toward this colliding fixed-axis target and
expect proximity to that target to establish clearance. The CLI now supports
explicit source/target solver initialization, with tests ensuring either start
still retains only independently feasible controls; no full-approach projection
has been run in this experiment.

All results are sampled vertex tests, not continuous-time or triangle-only
certificates. Both workers are terminal. No Studio replacement, training,
model/data acquisition or release approval occurred; all 14 release capabilities
remain unapproved.

## Reproduction and validation

Local ignored character and prior evidence inputs are required. Preserve old
studies and use fresh output directories.

```powershell
.venv/Scripts/python.exe -u scripts/plan_pair_waypoint_path.py reports/scene-pair-native-path-motion-v1 reports/scene-pair-full-approach-path-v1 --full-approach
.venv/Scripts/python.exe -u scripts/fit_pair_wrist_waypoint.py reports/scene-pair-wrist-waypoint-v1 reports/scene-pair-full-approach-motion-v1 --path-plan reports/scene-pair-full-approach-path-v1
```

The expanded focused suite passes 147 tests in both local runtimes. New coverage
includes nearest protected spans, float32 keys just before contact, independently
reconstructed interval policies, long native clocks and both solver starts.

| Temporal artifact | SHA-256 |
|---|---|
| Request | `4644b4f9419846e6b87d11075aa184946df5363670245f71979c2a8715542e31` |
| Decoded motion | `52a75f3ad7f7118688a8db1fa662370c0939205ad2e78e4c225f789b61def75e` |
| Geometry | `67f210b6191050d76d10312a9825494b2265a5b59e91a6d06f5402f15ce8c3fd` |
| Engine verification | `e6b9f5b84596e0bbb4acf2ce9599edef5e3e612e6a2946d85a8af7860dfe1dab` |

See [the preceding continuous projection](paired-continuous-projection-v1.md).
