# Windowed guide fitting preserves unselected motion

The guide initializer can now preserve the starting clip's rotations outside a declared native-frame window while keeping the original correction spline and source-relative edit limits. In the matched arm-guided trial, this removes changes to unselected motion and reduces whole-clip penetration and acceleration, but most hand contacts still fail. The candidate remains rejected.

## Mechanism and validation

`run_object_grip_seed.py --edit-window START END` selects an inclusive native-key interval containing the complete grasp. The fitter recovers the seed's existing spline controls, then optimizes additions in the null space of the basis rows outside that interval. Consequently those rows cannot change the seed's encoded rotations. This is a restriction of the existing control space, not a post-fit blend, a reset of the edit reference or a larger rotation budget. Root tracks must match between seed and original source in this mode; the fixed root is retained.

The default remains unrestricted fitting. Invalid windows, windows with no free controls, nonmatching roots and excessive outside-key residuals are rejected. The recipe records the selected window, free-control count, numerical basis residual and final rotation discrepancy. Native preservation does not by itself guarantee smooth boundary dynamics or between-key collision safety.

Twenty-eight focused tests pass. They exercise a cubic basis, a nonzero starting pose that must remain unchanged outside the window while an interior target moves, invalid intervals, original edit bounds and existing guide behavior. A separate 18-key moving-target test against the saved previous implementation produces bit-identical default motion arrays and identical objective history.

## Matched moving-clip experiment

`reports/region-windowed-arm-guide-v1` uses the same original source, starting clip, qualified guide, frame-121 reference, arm/hand targets, weights, 100-iteration budget and edit bounds as `region-arm-guide-transfer-v1`. The only requested behavioral change is window `[48,133]`, covering grasp frames 60–121 and twelve transition frames on each side. The control-space change is recorded in both implementation snapshots and protocols. Eleven free control directions remain, with 94 native keys outside the selected interval.

| Independent exported measurement | Global arm guide | Windowed arm guide |
| --- | ---: | ---: |
| Runtime | 12.359 s | 13.094 s |
| Failed hand contacts / 490 | 484 | 478 |
| Failed geometry samples / 717 | 390 | 379 |
| Maximum box penetration | 61.531520 mm | 28.574569 mm |
| Peak joint speed | 1.428788 m/s | 1.283170 m/s |
| Peak joint acceleration | 66.981300 m/s² | 37.521536 m/s² |

The native peak penetration is 27.926302 mm; the larger exported value shows why quarter-frame verification is retained. Original edit bounds pass, with maximum original rotation edit 35.964949 degrees. All 360 new Godot source/candidate actor-frames reproduce the 77-joint exports with position discrepancy below 0.382 micrometres.

An independently exported copy of the exact starting seed is compared against the candidate at all 717 quarter-frame times. On 370 samples whose interpolation keys are both locked, maximum joint-position discrepancy is 0.135 micrometres and rotation-matrix element discrepancy is below 1.40e-7. Including the six boundary-straddling samples outside the requested time window gives the same maxima. Inside the window, joint positions change by up to 174.824 mm. These checks bind the actual seed and output hashes; they do not infer preservation from the solver's status alone.

Global speed and acceleration peaks no longer exceed the original source, but local regressions remain: 27 joint speed peaks, 54 acceleration peaks, release/boundary speed windows and approach/end-boundary acceleration windows increase beyond the existing reporting allowance. Hand contacts and body geometry still fail. The selected time window improves edit locality; it does not enforce surface contact or certify transitions.

## Evidence and next work

The study retains fitting/audit drivers, implementation snapshots, matched comparison, `default-compatibility.json`, and `window-verification.json` with every sampled discrepancy. Studio collection `windowed-arm-guide-review-v1` exposes the failed comparison. Twelve package hashes and eleven permitted offline routes are verified; the Python snapshot remains unserved. No live browser or human review was performed.

Next carry the window restriction into explicit surface-contact fitting, retaining original edit limits and independently checking approach/release behavior. Neither this initializer nor the earlier arm guide is selected as a usable animation. All fourteen release capabilities remain unapproved.
