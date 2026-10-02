# Additional source peak bounds for native support repair

The native support repair CLI now offers `--repair-strict-peaks`. This adds the
existing independent full-clip per-joint peak comparison to both the proposal
objective and the final selection gate. It is opt-in and requires a completed,
source-matched warm study. Kimodo and the default Studio behavior are unchanged.

The previous coordinate study selected one proposal under the four-bin rate
screen, but its separate 1e-7 peak comparison failed. That historical result
remains intact: [coordinate repair](native-support-coordinates-v1.md).

## Method and acceptance

For each position speed, position acceleration, angular speed and angular
acceleration sample, the additional upper bound is the smaller of:

- The original time-bin cap plus its unchanged 1e-5 tolerance.
- That joint's original full-clip peak plus the unchanged 1e-7 peak tolerance.

The reference is the selected input GLB on the uniform 120 Hz derivative clock.
It is computed once for each repair problem. The existing signed row ordering,
normalization, structural graph, control boxes and authored contact constraints
remain present. Source caps are not modified. The strict limits apply to both
the rounded-key numerical model and independently exported/decoded probes.
The option works with minimax or coordinate repair.

Final selection independently decodes the final GLB and requires all original
support, rate, displacement, angle, clock and preservation checks plus the
per-joint peak comparison. The job records `selection_gates_pass` for each
trial. Optimizer merit or success cannot override a failing final peak check.
Default jobs retain their original selection criteria and still report the
separate peak diagnostic. Already-satisfied input retention is unchanged.

Requests record the mode, peak reference, both tolerances and the archived
implementation. Warm controls must still reproduce their previous GLBs exactly;
ancestor requests, results, archived methods and output/probe hashes stay bound.
The source clip and all failed proposals remain available.

```powershell
.venv/Scripts/python.exe scripts/native_support_job.py source.glb draft.json `
  reports/fresh-strict-repair --joint-rates --joint-swivel `
  --joint-foot-orientation --repair-from reports/completed-warm-study `
  --repair-iterations 8 --repair-trust 0.0000002 `
  --repair-quantized --repair-strict-peaks
```

Use `--repair-coordinates` in place of `--repair-quantized` for coordinate search.
Neither finite search failure nor solver convergence certifies feasibility.
Preserving the original peaks does not establish realistic dynamics, balance,
stationary sole contact, collision safety or human approval.

## Source verification

Thirteen new tests check the intersection without changing source caps, a
bin-pass/peak-fail counterexample, matching row populations, invalid inputs and
mode requirements. Real four-trial fixture jobs check exact warm GLB replay,
unchanged controls/authoring limits, method archival, saved probes and frozen
ancestor evidence. A separate routing test makes the independent peak checker
reject otherwise-passing synthetic outputs: strict mode retains the input;
the default preserves its previous selection behavior.

The preceding public commit `23e5b3d` passed hosted Windows and Linux checks
(run 36952881401). Those checks include the earlier quantized derivative
roundoff-test fix; no production acceptance tolerance was relaxed.

## Completed development study

`reports/native-support-strict-peaks-v1` starts from the four completed
coordinate controls at eight minimax iterations, 2e-7-radian trust and rounded
key differences. Its request binds 1,319 ancestor evidence files. The source,
rig, authored static plane, intervals and bounds are unchanged. These are four
optimizer warm starts on one clip/rig, not model-generation seeds or diversity
evidence. Source SHA256:
`87c185ddf0dc50dec7e56bbc4c301f66896ed460a53c6c8eb6797ce5a89107c7`.

**All four trials fail the strict final selection gate; the input is retained.**
All sampled support and preservation checks pass at 701 times, including 142
stance samples per foot. The study retains 138 independently decoded probes.
Every final GLB replays byte-for-byte from its controls; rounded-key proxy and
decoder component error is at most 9.993e-16, and normalized constraint error
at most 1.226e-11. All 1,662 ancestor, study and replay evidence files rehash
without mismatch. The full local suite passes **1,329 Python tests and 14
JavaScript suites**.

| Trial | Initial worst excess | Final worst excess | Bin failures | Peak-regressing joints | Iterations / stop |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.0038372600 | 0.0037046127 | 67 / 13 / 25 / 14 | 1 / 1 / 5 / 2 | 8 / budget |
| 2 | 0.0000352421 | 0.0000073278 | 2 / 1 / 0 / 0 | 0 / 1 / 3 / 1 | 7 / stall |
| 3 | 0.0110954797 | 0.0109573592 | 76 / 9 / 19 / 14 | 1 / 0 / 3 / 4 | 8 / budget |
| 4 | 0.0010672018 | 0.0010445473 | 59 / 14 / 14 / 11 | 0 / 1 / 3 / 1 | 7 / stall |

Counts are ordered position speed, position acceleration, angular speed,
angular acceleration. Bin counts measure failing sample rows; peak counts
measure regressing joints and are not interchangeable.

The previously bin-passing second warm start reduces its stricter worst excess
by about 79.2%, but the repair introduces three bin failures. Its largest angular
speed peak increase falls from 9.4454e-6 to 7.2799e-7 rad/s, still above 1e-7.
Position and angular acceleration peaks also regress. Worst-excess acceptance
can trade one constraint against another during repair; final selection accepts
none of these trades unless every gate passes. Squared excess does not decrease
at every accepted step when the worst excess improves. This is measured failure,
not an infeasibility proof or an animation-quality result.

Completed result hashes:

- Fit: `4f23ae17159fb3344904d583adb4edc480c94b95e50eabaaac666adf3f28e56b`.
- Controls replay: `26082ec04cc0939c6d267b40e6c6c2288076e4a74798490676b8316aaabd95dc`.
- Rehash receipt: `afe6b326924585d600922daf98d68e32671ff6e72f0f8b4075b6af2358ecec1a`.

Next test bounded coordinate repair under the same stricter contract, followed
by actual engine/imported-skin validation and broader rig/action/scene evidence.
The earlier ground-zero displacement failure remains unresolved. No new
training, held-out use, engine/GPU/browser rendering, human cleanup evidence or
release approval is claimed. All 14 capabilities remain unapproved; the one
full-project goal stays active.
