# Temporal clearance restoration: measured progress and rejected alternatives

The articulated crawl proposal is still rejected. Continuous-curve restoration
reduces its 499 intended / 503 serialized motion failures to 1 / 22 in a freshly
replayed alternative, while floor checks still fail at 76 of 2,017 times. A
separate full-floor proposal passes all sampled floor times but fails 24 intended
and 48 serialized motion conditions. Neither is a usable animation or evidence
of general motion quality.

## Unchanged problem and acceptance

This development study uses the existing humanoid asset and motion, not another
model generation or held-out case. It retains all 63 permitted root/six-arm
controls, three knots per track, 22 cm root/joint displacement limits, 30-degree
rotation limits, explicit editable clip edges, original rate caps and clocks.
The full original motion audit has 107,895 scalar conditions. Geometry uses
all 2,017 retained times and all 1,029 referenced surface vertices with the
original topology and 5 mm floor tolerance. There are no authored point-contact
targets in this scene; passing floor clearance would not establish hand support.

Proposals linearize all original three-vector motion norms using central
differences over every control. The conic step gives fixed surface witnesses a
hard prefix and motion norms a minimax restoration objective. Per-time proposal
floor limits are `max(5 mm, incumbent depth)`: they prohibit worsening a passing
time beyond the original tolerance or worsening a failed incumbent time. They
are progress guards, **not relaxed final acceptance**. Every exported candidate
still needs all intended, serialized and complete original floor checks to pass.

Solver `AlmostSolved`, lower surrogate error, or fewer failed rows never admits
an asset. Original clips remain selected and all raw rejected probes are saved.

## Measured alternatives

| Proposal | Intended failures | Serialized failures | Failed floor times | Peak depth, mm | Per-time floor progress guard |
| --- | ---: | ---: | ---: | ---: | --- |
| Constant articulated offsets | 499 | 503 | 174 | 27.783575 | Starting state |
| First restoration, full step | 189 | 191 | 79 | 14.861461 | Pass against starting state |
| Recentered full step | 4 | 29 | 76 | 12.436741 | **Fail** against first restoration |
| Recentered half step | 66 | 91 | 66 | 13.745054 | Pass against first restoration |
| Added switching witnesses, full step | 25 | 59 | 78 | 14.823869 | **Fail** against first restoration |
| Measured proposal margins, full step | 25 | 39 | 76 | 14.821123 | Pass against first restoration |
| Continuation from measured-margin step | 9 | 27 | 76 | 14.800027 | Pass against measured-margin step |
| Next recentered full step | 1 | 22 | 76 | 14.799323 | Pass against preceding continuation |
| Margins on floor and native proposals, full step | 8 | 41 | 76 | 14.799924 | Pass against preceding continuation |
| Direct original-floor target, full step | 24 | 48 | **0** | **4.974508** | Pass against preceding continuation |
| Direct original-floor target, half step | 5 | 16 | 49 | 9.845217 | Pass against preceding continuation |
| Restoration from floor-passing proposal, full step | 13 | 47 | 4 | 5.000064 | **Fail** against floor-passing proposal |
| Restoration from floor-passing proposal, half step | 19 | 51 | **0** | 4.987290 | Pass against floor-passing proposal |
| Floor-only margins, full step | 15 | 59 | 2 | 5.000002 | **Fail** against floor-passing proposal |
| Floor-only margins, half step | 19 | 40 | **0** | 4.987201 | Pass against floor-passing proposal |

The half step has better sampled clearance than the measured-margin full step;
the full step has fewer motion violations. Neither dominates every criterion.
Counts also conceal different failing rows; they do not measure perceived
realism, action correctness or animator cleanup effort.

The measured-margin full step still fails these complete motion groups:

| Group | Intended | Serialized |
| --- | ---: | ---: |
| Track bounds | 0 | 0 |
| Joint displacement | 10 | 10 |
| Position speed | 2 | 2 |
| Position acceleration | 0 | 15 |
| Angular speed | 10 | 10 |
| Angular acceleration | 3 | 2 |

This separates remaining curve restoration from additional storage defects.
Intended position acceleration passes with very little headroom; its serialized
version does not. No cap is enlarged to hide that difference.

## Witness changes and measured margins

The recentered full step with only four intended violations is rejected because
25 floor times worsen their per-time guard. At all 25, the worst surface point
changes from vertex 828 to vertex 285. A fixed-point affine plane constraint
does not protect the whole deformed mesh after another point becomes lowest.

