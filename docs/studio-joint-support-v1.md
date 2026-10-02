# Joint support and motion-rate search in Studio

Studio now exposes the existing bounded bend, knee-plane and foot-orientation
search as an explicit alternative to default smoothing. It works through the
same native support route for checked character clips and
[native review candidates](native-review-support-v1.md). This is deterministic
motion processing; it does not train or change Kimodo.

## Workflow and limits

Bind a clip in **Native foot supports**, then author its support plane, stance
seconds, frozen boundary keys and displacement/angular bounds. Choose
**Search support and motion rates together** before **Try correction**. The
choice is exclusive with between-key refinement. Neither method is enabled by
default. A reset clears both choices.

The request accepts only a strict boolean `joint_source_rate_search`; clients
cannot supply solver paths, warm controls, budgets or additional mode flags.
The job freezes an evaluation limit of **160 per proposal**, across the four
existing smoothing settings. It allows knee-plane swivels up to five degrees
and native foot-world orientation edits up to one degree, within the authored
local rotation/displacement bounds. Native ankle targets remain in the existing
parameterization. This freedom differs from the default fitter, which retains
the source bend plane and foot-world orientation. A larger set of variables
does not establish that a feasible solution exists or will be found.

The comparison report shows the search budget and actual solver-reported
evaluations. Finite-difference work adds computation; this is not a wall-clock
time limit. Each
completed proposal links to its saved numerical controls. The controls contain
parameter boxes, interval clocks, variable indices, smoothing settings and the
exported GLB hash. Their hash, schema, stated freedoms and proposal binding are
checked before serving. Replay also requires the frozen source, support draft
and archived methods. A controls file is not an acceptance receipt.

All existing final checks remain required: serialized sampled foot-region
heights, authored ankle/angular limits, source-relative 120 Hz motion rates,
unchanged clocks/root/free phases/unaffected branches and frozen boundary keys.
The rate limits still use the selected input's four time bins and 1e-5
tolerance. The least-squares residual and optimizer termination status do not
replace these checks. Native review conversion also retains its independent
serialized preview screens and cumulative original-relative edit budget.
Failed proposals remain available and the selected input is retained. Selecting
a native version remains explicit and clears contact labels and human claims.

These screens do not establish horizontal foot locking, whole-sole planting,
balance, forces, correct semantic stance timing, self-collision, continuous
collision or animation quality. Human review and separately licensed accepted
corrections are still required for training admission and release evaluation.

## Matched development study

The local study uses the prior native-review wave and kick floor requests with
the same candidate previews, authored stance windows, plane and edit bounds.
Only the proposal method changes. These are historical development candidates
with numerical forearm/root edits, not a new model generation, reviewed stance
annotations or the untouched release benchmark population.

The matched study is terminal. It runs two cases, four proposals each, on
the same native review sources and constraints as the earlier default canary.
Failed row groups below are positional speed, positional acceleration, angular
speed and angular acceleration. These are individual sampled joint/rate rows,
not counts of visibly incorrect frames.

| Case / proposal | Default failed rate rows | Joint-search failed rate rows | Evaluations |
| --- | --- | --- | --- |
| Wave / 1 | 37 / 7 / 24 / 8 | 9 / 4 / 1 / 3 | 160 |
| Wave / 2 | 20 / 7 / 26 / 13 | 4 / 2 / 2 / 3 | 160 |
| Wave / 3 | 45 / 6 / 24 / 8 | 23 / 4 / 4 / 4 | 160 |
| Wave / 4 | 23 / 8 / 24 / 8 | 14 / 4 / 0 / 8 | 160 |
| Kick / 1 | 25 / 11 / 3 / 9 | 6 / 6 / 3 / 5 | 160 |
| Kick / 2 | 21 / 11 / 3 / 9 | 4 / 7 / 10 / 5 | 160 |
| Kick / 3 | 42 / 14 / 3 / 4 | 16 / 9 / 5 / 5 | 160 |
| Kick / 4 | 35 / 15 / 3 / 4 | 7 / 12 / 6 / 6 | 160 |

