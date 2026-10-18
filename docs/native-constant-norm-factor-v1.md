# Exact constant constraints in a bounded solver model

The complete 49-control temporal census requires **68,900** affine norm
constraints, beyond the existing solver's 65,536-cone limit. No solver started
from that oversized population. The rejected first census is preserved, and a
second completed census records the full counts and failed admission explicitly.

| Planned population | Norms |
| --- | ---: |
| Original native controls | 5,400 |
| Original observation pose bands | 23,880 |
| Affected exact-native-clock pose bands | 1,990 |
| Passing affected/required world guards | 33,594 |
| Original prop native and 2,017-time translation/rotation bounds | 4,036 |
| Total | 68,900 |

Every one of the 6,050 failed world rows remains an objective, including those
outside the temporal support. All 72 protected repairs remain explicit guards.
Of the original 383,617 world conditions, 35,615 are affected or required;
348,002 have exact endpoint-zero support. All 23,880 original observation pose
bands and all 35,504 original pair rows occur outside the profile support.
Their sampled inputs are structurally invariant in this search subspace. That
does not prove new collision clearance or permit skipping nonlinear postchecks.

`scripts/native_constant_norm_factor.py` supplies an equivalent representation
of a complete **affine** norm system. Every nonconstant cone is retained.
For exact constant cones, `norm(v + J*d) - r` is independent of `d` because
every coefficient in its complete three-row Jacobian is exactly zero. Their
conjunction is represented by the cone with the largest original-unit norm
excess. Its original vector and radius are copied unchanged. A failing constant
therefore remains failing; it cannot be hidden among passing constants.

All original rows map to the retained cones, and the representative's original
index and maximum constant excess remain explicit. Exact duplicate coefficients
are summed before detecting constants. Tiny nonzero coefficients, including a
coefficient in column 768, are retained. There is no normalization, near-zero
cutoff, physical tolerance change or selection by motion error. The helper has
an explicit 131,072-input-norm and 64 MiB working bound; the solver's 65,536-cone,
768-column and matrix/process bounds remain unchanged. Whole inputs are rejected
when admission fails.

This equivalence applies only to the supplied local affine system. A zero
Jacobian is not a proof of nonlinear invariance. The caller must retain the
complete unfactored vectors/matrix/radii, verify every original norm at the
returned direction, then run the original raw/saved motion, contact and changed
scene checks. Neither a factored feasible point nor a solver status approves an
animation or establishes nonlinear feasibility/infeasibility.

## Source verification

The final local run passes **97 tests**: 20 new cases and 77 existing sparse
solver regressions. Cases cover complete row maps, both sparse layouts, exact
duplicate cancellation, tiny nonzero final-column coefficients, failed final
constants, unchanged original inputs/radii, invalid sparse storage and whole
budget rejection. A real backend solve uses the factored form of 70,000 original
cones, then rechecks all 70,000 original inequalities. Other fixtures compare
the full and factored predicates over multiple directions.

The initial run retains a failed test-harness lookup: it expected a dictionary
where the existing solver returns a tuple. The corrected run changes no motion
or solver tolerance, and also covers explicit rejection of a one-dimensional
sparse array. Final recorded resource replay: 33.672 s, 152,432,640-byte peak
process tree RSS and 35 observations. These model-free source fixtures are not
motion-quality, engine, human-review or release evidence.

