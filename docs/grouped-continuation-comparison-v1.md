# Actual stored motion after a fresh grouped correction

The [fresh continuation model](grouped-continuation-model-v1.md) now has an actual correction comparison. It keeps the original 90 controls, 30,450 vector norms, 1,707 native samples, 1,673 geometry samples, source/reference limits and 53 absolute storage choices. Its nine guide times cover all eight preceding times plus the shifted full-scene depth peak. The 1,274 material rows, 140 complete crossing groups and 2,628 guards are reused only at this already replayed same pose; zero new derivative stencils are taken during this solve comparison.

All three new conic problems have 230 variables. Every original native norm, control/trust limit, starting represented containment-depth ceiling, and complete positive-separation guard remains hard. Optional event or uniform-increment equations define the same comparison variants as before. The grouped deficit sum improves in each proposal, but it is neither crossing count nor collision approval. Solver status is retained exactly; `AlmostSolved` does not mean a verified optimum.

| Variant | Grouped sum before / after, m | Solver status | Stored-motion failures at fractions 1, 1/2, 1/4, 1/8 |
| --- | --- | --- | --- |
| Original norms | 0.414097803 / 0.402304352 | Solved | 17 / 2 / 0 / 1 |
| Event-preserving | 0.414097803 / 0.402320944 | AlmostSolved | 16 / 3 / 0 / 12 |
| Uniform increment | 0.414097803 / 0.413570597 | Solved | 4 / 0 / 0 / 0 |

All twelve fractions pass the represented affine guards and original reference/control/trust bounds, and differ from the authenticated anchor bytes. Actual mesh guards fail only the original and event full steps, at 30 and 22 rows. The original and uniform full steps also fail the point contact. Five exports pass complete original scalar/vector motion; each of those passes actual guards. Smaller fractions are not monotonically better: the event quarter passes, while its eighth fails twelve stored angular-acceleration rows.

The unchanged depth-first rule among changed motion/reference/trust/actual-guard passing exports selects the event-preserving quarter step. Its complete scene audit has 4.686034583 mm maximum partner vertex depth, zero over-limit vertices, 29,702 proper crossing records and 1,577 failed samples. The previous internal anchor had 4.691474461 mm, 29,757 crossings and 1,580 failed samples. This modest improvement still fails the original collision gate. The earlier depth-focused result remains lower in depth at 4.483570315 mm, with more crossings at 29,937; no dominance, optimum or quality claim follows.

The separate original-context reader authenticates reuse of the preceding full native/material/skin/guard replay and its 8,208 exact rational affine coordinate enclosures. It reconstructs all 140 nine-corner groups and all three complete conic systems, the 18 event and 72 uniform equations, every strict 81-fraction grouped/native/depth/guard prefix, and all twelve stored exports. Every complete native observation, source rate, contact, static/reference bound, actual guard row and nine-frame geometry query reproduces. The selected full-scene archive is transport-verified using shared predicates. This is not independent collision arithmetic, nonlinear enclosure, continuous collision, or solver optimality.

## Which motion bounds reject the larger steps

A saved-vector diagnostic now maps every failed stored norm to its original section and clock. It authenticates all original cap/scale arrays, every joint's source order, and the actual editable native-key population. It reads the existing vectors and the same-point Jacobian; it takes no new pose, native-derivative or geometry observation.

| Variant and fraction | Failed stored sections | Centered continuous proxy failures |
| --- | --- | ---: |
| Original full | 12 angular acceleration, 1 angular speed, 3 linear acceleration, 1 contact | 13 |
| Original half | 2 angular acceleration | 0 |
| Original eighth | 1 angular acceleration | 0 |
| Event full | 13 angular acceleration, 2 angular speed, 1 linear acceleration | 10 |
| Event half | 3 angular acceleration | 0 |
| Event eighth | 12 angular acceleration | 0 |
| Uniform full | 3 angular acceleration, 1 contact | 1 |

The three event-half failures are actor B nodes 6, 7 and 8 at the 0.45 s acceleration sample. Stored norms exceed their original approximately 7.740507924 caps by 0.000042054, 0.000100274 and 0.000068963, while their represented affine and centered continuous-proxy rows pass. At other clocks, near-static angular-acceleration caps are approximately 0.001025851 and stored failure behavior differs again. Complete offending row identities, vectors, caps, scales, affine defects and proxy residuals remain in the raw report.

This diagnostic distinguishes failed actual storage from passing local predictions; it does not isolate pure quaternion rounding from every nonlinear/export effect. The full-step continuous proxies themselves have 13, 10 and 1 failures. Therefore a change to storage choices alone cannot be assumed to fix the larger proposals. Neither the local objective nor strict affine pass justifies selecting them.

The first diagnostic incorrectly counted control-vector norm rows by five edit knots. The original norm contract checks every editable native key: 290 per track, yielding 870 control-vector rows per actor. Comparing the reconstructed cap array against the original archive caught that mismatch before any diagnostic result was emitted. The corrected mapping uses the source-bound boundary editor's actual key indices and exactly matches all protected cap/scale arrays, with 29,062 protected norm rows. The failed metadata-only driver, failure report and corrected version remain separate and immutable. Solver code and recorded exports were unaffected.

Next address actual post-export motion defects alongside nonlinear constraint response, under the same original acceptance limits. A separately declared experiment may test an observed-vector proposal correction or bounded storage alternatives, but those are approximate guides until every original decoded condition and full scene gate is rechecked. This comparison performs neither a storage repair nor another internal-anchor promotion.

Raw studies, diagnostics and readers stay in ignored `reports/`. Existing public source APIs and dependencies are unchanged; validation is the complete separate replay and publication data/hash checks. Original assets stay selected, all fourteen release evidence arrays remain empty, and the full-project goal remains active. This fixture does not approve arbitrary-action semantics, production anatomy, broad rigs/objects/partners, engine behavior, animator ratings or cleanup time. Hosted CI success is unverified.
