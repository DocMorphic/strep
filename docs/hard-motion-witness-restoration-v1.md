# Surface-witness repair with mandatory motion limits

The independent finger-return experiment ended with all original motion and
palm rows passing, but seven old signed surface-witness ceilings still failing.
This follow-up carries that exact expanded final state forward. It does not
restart from the donor or choose an earlier rejected trial.

## Method

The proposal problem keeps the entire vector-norm population hard, including
motion rates and palm constraints. Native edit bounds, arm guides, combined
finger angles, adjacent correction bounds and the collision-objective ceiling
also remain hard. Only the old witness rows may use elastic proposal slack.

Each witness proposal targets an interior margin of twice the absolute measured
serialized-versus-unrounded discrepancy at the current point, plus a normalized
floor of 5e-7 (1e-8 m under the existing 0.02 m normalization). This is a search
heuristic, not a certified rounding-error bound. It tightens proposal targets;
it never changes the original acceptance thresholds.

Every actual trial replays float32 native keys. An internal step must preserve
all non-witness constraints, retain improvement over the original objective,
and improve the worst actual constraint violation. A lower overall violation
cannot compensate for introducing a new motion or palm failure. Original caps,
scales, clocks, geometry and witness populations stay fixed.

The run allows three iterations at trust 0.001, with eight backoffs per proposal.
Any numerically feasible candidate must pass the complete 53-time mesh guard
before export and independently decoded geometry checks after export. Failed
internal candidates remain diagnostic evidence only.

## Verification and reproduction

Tests cover hard vector and non-witness scalar constraints in the conic system,
rejection of motion regressions despite a better overall score, reserve
calculation, unchanged acceptance thresholds, rejection of rebased caps, and
invalid starting states/settings.

```powershell
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-output> --witness-study reports/coupled-release-controls-v1 --iterations 3
```

This command requires bound local source clips and prior studies. Generated
artifacts are excluded from Git. It is a selected development interaction, not
a held-out result or a general motion-quality certificate.

## Completed outcomes

The first conic proposal reports `AlmostSolved`, with positive elastic slack
3.380603e-7. None of its eight exact backoffs offers an admissible improvement.
At fraction 0.25, only one witness fails, but a non-witness motion limit fails
too. Four other backoffs preserve the hard groups but worsen the worst witness
violation. The search stops without taking an internal step.

Because serialized scores vary non-monotonically along this proposal, a separate
replay evaluates 256 uniformly spaced fractions of the **same saved direction**.
All eight earlier backoff metrics reproduce within 1e-12. Forty samples preserve
the hard groups; none is fully feasible. Fraction 139/256 gives the best internal
score, reducing the worst violation by 88.94% and leaving three witnesses failing.

A third study samples both neighboring coarse-grid intervals around that best
state, 256 subdivisions each (512 additional evaluations). It finds only a tiny
further change and retains the same three failures. It does not recompute the
proposal, alter any constraint, or claim that a finite scan proves infeasibility.

| Saved internal state | Fixed-axis objective (mm) | Minimum normalized margin | Failing witnesses |
| --- | ---: | ---: | ---: |
| Release-control seed | 3.224629 | -2.253142e-7 | 7 |
| Hard-motion proposal, unchanged seed | 3.224629 | -2.253142e-7 | 7 |
| Coarse ray, fraction 139/256 | 3.224704 | -2.492485e-8 | 3 |
| Locally refined ray | 3.224708 | -2.492447e-8 | 3 |

All motion-rate, palm, arm-guide and finger-edit constraints pass in the final
internal state. Its largest old-witness excess is approximately 4.984893e-10 m;
this is a signed constraint excess, not measured fresh mesh penetration. The
original limits still reject it. All three studies therefore retain donor GLBs
byte-for-byte, report mesh pass/count as null, and perform no new mesh audit or
Studio promotion. The previous collisions remain present.

The surviving constraint rows are 238, 287 and 743. `HandWitnessObjective.gaps`
groups observations by actor direction (0 to 1, then 1 to 0), so these indices
must not be applied directly to the mixed original witness list. In that
evaluation order they map to original rows 478, 591 and 551, at times
2.0333333333, 2.05 and 2.0416666667 seconds respectively. They precede the
2.0917225951-second contact. The next meaningful search is to relinearize from
the exact refined final state and address these approach constraints while
preserving the passing motion rows, not merely subdivide the same ray again.

The complete minimal source suite passes **955 tests**. All declared inputs,
outputs and archived methods were rehashed for each completed study. Bindings:

| Local study | Result SHA-256 |
| --- | --- |
| `reports/coupled-witness-restore-v1` | `b8213059c86baec14d5fea33f89c3e032d6f4177196cbb07726ddcda8fec730b` |
| `reports/coupled-witness-ray-v1` | `584a378736bf37d648e0dcb2a79c7603313a0fc7b2b92eb6aa95f4cfac796f8e` |
| `reports/coupled-witness-refined-ray-v1` | `6a67d03ccb7d7569546607265e4707707b7d2e869724be980aac794195eada21` |

The refined iteration summary is
`a8ce063d1ea943dbfdf0c7c7ee14ea9780ec0436399850b7ecb7cc7719124763`;
its final constraint groups are
`86a5dd2712d9c96489d0df8de593ba88bf21d7c67beb9ec0c51203c25b6432f9`.

Additional reproduction commands:

```powershell
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-ray> --ray-study reports/coupled-witness-restore-v1
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-refinement> --refine-study reports/coupled-witness-ray-v1
```
