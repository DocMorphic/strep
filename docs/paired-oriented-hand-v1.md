# Intermediate hand orientation with both support intervals constrained

The previous continuous terminal correction passed its last interval but failed
full-clock motion and hand clearance. This experiment allows independent hand
orientation at the edited key and constrains the entire interpolation support
of that key. Protected contact and all other native quaternion keys remain
unchanged.

## Controls and evidence

The 11 controls comprise the symmetric XYZ wrist offset, two independent elbow
swivels and two independent XYZ hand rotation vectors in scene coordinates.
Hand orientation deltas compose onto the original hand world orientation after
two-bone reach. The scene placement is explicitly accounted for. Stored arm and
hand quaternions are quantized to float32 before motion evaluation.

The original native pose budget remains 45 degrees. Wrist and elbow guide
limits remain 0.8 m/s and 300 degrees/s. Each new hand rotation vector also has a
300 degrees/s guide bound, applied to its norm rather than independently to
three components. Both adjacent native intervals limit these controls; the
resulting orientation radius is 15.033495 degrees for this source clock.
Original-bin joint velocity/acceleration and world-angular velocity/acceleration
limits are unchanged.

`support_clock` includes both native intervals around the changed key, plus two
unchanged sample poses on either side. This gives sample indices 70 through 86
(17 original 120 Hz samples). Hand witnesses and fresh hand-mesh audits cover
indices 72 through 84 (13 times). Unchanged motion outside the key's support is
still independently checked after actual GLB export, along with full-clock
motion limits.

Four SLSQP starts use the original controls, a -5 mm X offset, a -20 mm Z offset
with opposing 2-degree Z hand rotations, and a combined -5 mm X/Z offset with
-1-degree elbow swivels and opposing 2-degree Y hand rotations. Each start has
the existing 100-iteration budget. The optimizer minimizes the fixed witness
penetration objective and retains only independently feasible observations;
fresh mesh queries remain the clearance evidence.

## Reusing source measurements

The prior completed study supplies 14 directional source queries at the last
seven times. Reuse verifies required source/scene input hashes, saved artifacts
and implementation snapshots, and the current geometry-query methods. Both
directions at every donor time must be present in order. Witnesses must exactly
reconstruct from source-query records and the current hand vertex IDs. Their
frame indices are rebuilt for the expanded clock. New queries cover the six
incoming times; no candidate geometry is reused as source geometry.

Tests reject changed inputs, missing directions, inconsistent witnesses,
changed query methods, mismatched times and changed hand vertex order. Hand
orientation tests independently verify the intended scene-space rotation and
wrist position under oblique placements, scalar GLB replay, frozen stored keys,
other-actor isolation, protected endpoints and native-budget rejection. At an
exact interpolation endpoint, the synthetic fixture permits at most 1e-12
matrix error for SLERP arithmetic (observed one-ulp differences), while frozen
stored quaternion keys must match exactly.

## Reproduction

Local ignored assets and the bound prior studies are required. Use fresh output:

```powershell
.venv/Scripts/python.exe -u scripts/fit_continuous_terminal_hand.py reports/scene-pair-terminal-hand-search-v1 reports/scene-pair-oriented-hand-v1 --hand-orientation --witness-study reports/scene-pair-continuous-hand-v1
```

The previous five-control mode remains available. Its historical snapshots and
results remain unchanged. See [the terminal-only experiment](paired-continuous-hand-v1.md).


## Completed result

The source pool contains 816 witnesses from 26 directional queries: 14 reused after binding checks and 12 newly measured. Fresh export geometry uses 26 additional directional hand-to-full-mesh queries.

The optimizer recorded 6,959 evaluations including finite differences. Only 1 passed the motion/domain gate: the unchanged source. No nonzero control was selected. All four starts terminated without success:

| Start | Iterations | Status | Returned witness peak (mm) | Returned minimum normalized margin |
|---|---:|---|---:|---:|
| 1 | 100 | 9: Iteration limit reached | 21.294039 | -9.84002433e-07 |
| 2 | 94 | 8: Positive directional derivative for linesearch | 21.294073 | -2.20872554e-07 |
| 3 | 100 | 9: Iteration limit reached | 21.293942 | -3.077252e-06 |
| 4 | 72 | 8: Positive directional derivative for linesearch | 21.294095 | -1.01185356e-06 |

All returned candidates and tested backoffs failed the strict motion/domain gate. These finite, nonconverged searches do not prove that every one-key or continuous correction is infeasible.

The selected unchanged source has a fresh hand peak of **21.433380 mm**, with **12 / 13** times over 5 mm. Actual GLBs have zero batched replay error, exact frozen stored keys, and zero full-clock positional or angular violations for both actors. Those motion passes describe the source retained after failure; they do not describe a new collision correction. The 13-time peak must not be compared directly with the previous seven-time peak as though the scopes were identical.

No engine audit, full-body whole-clock clearance, Studio replacement, human approval, training or new model/data acquisition occurred. The worker is terminal and all 14 release capabilities remain unapproved.

## Numerical follow-up and next experiment

A bound read-only diagnostic replays the second solver return, a 1% backoff and a hand-only variant. The solver return still exceeds the original 1e-5 export tolerance: B middle-finger positional acceleration is over its cap by 1.061838e-5 m/s^2, and A pinky angular acceleration by 6.969570e-5 rad/s^2. The 1% backoff has three positional-acceleration violations, with a maximum excess of 2.523270e-5 m/s^2. The small margins are actual sampled failures; solver output is not silently accepted.

A separate synthetic invariant check found that a hand-only edit could recompute unchanged upper-arm/forearm quaternions, introducing tiny components. The current implementation now leaves those channels byte-exact. That fix and its regression test were made after the real worker completed; its saved implementation snapshots remain unchanged. In the real hand-only diagnostic, those arm quaternions were already unchanged, so this fix alone is not evidence of a solution to the reported collision or motion failures.

The next experiment should distribute wrist/elbow/hand-orientation corrections across several existing permitted keys, constrain the full incoming and returning support, and retain final contact and original motion caps. This tests trajectory shaping beyond a single isolated pose. Reuse only independently bound source measurements, re-query selected candidate meshes, and require whole-clock decoded motion before publication. Do not interpret the additional control freedom as proof that a solution exists.

Validation: 637 public Python tests pass in the minimal environment after the invariant fix; 36 focused tests pass in the development environment. The preceding commit `b3a01af` passed its hosted Windows/Linux checks.

| Artifact | SHA-256 |
|---|---|
| Request | `a49189d986b1644740404a9efd4b526ddd0f0fb67187c126b7fb393ab3bb3092` |
| Witnesses | `0c0c29db71f076b43f178a91e817cd329ff3cf667c7ad0fa162590fd7c450f77` |
| Source queries | `866c6f4c84b8dae1bf67f148c0e4785730963ad5ed5eec7e74b891420bc5266c` |
| Solver reports | `b58bc2e0be287eca6baaab45c8a40624d4ae138375587ceabf5b12b31a9f9d4e` |
| Selected source | `f20c23d165cecc8a067fa4e4ad63d4513f151564f844fa0fc10ce3323ee1f66b` |
| Decoded audit | `3c94f006b18de8d30a172c1708c017fde80594f0f8f99ffd263bd4c3d903af03` |
| Fresh hand geometry | `634ea75022a5f29615612697d6812242ecb2d64c97a0b6612c2da019626084d4` |
| Read-only rounding/rate diagnosis | `3df2b23ac52bcf8b1e00ec3ab90a241f55850eb929ccbcf6bab7254d1cf18e81` |