The next proposal retains all 2,017 old witnesses and every original motion row,
adding those 25 switching witnesses. Full decoded checking then finds three
remaining floor regressions on original witnesses: at approximately 1.170833 s,
1.799999952 s and 1.8 s. Their overruns are approximately 0.002011,
0.007598 and 0.007583 mm. These are small but still fail the unchanged guard.

The existing measured-defect method tightens **proposal caps only**, doubling
observed affine underprediction or actual overrun. It adds reserves to 506 of
the 2,042 protected witness rows, with a maximum reserve of 0.073684 mm. Native
caps, scales and actual floor criteria remain unchanged. Reusing the complete
cached Jacobian avoids another finite-difference study. The new full step passes
the per-time progress guard but still fails actual motion and floor acceptance.
These empirical reserves are not certified nonlinear or storage error bounds.

## Resource policy and fresh replay

Every numerical phase uses the existing worker lock and unchanged guard:
2,048 MiB expected worker RSS, 2,776,629,248 bytes stable free RAM for admission,
15 seconds stability, 600 seconds admission timeout, 900 seconds worker timeout,
600 MiB runtime free-RAM floor and 7 GiB tree-RSS limit. No user apps are closed.

The first temporal worker stops on the runtime RAM guard after 40.937 seconds;
all 81 recorded observations replay and its failed phase remains retained. The
revised worker reuses saved decoded witnesses and completes after 497.14 seconds
of admission wait and 100.828 seconds execution; all 595 observations replay.
A replay first defers without starting at its 600.922-second admission limit
(597 observations). A later fresh guarded attempt completes at 54.843 seconds
with 72 observations. Neither admission wait counts as numerical validation.

The recentered study completes at 80.125 seconds / 97 observations; its retained
half-step fresh replay completes at 60.360 seconds / 77 observations. Added
witness refinement completes at 44.672 seconds / 62 observations. Margin reuse
completes at 44.671 seconds / 62 observations, followed by a fresh full-step
replay at 25.547 seconds / 43 observations. Recorded resource-policy, phase,
clock, stop, peak, exit and archive bindings match in the separate audits.

Fresh best-candidate replays reconstruct the GLB byte-for-byte and match worlds,
intended/native rows, original caps/scales, controls, clocks, authoring audit and
every full floor sample. Original rate caps recompute identically. All proposal
asset hashes are checked; unselected rays are not all numerically replayed.
Replays share repository arithmetic and are not implementation-independent
proofs. RAM is sampled, not guaranteed between observations.

Local ignored evidence: `reports/crawl-intended-restoration-v1` through `v5`,
`reports/crawl-intended-restoration-replay-v1`, `v2`, `v4` and `v5`,
`reports/crawl-intended-witness-refinement-v1`,
`reports/crawl-intended-witness-margin-v1` and
`reports/crawl-intended-witness-margin-replay-v1` and
`reports/crawl-intended-native-margin-v1`, `reports/crawl-intended-full-floor-v1`,
`reports/crawl-intended-full-floor-replay-v1`, `reports/crawl-intended-restoration-v6`,
`reports/crawl-floor-preserving-margin-v1` and its `-replay-v1` companion.
Preserve original phases,
inputs, raw probes, clocks, resource traces and failed results.

The next recentered continuation starts from the freshly replayed measured-margin
full step, keeping all original rows and all floor times. Its full step has
9 intended / 27 serialized violations and 76 failed floor times at 14.800027 mm.
Execution completes in 79.281 seconds / 96 observations. Separate fresh replay
matches every retained best-candidate quantity and full floor sample at 42.625
seconds / 60 observations; all four proposal hashes are checked. The one-eighth
ray worsens a floor time and is rejected even though its peak depth decreases.
This is another retained partial result, not motion approval.

The following recentered pass completes at 80.250 seconds / 97 observations.
Its full step retains only one intended violation, with normalized excess
1.9708212773078315e-10, and 22 serialized violations. The strict original gate
still rejects that tiny intended excess; it is not rounded away.
Separate fresh reconstruction matches all intended/serialized values, original
cap arrays, payloads, worlds and complete floor samples in 40.593 seconds /
58 replayed resource observations. All four proposal asset hashes match; other
rays are not numerically replayed.

Extending measured proposal reserves across both floor and native norms does
not solve the storage issue. The cached-model trial reserves 39,691 rows, of
which 38,643 are native, without changing any actual acceptance cap. Its full
step has eight intended / 41 serialized failures and worse intended minimax
error than its nine-failure starting state. The half step also fails to improve
that merit. Neither is retained as an improving continuation. Execution takes
43.719 seconds / 61 observations. Measured inward margins are a heuristic;
additional margins can produce a worse decoded result.

## Direct original-floor target

