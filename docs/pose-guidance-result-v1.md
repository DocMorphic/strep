# Pose guidance results and separation objective

A fresh model at the verified 45-choice anchor keeps all **90 controls, 30,450 original native norms, 1,707 native samples and 1,673 geometry times**. All original reference, rate, contact, control and geometry limits remain. It fits the eight hand vertices of each actor to the independently checked relaxed pose at 0.34375 seconds. The second variant adds 18 homogeneous event-key parameter rows; original contact constraints remain hard in both variants.

Both solver statuses are `AlmostSolved`. The unchanged finite-ray check selects strictly passing original affine norm points at fractions **0.9999923706054688** and **0.9999999403953552** of their respective raw proposals. These are feasible affine candidates, without an optimality claim. Fresh decoding gives the following results:

| Guidance | Export fraction | Native failures | Contact failures | Tested-frame depth in mm |
| --- | ---: | ---: | ---: | ---: |
| Original norms | 1 | 10 | 1 | 5.042218 |
| Original norms | 0.5 | 0 | 0 | 4.925456 |
| Original norms | 0.25 | 0 | 0 | 4.864665 |
| Original norms | 0.125 | 1 | 0 | 4.833671 |
| Event key preserved | 1 | 10 | 0 | 5.001536 |
| Event key preserved | 0.5 | 2 | 0 | 4.903235 |
| Event key preserved | 0.25 | 4 | 0 | 4.853089 |
| Event key preserved | 0.125 | 3 | 0 | 4.827768 |

Original reference bounds and represented control/trust bounds pass throughout. Pose-target squared error decreases for every export, but hand penetration at the tested frame increases from the anchor's **4.802282 mm**. Event-key preservation keeps the measured contact passing in these four trials; it does not establish a general contact guarantee or clear the stored-motion failures.

Among the two motion-feasible exports, the quarter step has lower tested-frame depth and receives the full geometry scan. Its maximum measured depth is **4.876273318 mm**, with **30,329 triangle records and 1,603 failed geometry conditions**, compared with anchor depth **4.802282354 mm**, 30,431 records and 1,608 failed conditions. The existing depth-first ranking rejects it despite fewer intersections. Full geometry is assessed only for this declared selection, not every export. Originals remain selected and every candidate is unapproved.

The first geometry scan stopped at sample 100 because the private progress callback supplied `status` twice. The failed run and partial archive remain immutable. A separately typed completion reuses the exact model, solves and eight exports, and repeats only the interrupted geometry scan in fresh output. The complete independent consumer reconstructs all 180 native stencils, all 90 native/point derivative columns, event parameter rows, strict ray prefixes, every exported payload/world/residual/reference bound and peak query. It verifies full geometry archive transport using shared geometric predicates. An earlier consumer's final squared-error check exposed the last-bit difference between column-major and row-major matrix evaluation; the corrected consumer explicitly restores the producer's contiguous layout and retains exact comparisons. Neither failed consumer nor failed producer is converted into a passing receipt.

`scripts/native_norm_hinge_guided_step.py` is a separate proposal method for this measured objective mismatch. It minimizes the squared negative part of explicit guide residuals using nonnegative slack, so already satisfied clearance rows are not pulled toward equality. Every original native norm stays hard; exact-zero fixed rows alone may be omitted from the solver and all rows are checked by the unchanged strict ray validator. Optional key-parameter rows and actual exported contact gates retain their existing semantics. A strictly improved guide deficit is required, but it is not collision or animation approval.

**75 local tests pass, zero skips**: 15 new one-sided guidance tests and the existing 60 guidance, ray and key-support tests. They exercise hard unreachable targets, complete coupled native rows, preserved parameter equations, satisfied-guide refusal and malformed/failed solver input. The new suite is registered in the Linux/Windows source workflow; hosted success remains unverified. A 64-pair clearance comparison is prepared from the independently replayed cached points, with no new world evaluations or changed original norm model. Its solves and actual exports remain pending.

This is a generated cube-skin fixture. It does not establish production-rig behavior, arbitrary action semantics, continuous collision, physical validity, engine playback or human cleanup quality. All fourteen release evidence arrays remain empty; the full-project goal remains active.

Ignored immutable result SHA256 values:

- completed pose-guidance study: `2d19258244a0695e2ab7bf73ef8958b32a3d91e05b76130864913b837046fd86`
- complete independent replay: `54bf7190ccaaf6e73b8e9061f575d92f8529ca5b576bdbbb0e225648d30884dd`
