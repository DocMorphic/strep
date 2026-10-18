# Complete current-violator surface study

Development evidence, 2026-10-18. The previously retained high-five diagnostic
still has 40 directed body-overlap failures and one palm-orientation failure
among its 496 physical conditions. Its maximum body depth is about 32.1 mm;
the unchanged development screen is 5 mm. A successful asset export does not
resolve these failures. The qualified reference and Studio selection remain
unchanged.

This study builds a local correction model at that retained pose using every
original surface vertex, all eight skin influences, all 120 editor frames and
both actor directions. It retains all 6,445 current soft violating points and
43 positive-depth points belonging to mandatory passing partner conditions.
There is no top-k selection. Together with the 496 original scalar conditions,
the model has 6,984 rows and 72 controls. Original source-relative permissions
remain five degrees for the selected joint edits and two centimetres for root
edits; protected keys and all source motion limits remain unchanged.

Complete pose differentiation and bounded skin/mesh Jacobians replace repeated
backward passes per vertex. Seven guarded chunks cover the complete clock;
each owns its resource receipt. The 64 MiB complete-model policy is unchanged.
Torch jobs retain a 2 GiB process-tree cap, pure numerical jobs a 512 MiB cap,
and both retain the 600 MiB available-memory reserve. No checkpoint inference,
training or raw source modification is involved.

At the original finite-difference step of 1e-5, two selected points fail the
unchanged 0.001 relative derivative-error check: frame 56 A-to-B vertex 12795
and frame 64 B-to-A vertex 12392. The failed whole-clock result is preserved.
Dedicated probes reproduce both failures, identify the same baseline triangle
in both skinning paths, and compare against the original backward derivative
and a frozen barycentric surface-anchor derivative. Maximum component errors
are below 4e-15. All 692 and 279 rows in the affected queries pass at **both
1e-6 and 1e-7** finite-difference steps. All frozen-anchor checks also pass.

This qualifies the local derivatives through step refinement, not by declaring
that the failed fixed-step check passed. Surface-feature changes can invalidate
a local prediction; finite-difference evidence is not proof over a finite edit.
The independent qualification retains every row and column and adds no physical
tolerance. Every proposed correction still requires complete nonlinear checks
against both the latest retained pose and the original benchmark.

Local evidence: `reports/all-violator-surface-model-v1`,
`reports/all-violator-derivative-diagnosis-v1`,
`reports/all-violator-derivative-diagnosis-v2` and
`reports/all-violator-derivative-qualification-v1`. Generated geometry and
machine receipts remain local ignored outputs. The derivative components have
307 passing focused source cases locally and on each hosted operating system.
No release capability or human-review requirement is approved by these checks.

The refreshed global model separately checks all 16 scalar conditions and 33
components of 11 local vector cones against the original full-array reference.
All directional checks pass. These local active motion cones are not a
replacement for screening every original skin vertex and motion interval.

The complete 6,984-row correction model finds all 12 tested variants that
require immediate repair of every scalar condition locally infeasible. This
is an observation about this linearization and parameterization, not proof that
the motion cannot be repaired. The first variant preserving all original and
currently passing conditions produces a candidate direction at a normalized
joint trust radius of 0.0625. The original five-degree/two-centimetre author
bounds remain hard. Evidence: `reports/all-violator-global-model-v1` and
`reports/all-violator-scene-solve-v2`. A proposed direction is not a retained
animation; nonlinear trial results must be considered separately.

The full proposed step then completes all 120 editor frames and all 496
nonlinear scalar conditions. Both the latest-progress guard and the original
benchmark guard retain it. No required condition fails and no previous pass is
lost. The maximum working violation decreases from 5.442634123054033 to
5.281024133534155, and physical failures decrease from 41 to 40. This is a
partial improvement: body overlap and the own-palm orientation failure remain.
Evidence: `reports/all-violator-scene-validation-v1`.

The new result is a retained raw logical-control diagnostic. Export and
independent native/saved-clock replay of this particular step remain
outstanding; it has not replaced the previous exported diagnostic, the
qualified partial reference, or the Studio preview selection. The whole-project
goal remains active with every release capability unapproved.
