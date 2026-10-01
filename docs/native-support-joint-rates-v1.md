# Joint native support and source-rate search

An experimental CLI search now evaluates bounded native knee bends against
foot-region heights, ankle displacement, local rotation limits and all four
source-relative motion-rate measures together. It still preserves the source
root, other branches, free phases and frozen edit boundaries. At native keys it
retains the source foot’s world orientation and tangent position and transports
the existing knee bend plane. It does not add a trained editor or physics model.

The first two studies **fail** the rate screen. Every output retains the exact
input. A large reduction in the optimizer’s residual is not constraint success,
convergence, animator approval or evidence of general motion quality.

## Method and reproduction

`native_support_rates.SupportRateProblem` constructs the same source-bound bend
boxes used by the existing support method. Each non-fixed native bend is an
independent bounded variable. An initial source-clock smoothing proposal seeds
the search. Vectorized rigid two-bone IK preserves exact per-key source lengths,
native translations and source foot orientation. Quaternion signs match the
source; fixed keys remain unchanged.

The proxy reconstructs only the affected branches on the complete audit clock:
uniform 120 Hz, all native keys/midpoints, authored stance boundaries and edit
boundaries. Exact keys use the dedicated native-support sampler’s normalization
policy; free phases use the unmodified source worlds. Positions/angular velocities
and their accelerations use the unchanged source-derived four-bin caps and
**1e−5 tolerance**. This is the selected clip’s reference, not a substitution for
the older paired benchmark’s original-baseline caps.

The least-squares residual includes positive normalized rate excess, sampled
stance-height excess, sampled ankle-displacement excess and native local-angle
excess. Native bend boxes remain hard bounds. Numerical rate scales are
`max(cap, [0.05, 0.5, 0.1, 1])`; these only scale residuals, never acceptance.
The support proxy reserves 0.125 mm between its desired sample corridor and the
final floor/gap limits. A sparse finite-difference graph includes neighboring
native interpolation keys, derivative stencils and affected branches.

Every final proposal is serialized to float32 GLB and independently reloaded by
the existing `native_support_job` audit. Unchanged channels/clocks, outside
motion, support heights, displacement/angles and all source-rate caps must pass
for selection. The proxy objective does not select an otherwise failing clip.
Budget-limited outputs remain diagnostic proposals, with optimizer status saved.

```powershell
.venv/Scripts/python.exe scripts/native_support_job.py source.glb draft.json `
  reports/fresh-joint-support --joint-rates --joint-evaluations 320
```

The budget is an integer from 1 to 2000 per trial, default 80 in joint mode.
Four fixed smoothing seeds are retained: `(0.05,0.5)`, `(0.05,5)`,
`(0.15,0.5)`, `(0.15,5)`. The request records the method, budget and immutable
input/method hashes. Joint mode archives its additional implementation files.
The ordinary CLI and Studio still use the existing smoothing method by default;
this joint search has not been promoted into a Studio option or default result.

## Real development results

Both studies use the frozen [Studio v2 support request](studio-native-support-v1.md):
selected source SHA-256
`87c185ddf0dc50dec7e56bbc4c301f66896ed460a53c6c8eb6797ce5a89107c7`,
Y-up plane offset **−0.056 m**, two stance intervals **[1.6,2.4] s**, edit keys
**[15,105]**, 0.25 mm clearance, 5 mm maximum gap, 30 mm maximum displacement
and 45° source-relative local rotation bounds. There are **178** free bends and
**701** full-clip audit times. All eight serialized proposals pass support height
screens at **142 stance samples per foot**, preserve other/root/free motion and
keep native channel clocks. All eight hit their evaluation budget without
optimizer convergence and fail source-rate acceptance.

| Trial | 80-evaluation rate failures: speed / acceleration / angular speed / angular acceleration | 320-evaluation rate failures |
| --- | --- | --- |
| 1 | 78 / 21 / 35 / 17 | 65 / 20 / 37 / 19 |
| 2 | 92 / 21 / 35 / 17 | 67 / 23 / 35 / 18 |
| 3 | 82 / 17 / 33 / 21 | 65 / 20 / 33 / 21 |
| 4 | 64 / 14 / 33 / 18 | 58 / 16 / 33 / 19 |

Trial 4’s combined proxy squared residual falls from **0.6554625566** to
**0.0005640355** at budget 80 and **0.0003127406** at budget 320. Its independently
decoded 320-evaluation rate excess still reaches **0.0003568401 m/s**,
**0.0015101637 m/s²**, **0.0012723626 rad/s** and **0.0605092009 rad/s²** over the
unchanged cap-plus-tolerance. Failure counts and some peak violations are mixed
across seeds/budgets; no global improvement or feasibility claim follows.

The retained-input result hashes are:

- `reports/native-support-joint-rates-v1/result.json`:
  `ad80c04b2192330d474a3c491934ef7c039c148d640a0616f1d2cf99a7f80058`.
- `reports/native-support-joint-rates-v2/result.json`:
  `94f63ca1e81b5d43a883129f908ca4bc473b36a8bd8508c79ede51c53ac0d5ba`.

Neither study mutates the preceding source, draft, smoothing trials or outcomes.
Per-time foot-height audits, proposal GLBs, root tracks, intent markers, method
archives and failed-rate diagnoses remain local and unapproved.

## Validation and remaining work

Twelve model-free tests compare the batch rotation transport/IK against the
independent exact solver, including signed/inclined-plane reaches. They compare
the quantized proxy against the independently exported decoder at every audit
time (maximum allowed matrix error 2e−14), verify sparse dependencies by finite
differences, and cover frozen/disjoint same-foot phases, invalid boxes and
invalid budgets. A NumPy axis-order error was caught and fixed before the real
studies. The full suite passes **1,241 Python tests** and **14 JavaScript suites**.
Previous commit `49ade88` passed both Windows/Linux hosted source checks.

The remaining source-rate failures may involve the restricted bend-plane
parameterization as well as convergence. The next experiment should add bounded
knee-plane/swivel freedom while retaining the same authored supports and final
checks, rather than infer that more iterations alone will solve them. Any added
motion freedom must be audited against the supplied source/authoring bounds.
Broader rigs, scene/partner constraints, all-action evaluation and engine/human
evidence remain part of the single full-project goal.

No new training, held-out use, scene/engine/GPU validation, browser render,
submitted human review, quality approval or release gate changes are claimed.
All 14 release capabilities remain unapproved.