The next experiment reuses the entire cached finite-difference model from the
second continuation, centered at the freshly replayed nine-intended-failure
anchor. It replaces per-time progress allowances with the original 5 mm target
in all 2,017 affine plane witnesses. Every original native norm, cap, scale,
control bound and clock stays present. The actual complete mesh decides floor
acceptance; affine solver status remains guidance only.

The full step passes all 2,017 sampled floor times and their topology/degeneracy
checks at 4.974508 mm peak depth. It fails 24 intended / 48 serialized motion
conditions and is rejected. The half step fails 49 floor times at 9.845217 mm
and five intended / 16 serialized conditions. Its lower motion failure count
does not make it a valid alternative. This trial completes in 45.640 seconds /
63 replayed resource observations. Continue motion restoration from the
floor-passing proposal while keeping the original floor tolerance.
Separate fresh replay reconstructs its export, all motion/world/cap/clock/control
arrays and every floor sample exactly in 25.407 seconds / 43 observations.
Both proposal asset hashes match. This shared-arithmetic replay confirms sampled
floor compliance and the same 24 / 48 motion failures, not motion approval.

Recentered restoration from that floor-passing proposal finishes in 79.063
seconds / 96 replayed resource observations. Its full step reduces intended
failures to 13, with maximum normalized excess 1.477186710745063e-7, but has 47
serialized failures and regresses four floor times. Peak depth is 5.000064 mm;
the strict 5 mm gate rejects it. The half step keeps every sampled floor time
passing at 4.987290 mm peak depth, but retains 19 intended / 51 serialized
failures. Quarter and one-eighth rays also remain raw rejected alternatives.
Lower intended error therefore still does not guarantee complete decoded
compliance; floor margins and storage repair remain separate measured problems.

Measured floor-only proposal margins reserve 810 witness rows, with a maximum
reserve of 0.000135894 mm; no native proposal or actual cap changes. The full
step still exceeds the original floor tolerance at two times, peaking at
5.000002 mm, and retains 15 intended / 59 serialized violations. The half step
passes every sampled floor time at 4.987201 mm but retains 19 intended / 40
serialized failures. Compared with the preceding half step, its intended
minimax excess is slightly worse despite fewer serialized failed rows. This is
a tradeoff, not uniform improvement. Execution completes in 46.860 seconds /
64 replayed resource observations.
Separate fresh half-step reconstruction matches every retained payload, world,
intended/native condition, original cap/scale, clock/control and full floor
sample in 28.407 seconds / 46 replayed observations. Both probe hashes match;
the rejected full ray is not numerically replayed in that phase. The half step
is a verified partial continuation, with original clips still selected.

These are explicit experimental wrappers around the existing public
`native_scene_norms.linearize`, `native_surface_lift.lift`,
`native_scene_conic.direction`, `native_scene_restore.tighten` and the complete
decoded motion/geometry audits. They are not automatically integrated into
Studio, do not whitelist crawl prompts, and do not establish object/partner
contact correctness. Raw test-character payloads and bulky observations remain
excluded from Git under their existing provenance and license rules.

## Hosted source verification

The [full model-free workflow](https://github.com/DocMorphic/strep/actions/runs/38210165808)
at `2c998a20856cd55461ca1c9dc2189c1696eed024` now
completes successfully in all 12 Windows/Linux jobs. Its four main Python shards
per OS pass 2,421 + 2,092 + 2,412 + 2,370 tests: **9,295 passed, seven skipped and
60 subtests passed per OS**. Additional adapter jobs pass 475 + 21 + 215 checks
with one skip per OS; material-package jobs pass 217 per OS. These invocations
overlap the main inventory, so they are not added as distinct coverage. The
declared 42 Node suites and offline editor checks complete in shard zero.

This supplements the eight successful focused jobs recorded in the previous
study. It validates source behavior, not the rejected development animation,
learned model quality, engine playback or release criteria. Archived workflow
metadata and logs remain under `reports/wide-pose-hosted-2c998a2`.

## Scope and next decision

Continue curve restoration from verified partial alternatives, preserving all
original constraints and full decoded geometry. A whole sampled pass would
still leave continuous collision, self-collision, support/dynamics, semantics,
engine fidelity and human quality unverified. These experiments introduce no
new training, model, held-out evaluation, live browser/rendering/engine check,
animator rating or timed cleanup evidence.

The single whole-project goal stays active. All 14 release capabilities remain
unapproved; broad actions, object/partner interactions, rough editing, style and
capability controls, rig transfer, transitions, engine imports and independent
review/cleanup requirements remain. Evaluation categories are not a whitelist.
