# Simultaneous motion restoration and higher-order stored-key search

The development curve now passes every intended motion condition and every
sampled floor time under its original constraints. Exported motion still fails:
the verified half step has 36 native violations, and paired stored-key search
retains a partial best with 32. Original clips remain selected. These are
sampled numerical results, not animation, engine or release approval.

## Simultaneous original norms

One-row correction repaired an angular-acceleration violation but introduced a
speed violation elsewhere. The next model therefore constrains all 107,895
original three-vector motion norms together with all 2,017 floor witnesses.
Every original control, cap, scale, clock and permission remains present. A
minimum-control-step quadratic objective has no minimax slack variable. A
1e-9 normalized inward margin applies only to variable proposal rows; actual
acceptance caps are unchanged. Geometry retains the previous one-micrometer
proposal headroom while complete decoded acceptance remains at 5 mm.

The first solve reports `InsufficientProgress` after 31 iterations: no candidate
is initially exported. It completes at 28.312 seconds / 46 replayed resource
observations. The equivalent scalar-axis formulation replaces 86 norm cones
with both signed linear inequalities, retaining 122 full cones. It still
reports `InsufficientProgress`, after 20 iterations; this phase completes at
16.203 seconds / 34 observations. All fixed and box-screened rows remain in
complete post-solve evaluation; conservative screening is proposal work only.

The next phase examines the finite iterate independently of its status. All
109,912 original affine rows pass, with maximum excess -6.302310e-9. The first
export and full geometry audit complete, but the wrapper then fails because a
cached floor-limit variable is missing. That raw failed phase is retained:
23.281 seconds / 41 replayed observations. A fresh corrected wrapper reuses the
unchanged cached model and completes at 36.547 seconds / 54 observations.

| Rechecked ray | Intended failures | Native failures | Failed floor times | Peak depth |
| --- | ---: | ---: | ---: | ---: |
| Full | **0** | 39 | **0 / 2,017** | 4.998939 mm |
| Half | **0** | 36 | **0 / 2,017** | 4.998960 mm |

The half step is chosen for lower native failure count while both pass intended
motion and sampled geometry. Its peak depth is slightly higher; no uniform
improvement across every metric is claimed. Separate fresh reconstruction
matches its GLB, worlds, all intended/native values, original caps/scales,
controls/clocks and every floor sample. Original rate caps recompute identically.
Both probe hashes match; the other ray is not separately numerically replayed.
This shared-arithmetic replay takes 40.563 seconds / 58 observations.

An early termination status does not certify solver feasibility or optimality.
Here every original affine row and every intended/decoded/mesh condition is
rechecked before any use. The exported candidates remain rejected because
their complete native conditions fail. The experimental simultaneous wrappers
are not automatically wired into Studio or the default fitting method.

## Paired storage repair

The verified half step admits bounded storage search because its intended
curve passes. The unchanged policy permits one absolute Float32 neighbor per
component, at most 64 corrections, only on explicitly editable rotation and
translation keys. Eight stages with up to 64 probes per stage test 68 changed
neighbors and write 69 complete native exports. Partial best reduces failures
from 36 to 32, repairing five old rows but introducing one new row. Worst
normalized excess stays 1.936282358088868e-5; secondary merit decreases from
1.256569974102831e-9 to 9.806404263728356e-10. The returned payload is still the
byte-identical failed 36-row seed.

Both best and returned full floor screens pass all 2,017 times at 4.998960 mm
peak. Search completes at 316.015 seconds / 330 replayed observations. Separate
fresh returned/best reconstruction matches payloads, worlds, all native rows,
caps/scales, controls/clocks and typed continuations; both complete floor
screens reproduce. Original caps and all intended rows recompute identically.
All 69 receipt/observation/asset hashes match; other neighbors are not all
numerically replayed. Replay takes 41.500 seconds / 59 observations.

The remaining best groups are one position-speed, 28 position-acceleration and
three angular-acceleration failures. The largest is RightArm positional
acceleration at original row 60,809 / uniform frame 379. Its joint origin can
be moved by permitted root translation; its own rotation does not move that
origin. Acceleration sampling can require three native keys, motivating an
additional explicit search family without widening the one-neighbor envelope.

## Explicit triple search

`native_component_triple_search.py` adds an opt-in search for three different
components at one native key or one component at three consecutive native keys
of the same actor/track. Choices remain absolute -1, 0 or +1; zero restores the
baseline component, and steps never accumulate. Cross-actor/track bundles,
duplicate identities, gaps and malformed choices reject before application.

