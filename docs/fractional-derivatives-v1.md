# Faster fractional-frame contact derivatives



The current partner experiment evaluates 30 fitting times, including the missed half-frame collision witnesses. Its original derivative code perturbs each active control coordinate and recomputes the whole interpolated skeleton twice. The separate `BatchedFractionalActor` adapter instead batches those perturbations at the affected local joint, then propagates the matrix product rule through the skeleton hierarchy. A control coordinate affects one edited local joint at both adjacent animation keys.



The local-rotation interpolation, float32 glTF time convention and 1e-6 finite-difference step remain unchanged. These are batched **local finite differences**, not a claim of an analytic SLERP derivative. The existing analytic integer-frame path is retained. Controls, basis, geometry, bounds and quality thresholds are not altered.



`reports/batched-fractional-skin-v1` compares the new route against the unchanged whole-skeleton finite differences on both actors, the original initializer and a fixed small perturbation, 19 times and 96 vertices per actor. The samples include the collision witnesses, quarter frames, integer frames and the editable envelope boundaries. All **76 comparisons** pass: maximum position difference 4.4409e-16 m and derivative-element difference 4.1486e-10. The request, source inputs, implementation copies and result hashes are retained.



Across active fractional samples, the median measured speed ratio is **6.86×** over three cold-cache repetitions on this busy laptop. Some zero-influence cases are slower. This is local point/Jacobian timing; it does not measure the full solver, geometry queries or SLSQP work. The current enriched trial already has 5,272 active surface rows at its initializer, and the remaining optimization costs may dominate.



`BatchedBoundedPathFitter` provides an opt-in adapter for a subsequent controlled experiment. No running solver was changed or restarted, no candidate was generated with it yet, and no collision or motion-quality improvement is claimed. Its actual fitting/export/full-geometry behavior still needs validation before adoption.



## Larger and actual constraint workloads



`reports/batched-fractional-dense-v1` sizes uniformly sampled vertex batches from the retained collision witnesses. All 24 comparisons match (position error zero; maximum derivative error 3.744e-10). Median speed ratios fall from 6.81× at 96 vertices to 1.31× at 3,753 vertices. These are representative batch sizes, not the actual triangle correspondences.



`reports/surface-constraint-profile-v1` reconstructs and freezes the actual largest per-direction fractional witness at frame 65.5. All 2,230 coupled constraints and their 120-column Jacobians match at the initializer and a fixed perturbation (zero value error; maximum derivative error 3.412e-10). Its measured ratios are 1.00× and 1.40×. Thus the small-batch result substantially overstates the gain for this workload. Geometry construction itself took 20.02 seconds and is not accelerated by this derivative change.



The retained triangle requests contain many repeated vertices: 3,753 requests use 867 unique vertices in one direction, and 2,937 use 878 in the other. The separate `UniqueFractionalActor` adapter skins unique indices and restores their original order. `reports/unique-surface-profile-v1` reuses the hashed correspondences, comparing all three routes with five cold-cache repetitions. Ten explicit repeated/unsorted-index checks across both actors, integer and fractional frames pass. Coupled values remain identical and maximum Jacobian difference remains 3.412e-10. Measured speed is 2.55× and 2.99× over the original route, about 2.00× over batching alone.



All timing was collected on the busy local machine and applies only to these evaluations. The opt-in `UniqueBoundedPathFitter` has not been used by the running solver, and neither full optimization behavior nor export/geometry quality has been established for it. A subsequent frozen controlled trial is required before adoption.


The next [direct surface-distance implementation](projected-surface-v1.md) removes full per-vertex Jacobian materialization for frozen fractional constraints. Its actual 2,230-row batch agrees numerically and measures 23.29-32.28x over the original route. Full-clock verification has completed 120 comparisons across all 5,272 rows and 30 fitting times, with about 9x improvement in summed median evaluation timings. Correspondence construction still takes about ten minutes. The serialized matched fitting/export comparison remains pending; no whole-solver gain or quality improvement is established.
