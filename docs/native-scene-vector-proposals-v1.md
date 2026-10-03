# Native scene vector proposals

The optional vector proposal model addresses a measured failure in the scalar
finite-difference model used by [native scene fitting](native-scene-fitting-v1.md).
It supports the same explicit body, moving-object and partner point conditions
on supplied rigs. It changes proposal generation; independently decoded native
conditions still determine a pass. Every job continues to select its original
inputs pending scene geometry, actual imported-skin checks and human review.

## Why preserve vectors

In a saved rejected root-translation probe, a scalar acceleration row predicted
a normalized residual of -78.133340 while the decoded GLB measured +82.688060.
Forward and backward norm differences had opposite signs around small vectors.
The norm of an affine vector predicted +67.802718 for that same row, catching
the missed failure. This identifies a local proposal-model defect, not a proof
that the requested motion is impossible or that another solver will succeed.

The new model keeps three-vector forms for cumulative native-key edits,
all-joint displacement, positional/angular speed and acceleration, contact
position and each separate frame-clock contact speed. It proposes a minimax
step with second-order cones, followed by a minimum-step-norm phase at the
same affine optimum. [Clarabel's Python interface](https://clarabel.org/stable/python/getting_started_py/)
provides those cones; the optional dependency is pinned to
[Clarabel 0.11.1](https://pypi.org/project/clarabel/0.11.1/).
Solver status and affine feasibility never approve a decoded animation.

Float32 storage is a second limitation. On a saved vector-model root probe,
the original 1e-5 difference step predicted a worst residual of 0.760193 while
the actual export measured 47.276840. Prediction errors at steps 1e-5, 1e-4,
1e-3 and 1e-2 were respectively 47.286840, 5.005980, 0.657845 and 0.084808.
The last three caught all missed failing rows in that probe. The vector mode
therefore defaults to an explicitly recorded 1e-3 normalized control step;
it can be specified separately. This is evidence from one fixture, not a
universal optimal step or a smoothness guarantee for stored keys.

## Storage and safeguards

Vector Jacobians use sparse CSC storage. Only exact zeros are omitted; small
derivatives, actors and final constraint populations remain present. The local
limit is 60 million stored nonzero elements, with both dense-size and stored-size
counts recorded. A solver cone may also be omitted when the norm of its entire
affine trust-box enclosure is below its original cap, with an arithmetic reserve.
Fixed failed rows still constrain the minimax excess. This screening concerns
the affine model; all serialized final rows are always checked.

The matched partner trial contains 459,121 norm rows and 54 controls: 74,377,602
dense Jacobian elements. Its first sparse Jacobian stores 34,868,487 nonzeros.
The first step has 1,475 active cones, with 451,223 variable rows bounded passing
throughout the affine trust box and 6,423 fixed passing rows. The initial dense
implementation rejected this trial at its resource limit. That failed attempt
is retained; sparse storage allows the same interaction to execute locally.

All source motion bins, tolerances, contact budgets, protected key supports,
mesh payloads and native edit limits remain unchanged. Package version and
installed solver file hashes join the request/result provenance and are checked
again before publication. A missing dependency or changed solver fails the job.
The scalar CLI and existing Studio path retain their numerical defaults.

## Run an optional proposal job

Acquire dependencies in the chosen environment before working offline:

```powershell
uv pip install --python .venv/Scripts/python.exe --only-binary=:all: -r requirements-scene-proposals.txt
.venv/Scripts/python.exe scripts/native_scene_fit.py contacts.json permissions.json reports/my-vector-proposal --proposal-model vector --iterations 4 --trust .02 --vector-difference-step .001
```

Use a fresh output directory. Contacts and permissions follow the existing
source-bound scene/edit schemas; node names or action labels do not select a
hidden anatomy map. The result contains separate proposed and selected files.
The selected files remain original copies even if native conditions pass.
This optional setup is not a complete offline installer or Studio integration.

## Development results

The scalar baseline, initial dense vector trials and sparse follow-up use the
same clips, contact requests, edit permissions, four-iteration budget and 0.02
trust bound. No new motion inference or formal held-out trial is run. The
synthetic body fixture and two retained interactions all still fail acceptance.

| Case | Scalar worst residual | Sparse vector worst residual | Final contact observation |
| --- | ---: | ---: | --- |
| Synthetic body lift | 0.989874 | 0.356134 | 1.152541 mm position error against 1 mm; hold-speed clocks pass |
| Retained sphere grip | 1.037736 | 1.035061 | Right grip-speed limit still fails |
| Retained high-five, seed 5101 | 4.686231 | 4.682078 | 170.462344 mm hand separation against 30 mm |

The body result improves the measured residual without satisfying the request.
The interaction differences are small and do not demonstrate an animator-visible
improvement. A separate authored two-millimetre root plateau also fails the
unchanged constraints. An endpoint-travel check does **not** rule out the body
request; it is a necessary condition only, and its passing result is not a
feasibility certificate. An earlier verification wrapper incorrectly asserted
that this check must conflict; the failed observation is retained and the fresh
wrapper records the actual compatible bound.

The separate storage diagnostic compares two authored root triangles. The
ordinary two-millimetre peak fails the unchanged rate checks. Rounding its peak
to five equal stored increments produces 1.999736 mm, with 0.400211 mm contact
error and 1.999736 mm/s hold speed; all original native conditions pass. The
source values share a 1.192093e-7-metre Float32 spacing. This is a known feasible
**synthetic authored clip**, not a solver success, generated humanoid correction,
engine/geometry approval or training example. Its original remains selected.

All 163 focused model-free checks pass locally, including twenty-one vector-model
checks for dense/sparse parity, radial conflicts, full trust-box screening,
moving/partner contacts, missing clocks, raw exports, solver mutation and
configuration rejection. They join Windows/Linux hosted source checks.
Independent replay reproduces all 27 GLB exports from 21 saved control vectors
in the sparse follow-up byte-for-byte. All original cap arrays match the scalar
study exactly; final merits and contact metrics reproduce, and independent
full-skin contact coordinates agree within 3.34e-16 metres. All 234 study files
rehash. The initial dense study's 22 exports from 22 controls also replay exactly,
and its partner resource failure remains recorded. Independent scalar sampling
of the authored aligned triangle confirms zero rate failures, preserved clocks
and unedited tracks, and its full-skin contacts on an additional 301-time clock.
These are software and sampled native-development results. No collision-free,
actual engine/render, human-quality, training admission, learned improvement
or release approval is granted. All full-project release requirements stay open.

Detailed local evidence is excluded from Git under
`reports/native-scene-vector-development-v1`,
`reports/native-scene-vector-development-v2`,
`reports/native-scene-vector-step-diagnosis-v1` and
`reports/native-scene-storage-seed-development-v1`, with validation in
`reports/native-scene-vector-validation-v4`. These paths require the development
workspace and are not public downloads.