The complete declared triple population is counted before materialization and
must fit its 65,536-candidate budget. Actor/track/family groups interleave so a
finite prefix is explicit, not silently reduced coverage. The checked search
still validates all original caps/scales/controls and every decoded row for each
export. Geometry remains a separate complete check, and defaults are unchanged.

Twenty-one new tests plus related fitting, component, paired and inventory checks
pass **143 tests** in 54.37 seconds. Guard execution is 54.844 seconds / 72
observations. A previous test invocation used a nonexistent module path and
ran no tests; its failed phase and all 18 observations are retained. The
declared inventory now contains 480 Python modules / 42 Node suites and 42
focused modules. No action name is a supported-prompt whitelist.

The matched trial starts from the freshly replayed 32-failure paired state,
retaining the same continuous controls, source and one-neighbor policy. All
eight stages test 87 changed neighbors and save 88 complete native exports.
Partial best reaches 31 failures, repairing one old row and introducing none.
Worst normalized excess remains unchanged; secondary merit decreases to
9.461773322749022e-10. Returned bytes remain the failed 32-row seed. Both complete
best/returned floor screens pass all 2,017 times at 4.998960 mm peak depth.
Execution completes at 404.313 seconds / 417 replayed observations.

Separate returned/best reconstruction matches every payload, world, original
native row, cap/scale, control/clock and typed continuation, and recomputes both
complete floor screens. Original caps and intended rows rebuild identically.
All 88 probe receipt/array/asset hashes match; other neighbors are not all
numerically replayed. Shared-arithmetic replay completes at 42.500 seconds /
60 observations. The search is finite, not an infeasibility proof or animation
approval. The dominant RightArm acceleration failure still remains.

## Full-workflow regressions and targeted fixes

The larger hosted workflow at `b465ad2` exposes two failures not covered by the
green focused job: the budgeted solver's copied secondary selection no longer
matches the checked shared formulation, and a Studio failure-preservation
fixture now successfully meets its contact target while other checks fail.
Those are reported as full-workflow failures; no full-suite pass is inferred.

The budgeted solver now recomputes the primary affine merit and checks all
secondary norms, hard rows, bounds and the same recorded proposal tie reserve.
It retains its explicit **two-phase** budget, without adding a retry. Two new
tests verify that misleading `Solved`/`AlmostSolved` secondary results cannot
replace a valid primary or add a third budget phase.

The Studio fixture retains the ordinary reachable target but grants only
0.000001 degrees of arm rotation for this failure-preservation case. Its
existing catalog, rejection, contact-failure, original-library, lineage and
timing assertions remain intact. The ordinary editable transition fixture is
unchanged. This removes reliance on a particular optimizer failing to reach
an otherwise reachable target; it does not relax product acceptance criteria.

An initial broader local run reaches its unchanged 900-second time guard while
executing shared transition tests. It is retained as incomplete validation;
all 907 resource observations replay. A targeted four-module run then passes
**72 tests** in 565.40 seconds, with 565.453 seconds guard execution / 576
observations. The subsequent budget/shared-norm run, including the two new
budget tests, passes **53 tests** in 9.32 seconds, with 10.171 seconds execution /
28 observations. Those populations overlap and are not summed as distinct
coverage. The full hosted suite remains required after publication.

Ignored evidence remains under `reports/crawl-simultaneous-norms-v1` through
`v4`, `reports/crawl-simultaneous-norms-replay-v1`,
`reports/crawl-simultaneous-storage-v1`, `reports/crawl-simultaneous-storage-replay-v1`,
`reports/crawl-simultaneous-triples-v1`, `reports/crawl-simultaneous-triples-replay-v1`,
`reports/simultaneous-storage-failures-v1` and
`reports/triple-storage-validation-v1` / `v2`. Keep failures and provenance.
CI failure logs and guarded targeted repairs are retained in ignored
`reports/b465-full-shard0-linux.log`, `reports/b465-full-shard3-linux.log`,
`reports/full-ci-regression-validation-v1` / `v2` and
`reports/full-ci-regression-budget-v3`.
All 14 capability requirements and the single whole-project goal remain intact.
No new learned model, training, generation, reserved held-out evaluation, live
rendering, engine fidelity, semantic/human review or timed cleanup approval is
performed by these phases.
