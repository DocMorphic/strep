# Fixed-surface restriction diagnosis on the refined pair

The preceding trust study could not predict meaningful clearance even at five degrees with a much weaker movement penalty. This experiment separates its two local surface restrictions: signed fixed-normal planes and distances to retained barycentric points. It keeps all positional/angular motion rows, empirical margins, edit budgets, native controls and contact-key protections.

This is diagnostic ablation only. The existing animation acceptance policy is unchanged. No omitted condition is silently treated as passing, and no new animation is exported or published.

## Why check the distance bound?

For an inside point, distance to a known target-surface point upper-bounds its nearest-surface penetration depth. That makes it conservative. It can nevertheless reject harmless tangential escape: moving from `(0,0,-0.02)` inside the top face of a box to `(0.03,0,0.005)` outside gives zero penetration but increases distance to the original surface witness beyond 0.02 m. A model-free analytic box test demonstrates this. It does not establish that the same effect dominates the character fixture.

## Matched character comparison

Reference: `trust_5_weaker_penalty` from `reports/scene-pair-refined-trust-v1`. The reference controls reproduce with zero difference. Each solve uses 168 controls, 4,287 surface rows, a five-degree trust radius, scale 0.025 and regularizer 0.000005. Initial source peak is 22.568796 mm.

| Proposal restrictions retained | Predicted peak, mm | Numerical hard-check result |
| --- | ---: | --- |
| Local planes and distances | 22.231453 | Pass |
| Local planes only | 22.125997 | Pass under this diagnostic subset |
| Distances and global peak cap | 22.231453 | Reject: one motion norm fails |
| Global peak cap only | 21.991187 | Reject: one motion norm fails |

The plane-only proposal violates **134 original surface-distance rows**, with maximum distance-cap excess **14.425601 mm**. It does not pass the original acceptance policy. Omitting planes while retaining distance cones changes the prediction negligibly. The two rejected solves report `Solved`, but their norm excesses (2.240267e-6 and 3.367090e-6) exceed an unchanged comparison tolerance. Their numerical predictions are not usable proposals.

Thus, the fixed-distance restriction is conservative but does not alone explain the roughly 22 mm residual in this local model. Even the most relaxed surface subset's numerical prediction remains far above the 5 mm screen. This does not prove nonlinear infeasibility or justify loosening actual mesh penetration limits. The next comparison should isolate source-relative motion restrictions on the refined system and assess whether a regenerated approach path is needed.

## Reproduction and scope

```powershell
.venv/Scripts/python.exe scripts/study_refined_surface_limits.py reports/scene-pair-refined-trust-v1 reports/scene-pair-refined-surfaces-v1 --variant trust_5_weaker_penalty
```

The worker is complete. Parent request/results, matrices, margins, controls and implementation snapshots are bound and preserved. All four diagnostic variants report original-condition violations where a valid numerical proposal exists. Twenty-four focused tests pass, including retained motion-row identity, unchanged edit budgets/tolerances, explicit surface selection and the box counterexample. The prior commit `aa40037` passed [Windows/Linux source checks](https://github.com/DocMorphic/strep/actions/runs/36712711928); those checks predate this diagnostic. All release capabilities remain unapproved.
