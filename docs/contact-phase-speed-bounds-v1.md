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
