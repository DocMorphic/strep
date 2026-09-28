# Individually guarded release correction

The protected-joint interpolation experiment improved aggregate acceleration error by moving errors between releases. This trial instead constrains every affected foot-acceleration sample against a fixed envelope. All envelopes are frozen before optimization; they cannot expand as iterations proceed.

The pilot starts from the original held-support correction on the backpedal/check development clip, rig01. It retains the held root and joint9 correction tracks exactly. Three additional alternating coordinate sweeps use SLSQP with at most80 iterations per frame. This is a new development method and extra compute, not an equal-budget or held-out comparison.

For each foot and interior frame, the acceleration envelope is the greater of the original raw/prior cap and the held acceleration magnitude. This retains previously failing values as feasibility bounds; it does not declare them acceptable. The objective remains squared excess above the original raw/prior cap. Every original support step is constrained by its held horizontal speed; integer-frame mesh clearance, support hover and adjacent/absolute edit limits are constrained too. A proposed step must also preserve the held decoded local-rotation peak. Root and joint9 are removed from the variables, not softly penalized. Each proposal has eight fixed safeguard fractions. The serialized output still receives the unchanged full development comparison and half-frame clearance checks.

`tests/test_guarded_release_fit.py` covers acceleration-center indexing, both support-neighbor signs, contact masks, analytic derivatives, and reduction of a known synthetic spike while preserving eliminated tracks. Together with existing acceleration tests,11 tests pass. The synthetic test checks descent rather than claiming convergence in two sweeps. Before fitting,15 actual skin directional checks at five frames pass with maximum normalized derivative error1.384e-6. The derivative proof and implementation are frozen in `reports/guarded-release-v1`.

## Completed result

The trial completed all450 coordinate visits, then independently verified450 Godot actor-frames for raw, held and candidate. Solver statuses remain visible:399 successful exits,44 line-search failures,7 iteration limits;426 proposed updates were accepted by the separate feasibility/descent checks. SLSQP's bound-clipping warning is retained in execution output. Last-sweep parameter change0.06354 means convergence is not established.

| Measure | Held correction | Guarded correction |
| --- | ---: | ---: |
| Unserialized acceleration excess energy |225.4283|101.6975|
| Full/half-frame floor peak (mm) |2.349|4.473|
| Root acceleration peak (m/s²) |4.478535|4.478535|
| Local rotation peak (degrees/frame) |19.959219|19.959219|
| Left support speed max (m/s) |0.074265|0.074265|
| Right support speed max (m/s) |0.060363|0.056947|
| Failed release windows |3|1|

Right releases86 and109 now pass the original limits. No previously passing release becomes a failure. Right release19 improves from7.445875 to3.561474m/s² but still exceeds its3.468900 limit by0.092574m/s². Right global foot acceleration also fails:32.648565 versus the original allowed prior maximum32.633412, before its unchanged1e-5 comparison tolerance. The new maximum occurs at frame31. All other original full development checks pass. The result remains rejected, not promoted to the Studio default.

## Serialized envelope discrepancy

Fresh independent decoding in `reports/guarded-release-audit-v1.json` verifies300 integer poses and298 half-frame skins, retained root/joint tracks, all11 release windows and engine bindings. It also finds two additional failures against the newly declared frozen envelopes: maximum acceleration excess0.000237629m/s² at left acceleration center129, and support-speed excess0.000005278m/s at the left step ending118. These exceed the audit's unchanged serialization tolerances of1e-4m/s² and1e-6m/s respectively. Hover, protected joint, root, floor, rotation and absence of new release failures pass.

`reports/guarded-release-roundtrip-v1.json` reconstructs every optimized pose from retained parameters and compares its actual skinned centroids to fresh GLB decoding. Before serialization, acceleration-envelope excess is only1.63e-8m/s² and support-speed excess1.05e-9m/s. Export changes a centroid coordinate by at most1.272e-7m; finite differences amplify those small errors into the measured envelope violations. The mechanism is numerical export/sample precision, not an engine import mismatch. The original recorded failures and tolerances remain unchanged.

The next acceptance step must evaluate the serialized poses or establish and validate a conservative export-error bound. Merely widening tolerances would conceal the discrepancy. The remaining physical-motion development failures—right release19 and global acceleration near frame31—also require correction. This evidence does not establish realism, force balance, support semantics or generalization. Independent animator review and cleanup time remain missing.

The concurrent whole-support population reached10 of24 cases. Its first broad-jump rig improves floor penetration72.983→1.863mm, but increases root acceleration10.983→12.158m/s² and both support-speed maxima. `reports/whole-support-breadth-interim-v10` retains that failure; the original worker continues the other rigs without protocol changes.
