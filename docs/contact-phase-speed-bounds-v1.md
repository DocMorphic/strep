# Contact targets impose motion requirements

`scripts/contact_phase_speed_bounds.py` compares constant world-space contact
targets for the same material vertex of one mesh. For target-center distance
`d`, contact tolerance `e` at each endpoint and positive time gap `dt`, every
satisfying trajectory must travel at least `max(0, d - 2e)` and therefore have
average speed at least `max(0, d - 2e) / dt`. Overlapping or touching phases with
disjoint target balls are reported as simultaneous target conflicts instead of
returning an infinite JSON value.

The helper uses actual phase times, preserves original phase indices, compares
nonadjacent phases too, and never compares different vertices. Call it
separately for each actor. It does not measure actual motion, select a realism
threshold, prove reachability or approve a trajectory. Floating-point results
are numerical diagnostics, not formal interval-arithmetic certificates. Moving
object-relative targets require a different analysis.

## Get-up contact boundary

The unchanged 25-phase study produces 12 same-vertex comparisons and no
simultaneous target conflict. Right-toe vertex 4619 is constrained through key
92 and again from key 94. Its target centers are 363.644149 mm apart, separated
by 66.666842 ms. With the original 20-mm tolerance at both ends, the required
minimum travel is 323.644149 mm and minimum average speed is **4.854650 m/s**.
This is a concrete requirement to review, not a new speed gate or proof of
physical impossibility. The contact intervals and generated targets remain
unchanged and are not human-approved ground truth.

The rejected six-key solve in `reports/kaykit-getup-backtrack-v2` retains the
94-pose accepted checkpoint. A read-only replay covers all 200 local sample
times and 600 active contact observations. The new right-toe contact misses by
23.181073 mm; both hands and the earlier toe contacts also have failed samples.
There are 20 failed correction-step rows. Actual toe endpoint displacement is
326.405896 mm, or 4.896076 m/s over that gap. It meets the necessary travel
bound, demonstrating why that bound alone cannot diagnose the solve's failure.
No path length, peak speed, force or balance approval is inferred.

A separate static key-94 diagnostic can satisfy the original pose/contact/floor
budgets. Its first export narrowly exceeds an edit budget and remains rejected.
Using the sequence solver's existing fitting reserves yields a decoded static
pass: 4.000025 mm floor depth and 19.000004 mm contact error. Adjacent-step limits
are absent only from this explicitly static diagnostic; the transition and
accepted clip are unchanged. This provides a possible endpoint initialization,
not permission to relax the transition.

Evidence is retained in `reports/contact-target-transition-v1`,
`reports/getup-contact-boundary-diagnostic-v1`, and
`reports/getup-key94-static-v1`/`-v2`. Sixteen new helper tests and 60 existing
solver checks pass. Five resource traces replay across 567 observations, with
peak worker-tree memory 359,948,288 bytes. Publication checks and hashes are in
`reports/contact-target-publication-v1/summary.json`. Both CI inventories include
the new tests (649 full and 198 focused Python files). The focused workflow now
preserves an in-progress run across newer pushes, so continuous development
does not repeatedly cancel its longer jobs. Full hosted validation remains pending.

## Studio contact-revision preview

The contact-revision preview now displays necessary timing requirements for
constant world targets in the staged draft. It runs after the preview response
has been checked against the exact original and authored contacts. It does not
change contact intent, animation bytes, solver limits or approval state.

`worldContactTiming` in `scripts/native-scene-editor.mjs` uses each contact's
own tolerance: minimum travel is `max(0, d - e1 - e2)`. Zero tolerances are
supported. Contacts must refer to the same actor and exact material point.
Individual vertices preserve their corresponding target positions even when
listed in a different order. A centroid is identified by its complete unordered
vertex set; it is never equated to one of its constituent vertices. A one-vertex
centroid and that individual vertex are equivalent.

All comparable phase pairs are checked, including nonadjacent overlapping holds.
The UI shows the strongest point requirement for each contact pair, with an
explicit conflict for disjoint allowed positions at overlapping or touching
times. This bounds output to at most 2,016 rows for the 64-contact scene limit.
Object and partner contacts are listed as unassessed. Pairwise consistency is
only necessary; it does not prove simultaneous multi-target feasibility,
reachability, actual speed or motion quality. There is no arbitrary fast/slow
classification. The display rounds numerical bounds and labels them approximate.

