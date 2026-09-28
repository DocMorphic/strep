# Knee surface support feasibility

The existing body-clearance pass removes sampled floor penetration but creates knee gap or sliding warnings in seven of eight ending-guided clips. This experiment tests whether explicit knee and foot mesh targets can satisfy the existing contact and floor screens within the existing pose edit bounds.

One pose per source clip is selected by the maximum knee-gap increase among the previous low/slow geometric support candidates. All eight clips are retained, including the unflagged case. Two pairs have byte-identical reference world transforms: there are six exactly distinct reference poses, not eight independent pose examples.

Targets use the existing knee-region definition: shin-dominated skin within 13 cm of the bind knee joint. Patches include vertices within 1 cm of the local surface minimum. The original patch-centroid XZ is retained, with an explicit Y target of 1.5 mm. Low/slow foot regions are included. These are geometric drafts rather than confirmed weight-bearing annotations.

The first probe uses the unchanged authored-contact objective and pose bounds. `AnalyticPatchFitter` supplies its derivative using the existing skin Jacobian. Two tests match the legacy residual and independent finite differences. Only one of eight cases passes the existing pose screen: the weighted objective trades contact error against residual floor penetration.

The second probe adds inequalities for every skin vertex and each declared patch-centroid error. It keeps the same objective, target patches and pose bounds, starts from the retained soft fit and allows 120 SLSQP iterations. A 10 micrometre interior numerical margin tightens the constraints; the acceptance screens remain 5 mm floor penetration and 20 mm contact error. Two derivative/margin tests pass.

All eight constrained cases pass those existing pose screens. Independent evaluation decodes the exported GLBs, checks whole-surface floor depth, patch targets, actual root and joint edits, unchanged local offsets and unedited rotations. Both sets of eight two-frame static exports pass Godot import, totaling 32 actor-frames. Engine validation does not establish motion quality.

Artifacts: `reports/knee-patch-feasibility-v1`, `reports/knee-patch-constrained-v1`, and `reports/knee-patch-comparison-v1`. Full source hashes, source poses, specs, solver parameters, implementation snapshots, failed soft candidates and engine proofs are retained. Source motions are untouched. These solvers are experimental and are not promoted to the Studio default.

This establishes isolated-pose feasibility only. Each export repeats one pose twice; no animation continuity, neighboring-frame feasibility, dynamics, balance or human quality approval is established. Next, test the same targets with neighboring motion and hard temporal bounds before attempting full-clip correction. The project-wide release goal remains active.