All eight trials complete and pass their sampled support screens.
**All eight fail at least one motion-rate row.**
The native conversion accepts **0 of 2 requests**. Both retain
the exact selected input. The retained inputs still fail their authored support
height screens; successful export does not conceal that result.
The bounds and final gates are unchanged. Optimizer residuals are diagnostic
only. These two development cases cannot establish general motion improvement
or infeasibility under different parameterizations.

The controls reconstruct all eight proposal GLBs byte-for-byte. An independently
decoded float32 GLB matches the rounded-key model within 7.568e-09 matrix
elements. Outside the single terminal clamp sample, agreement is within
1.221e-15 matrix elements. The sample at 3.966666666666667 s precedes the
exact final float32 key,
but the current scalar decoder's endpoint comparison clamps it to that key.
The batch proxy interpolates instead. The clamped decoded pose matches the
frozen final source pose exactly. The original V1 replay diagnostic stopped
on its blanket 2e-14 conformance assertion; that failed record and runner remain
preserved. V2 reports the endpoint discrepancy separately rather than changing
a production gate or hiding the first attempt.

Replay preserves the exact recorded failure counts. Continuous and serialized
failure counts remain separately recorded: rounding can both add and remove
borderline rows, and no tolerance is widened to hide them.

| Case / proposal | Continuous-model failed rows | Serialized failed rows |
| --- | --- | --- |
| Wave / 1 | 11 / 5 / 5 / 3 | 9 / 4 / 1 / 3 |
| Wave / 2 | 4 / 3 / 2 / 3 | 4 / 2 / 2 / 3 |
| Wave / 3 | 25 / 5 / 8 / 3 | 23 / 4 / 4 / 4 |
| Wave / 4 | 15 / 4 / 0 / 4 | 14 / 4 / 0 / 8 |
| Kick / 1 | 6 / 8 / 3 / 5 | 6 / 6 / 3 / 5 |
| Kick / 2 | 6 / 5 / 7 / 5 | 4 / 7 / 10 / 5 |
| Kick / 3 | 16 / 11 / 5 / 6 | 16 / 9 / 5 / 5 |
| Kick / 4 | 5 / 8 / 3 / 7 | 7 / 12 / 6 / 6 |

Godot 4.7.2 imports both selected clips/240 native frames with
77 bones, one skinned surface and non-looping playback. All native-time
joint samples agree within 5.437e-07 metres and
9.795e-07 basis elements. These are import/CPU pose checks,
not browser appearance, GPU deformation or motion-quality measurements.

The unchanged source/method bindings are rechecked at completion. Local evidence:

- `reports/native-joint-support-canary-v1/result.json`: matched requests,
  controls and selected native preview/import results.
- `reports/native-joint-support-replay-v2/result.json`: exact replays,
  continuous/serialized rates, quantization deltas and bound evidence.
- `reports/native-joint-support-validation-v1/verification.json`: current
  public sources, local evidence and completed check receipt.

Ten new synthetic wrapper tests cover strict choices, mutually exclusive modes,
blocked client-supplied budgets/solver options, real bounded search, retained
source, controls binding and changed evidence. Offline DOM assertions cover the
explicit checkbox, immutable request and reset behavior in both editor
namespaces. The full model-free selection passes **1,658 Python tests and 15
JavaScript suites**; the separate focused CPU pipeline passes **212 tests**.
These software checks are distinct from the two actual development cases.
The preceding public commit `f1c14d7` passes all four hosted Windows/Linux jobs
in run `37033732741`.

The next numerical experiment should align the diagnostic clock with the
actual decoder, then warm-start a serialized feasibility repair
from these reproducible controls, using the same source/draft, parameter boxes
and final gates. This study does not justify simply raising an iteration limit,
relaxing source-rate caps or claiming that prompting solves contacts. Broader
actions/rigs, horizontal planting, object/partner/finger geometry, real licensed
reviewed corrections, model improvement and human cleanup remain unfinished.
There are zero real human submissions and zero model updates here. All 14
release capabilities remain unapproved, the formal 72-by-five population is
untouched and the single full-project goal remains active.


The [decoder-aligned repair follow-up](native-support-clock-repair-v1.md) addresses
the measured batch/scalar endpoint discrepancy without changing the historical
outputs or final acceptance gates, then tests a serialized warm repair.
