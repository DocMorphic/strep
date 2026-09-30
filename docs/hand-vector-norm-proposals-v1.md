# Vector-norm proposals for paired hand correction

The preceding individual-witness optimizer could lower predicted penetration but
its final proposals violated original motion limits. The precision audit improved
individual witness derivatives with float64 construction, yet acceleration
prediction errors remained. This experiment retains each three-dimensional
velocity and acceleration vector inside its norm constraint.

## Method

`hand_norm_proposal.py` builds a central-difference local model at the completed
selected controls. Actual float32-authored poses supply the base values; the
separate float64 proposal editor supplies derivatives. The four vector families
match the existing positional speed/acceleration and world angular
speed/acceleration measurements. Original per-bin caps, the existing 9e-6 search
reserve, native edit limits, guide budgets and frozen endpoints remain unchanged.

Each motion row constrains the norm of its affine three-vector with a
second-order cone. Individual signed witness depths share an epigraph objective.
Guide and native-edit margins use scalar affine proposals. A triangle-inequality
bound omits only norm rows certified safe throughout the affine trust box; it
does not certify the nonlinear animation. All rows return for actual acceptance.

The one-point experiment tests normalized trust radii 0.01, 0.001 and 0.0001
independently, using the same central step 0.0001. Each proposed direction has at
most eight halving backoffs. A step must improve measured witness depth by more
than 1e-9 m and pass every actual motion/domain margin without relaxation.
Clarabel's status and predicted epigraph cannot accept an animation. The existing
locally pinned Clarabel 0.11.1 is verified before use; no dependency was acquired.

The best candidate is exported through the unchanged editor, independently
decoded, checked across the original 148-pose clock, and screened at all 43 hand
times against full partner meshes. Stored native clocks/frozen keys must remain
exact. This is not a full-body collision or engine acceptance test.

```powershell
.venv/Scripts/python.exe -u scripts/study_hand_norm_proposal.py reports/scene-pair-witness-epigraph-v1 reports/scene-pair-hand-norm-proposal-v1
```

## Completed one-step solve, export and geometry

All three convex proposals returned `Solved`. All full steps failed exact
motion checks, and all half steps passed. The largest trust radius produced the
best accepted candidate: fixed-witness depth decreased from 20.927446 mm to
20.897778 mm, about 0.029668 mm. This is a small surrogate improvement, not a
claim of good interaction quality.

| Trust radius | Norm cones retained out of 28,028 | Full-step minimum actual margin | Accepted half-step depth (mm) |
| --- | ---: | ---: | ---: |
| 0.01 | 970 | -0.000348608 | 20.897778 |
| 0.001 | 146 | -0.000002968 | 20.922528 |
| 0.0001 | 35 | -0.000001002 | 20.926651 |

On the same eight deterministic directional probes used in the prior audit,
maximum normalized vector-norm prediction residuals against actual float32 poses
are 1.435924e-6 (positional speed), 8.943103e-6 (positional acceleration),
1.795526e-6 (angular speed), and 5.838283e-6 (angular acceleration).
Local predictions still have error; they do not replace exact acceptance.

Both selected GLBs replay with zero batch error, retain frozen native keys and
pass all four motion categories across the original 148 samples. Fresh geometry
completed at all 43 hand times. Failing samples decrease from 17 to 16: sample 69
now passes and no new sample fails. Peak penetration decreases from 20.932800 to
20.901569 mm, a 0.031231 mm improvement. This remains far above the 5 mm limit.

Twelve directional observations worsen, by up to 0.360605 mm. The largest
regression in the maximum across both directions at a single sample is
0.047039 mm. Lower peak depth does not imply every local contact improved.
The candidate does not replace Studio or approve a release capability. The
entire project-wide goal remains active.

Local evidence in `reports/scene-pair-hand-norm-proposal-v1`:

- Request: `19ee36dcee6e216b661903b06b9f619630e963754c4749e692df34b87cce4482`.
- Saved affine model: `30e7783e773605e6e925655cb68ac807b892afdefc259a6605a4d699a42731df`.
- Prediction audit: `197dc095fb3475cd8c0f4481e193a979ac6bf4c207846e24075df8704c925a68`.
- Proposals/backoffs: `5dfb3783ad90955aa049473de5f8520abcb68944edab187a68eb0456acf699c3`.
- Selected controls: `5659f637bff6db981cb8d8c9f6c15ea80510792b912a9355970bb510bcd9e4c9`.
- Decoded audit: `759e23232702192602702268968caea593d5292437b3c75c75027084cebaf946`.
- Actor A GLB: `3571a6f34524a8235004acc367f8c5aeab6a6a8163ebc48586b4285dd053ef10`.
- Actor B GLB: `b37263948936a19767ec86415ce99e4c8bbe9bbf3023785d9fe5ad83717a63cb`.
- Fresh geometry: `0ad5af71b9924b91e68fce68d0dfe252b810fe3c497cd989075e435beec62174`.
- Directional donor comparison: `7ec0a45bba3a3d48c047afb2cdeae2b41f5785e2aa87799612acf752532eb2a7`.
- Completed result: `56a0d85d258ee64d8801538e59c145605f25707f28c2efb8bfaaaf5ff36f45fd`.

## Validation and platform test correction

Fourteen new model-free tests cover norm equivalence, angular ambiguity,
tangential acceleration missed by scalar linearization, affine cone signs,
conservative row omission, fixed caps, exact rejection, backoff and boundary
handling. All 751 minimal public Python tests passed locally. After the separate
fixture assertion correction below, the 19 affected tests passed again.

Hosted Windows CI for commit 548eea4 exposed a strict equality assertion on
recomputed float64 transforms: differences were at most 8.8817842e-16. Frozen
stored quaternion values still matched exactly. The fixture now checks frozen
native values explicitly for exact equality and allows 1e-14 absolute error only
when comparing reconstructed outside-window transforms to the cached source.
Zero-control poses still require exact equality. No production export or motion
acceptance tolerance changed. Both Windows and Linux hosted checks passed on
commit e7e0413 (run 36773060121).

## Bounded relinearization study

The completed one-step study supports testing further exact-feasible local steps,
without treating a solved convex approximation as the final animation.
`iterated_hand_norm.py` rebuilds the local approximation at each accepted point.
Every probe and accepted step must retain the initial caps, scales and row
populations. Caps cannot be recalculated from the newly edited animation.

For each iteration, the same three trust radii produce proposals; the best
actual-feasible improvement becomes the next point. The search stops at its
fixed budget, when no tested step improves exact depth while remaining feasible,
or when central probes would leave the control domain or two-bone reach. These
stops do not prove global infeasibility. Every local model and proposal history
is saved. Fresh mesh screening still follows the final export, so intermediate
surrogate improvements are not mesh quality certificates.

Fourteen additional tests cover relinearization on a nonlinear vector constraint,
original-cap preservation across iterations, best feasible candidate selection,
stopping, changed populations, initial feasibility and explicit probe boundaries.
All 765 minimal public Python tests pass. A separate analytical nonlinear fixture
using the pinned solver made six accepted steps while preserving its initial
norm cap; it is solver evidence, not an animation result.

The connected six-iteration experiment starts at the same bound selected controls
as the one-step experiment. It is running at
`reports/scene-pair-hand-norm-iterations-v1`; no completed geometry result exists
yet. Both source and method snapshots must remain unchanged while it runs.

```powershell
.venv/Scripts/python.exe -u scripts/study_hand_norm_proposal.py reports/scene-pair-witness-epigraph-v1 reports/scene-pair-hand-norm-iterations-v1 --iterations 6
```

No model was trained, no held-out prompt was used, and no release gate changed.
