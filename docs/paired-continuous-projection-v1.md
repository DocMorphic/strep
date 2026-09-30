# Continuous projection of paired wrist paths

This experiment removes the 20 mm / 15-degree state quantization from the
first-cluster path search. It seeks the closest feasible wrist/swivel guide to
the earlier collision-clearing Xplus path, without relaxing its original motion
limits. Closeness to a clear guide is an optimization objective, not evidence
that the resulting motion is clear.

## Method

Seven editable native keys each have a continuous symmetric wrist displacement
and two independent elbow swivels: 21 variables. Wrist displacement stays within
0-60 mm along the declared Xplus axis; each swivel stays within +/-30 degrees.
The nine-key clock, 0.8 m/s and 300 degrees/s guide limits, 45-degree native edit
budget, protected contact, source clips and original motion bins are retained.

`continuous_waypoint_motion.py` reconstructs local two-bone rotations at native
keys, quantizes them to float32 as the exporter does, and batches the existing
SLERP and forward-kinematics calculations. The full 148-time clock includes the
return to unchanged motion. Tests compare both actors with separately baked
GLBs to 2e-12 matrix-element tolerance, including between-key poses and shared
samplers; the zero-control source world compares exactly.

`waypoint_projection.py` minimizes the mean squared distance from the desired
controls after normalization by 60 mm and 30 degrees. Every evaluated state is
checked against actual positional and world-angular speed and acceleration for
all source joints. Only a feasible observed state can replace the incumbent;
an optimizer's status flag cannot approve a failing candidate. An unchanged
source is the initial feasible incumbent. Evaluation records retain controls,
objective, motion margins, reach failures and feasibility decisions.

The first attempt uses SciPy 1.15.3 COBYLA with four aggregate worst-motion
constraints and a 1,200-function-evaluation ceiling. It stops after 598 function
evaluations, with 599 unique recorded candidates including the explicit target.
Only the unchanged source passes. The returned objective is 0.051696557, but
its minimum normalized margin is -5.330643 and the solver reports constraint
failure. The retained feasible objective is 0.285714286. No GLB, engine test or
new geometry audit is produced for this unchanged result.

The second attempt uses SLSQP with every per-joint/per-stencil motion inequality
supplied separately, an analytic objective gradient, a normalized finite
difference step of 1e-4 and at most 100 iterations. The batch constraint gate
reserves a numerical margin: 9e-6 versus the unchanged independent scalar export
replay tolerance of 1e-5. This tightens numerical admission; it does not increase
a source motion cap. Full constraint vectors use a bounded 32-entry replay cache.

SLSQP reaches its 100-iteration ceiling. It reports 535 objective evaluations;
the trace records 2,594 evaluations including constraint finite differences,
explicit targets and replay calls. Eight observed records pass admission. The
solver's returned candidate still fails constraints (minimum normalized margin
-0.0001059591), despite a lower objective of 0.2508499874, and is not selected.

The retained feasible candidate was observed at evaluation 8: a symmetric
6e-6 m wrist displacement at only native key 1.5906041860580444 seconds, with
zero swivel and all other controls zero. Its objective is 0.2857047624, barely
below the unchanged source's 0.2857142857. This is 0.006 mm, not a useful
collision correction.

If a nonzero feasible candidate is found, the worker bakes actual GLBs and
independently checks all decoded joint rates, frozen keys and outside-window
poses. It then performs engine import verification and a mesh query at only the
original peak time. That single-time query must not be presented as full-clock
clearance. Publication and quality approval remain false.

For this retained candidate, both actual GLBs pass independent positional and
angular rate replay with zero failures. Batch and scalar world transforms match
exactly; native clocks, frozen keys and outside-window poses remain unchanged.
Godot verifies four clips / 444 actor-frames / 77 bones, with maximum position
discrepancy 5.366924e-7 m and basis-element discrepancy 6.851266e-7. At 1.675 s,
full-mesh vertex depth remains exactly 22.426395245662506 mm. The 5 mm screen
still fails, so no full-clock mesh audit or Studio replacement follows.

Both workers are terminal. Neither local optimization result proves that all
continuous paths are infeasible. Keep the failed returned candidates, feasible
incumbents and actual exported evidence distinct.

| SLSQP artifact | SHA-256 |
|---|---|
| Request | `ff876321d3e802a8f98d413321b55b5f0e20d03339c3850b7e82ee40c957f452` |
| Selected feasible controls | `010bdd1039f0999b10edb63e90ccef9fef0422998bbf090a377417e97e30d8d3` |
| Solver result | `f498873421dbb2e823008be11489de47ed50f92f815e47a0e352510bbb582b5e` |
| Evaluation trace | `9f4e9117fab21c497e414076b99df525754f40e0c71316aa95603c03a5c8909c` |
| Independent decoded motion | `fc43cfbf6fd0eecc00a92ec7f9e5f67daea617e460260a7fb66a41c2c7cafc0b` |
| Peak-time geometry | `241d2e52ad4e172e6173f47a4e614469d6b7587ed1d0dfb070cf51b230cbeff4` |
| Engine verification | `809dcd527135609cc244812fd294454aa07450d5802a50770c9a35357e66a0ce` |

## Native support diagnosis

The short experiment returns to zero at 1.8411632776260376 seconds. A separate
read-only check of the original authored window, 1.4083333333333334 through
2.5917225950783 seconds, finds a contiguous pre-contact native support of 14 keys,
from 1.4402683973312378 through 2.0917224884033203 seconds. The protected contact
is at 2.0917225950783 seconds. The broader support already exists within the
authored request; no guard or window has been changed by this diagnosis.

This identifies a more useful next experiment than repeatedly searching the
short return interval: plan through the entire permitted pre-contact support,
including the later collision cluster, while preserving the exact contact and
source-relative motion bounds. The current fixed-axis symmetric-control
representation and local solvers do not establish general infeasibility.

## Reproduction

Local ignored character, native-lattice and prior evidence inputs are required.
Use fresh output directories and retain both attempts.

```powershell
.venv/Scripts/python.exe -u scripts/project_native_waypoint_path.py reports/scene-pair-native-path-v1 reports/scene-pair-continuous-projection-v1
.venv/Scripts/python.exe -u scripts/project_native_waypoint_path.py reports/scene-pair-native-path-v1 reports/scene-pair-continuous-projection-v2 --method SLSQP
```

V1's preserved implementation snapshot predates the bounded replay cache and
the 9e-6 numerical admission margin. Use its snapshot for exact historical
reproduction; running the current CLI creates a new experiment.

The expanded focused suite passes 135 tests in both local runtimes. New tests
include false optimizer success, retaining a feasible target when optimization
stops early, and batch replay versus actual export for both actors. No model
training or new model/data acquisition occurred. All 14 release capabilities
remain unapproved.

See [the preceding discrete constrained search](paired-motion-bounded-path-v1.md).
