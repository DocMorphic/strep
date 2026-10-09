# Geometry-aware descent for guarded pose repair

`guarded_pose_restoration.py --proposal nonlinear --proposal-start geometry-descent` starts from complete vector-distance constraints and a direction that lowers the first-order squared violation. The existing `zero` and `linear-feasible` modes remain available. This remains a diagnostic native pose repair, not animation generation or release approval.

## Method

The native builder differentiates complete three-dimensional contact offsets, surface normal chords and all joint positions. It retains every raw/limb/previous reference and available fixed neighbor. It adds the exact control-space rotation vectors and maps each vector back to the original scalar row. Per-row minima of vector slacks must reproduce the complete current scalar values. Fixture tests check values, derivative parity, population multiplicity and finite directional differences.

Each vector is `o + D delta`. A distance row `(r - norm)/scale >= cap` becomes a ball with radius `r - scale*cap`; a squared-distance row `1 - norm²/r² >= cap` becomes a ball with radius `r*sqrt(1-cap)`. Existing complete scalar proposal caps and trust/global bounds also remain present. No final threshold is relaxed.

The initializer minimizes `g dot delta`, where `g = 2 Jᵀ min(s,0)` is the complete squared-violation gradient. Supporting-plane LPs approximate the convex vector-norm balls. At each candidate, every vector ball is replayed; up to 32 violated balls supply new supporting planes. The initializer stops after at most 64 LP iterations or 20 seconds/remaining local budget. LP feasibility alone is insufficient: original linear bounds/caps, all vector balls and a negative directional merit are required, with search-only tolerance `1e-8`. All coefficients, vector populations, supporting planes, statuses and directions are archived. Recorded derivatives and vector-affine feasibility are not independent full-derivative or nonlinear certificates.

For this mode, a checked start is tested at eight backoff fractions before the expensive nonlinear inner solve. Only complete original nonlinear retention plus exact recorded tangent protection can replace the current point. Passing rows stay feasible, failed nontradeoff rows cannot worsen, and declared merit tradeoffs must lower total squared violation without increasing the largest violation. If the initial backoffs fail, the existing nonlinear proposal solver may refine the start. Its reported success or failure never decides retention. Budget expiry retains the last accepted point, never a last query or unchecked start.

## Validation

A fresh no-vendor source copy passes 214 focused tests across 11 modules; 110 also pass without Torch. They cover transverse distance curvature, checked initial adoption before inner search, both accepted/rejected budget-expiry cases, changed vector populations, three-reference/neighbor multiplicity and derivatives, default solver regression behavior and immutable resume provenance. CI inventory remains 405 Python modules and 39 Node suites; focused coverage is not a complete hosted-CI or release claim.

## Native studies

The source remains the unchanged V17 box-lift study, frame 98, with original point/normal/floor/position/speed/rotation/root limits, trust `.03`, 30 outer steps, 50 nonlinear inner iterations and 300-second local budget. The original raw, limb and previous reference motions stay immutable.

- V11's dense vector-constrained initializer reached its 20-second search guard without a checked start. The supervisor exited 0 after 50.953 seconds, peak tree RSS 695,902,208 bytes. Two saved native pose records remain failed. Its method is retained in the local archive; it is the comparison for the supporting-plane implementation.
- V12's worker was terminated by its unchanged available-RAM guard at 567,709,696 bytes available (below 600 MiB), before preflight or any pose record. Exit code 15 and partial files are preserved. That interruption supplies no motion-infeasibility evidence. No unrelated process was stopped. After the worker exited, available RAM recovered and checks completed before another native run.
- Recorded V11 vector data with body-feasible proposal caps supplied no usable LP start after two supporting-plane rounds. With the existing preserve-body proposal policy, it supplied a checked approximate vector-feasible direction in 0.328 seconds with directional merit `-11.355`. This permits incremental restoration of failed rows; the original final body gate remains 220 mm.
- V13 uses that preserve-body proposal policy and the same original thresholds. Its supervisor completes with exit 0 after 332.438 seconds, peak tree RSS 1,066,745,856 bytes. The local fit stops at 300.094 seconds after 348 measurements, 296 unretained inner queries, 51 backoff tests and six retained steps. Four geometry-start backoffs are retained within 5.797 seconds. Two later optimized backoffs pass full replay even though the inner solver reports a failed line search. The last point, not an unaccepted query, survives budget expiry.

| Check | Bound seed | Retained final | Result |
| --- | --- | --- | --- |
| Left/right grip points | 4.455 / 4.916 mm | 4.813 / 4.977 mm | Both pass 4.99 mm |
| Left/right surface orientations | 19.684 / 17.209 degrees | 19.721 / 19.358 degrees | Both fail 10 degrees; both worsen |
| Maximum physical box vertex depth | 13.566 mm | 11.108 mm | Improved; still failed |
| Maximum raw-reference joint displacement | 222.107 mm | 222.062 mm | Still fails 220 mm |
| Raw fixed-neighbor added speeds | 0.228 / 0.454 m/s | 0.736 / 0.737 m/s | Pass 1.5 m/s |
| Minimum skin floor height | 2.012 mm | 3.919 mm | Pass 2 mm |
| Complete squared violation | 17.598477 | 10.685808 | Decreases; not a quality rating |

The failed orientation rows may trade under the declared merit policy. Their regression is explicit; improving the aggregate score does not solve the grasp. Original rotation/root budgets, passing rows and failed nontradeoff rows remain protected. Full pose, quality and release flags remain false.

Complete NumPy replay verifies 351 native records across V11/V13, every input/predecessor/method/pose binding, all recorded vector envelopes/gradient/radii/supporting planes, every backoff/tangent decision, and full skin point/normal/depth/floor plus three-reference/fixed-neighbor speed populations. Six accepted decisions are reproduced. This replays recorded Jacobians rather than independently certifying a full native derivative. No original source clip or preview is replaced.

Reproduction with unchanged local native acquisitions:

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/new-geometry-descent/frame-98 --frame 98 --iterations 30 --trust .03 --seconds 300 --failure-policy merit --proposal nonlinear --solve-iterations 50 --row-chunk 16 --point-policy preserve --point-proposal feasible --point-headroom 1e-5 --tangent-guard --resume reports/box-lift-guarded-restoration-v11/frame-98 --body-proposal preserve --proposal-start geometry-descent
```

Use an owned supervisor for native runs. All studies keep the existing 3,600-second / 7 GiB process-tree / 600 MiB available-RAM guards. Licensed native inputs and generated archives stay excluded from Git; a bare public source snapshot cannot reproduce native inputs by itself.

Next: carry this last bound correction forward, control memory growth from archived vector populations, and test shorter nonlinear inner budgets and tighter direction choices for the remaining failures. Extend successful repairs to coordinated key windows and full temporal/geometry replay before claiming a usable clip. No between-key, support-slide, triangle/volume, self-collision, anatomy, dynamics, retargeted engine import or human certificate follows from this single pose. All fourteen project-wide capabilities remain unapproved; arbitrary actions, scenes/partners, editing/style, rig transfer, transitions/events, exports and held-out/human/cleanup evidence remain the full goal.