Offline tests cover actor/mesh/primitive/vertex identity, reordered individual
points, centroid equivalence, unequal and zero tolerances, overlap and touching,
nonadjacent phases, strongest-point aggregation, unsupported-target coverage,
invalid inputs, and non-mutation. Editor interaction tests check the visible
speed/conflict messages and retained original draft. The new test file is in
the model-free JavaScript CI inventory. Browser visual inspection has not been
performed for this text-only addition; no preview service was started.

## Warm transition retry

`reports/kaykit-getup-backtrack-warm-v2` adds the prior rejected transition and
the separately passing static endpoint to the initialization candidates. The
rejected transition has the lowest initial aggregate violation and is selected;
the static endpoint candidate is retained in the comparison. After three
bounded solver passes, the decoded candidate still fails seven sampled times:
maximum floor depth 4.182631 mm, contact error 20.283512 mm, root correction step
25.287128 mm, and rotation correction step 5.223077 degrees. Original limits
remain 5 mm, 20 mm, 25 mm and 5 degrees respectively. Candidate SHA-256:
`fc5db4e2d026504349984da960e664fc5233b63496d3e22e129f904cd28c51ba`.

The existing 94-pose checkpoint remains unchanged; all 3,699 prefix samples
pass again. The failed candidate is not sent to engine acceptance. Sixty solver
support checks pass, and resource replay validates 498 observations with peak
worker-tree memory 356,200,448 bytes. The retry completed under the memory guard;
its remaining failure is geometric/transition quality, not resource admission.
This does not establish impossibility or justify changing the authored targets.

### Attributing the remaining failures

`reports/getup-contact-boundary-diagnostic-v2` replays all 200 local sample
times and 600 active contact observations from the warm candidate. Four samples
fail contact distance: three on the left toe near key 92, and the new right-toe
contact at key 94. Both hand contacts pass. The other three failed pose samples
are left-hand rotation-edit budget violations, reaching 45.002036 degrees
against the original 45-degree limit. Thus “seven failed samples” must not be
reported as seven contact misses. There are also 23 failed adjacent correction
step rows, principally in the root and right-leg chain.

A deterministic step projection keeps the incoming key fixed and changes root
corrections by at most 0.801124 mm and rotations by at most 0.244498 degrees.
Decoded correction steps then pass, but contact error increases to 23.974875 mm
and 13 local samples fail. That proposal is rejected; the accepted checkpoint
is unchanged. Small parameter changes are not evidence that contact geometry
has been preserved. The retained projection SHA-256 is
`14040001d8db2d8af14c05b70701f71da299ba02ab427222334471c16fafab68`.

### Feasibility-only restoration

`reports/kaykit-getup-feasibility-v1` changes the six-key solver objective to
constant zero, keeping its nonlinear constraints, original acceptance limits,
fitting reserves and fixed incoming pose. This removes the competing preference
for the old checkpoint during this repair experiment. It is not an optimality
or realism objective, and is not automatically selected by Studio.

The exported candidate passes all 200 sampled pose/contact/floor checks: maximum
floor depth 4.358469 mm and contact error 19.689214 mm. However, root correction
steps reach 25.254993 mm and rotation correction steps reach 5.039332 degrees,
so the candidate remains rejected. Subsequent bounded passes do not improve the
retained candidate. No inference of infeasibility follows. Candidate SHA-256:
`2c18e37e9d1a9c6f50933bef857c28b3dceca8a5aa98d5ea5ba449b61052d862`.

The accepted 94-pose checkpoint remains identical and its 3,699 samples pass
again. All 60 supporting solver/export tests pass. The attribution/projection
and feasibility experiments have 496 replayed resource observations with peak
worker-tree memory 322,490,368 bytes. The publication receipt is
`reports/getup-feasibility-publication-v1/summary.json`. Engine validation is not
run on the rejected candidate. Human review, the remainder of the clip and the
broader release acceptance matrix remain unfinished.
