# Serialized native support feasibility repair

The native support CLI can now warm-start a repair from the saved controls of a
completed four-trial [foot-orientation study](native-support-orientation-v1.md).
It retains the same parameter boxes, source-relative rate caps and final
serialized acceptance checks. This is deterministic motion processing; the
Kimodo checkpoint remains unchanged.

Two matched studies at 8 and 32 repair iterations reduce the worst normalized
violation, but **every trial still fails acceptance**. The original input is
retained in both studies. A lower worst violation can increase the number of
failing rows and the summed squared violation; these tradeoffs remain visible.

## Method and reproduction

`native_support_feasibility.signed_constraints` retains the parent residual's
row order and numerical scales, including interior rows rather than clipping
them to zero. The four rate groups still use selected-input four-bin caps and
**1e-5 tolerance**. Sampled height, ankle displacement and native local-angle
constraints remain present. The height model targets an interior corridor of
0.125 mm to `maximum_gap - 0.125 mm`; the independent job's final checks remain
unchanged. The native bend boxes still assume the original foot orientation,
which is an additional parameterization restriction, not proof of infeasibility.

A structural coloring groups columns whose native-key interpolation and
derivative stencils do not share a constraint row. Bound-aware absolute
differences use a **1e-5 radian** step, shortened inside narrow boxes. The
Jacobian comes from the smooth float64 model; the current constraint vector and
step-selection scores come from independently decoded float32 GLBs.

Two [SciPy HiGHS linear programs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html)
first minimize the linearized largest positive normalized excess, then minimize
the L1 coordinate step while preserving that optimum within 1e-10 numerical
slack. A 0.0002-radian trust box intersects the original parameter bounds.
LP status describes the local linear model, never nonlinear feasibility.

Every proposed step is exported and loaded with `RigAsset` and the dedicated
native sampler at all 701 audit times. Up to ten dyadic backoffs are considered.
Only a lower serialized worst excess, or a numerical tie with lower squared
excess, replaces the current controls. Rejected probes and their controls remain
saved. A rejected direction shrinks the trust radius by four; below 1e-7 radians
the search reports a stall. This cannot certify infeasibility.

```powershell
.venv/Scripts/python.exe scripts/native_support_job.py source.glb draft.json `
  reports/fresh-feasibility-repair --joint-rates --joint-swivel `
  --joint-foot-orientation --repair-from reports/completed-orientation-study `
  --repair-iterations 32
```

Warm mode requires the three experimental flags, 1–32 iterations and a positive
trust radius no larger than 0.001 radians. It does not use a joint-search
evaluation budget. The prior study must be complete, source/draft matched and
hash intact, with four ordered original orientation trials. The new request binds
its old GLBs, controls, outputs, input and implementation archive. Each warm
control vector must reproduce its old GLB exactly before repair. The final
independent audit can select a proposal only when every existing screen passes.
The ordinary Studio and CLI defaults remain unchanged.

## Real development results

Both studies reuse all four original orientation controls on the same Studio v2
source (`87c185ddf0dc50dec7e56bbc4c301f66896ed460a53c6c8eb6797ce5a89107c7`),
Y-up plane offset -0.056 m, two [1.6,2.4] s stances, edit keys [15,105],
30 mm maximum displacement and 45-degree local-angle bounds. All eight final
proposals pass sampled support heights at 142 stance times per foot and preserve
native clocks and frozen/free/root/other-branch motion across 701 times.

| Trial | Original worst normalized excess | After 8 iterations | After up to 32 iterations | 8-iteration rate failures | Larger-budget rate failures |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.0103049395 | 0.0090547535 | 0.0045174394 | 58 / 12 / 17 / 8 | 67 / 13 / 25 / 14 |
| 2 | 0.0033033713 | 0.0006067426 | 0.0000034781 | 60 / 12 / 10 / 8 | 5 / 1 / 0 / 1 |
| 3 | 0.0165417600 | 0.0155489729 | 0.0115194763 | 62 / 9 / 11 / 12 | 76 / 9 / 19 / 14 |
| 4 | 0.0086025107 | 0.0048957817 | 0.0018138644 | 58 / 12 / 6 / 4 | 59 / 14 / 14 / 11 |

Failure groups are position speed, position acceleration, angular speed and
angular acceleration. All first-study trials reach their 8-iteration budget.
In the larger study, trial 2 stalls after 29 iterations; the other three reach
32. Its worst normalized violation falls **99.89%**, but seven rows remain above
the unchanged caps-plus-tolerance. Its remaining peak excess is
**5.34246e-8 m/s**, **3.837886e-6 m/s²**, no angular-speed failure, and
**6.047799e-5 rad/s²**. Tiny violations are still failures under this protocol.

The two studies preserve **86** and **392** independently decoded GLB probes,
including the four warm starts per study. All eight final GLBs replay byte-for-byte
from their saved controls. Quantized proxy/decoder component differences remain
below 9.993e-16. All **1,133** bound study, ancestor and replay files rehash
without mismatch.

Result hashes:

- `reports/native-support-feasibility-v1/result.json`:
  `ee8f034397dcb17c1e49d9ca1d61c47b71ce375ffc560a781567c9f93d737174`.
- `reports/native-support-feasibility-v2/result.json`:
  `96927e914eb58951ca8e192cb111010263c52de26685d66bde2254f691eb9c8b`.
- Eight-iteration replay:
  `6891e1e728453acf91b6972038384c430698676b9f399550957b05c017f76ea9`.
- Larger-budget replay:
  `9526588739f9a4a064f5f5dee4324f08c5e1bc484bf361cfe2c23de92dbcd2ec`.

## Validation and next work

Nineteen new tests check signed/positive residual equivalence, colored versus
individually evaluated derivatives (including disjoint windows), independent
serialized decoder agreement, smallest feasible linear steps, conflicting
constraints, decoded-sample acceptance, plateau retention, bounded budgets and
real four-trial warm-job archival. Mutated warm controls are rejected before a
new study is created. A float32-interpolation diagnostic mismatch was caught and
fixed by promoting stored keys to the decoder's float64 arithmetic. The actual
repair always uses independently decoded artifacts. All **1,292 Python tests**
and **14 JavaScript suites** pass. Preceding public commit `31d3945` passed
Windows/Linux hosted checks.

The near-feasible trial still has both continuous-model and quantized failures:
13/8/0/1 versus 5/1/0/1 rows. Quantization-aware finite differences or a bounded
coordinate search should be tested on those saved controls. The other seeds also
retain substantial parameterization/optimization failures; tiny quantization
repair is not a complete solution for them. After contact/rate feasibility,
broader rigs/actions/scenes and engine/human validation remain required.

No new training, held-out use, engine/GPU/browser rendering, human review,
cleanup-time evidence, default selection or release approval is claimed. All
14 release capabilities remain unapproved and the full-project goal stays active.
