# Bounded affine surface restoration

The [existing production phase selector](native-depth-phase-selection-v1.md) rejects invalid later solver points. This separate helper measures a strictly feasible segment toward a surface solution, without changing production phase selection or decoded acceptance. It is local guidance, not a motion or geometry certificate.

## API and checks

`scripts/native_affine_surface_restore.py` accepts complete original norm and scalar-surface populations, their Jacobians, original depth witness indices, verified origin and target deltas, and the intersection of authored/trust/certificate delta boxes. Pass finite Python scalar bounds and a positive scale. The caller must bind complete populations and original limits; this helper cannot discover an omitted witness or authenticate a source model.

Every finite trial evaluates all provided native three-vector norms strictly at zero tolerance, original depth priority and the delta box. Along this segment their sublevel intersection containing the origin is convex; a finite bisection measures feasible points. Default budget is 32 iterations, maximum 64. It measures the full scalar surface objective, retains the origin when no measured improvement exists, and rejects a non-feasible origin. No cap, scale, source or input is mutated. This is neither a global optimum nor an exhaustive feasibility proof. The production selector is unchanged.

Seventeen focused CPU tests pass in 0.74 seconds, zero skips. They cover curved full-vector norms, late norm/surface rows, depth priority, feasible targets, fixed-boundary/no-improvement behavior, malformed inputs and iteration budgets. CI adds this suite; hosted success is not claimed.

## Full saved-model experiment

The [preceding complete partner study](partner-depth-crossing-study-v3.md) and its independent sixty-column replay remain immutable. Conic-only capture reproduces both phase points using unchanged producer code. The failed first private driver passes a NumPy scalar to the explicit scalar contract; its failure, code and inputs are retained. A fresh retry converts that value to Python float without modifying the helper. No motion or geometry runs in the failed attempt.

All 29870 native norms, 276815 scalar surfaces, 2873 witnesses, original references, rate arrays, contact targets, limits and clocks remain. The bounded search selects fraction **0.9999996377155185** toward the surface point, reducing affine surface excess **2.4788154716763904 → 2.332382585965304**. Measured affine native excess is approximately **-4.574e-13**, depth deficit zero. The original depth bound includes the prior 1e-9 phase lock; native checking introduces no tolerance.

Every requested actual export gets all 1707 native and 1673 geometry samples:

| Fraction | Stored failures | Centered failures | Contact failures | Depth, mm | Triangle records | Contained vertices | Failed geometry samples |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1.0 | 10 | 6 | 0 | 5.005961 | 30390 | 2 | 1611 |
| 0.5 | 0 | 0 | 0 | 5.001430 | 30408 | 2 | 1606 |
| 0.25 | 3 | 0 | 0 | 5.000413 | 30445 | 5 | 1605 |
| 0.125 | 6 | 0 | 0 | 5.000606 | 30438 | 6 | 1603 |

All original reference bounds pass. Every geometry fails. Compared with the preceding depth direction, the full step reduces triangle records from 30454 to 30390 but exceeds the depth limit, contains two vertices and fails actual native motion. Its unrounded centered motion has six failures, showing that Float32 storage is not the sole problem. The half step passes native/contact checks but exceeds five-millimetre depth and retains crossings. The preceding native-feasible depth-passing candidate remains intact and no new candidate replaces it.

An independent consumer imports no restoration/job/model/proxy/solver, reconstructs every segment probe and bisection decision from the frozen complete matrices, reproduces the selected direction exactly, and uses the tested public observation API for every stored payload, decoded world and native observation. Original rate arrays and all-native original static/animated reference bounds match. Saved geometry transport is verified; collision predicates and producer auxiliary centered observations are not independently replayed.

Next measure tightened local depth guidance and nonlinear/geometry checks under unchanged external acceptance. This separates the numerical phase issue from nonlinear model error and persistent crossing constraints. These generated cube-skin fixtures provide no production humanoid, broad-action, engine, physical or human-cleanup release evidence. All fourteen release evidence arrays remain empty.

Immutable ignored local receipt SHA256 identities:

- capture: `fe3fa40522122d42c7510a41d0e88dc50425df28da2699b52801cabad0c0a938`.
- study: `46f9ba0368b2ddff4977e856008df70ed089b83081618f80873524ce2f352e5c`.
- replay: `54007e5b3885cf6ca5b7b5a88af8e7256641e416a4383548f4080e5c50b1f507`.
- tests: `64d70ca5f4ae20a805ba0aa1e51f3525c37345ed0c952e3d6610ee13c0e349c9`.
- failed_driver: `2a2a05c599fe74901c6465a76b36c6f44a7b7a919bd47c72b18f8c2ace12d0a0`.
