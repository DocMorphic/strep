# Continuing from the exact refined witness state

The previous study left three pre-contact surface-witness violations after
coarse and locally refined replay of one correction direction. All original
motion-rate, palm and edit constraints passed. This experiment rebuilds the
local proposal at that exact refined final state.

## Bounded continuation

The continuation verifies the completed input's file hashes, original control
reference, scales, sample clocks, archived decoder/constraint methods and
saved final metrics. It copies the saved expanded controls without rebasing
their reference or selecting an earlier trial.

Each outer iteration computes a new hard-motion witness proposal using the
existing unchanged solver and original limits. If its eight backoffs do not
improve the real minimum constraint margin, a 256-point exact serialized scan
checks that same proposal direction. An admissible improvement becomes the
next linearization point. If neither stage improves it, the loop stops without
repeating the same search. The run permits at most three new linearizations.

Caps, scales and populations are frozen across the whole continuation, not
only within each nested solve. The outer loop independently evaluates selected
controls and enforces all non-witness constraints and the original objective
improvement ceiling. Solver status and predicted scores cannot accept a clip.

Numerical feasibility still only grants access to the full 53-time mesh guard.
Changed exported motion must pass independent decoded checks. Internal rejected
states are saved separately from the selected output clips, and no step changes
Studio automatically.

## Verification and reproduction

Tests verify that a new linearization starts at the exact preceding ray result,
that lack of progress stops the loop, that stage results cannot introduce a
motion failure, that caps cannot change between iterations, and that budgets
are bounded.

```powershell
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-output> --continue-study reports/coupled-witness-refined-ray-v1 --iterations 3
```

The command requires the bound local studies and assets. This remains a
development-pair experiment, not held-out evaluation or a quality certificate.

## Completed numerical outcome

The new linearization reports `AlmostSolved` with elastic proposal slack
5.761079e-7. Its eight backoffs do not improve the saved state admissibly.
The fallback evaluates 256 fractions of this new direction; 34 preserve the
hard groups, but none improves the minimum constraint margin. The loop stops
after one outer iteration with `no_admissible_progress`, rather than spending
its remaining budget repeating the same search.

The internal final state is unchanged: fixed-axis objective 3.224708 mm and
minimum normalized margin -2.492447e-8. The same three old witnesses fail, while
motion, palm and edit limits still pass. Selected output GLBs remain byte-identical
to the donors, and this numerical study runs no mesh guard or Studio promotion.

The 962-test minimal suite passed, including the seven new continuation tests.
Every bound input, output and archived method was rehashed after completion.
Local study `reports/coupled-witness-continued-v1` binds:

- Result: `df56eba27da8fdffd47c27791333a83305069a800bc36864603f9f5d508c92ec`.
- Request: `4e871b784b4ddcce75e6c28ddc16a47c78dd9895db87ec3d13be0505bb80a92d`.
- Iteration summary: `841b180ab2334948652c4c360e139a12a7f24ba9719fbdbac17d989dc104b3fd`.
- Final constraints: `86a5dd2712d9c96489d0df8de593ba88bf21d7c67beb9ec0c51203c25b6432f9`.

This stalled numerical search motivates a **separate diagnostic mesh audit** of
the rejected candidate. That audit asks whether fresh geometry reveals more
substantial regressions before investing further in subnanometre witness
feasibility. It does not bypass or relax any acceptance gate.
