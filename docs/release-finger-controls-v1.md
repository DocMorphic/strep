# Independent finger return controls

The preceding feasibility-restoration trial left finger acceleration failures
after contact. Each finger had only one correction vector, applied through a
single rise-and-return curve. This experiment adds a second correction vector
for the return without changing the original reference motion or its limits.

## Parameterization and preserved limits

Each joint retains its original triangular correction basis. The second basis
starts at contact, peaks halfway through the remaining edit interval and returns
to zero at the existing window end. Only native keys whose entire interpolation
support starts at or after contact receive this second correction. Therefore it
cannot change the contact pose or the approach, including when contact lies
between native keys. Native clocks and all unselected channels are preserved.

There are 140 arm controls and 228 finger controls, for 368 in total. The new
controls begin at zero. The starting state is explicitly the **final internal
point** from the preceding three-step restoration, not a newly selected earlier
trial. Every serialized quaternion is checked for exact equality after embedding
that state, and its objective and worst constraint margin are reproduced.

The original per-finger angle budgets and five-degree adjacent correction limit
still apply. Additional rows check the combined basis at every edited native
key and the difference between neighboring correction vectors. The latter is
a conservative bound on correction rotation distance. Export also checks actual
serialized original-reference angles. Adding controls does not increase budgets.

Original motion-rate, palm-position, palm-normal and old surface-witness limits
remain unchanged. The experiment uses the existing restoration algorithm with
three iterations at trust 0.001. A changed candidate must be numerically feasible
before the full 53-time mesh guard runs. Exported changes must pass independently
decoded checks. No failed internal point may replace the Studio animation.

## Verification

Ten new model-free tests exercise exact seed embedding for both actors, separate
return movement with unchanged approach/contact, decoded combined export,
unchanged clocks/channels, original angle and adjacent correction budgets,
actor/joint control ordering, and invalid release intervals. These tests and the
926 existing minimal source tests pass (936 distinct tests in total).

Reproduction requires the bound local assets and previous studies:

```powershell
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-output> --temporal-study reports/coupled-feasibility-restore-v1 --iterations 3
```

Generated study artifacts remain excluded from Git. This is a development-pair
experiment, not a held-out evaluation or animation-quality approval.

## Completed outcome

The three-step run completed without a feasible candidate. All 24 exact trials
remain rejected, and both final GLBs are byte-identical to the original donors.
The full mesh guard did not run; its pass and new crossing-count fields remain
null. Historical collisions are retained, and Studio is unchanged.

| Internal state | Fixed-axis objective (mm) | Minimum normalized margin |
| --- | ---: | ---: |
| Embedded preceding final state | 3.224534 | -4.249634e-7 |
| Step 1 | 3.224607 | -2.883990e-7 |
| Step 2 | 3.224612 | -2.637096e-7 |
| Step 3 | 3.224629 | -2.253142e-7 |

The worst constraint violation is reduced by 46.98%. In the final internal
state, **all original position/angular speed and acceleration rows pass**.
Palm points, normals, arm guides, native arm edit limits and all 3,610 additional
finger angle/adjacent-correction rows also pass. Seven of 962 older signed
surface-witness ceilings remain violated (rows 245, 253, 281, 318, 330, 863, 895).
Their largest excess is 4.506284e-9 m. This is a constraint violation, not a
fresh mesh-penetration measurement, and its small size does not authorize
discarding it. The next repair should preserve the now-passing motion rows while
addressing these serialized witness failures; increasing finger freedom alone
is no longer the demonstrated priority.

Every input, output and archived method was rehashed after completion. Local
study `reports/coupled-release-controls-v1` has these SHA-256 bindings:

- Result: `ca07f09e3173ba337de4d4fc75edbf5e4eff7b16b31a065c596940928ba478f2`.
- Request: `8259a30117d7fdf03fd139ae2c7b865f3c1039a0fffb2035cd56a4c80c4c96f0`.
- Iteration summary: `f35e60f568f6c9e59e1be1a1dfc96ec22e8c68c875d32ede0b7d25d3f9ed152b`.
- Final constraint groups: `edb339098851169f28e67a3a8eaff19e26f407dcac80b5dbfb2ba13ee31151d2`.

An improvement during this continuation alone does not establish that the new
basis caused it: that requires a matched continuation without the extra controls
from the same saved state. The present test first asks whether the expanded
parameterization can produce any feasible candidate under unchanged limits.
