# Actual foot acceleration pilot

The project-wide goal remains active. This is a development correction, not a separate goal or a release approval.

The held-support experiment improves planted-foot drift but snaps some feet back toward their raw swing reference. The three completed cases contain31 releases and11 acceleration regressions. Backpedal rig01 right release19 has a6.84mm residual horizontal offset and peak acceleration7.45m/s² against3.47raw and3.17original whole-support prior. Root-correction curvature alone does not constrain the actual skin's foot acceleration.

## Fixed experiment

`reports/support-acceleration-v1/request.json` freezes one150-frame backpedal rig01 pilot, six sweeps, weight1, and the original raw/prior baselines. It waits for the exact held-support study owner to finish before fitting. No weight search, extra sweeps, inference or training is included. The raw input, original whole-support prior, held-support attempt and all failures remain retained.

The new residual is `max(norm((p[t-1]-2p[t]+p[t+1])*fps²)-cap[t],0)`. Positions are actual3D skinned foot-region centroids. Each cap is the larger raw/original-prior acceleration at that same frame and foot, plus1e-5m/s². The weight1 is an experimental residual scale, not a physical limit. The penalty is soft; it may fail and may trade support accuracy for smoothness. It is evaluated across every interior frame, including the entire swing and clip boundaries with a valid three-frame stencil.

Each coordinate update includes all affected centers f-1,f,f+1. Analytic gradients pass through the skinning Jacobian. The fitter reuses the surface evaluation from its support objective and explicitly updates its centroid cache after each accepted frame. A rejected optimizer trial cannot become the neighboring-frame cache. Root curvature10, support40, six sweeps, zero-edit initialization, original pose/root limits and the existing export remain unchanged.

## Evidence before launch

- Eight unit tests pass: finite-difference gradients at both ends and interior frames; equality of coordinate energy changes to full-track energy changes; a synthetic8mm release snap; baseline caps; inactive/zero-weight behavior; invalid input rejection.
- Actual skinned-rig proof at frames0,18,19,20,149 with three random directions each: maximum derivative discrepancy4.03e-6. Accepted-frame cache agrees with fresh skin within1e-12m. Retained in `reports/support-acceleration-skin-proof-v1.json`.
- New implementation files are separate from all live/frozen prior studies.

## Required outcome checks

The runner retains decoded limits and preservation, full and half-frame floor depth, support max/p95 and hover, root dynamics, local rotation steps, every release and global foot acceleration. It imports input/prior/candidate in Godot for450 actor-frames. Full centroid tracks and fixed per-frame caps allow every-frame excess to be checked; release-only improvement is insufficient. Compare with the original raw/prior screen and additionally report whether the held-support release defect improved. Keep all failures. No naturalness, anatomy, semantic correctness, self-collision or animator approval follows from these numerical checks.

Pilot owner: PID34756, created1790564579.9352717, exec57594. The request-bound implementations are frozen while queued or running.

## Full-track baseline diagnostic

`reports/support-acceleration-baseline-v1.json` retains every violating foot/frame against the frozen per-frame raw/prior cap across three completed cases:248 centers,181 outside the existing short release windows. This is a stricter per-frame diagnostic than the old window-maximum screen, not181 new proven physical defects. It supports measuring the whole clip rather than only the first three swing frames.


## Completed pilot: lower acceleration excess, worse clearance

The frozen one-case backpedal rig01 pilot completed six sweeps and450 actual Godot actor-frames. Exec57594 returned0 and was consumed. Solver clipping warnings remain in the record. All original inputs and fixed settings were retained; no extra iterations or weight tuning followed.

`reports/support-acceleration-final-v1` independently recomputes the frozen decision and verifies the450 engine poses. Its additional decoded audit freshly samples all600 integer poses and596 half-frame skins across raw motion, original whole-support prior, held-support trial and the new candidate. Full foot-centroid acceleration tracks match the retained evidence, and the per-frame caps match the frozen max(raw,original prior)+1e-5m/s² definition.

| Measure | Raw | Original prior | Held support | Acceleration objective |
| --- | ---: | ---: | ---: | ---: |
| Floor depth incl. half-frames (mm) |65.256|2.348|2.349|57.559|
| Root acceleration peak (m/s²) |4.637|4.510|4.479|13.074|
| Left support speed max (m/s) |0.11997|0.07550|0.07426|0.15770|
| Right support speed max (m/s) |0.11739|0.10368|0.06036|0.11590|
| Right release19 acceleration (m/s²) |3.469|3.174|7.446|3.554|

Relative to held support, squared positive acceleration-cap excess falls225.428→1.232 and maximum excess falls8.086→0.191m/s². The number of exceeding foot/frame entries rises86→202: much smaller errors are spread over more frames. Count alone would obscure the magnitude improvement; the reduced objective alone would obscure the serious floor/root regressions.

The candidate fails11 frozen checks, including support-speed tails,9 of11 release comparisons, floor, root acceleration and local rotation steps. Hard edit bounds pass. This is0/1 development-screen passes and no release approval. The targeted release19 spike improves against held support but still exceeds the original raw/prior cap. No weights or acceptance tolerances were changed afterward.

The next correction should protect whole-mesh clearance and root dynamics explicitly while reducing acceleration error. This result does not justify adding this soft penalty as a product default, extending its sweep budget, or treating one objective reduction as physical realism. Source semantics and independent animator review remain unresolved.
