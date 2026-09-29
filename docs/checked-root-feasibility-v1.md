# Small root correction clears the retained contact constraints

The retained get-up candidate now satisfies its checked stationary pin, point-rate ceilings, full-mesh floor nonregression and outside-window preservation in the decoded export. This repairs the two remaining numerical failures from the [longer solve](checked-contact-convergence-v1.md). It does not approve the animation's broader quality or establish general editing reliability.

| Decoded measurement | Retained candidate | Root correction |
| --- | ---: | ---: |
| Maximum pin error | 5.001649 mm | 4.999499 mm |
| Samples exceeding the original 5 mm limit | 1 / 81 | 0 / 81 |
| Release speed excess over original ceiling | 0.0000795925 m/s | 0 |
| Other point speed/acceleration excesses | 0 | 0 |
| Maximum floor penetration | 1.462459 mm | 1.454941 mm |
| Added depth at any of 717 sampled times | 0 | 0 |
| Preserved outside-window samples | 160 / 160 | 160 / 160 |

One accepted linearized proposal changed root height by at most **7.519 micrometres**. Local/global joint rotations, root XZ and heading remain fixed. The original clip continues to define the 220 mm absolute root-lift budget, floor reference and all rate ceilings; the retained candidate is only the initializer. The held boundary keys and outside segments remain unchanged. No acceptance threshold was relaxed.

## Method and verification

`root_height_feasibility.py` specializes the existing linear feasibility repair to root Y translation. It uses 138 free native root keys and 3,344 normalized inequalities: every authored pin sample, every per-point rate stencil, each time's maximum joint speed/acceleration, and each time's full-mesh floor minimum. The interpolation matrix matches float32 export key times. Skin-weight sums are retained, rather than assuming exactly unit weight sums.

The linear program minimizes the maximum coordinate step inside a 10-micrometre trust box and the original source-relative root bounds. It seeks a stricter 1e-4 normalized interior margin on movable rows. That margin is a solver target, not acceptance padding. All nonlinear rows and floor/joint witnesses are recomputed for proposals; any previously passing row becoming a violation causes rejection. Failed searches are saved. The resulting sampled slack must be nonnegative, and float32 serialization and decoded exports are checked separately.

Caching is valid only in this root-translation subspace. On this actual clip, every cached constraint matches the independent full interpolation/skin calculation exactly at the seed and within 4.57e-13 normalized units at a perturbed pose. A fixed random directional derivative check covers every row; maximum absolute derivative discrepancy is 1.40e-7. The dense Jacobian uses 3.69 MB and cached full-mesh heights use 103.57 MB. Setup and these checks took 2.14 seconds. Fitting, body evaluation, export and decoded audit together took 52.56 seconds, excluding the later engine check.

Float32 serialization retains all sampled constraints. Decoded release speed is 0.120098002 m/s against its unchanged 0.120110314 m/s ceiling. Actual global joint peaks also remain below the original limits: 3.867704 m/s versus 3.868428 m/s, and 222.838183 m/s² versus 224.238702 m/s². Those global limits do not establish per-joint naturalness.

BVH reconstruction error is 1.30e-6 m; GLB native joint error is 1.12e-7 m. All eight skin influences are verified. Actual Godot playback passes 407 pose observations, two requested-boundary events, four callback-mutation rejections, forward/reverse playback and unload. Maximum actor matrix component error is 1.27e-6. No browser rendering, HTTP interaction or human review is claimed.

Thirty-four focused tests pass, covering the new translation cache and derivatives, held boundaries, unchanged budget reference, float32 key clock, feasible/infeasible linear proposals, rejection of a nonlinear regression, and the existing point/floor/global-rate objectives. SciPy emits its existing warning that the `threads=1` option is forwarded to HiGHS; the actual LP reports an optimal solution.

## Reproduction and scope

With the local retained study, licensed asset and existing dependencies available:

```powershell
.venv\Scripts\python.exe scripts/study_root_height_feasibility.py `
  reports/contact-jobs/studio-sampled-pins-convergence-v1 `
  reports/contact-jobs/studio-root-feasibility-v1
```

The output directory must not already exist. The script checks and snapshots the original source, checked plan, seed candidate, asset hash and Python implementation. Both controls and the new study remain immutable. Local numerical/export evidence is under `reports/contact-jobs/studio-root-feasibility-v1`; the independent engine and original global-budget checks are under `reports/studio-root-feasibility-v1/verification.json`. Generated assets and machine data are excluded from the public repository.

The candidate still has added-joint-speed, hand/body support-gap and surface-slide flags. This is a successful constraint repair on one development clip, not evidence of realistic support, force balance, action correctness, cleanup savings or held-out generalization. Studio's default fitter is unchanged. The root-only correction cannot repair arbitrary contact targets or large rotational defects. All release capabilities remain unapproved.

Next test the correction as part of complete, source-referenced contact fitting on predeclared cases from other action families, including cases expected to be infeasible in root-only coordinates. Preserve failed proposals and compare support/pose quality, not only the authored pin. This evidence is needed before exposing an automatic correction path or claiming broader reliability.
