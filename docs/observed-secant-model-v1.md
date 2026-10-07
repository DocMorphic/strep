# A measured export response as an additional proposal constraint

The [preceding export comparison](grouped-continuation-comparison-v1.md) showed actual stored motion failing despite passing local predictions. This experiment tests whether one measured response can guide the next proposal. It does not alter motion tolerances, change the anchor, repair storage, or select a clip.

`scripts/native_observed_secant_model.py` appends a complete sampled secant model alongside the complete original affine native model. For anchor vectors `v`, original Jacobian `J`, observed control step `d` and observed exported vectors `w`, the additional Jacobian is:

```text
E = w - (v + J d)
J_sample = J + E d^T / (d^T d)
```

Both models start at the same original vectors and use exact copies of the original caps and scales. Original rows come first and remain hard; a sampled guide can add restrictions, never replace those rows. Every sample vector participates, including passing rows. The builder rejects changed populations/caps/scales, degenerate or excessive steps, failed original anchors and resource overflows. It preserves all dependencies rather than dropping rows to fit a budget.

This is a rank-one empirical proposal guide. It is not a derivative of discrete storage choices, a nonlinear error enclosure, or evidence of generalization. It can reproduce one observed endpoint within an explicit arithmetic allowance; that allowance applies only to checking the reconstruction, not to accepting motion. Directions orthogonal to the observed step receive no empirical correction. Callers must authenticate row identities, clocks and source jobs; matching arrays alone cannot establish that provenance.

## Complete fixture comparison

The already replayed event-preserving half export provides the response sample. Its three failing rows are actor B nodes 6/7/8 angular acceleration at 0.45 seconds. All 30,450 original norms and 90 columns remain present, followed by 30,450 sampled-guide norms. The resulting Jacobian has 1,389,025 nonzero entries; its complete dense-dependency budget is 16,443,000 entries. Endpoint maximum component error is approximately `8.882e-16`, below the reconstruction allowance of approximately `1.800e-12`.

Three fresh 230-variable grouped conic problems keep the existing 1,274 material rows, 140 complete triangle groups, 2,628 positive-separation guards, control/trust limits and starting containment ceiling. The original fresh nine-frame model's 180 stencils are reused at the same unchanged anchor; no new derivative stencils are taken. Each new proposal is exported at fractions 1, 1/2, 1/4 and 1/8 under the original 53 absolute storage choices.

| Variant | Solver status | Stored-motion failures at 1, 1/2, 1/4, 1/8 | Previous comparison |
| --- | --- | --- | --- |
| Original parameterization plus sampled guide | AlmostSolved | 14 / 4 / 2 / 5 | 17 / 2 / 0 / 1 |
| Event-preserving plus sampled guide | AlmostSolved | 10 / 2 / 3 / 0 | 16 / 3 / 0 / 12 |
| Uniform increment plus sampled guide | Solved | 2 / 0 / 0 / 0 | 4 / 0 / 0 / 0 |

Four of twelve exports pass complete original decoded motion, versus five previously. All four also pass actual separation guards. Original and event full steps fail 34 and 21 actual guards despite passing represented guards; original and uniform full steps fail the point contact. Centered continuous-proxy full-step failures are 13/4/1. Every export passes the original reference and control/trust checks. The sampled guide reduces some failure counts but introduces others, and smaller steps remain nonmonotonic.

The existing depth-first rule among changed motion/reference/trust/actual-guard passing outputs selects the event-preserving eighth step. Its complete 1,673-sample scene audit records approximately 4.688772867 mm maximum partner vertex depth, 29,715 proper crossings, zero over-limit vertices and 1,578 failed samples. The preceding event quarter was better at 4.686034583 mm, 29,702 crossings and 1,577 failed samples. Both fail the original geometry gate. The older depth-focused branch remains lower in depth. This empirical guide is an experimental primitive, not a preferred correction policy or a demonstrated quality improvement.

The separate original-context reader decodes the response sample, reconstructs every original and sampled model row, checks the endpoint arithmetic, then reconstructs all three conic systems and strict ray prefixes without calling the empirical producer API. It replays all twelve actual exports, original motion/contact/reference checks, complete nine-frame mesh queries and selection. The full-scene archive uses shared collision predicates; its transport verification is not independent collision arithmetic, continuous collision certification, or an optimum claim.

Validation includes 39 focused tests across the new builder and existing grouped solver. Tests demonstrate both models retaining hard caps, new dependencies for previously fixed rows, unsupported orthogonal directions, complete resource rejection and input immutability. The new tests are registered in the source workflow; hosted CI success is unverified.

Next investigate bounded storage responses at the failing clocks and differences between raw intended motion, centered proxies and actual exported curves. Repeating a single sampled correction as though it enclosed storage/nonlinear error is unsupported by these results. Keep original native-key clocks, limits and complete scene gates intact.

Raw studies and readers remain in ignored `reports/`. Original assets remain selected, all fourteen release evidence arrays remain empty, and the project goal stays active. No neural-model, production anatomy, arbitrary-action semantics, engine, animator-review, cleanup-time or release approval follows from this fixture.
