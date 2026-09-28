# Preserve patch dynamics during root correction

The root adapter now constrains the acceleration of every declared mesh-patch centroid at every integer-frame second difference. This includes inactive patches and approach/release boundaries. It preserves the earlier target positions, interval movement, floor, rotation channels, original root budgets and endpoints. The full previous 15-job population is retained; no case was removed to improve the result.

The first surface-constrained run, `authored-root-correction-v2`, produces five candidates, four unchanged contact inputs, one solver failure and five fixed-body joint/posture controls. The separate `authored-root-correction-audit-v2` verifies all selected outputs and 1,451 Godot actor-frames. Eight tests pass, including a temporary inactive-patch recipe that demonstrates rejection of the previous root-only tradeoff. The real source recipe is unchanged. The initial test incorrectly assumed that source patch was inactive; the corrected test explicitly constructs its own inactive fixture.

## Export precision and the final run

The failing contact source had decoded root-budget excesses of up to 4.89269 nanometres, caused by retained serialized transforms. The original candidate acceptance already allows 1 micrometre of position error and 2 micrometres of edit-step error, but the proposal constrained nominal budgets exactly. `reports/authored-root-source-budget-diagnostic-v1.json` records each measured excess and whether its samples are fixed.

Run v3 uses a cap equal to the larger of the nominal limit and the exact source value, only if that source is inside the original export allowance. It does not grant the entire allowance to the solver and rejects sources outside the original bounds. The final exported acceptance rules are unchanged. The previously failing case changes from `AlmostPrimalInfeasible` to `AlmostSolved`; independent exported checks still decide selection. Its zero-displacement initial constraint margin is now zero, with 24 retained source caps and a largest retained excess of 4.89269 nm.

`authored-root-correction-v3` and `authored-root-correction-audit-v3` finish all 15 cases: six improved-energy contact candidates, four unchanged contact inputs and five fixed-body controls. All six candidates pass the independent exported checks. All 15 selected outcomes again reproduce 1,451 Godot actor-frames. Ten tests pass, including rejection of an actual source-budget failure and proof that unused serialization allowance is not added to a proposal cap. v1 and v2 implementations, policies and outcomes remain frozen in their study folders.

| Contact job suffix | Root peak before → v3 (m/s²) | Note |
| --- | --- | --- |
| 195612-5047106e | 13.446 → 10.668 | Head patch also improves |
| 195952-76bed1e3 | 23.628 → 23.628 | Squared acceleration sum improves 8314.603 → 7969.384; peak and P95 unchanged |
| 202244-c3c3bb14 | 17.679 → 16.652 | Original floor failure remains |
| 210755-7717c78e | 22.845 → 20.094 | Previous multi-m/s² foot-patch regression removed |
| 224245-27ed02e6 | 19.363 → 18.238 | Original floor failure remains |
| 225025-7cb4f8f4 | 23.051 → 18.814 | Original floor failure remains |

The largest positive per-frame patch-acceleration difference is about 0.00006882 m/s², within the existing 0.0036 m/s² serialization allowance. No declared patch's whole-clip peak increases in these six candidates. The repeated forefoot cases that regressed in v1 are now retained unchanged. These are numerical component results, not anatomy, continuous contact, action correctness, human quality or release approval. The precision-fixed case still penetrates the floor by about 22.493 mm, unchanged from its input. Existing rejected statuses remain rejected.

The adapter is still a study CLI, not a Studio action. Next expose an immutable, single-source correction job with input/candidate comparisons, recipes, updated root tracks and inherited failure status. Preserve explicit world-joint/finger intent when broadening beyond the supported contact-edit path. General pose correction and scene/partner handling remain separate open work.

## Completed partner trial

The original projected partner solver, validator and comparison are now terminal. `projected-surface-path-completion-v1` verifies 600 engine actor-frames and 299 mesh samples per raw/candidate scene. `projected-partner-comparison-v1` finds no change from the preceding enriched solver: final body overlap is 24.740401 mm at frame 66.5, with 14 failed samples; raw overlap is 21.622598 mm with 9 failed samples. Floor depth remains 11.959117 mm. Event gap improves relative to raw (64.950 → 22.628 mm), but the projected method adds no improvement. This trial remains unsuccessful; do not restart it or promote the pair. A different correction formulation is needed, not an identical continuation.
