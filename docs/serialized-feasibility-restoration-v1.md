# Restoring feasibility around serialized animation controls

The preceding combined arm/finger experiment found useful collision-objective
reductions, but none satisfied every preserved motion and witness limit. Its
unrounded starting reconstruction also differed from the feasible serialized
donor. This follow-up starts from the saved rejected proposal and evaluates all
real constraints using the actual float32 key path.

## Search and acceptance

The seed is selected deterministically: the rejected prior trial with the lowest
collision objective, breaking ties by constraint violation. On this development
pair it is trust 0.01, full fraction, with objective 3.224399 mm versus the
original 3.580943 mm. The complete saved trial is bound and its objective and
constraint margin are reproduced before the new search begins.

An elastic conic proposal minimizes the maximum normalized constraint deficit
with a small correction penalty. Its nonnegative slack can relax motion and
surface-witness rows only inside this proposal problem. Control bounds remain
hard, as does an objective ceiling strictly below the original donor's score.
Affine rows are omitted only when their fixed trust-box bound proves them safe
throughout that local model. Every real replay still checks the complete
unchanged population.

Three restoration iterations are allowed at trust radius 0.001. Each rebuilds
derivatives around its current internal point and tests eight exact backoffs.
An internal step must reduce the actual worst constraint violation and remain
below the original objective ceiling. Internal points may be infeasible; none
is an accepted animation. Only a zero-violation serialized result may proceed
to independent mesh validation. Original caps, scales, witness populations,
arm/finger limits and palm contact bounds are never rebased or relaxed.

## Complete edit-interval sampling

The earlier fourteen mesh observations stopped at the contact, even though the
finger correction envelope continues afterward. The new guard clock includes
the full edit interval's endpoints, every native animation key partition inside
it, each partition midpoint and all historical required times. For this pair it
has **53 times from 1.4083333333 to 2.5917225951 seconds**, including twenty after
the last historical observation. Its largest adjacent sample gap is about
25.056 ms. This is broader sampled validation, not continuous collision proof.

In restoration mode, expensive mesh queries are deferred until a numerically
feasible candidate exists. A candidate must pass full-mesh checks before export;
changed exports are independently decoded and queried again. If restoration
fails, the driver retains byte-identical donor files and explicitly records that
no new mesh audit occurred. Missing measurements are never reported as zero
collisions or a passing mesh guard.

## Completed outcome

All three iterations take an internal step. The maximum normalized constraint
violation falls by 64.18%, while retaining 99.962% of the seed's collision-score
improvement. This is progress inside the search, not an accepted animation:

| Internal state | Fixed-axis objective (mm) | Minimum constraint margin |
| --- | ---: | ---: |
| Rejected seed | 3.224399 | -1.186530e-6 |
| Restoration 1 | 3.224462 | -5.610711e-7 |
| Restoration 2 | 3.224501 | -4.277392e-7 |
| Restoration 3 | 3.224534 | -4.249634e-7 |

An exact diagnostic replays all 24 backoffs and reproduces their saved scores
and margins. Neither the serialized nor unrounded path passes all original
constraints. The final internal point still fails one positional-acceleration
row, six angular-acceleration rows and 32 older witness ceilings. Its worst
angular row is A:LeftHandThumb2 after contact, at acceleration sample 113;
the largest angular-acceleration excess is 5.863172e-5 rad/s^2 above the
proposal cap. The worst positional row is B:LeftHandMiddle2 at the same sample.

The three-iteration budget ends without a numerically feasible candidate. Both
exported files are byte-identical to the donors. Therefore the new 53-time mesh
guard is planned but not executed in this trial; mesh-pass and new crossing-count
fields are explicitly null. Historical collisions remain in the unchanged clips.
No animation is promoted to Studio.

The current single-peak finger curve couples contact correction to the later
return motion. The repeated post-contact acceleration failures motivate testing
additional temporal finger controls under the same original limits, rather than
assuming more identical restoration iterations will resolve them. This is a
parameterization hypothesis, not a proof of infeasibility or a promised fix.

Local result bindings (SHA-256):

- Restoration: `reports/coupled-feasibility-restore-v1/result.json`,
  `d0c4112eccc4f4efc513ba085d996b2cf6ecb743f9d5d0333cd503121955b9f9`.
- Request: `6a55c05b249d9697de3637a037d472fade5b7b8ce2ee90082e46aa807e88c98f`.
- Iteration summary: `73ba181d534de0c5743461effe2b8deb98c2fc293546c82c7c20e54e457c81ba`.
- Exact replay: `reports/coupled-restoration-constraints-v1/result.json`,
  `83dfbe3759aceba8391aa2f4f43377b1ab8ff7e25be8461ffeb345a1aba42919`.

All recorded inputs, outputs and archived methods were rehashed after completion.

## Verification and reproduction

The complete minimal source suite passes all 926 tests. Tests cover recovery of a quantized feasible edit, rejection of objective loss,
unchanged caps, non-acceptance of positive proposal slack, hard control bounds,
safe affine row omission, full release coverage and asynchronous native clocks.

```powershell
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-restoration-output> --restore-study reports/coupled-window-repair-v1 --iterations 3
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-failure-replay> --diagnose-study reports/<completed-restoration-output>
```

The command requires the bound local assets and prior studies, which remain
excluded from Git. It is a selected development interaction, not a held-out
evaluation, general feasibility proof or animation-quality approval.