The 20 new cases also passed on hosted Windows and Ubuntu at
`118b7d0d6b7b4bd9e8449c47ff9e1e4a22689336`
([run 39113372853](https://github.com/DocMorphic/strep/actions/runs/39113372853)).

## Complete temporal model preparation

The real scene's world model retains **33,594 passing vector guards** and all
**6,050 failed-row objectives**, with 49 columns and all 72 repaired witnesses.
Every one of the 100,782 world-vector components and all objective derivatives
passes two full nonlinear directions. Maximum vector differences are
7.592e-7 / 5.875e-7; objective differences are 3.719e-7 / 3.540e-7. Canonical
values and scalar derivatives are separately compared with the original kernels.
World search radii retain half the initial raw slack; scalar guards retain half
the smaller raw/saved slack. Original physical radii remain recorded separately.

The companion input keeps all **35,306** native/pose/prop norms, including all
23,880 constant original observation poses. The 1,990 affected native-clock pose
vectors receive complete two-direction replay, covering all 5,970 components and
49 columns; maximum differences are 8.846e-10 / 6.518e-10. Native control affine
maps replay exactly across all 5,400 vectors. Original pose invariance follows
from exact zero endpoint directions, rather than an observed zero tangent.

The prop follows a saved-reference hand target plus the raw body displacement
for local guidance. That explicit tangent anchor is not a Float32 derivative or
new author epoch. Actual exported trials must recompute the target from their
new saved body files. All 2,017 original translation/rotation permission samples,
both native prop norms and all four prop controls remain. Complete prop sample
directions and the separate boundary-clearance column are checked. An initial
preparation mistakenly used the short geometry clock; its assertion stopped it
before assembly. The preserved replacement follows the existing permission
method's native-and-frame clock, retaining all 2,017 samples and original limits.

Actual factoring maps all **68,900** original affine norm conditions to
**15,864** solver cones. No author cap, solver budget or physical tolerance grows.
The complete unfactored vectors, sparse matrix, search/physical radii and every
row's occurrence map are saved. Two full original-model directions exactly match
the retained rows and maximum norm excess. Positive per-cone radius scaling is
checked separately and only conditions the solver representation. The finished
input is **7,165,664 bytes**, with all 33,594 scalar guards, 6,050 objectives and
49 columns retained. A separate solve must recheck all 68,900 unfactored norms
and original box/hard/peak/cost conditions before any motion export is tried.

Resource replays passed for world preparation (103.313 s / 325,144,576 bytes /
103 observations), native/prop preparation (56.172 s / 262,615,040 bytes /
57 observations), native directions (47.109 s / 196,468,736 bytes /
48 observations), and assembly (36.734 s / 104,742,912 bytes / 38 observations).
These are recorded sampled process limits, not guarantees between samples.
No prepared input itself constitutes feasible motion, changed-time geometry,
engine, developer/animator cleanup or release approval.

## Bounded solve and provisional motion improvement

The separate solver reached `AlmostSolved`. Its full raw point failed the local
box, hard-row and norm admissions and was rejected. The predeclared half-ray
proposal passed the strict normalized norm/hard/box/peak/cost comparisons.
An additional process-level check evaluated **all 68,900 original unfactored,
unscaled norms**, physical radii, all 33,594 hard rows and the original control
box. Every maximum excess/residual was strictly negative. This is local-model
evidence; solver status and diagnostic tolerances do not replace physical checks.

The first exported trial then completed **all 944,562 original raw/saved motion
conditions**. All 177,328 nonworld scalars pass, including original native,
observation pose/pair and exact-native-clock pose populations. The world
comparison retains all previous passing rows and every one of the 72 prior
repair witnesses:

| Measurement | Qualified reference | Provisional raw | Provisional saved |
| --- | ---: | ---: | ---: |
| Source-rate failures | 6,050 | 6,040 | 6,040 |
| Newly failed previously passing rows | — | 0 | 0 |
| Previous repair witnesses reopened | 0 | 0 | 0 |
| Newly repaired rows | — | 10 | 10 |
| Worst normalized violation | 43.283007 / 43.283008 | 42.991808 | 42.991810 |
| Squared-violation reduction | — | 1,849.028656 | 1,849.034634 |

The same ten row identities are repaired in both modes. The actual saved hand
target recouples the prop using the original controls plus the four proposed
deltas. Its native permissions, **all 2,017** original sampled permissions and
every declared base/mesh contact pass. The second and third predeclared trial
fractions were unnecessary after the first passed. These are source-preservation
measurements, not anatomical limits or realistic-motion approval.

An independent process excludes the new profile/context/producer/coupled-prop,
factor and solver modules. It rebuilds both complete cumulative control tables
and original-source GLBs byte for byte, freshly matches all 5,400 raw and 5,400
saved native bounds, 23,880 saved native pose scalars and 383,617 saved world
values, and reconstructs the prop position/quaternion directly from the original
source and four controls. Every original permission and base/mesh contact array
matches byte for byte. The other 177,328 nonworld scalars remain archived,
source-bound passing evidence; the replay does not claim fresh triangle queries
for every one. Baseline interpolation, skinning and serialization libraries are
shared, so this is not independent physics.

Local artifacts are `reports/native-track-conic-solve-v1`,
`reports/native-track-motion-trial-v1/probe-00` and
`reports/native-track-independent-export-v1`. Their resource replays passed:
39.797 s / 197,193,728 bytes / 41 observations;
178.094 s / 293,715,968 bytes / 175 observations; and
40.843 s / 217,268,224 bytes / 42 observations, respectively.

**The candidate is provisional.** Qualified reference and Studio selection stay
unchanged. The reference still has 6,050 source-rate failures, two scene
failures, 113 crossing records, 23.475561 mm maximum depth and 1,785 other body
policy times unverified. Fresh geometry must preserve all old 44 scene times and
cover all 185 potentially changed body-policy times using the complete original
meshes and limits. A changed prop curve cannot inherit old prop geometry merely
because a character hierarchy is unchanged. Its 2,017 permission samples are not
2,017 geometry samples. Complete prior-condition comparison and independent
geometry replay remain required before qualifying the candidate. Continuous/self
collision, dynamics, semantics, engine and genuine human cleanup evidence remain
open; all release capabilities stay unapproved.

The source/resource-qualified checkpoint is
`reports/native-track-conic-progress-v1`. Its conservative geometry plan contains
**222 distinct scene times**, the union of all prior 44 and all 185 potentially
changed body-policy times. This is a plan, with zero geometry queries performed
by the checkpoint. Every prior scene condition and collision metric must be
compared, changed prop geometry queried afresh, and results independently replayed.
