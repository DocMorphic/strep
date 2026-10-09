# First-order feasible initialization for native pose repair

`guarded_pose_restoration.py --proposal nonlinear --proposal-start linear-feasible` initializes each nonlinear proposal from a minimum-L1 step in its complete first-order inequality system. The default remains `zero`; the opt-in initializer requires nonlinear proposals. The existing full nonlinear retention and tangent guards still decide which point may replace the current one.

For the current normalized controls `z`, complete slacks `s`, Jacobian `J` and proposal caps `c`, the initializer solves `min sum(t)` subject to `s + J delta >= c`, `-t <= delta <= t` and the existing trust/global delta bounds. When tangent protection is enabled, each hard row cap is also at least its tangent-search preservation cap. Point/body feasibility masks and point-only proposal headroom retain their declared meanings.

HiGHS runs for at most 20 seconds, bounded by the remaining local study time. Its reported success must replay complete finite controls, auxiliary/bound checks and every first-order row, with a solver tolerance of `1e-8`. The tolerance concerns search initialization only. Endpoint retention still requires the original strict nonlinear inequalities and declared failed-row policy; neither LP success nor a solver query approves a pose. All starting controls, caps, bounds, directions, LP statuses and complete initial Jacobians are archived.

An unavailable first-order initializer preserves the last retained point and stops with `linear_start_unavailable`. This is a local first-order search result, not nonlinear infeasibility. Budget expiry also preserves the last retained point. Resume checks reject promotion of a linear initializer and verify that recorded initialization policy matches the protocol. Existing source/predecessor/reference/edit bounds remain immutable; see [resumable pose repair](resumable-pose-repair-v1.md).

## Validation

A fresh no-vendor source copy passes 200 focused checks across 11 modules; 99 also pass in the pure NumPy/SciPy environment without Torch. Tests exercise a real minimum-L1 initializer, distinguish unretained queries from accepted backoffs, reject nonlinear failures despite first-order success, preserve output when the query budget expires, reject incompatible first-order constraints without entering the nonlinear solver, and reject forged LP success or promoted initialization records. This is focused coverage, not a release or complete CI claim.

## Native comparison

The V10 study uses the unchanged V17 source, the V9 terminal pose as its explicitly bound seed, original frame 98, trust `.03`, feasible point/body proposals, preserved point rows, point headroom `1e-5`, tangent protection, 50 inner iterations and a 300-second local budget. The intended comparison changes proposal initialization only. The supervisor completes with exit 0 after 324.375 seconds, peak process-tree RSS 682,041,344 bytes. The local pose budget expires after 300.562 seconds: 292 measurements, 291 unretained queries, no completed backoff or newly accepted step. The first-order initializer itself takes 0.015 seconds, with an L1 normalized step of 0.0510395 and minimum linear residual within rounding (`-7.4e-18`). Starting feasibility alone does not resolve this nonlinear search.

Complete NumPy replay verifies all 293 saved poses, original/predecessor/archive bindings, complete recorded linear caps/deltas/bounds, full-skin point/normal/depth/floor and three-reference body/speed populations. It confirms that neither the initializer nor any inner query was promoted. Final metrics equal the bound predecessor: hand points 4.455/4.916 mm pass the 4.99 mm threshold; orientations 19.684/17.209 degrees, physical box vertex depth 13.566 mm and raw displacement 222.107 mm still fail. The original full clip and preview remain unchanged.

## Diagnostic: distance curvature and direction quality

A separate owned, guarded directional experiment evaluates the saved initializer with finite directional differences at fractions `1e-4` and `1e-5`. The two estimated grip velocity vectors agree within 6 nm per unit fraction. It compares scalar distance linearization with the norm of the linearized three-dimensional grip vector and with complete nonlinear skinning. This agreement concerns one direction, not a full Jacobian certificate.

| Grip | Scalar predicted distance | Vector-norm predicted distance | Nonlinear distance |
| --- | --- | --- | --- |
| Left | 4.989 mm | 6.347 mm | 6.350 mm |
| Right | 4.989 mm | 8.381 mm | 8.438 mm |

The scalar tangent approximation loses substantial distance curvature when a point moves sideways relative to its target. The vector-norm approximation exposes that loss before a nonlinear replay; it still approximates nonlinear skinning. Body vector-norm prediction also remains imperfect: maximum raw displacement is predicted at 220.085 mm versus 220.030 mm nonlinear, both above the 220 mm limit. The diagnostic's double-precision FK and saved float32 reconstructed poses differ slightly; the rounded table is consistent with both.

All eight diagnostic fractions `1, .5, .25, .125, .0625, .03125, .015625, .0078125` pass the recorded tangent retention test but fail complete nonlinear retention. Fractions at or above `.125` lose at least one passing hand point. Smaller fractions preserve passing and protected rows, but increase total squared violation. For example, `.0625` increases it from 17.598477 to 17.669674. No diagnostic pose is selected. A separate NumPy replay verifies all eight complete poses and physical metrics; the supervisor exits 0 with peak RSS 565,760,000 bytes.

The initializer's directional derivative of total squared violation is positive, `1.1381861`. Its minimum-L1 objective enforces proposal feasibility but does not enforce a descent direction for the retention merit. An additional recorded-Jacobian LP can satisfy the same bounds/caps and a small negative merit derivative (`<= -1e-6`). That feasibility result is only diagnostic: it does not prove sufficient decrease at any finite backoff, nonlinear feasibility or a path.

Reproduction of the V10 pose worker with unchanged local native acquisitions:

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/new-feasible-start/frame-98 --frame 98 --iterations 30 --trust .03 --seconds 300 --failure-policy merit --proposal nonlinear --solve-iterations 50 --row-chunk 16 --point-policy preserve --point-proposal feasible --point-headroom 1e-5 --tangent-guard --resume reports/box-lift-guarded-restoration-v9/frame-98 --body-proposal feasible --proposal-start linear-feasible
```

Use an owned supervisor for native work; both local supervisors preserved the existing 3,600-second / 7 GiB process-tree / 600 MiB available-RAM guards. Records remain in ignored `reports/box-lift-guarded-restoration-v10/` and `reports/box-lift-linear-curvature-v1/`.

Next: make starting directions compatible with merit descent and retain the full three-dimensional contact/reference distance in geometry-aware proposals. Test finite nonlinear backoffs before retention; a tiny negative first-order slope alone may be overwhelmed by second-order error. Then extend to coordinated windows and full temporal/geometry replay. Do not relax point, rotation, root, floor, reference or import limits to hide the failed experiment.

Scope remains a diagnostic pose with fixed neighbors, not a generated or repaired full animation. No support-slide, between-key, triangle/volume, self-collision, anatomy, dynamics, engine import or human approval follows from this experiment. Licensed native acquisitions and generated study records remain outside the public source repository. All fourteen full-project release capabilities remain unapproved.


The next comparison preserves vector distances and explicitly checks merit descent before nonlinear adoption; see [geometry-aware descent](geometry-descent-repair-v1.md) for six retained native steps and the remaining orientation, collision and displacement failures.
