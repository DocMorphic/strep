# Bounded native foot-orientation search

An experimental CLI parameterization now lets native foot-world orientations
change by up to **1 degree** while retaining the ankle targets. It extends the
[knee-plane search](native-support-swivel-v1.md); the original bend-only and
swivel-only options and the ordinary Studio solver remain available. Final
sampled height, angle, displacement, rate and preservation checks are unchanged.

## Method

`native_support_orientation.SupportOrientationProblem` adds three world-axis
rotation-vector components at each interior native edit key. Each component is
bounded to `min(1 degree, authored angle limit) / sqrt(3)`, which bounds the
rotation-vector norm to the stated limit. Zero vectors preserve the swivel-only
quaternions exactly; frozen boundaries remain the original source quaternions.

The source foot-world frame conjugates each world-space delta into the local
foot frame. This edits orientation without moving the ankle origin at native
keys or changing the hip/knee controls. Interpolated motion, toe positions and
foot-region heights can change, so serialized independent audits still decide
acceptance. The existing sparse derivative graph includes the new key variables.
The matched request has 178 bends, 178 swivels and 534 orientation components,
or **890 variables**.

```powershell
.venv/Scripts/python.exe scripts/native_support_job.py source.glb draft.json `
  reports/fresh-oriented-support --joint-rates --joint-swivel `
  --joint-foot-orientation --joint-evaluations 320
```

Orientation mode requires both preceding experimental modes. It explicitly
changes the swivel-only method's native foot-orientation retention policy;
authoring angle/displacement limits and source-rate caps are not relaxed.
The request records the one-degree freedom and archives the extra method.

## Preserved numerical controls

Each proposal saves `trial-N.controls.json` with float64 parameters, hard boxes,
native interval clocks, variable indices, seed settings and the exported GLB
hash. Its hash is bound in the proposal report and completed job outputs. These
are solver controls, not a quality or acceptance receipt. Replaying them requires
the separately frozen source, draft and implementation. Existing control files
cannot be overwritten by the proposal function.

## Validation and study state

Twenty-two focused tests cover independent world-frame rotations on all axes,
exact zero-orientation parent equivalence, unchanged native ankle origins and
hip/knee controls, frozen/free/root preservation, the hard norm bound, independent
float32 decoder agreement, sparse dependencies for disjoint intervals, invalid
modes/budgets and exact byte-for-byte GLB replay from saved controls. The actual
job test archives the method and preserves all four rejected proposals and
their controls with an unchanged final input. A list-to-array replay bug was
caught and repaired before the real experiment. The full model-free source suite
passes **1,273 Python tests** and **14 JavaScript suites**. Preceding public
commit `faa8ba6` passed hosted Windows/Linux checks.

The matched real four-trial **320-evaluation** study,
`reports/native-support-orientation-rates-v1` (session 70778), is terminal. It
uses the same Studio v2 source and authored plane/stances/bounds as the completed
swivel studies. All four proposals pass sampled support heights at 142 stance
times per foot and preserve native clocks, frozen/free/root/other-branch motion
across 701 times. All exhaust their budgets and fail the unchanged source-rate
screen. **The exact original input is retained.**

| Trial | Failed rows: speed / acceleration / angular speed / angular acceleration | Final proxy squared residual | Largest fitted native orientation edit (degrees) |
| --- | --- | --- | --- |
| 1 | 49 / 12 / 18 / 5 | 0.0002648722 | 0.006067 |
| 2 | 55 / 11 / 10 / 9 | 0.0000492919 | 0.004062 |
| 3 | 57 / 8 / 12 / 10 | 0.0006114025 | 0.012991 |
| 4 | 37 / 9 / 8 / 2 | 0.0001930569 | 0.004691 |

The result SHA-256 is
`00806eb7ce6dd69c0c9e286a89901967a15abb93d6116d8a16823337b901266a`.
All **52** bound input/output/archive files rehash without mismatch.
The combined two-study/replay rehash checks **104** files without mismatch.
Compared with the matched 320-evaluation swivel-only study, trial 1's largest
angular-speed excess falls from 0.000283093 to 0.000001699 rad/s and its largest
angular-acceleration excess falls from 0.01447448 to 0.00045917 rad/s². Other
counts and scores are mixed; no general improvement or feasibility follows.

## Independent replay and float32 diagnosis

`reports/native-support-orientation-replay-v1` reconstructs every trial from its
saved parameters after checking its boxes, variable indices, native clocks and
method hashes. All **four replays produce byte-identical GLBs**. Quantized
proxy and independently decoded matrices agree within 9.993e-16 component error.
Observed serialized native foot-orientation changes remain below 0.013 degrees;
maximum native tangent-position difference is 4.452e-8 m. These numerical
rounding differences are distinct from intended ankle-target retention.

| Trial | Continuous proxy rate failures | Independently serialized rate failures |
| --- | --- | --- |
| 1 | 54 / 17 / 21 / 5 | 49 / 12 / 18 / 5 |
| 2 | 57 / 13 / 6 / 7 | 55 / 11 / 10 / 9 |
| 3 | 55 / 12 / 5 / 3 | 57 / 8 / 12 / 10 |
| 4 | 38 / 11 / 8 / 3 | 37 / 9 / 8 / 2 |

Float32 export both adds and removes borderline failures. Across trials, it
changes measured angular acceleration by up to **0.0008058361 rad/s²**, above
the unchanged 1e-5 acceptance tolerance. Continuous proposals themselves still
fail; serialization is not the only remaining cause. The replay result SHA-256
is `efcd720847ce5bd8cb36d9cbf8ec2bbb1a84b0ccfd4b97c35996e01732cbd581`.

The next solver experiment should warm-start from these reproducible controls
and repair explicit feasibility violations while checking the serialized
proposal, instead of relying on a lower summed residual or more iterations.
Broader rig/action/scene coverage and engine/human validation remain required.

No new model training, held-out use, engine/GPU/browser rendering, submitted
human review or release approval is claimed. All 14 release capabilities remain
unapproved; the full-project goal remains active.
