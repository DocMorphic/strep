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
source manifests and the focused Ubuntu/Windows workflow. The new **20 tests
pass on both hosted systems** at `a7c572597d618f554af75174a0be97db7d86794c`
([run 39118450765](https://github.com/DocMorphic/strep/actions/runs/39118450765)).

The first full nonlinear trial completes all **944,562 original raw/saved
motion scalars**. Both representations reduce failed world-rate rows from
6,050 to **6,048**, repair the same two rows (93997 and 276336), add no failing
row and preserve all 72 protected repairs. All 177,328 other motion conditions
pass. Raw/saved squared violation decreases by 279.9250577/279.9269240 and
peak becomes 43.1374084/43.1374085. All 2,017 original sampled prop permissions,
native prop bounds and declared contacts pass. This is numerical progress only;
the remaining rate failures and unverified physical geometry are not waived.

A fresh replay excludes the new profile, factor, model, solver and coupled-prop
modules. Direct original control-table reconstruction reproduces both saved
GLBs byte for byte, 5,400 raw and 5,400 saved native values, 23,880 saved native
pose values and all 383,617 saved world values. Original-relative prop
quaternions/positions, all 2,017 permission samples and every contact array
match. This replay shares the established interpolation, skinning, collision
and serialization libraries; it is not independent physics. Its evidence is
`reports/native-track-independent-export-v3`.

Local immutable evidence is under `reports/native-constant-affine-tests-v1`,
`reports/native-scene-conditioning-census-v1`,
`reports/native-track-conic-assembly-v3` and
`reports/native-track-conic-solve-v3`. The previous mesh-rejected proposals
remain rejected. This proposal requires full nonlinear motion, saved export,
actual contacts, fresh scene geometry and independent replay before adoption.
The qualified partial reference and Studio selection remain unchanged.

## Mesh result: rejected

The same four highest-risk times from the existing 222-time schedule are
queried using every character face, all five mesh pairs per time, and unchanged
limits/planes. At 2.1666667461395264 s the crossing count remains **113**, but
maximum penetration increases from **23.475560824 to 23.548887010 mm**. The two
failed condition identities remain the same; that does not hide the worse
depth. The other three times and all previously passing condition identities
are preserved. This proposal is **rejected**. The remaining **218 planned
times are unqueried after rejection**, not reported passing.

Evidence: `reports/native-track-scene-conditioned-batch00-v2`. The initial v1
setup retained the previous mesh-scene hash and stopped before querying
geometry. It is preserved as a setup failure. V2 binds the actual candidate
hash; times, limits, planes and complete meshes are unchanged.

`reports/native-track-scene-conditioned-independent-batch00-v1` independently
reproduces every complete world array, all 20 mesh-pair/depth/plane decisions
and all 796 original source-pose scalars at those four times. The base body
checks pass; the combined scene still fails. Shared baseline geometry
libraries mean this is a separate replay, not independent physics.

The conditioned representation improves solver admission, but the complete
animation still has 6,048 rate failures and its actual depth regresses.
Known triangle-crossing witnesses do not protect all penetration metrics.
This finite conditioning study ends with that failure; further fraction
sweeps are not the next step. Compare scene-conditioned full-body proposals
and scene-aware editing against this unchanged baseline, retaining explicit
object/partner geometry, complete depth/contact checks and broad action
evaluation. A new proposal is a separate experiment, not a replacement for
this failed benchmark. No new character-stat calibration or release claim
follows from this solver change.

The final checkpoint is `reports/native-affine-conditioning-progress-v1`.
It verifies 13,176 current source/archive/data bindings and recorded resource
receipts, and binds the prior checkpoint receipt without claiming an
all-ancestor rehash. The audit completes in 62.359 s with 87,613,440-byte peak
tree RSS. All completed studies respect the 512 MiB tree limit and 600 MiB
free-memory reserve. It confirms the fixed release contract is unchanged
outside goal line 3 and the two permitted progress fields. All 14 release
capabilities remain unapproved and the entire-project goal remains active.
