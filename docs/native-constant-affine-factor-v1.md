# Exact constant affine factors

Development evidence, 2026-10-18. The full-project release contract is unchanged.

`scripts/native_constant_affine_factor.py` represents exact constant rows outside
the changing part of an affine solve. Every original row remains accounted for:
constant hinge values contribute their full cost and peak, while constant hard
rows retain their strongest conjunction and every original occurrence map.
An impossible constant row or peak ceiling is reported as a conflict. There is
no near-zero threshold, variable deletion, physical tolerance change or claim
that an affine zero proves nonlinear invariance. An all-constant objective is
explicit, rather than a fabricated optimization success.

The complete 49-control scene-aware model contains 6,050 hinge objectives and
34,530 hard rows. Exactly 4,029 objectives and 23,194 hard rows have zero
coefficients. The solver therefore receives 2,021 responsive objectives and
11,337 hard rows, including the strongest constant hard condition. The constant
hinge cost is **2,858.328167351622** and its peak is **13.35055703815407**; those
failures remain visible. All original arrays and maps are saved separately.
Two complete random directions reconstruct original costs, peaks and maximum
hard residuals; the largest cost difference is 9.095e-13 from summation order.
All 68,900 original norm witnesses are copied byte for byte. Their existing
equivalent norm factorization still supplies 15,864 solver cones. No control,
bound, source epoch, objective/L1 tradeoff or permission changes.

The bounded solve reaches `AlmostSolved`. Its full and half proposals fail
admission; the predeclared quarter proposal passes. All **68,900 unscaled,
unfactored norms**, their physical radii, **34,530 original hard rows**, all
**6,050 original cost/peak values**, and original boxes are then rechecked with
strict nonpositive residuals. Maximum original norm and hard residuals are
-4.5863e-8; predicted original hinge cost is 6,970.779845235327 and peak is
43.13740477520431. A separately checked objective-null prop reset lowers L1
without changing full primary values and preserves all original local bounds.
These are local model results, not physical or animation-quality approval.

Local tests pass **97 cases: 20 new and 77 existing sparse-solver regressions**.
They cover complete cost/peak/conjunction reconstruction, late constant
conflicts, a 1e-300 nonzero final-column coefficient, all-constant/empty cases,
ownership, invalid and duplicate sparse storage, budgets and a real backend
solve followed by complete original checks. The suite is registered in both
source manifests and the focused Ubuntu/Windows workflow.

Local immutable evidence is under `reports/native-constant-affine-tests-v1`,
`reports/native-scene-conditioning-census-v1`,
`reports/native-track-conic-assembly-v3` and
`reports/native-track-conic-solve-v3`. The previous mesh-rejected proposals
remain rejected. This proposal requires full nonlinear motion, saved export,
actual contacts, fresh scene geometry and independent replay before adoption.
The qualified partial reference and Studio selection remain unchanged.
