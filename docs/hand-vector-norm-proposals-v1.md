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
as the one-step experiment. It completed at
`reports/scene-pair-hand-norm-iterations-v1`, with results below.

```powershell
.venv/Scripts/python.exe -u scripts/study_hand_norm_proposal.py reports/scene-pair-witness-epigraph-v1 reports/scene-pair-hand-norm-iterations-v1 --iterations 6
```

No model was trained, no held-out prompt was used, and no release gate changed.

## Completed six-step study and trust-bound diagnostic

All six local iterations accepted their half-step proposals. The accepted
fixed-witness peaks were 20.897778, 20.878440, 20.865582, 20.856424, 20.849231
and 20.843009 mm. Every full step was rejected by actual motion/domain checks.
The first accepted controls exactly match the completed one-step experiment.
The fixed six-iteration budget ended the solve; no convergence or infeasibility
certificate was obtained.

Both final GLBs replay exactly, preserve frozen native keys and have zero
violations in all four motion categories over the original 148-sample clock.
Fresh geometry at all 43 hand times finds 16 failures, the same count as the
one-step candidate. Peak penetration is 20.873814 mm, versus 20.901569 mm after
one step and 20.932800 mm in the original donor. The 5 mm limit remains unmet.

Compared with the original donor, 13 directional observations worsen, by up to
0.836258 mm; the maximum two-direction peak regression at a sample is 0.234396 mm.
Compared with the one-step candidate, 15 directional observations worsen, by up
to 0.486688 mm; the maximum sample peak regression is 0.356611 mm. No newly
failing sample appears against either reference. These tradeoffs remain visible;
the candidate does not replace Studio or approve contact quality.

A read-only diagnostic of the saved six local models finds that 11-19 controls
per largest-trust proposal reach at least 99% of its normalized 0.01 step box.
Five or six of those controls have nonzero derivatives for that proposal's
locally predicted worst witness. Their share of absolute per-coordinate linear
contributions for that one witness ranges from 14.6% to 55.3%. The predicted
worst witness changes between iterations. These shares are not a certificate
about the whole max objective or the physical feasible region.

The maximum accumulated normalized coordinate change after six accepted half
steps is 0.03. This supports comparing larger proposal trust boxes with the
same original motion/domain limits and exact
backoff acceptance. It does not justify widening any physical cap, increasing
the iteration budget blindly or assuming that a larger proposal will be safe.

Completed local evidence:

- Request: `cacc8c868ad9ef06f2343971a8b5eaf28f3c815ee347e1a51dfe7024f7def0a3`.
- Iteration summary: `40dbcd9f7b502faca4e53a571c952ab0861115da14efc255347f854ec34e1c7c`.
- Selected controls: `7fac6a705d8ebb52e9e78b350d2a045d39d4fc4c62137747f470f0943c5afc34`.
- Decoded audit: `3c4116de8de04c80549c2162886113626fc3d62a3415ed760457af02f46b7635`.
- Actor A GLB: `e546860ff4c3b295030dddeb50bf9363c3f7ba214ca3967d4d219101d92c555a`.
- Actor B GLB: `b954be73555f661b1512abeb1199a76a6ba18c4a90cdfe89c681b230936b4401`.
- Bound trust diagnostic: `reports/hand-norm-trust-diagnostic-v1/result.json`, SHA-256 `161e66610b3e09a8e067ed346624c43218e9890eaf126b0f3ac8ff57381326be`.
- Geometry: `8637a065a5a74b5229fa255fa203178aea0a5238504059a261e1eb9474fc3190`.
- Donor comparison: `82b7ab90ae6d724c57c73161642da1add50b5deab0b0f7d5b5e1131116f58e41`.
- Completed result: `49acc46f3dfce006833c9f8cfa05f28d8392f395c7af8626336653002681d504`.

The trust diagnostic records hashes of its input artifacts and its local audit
script, reproduces each saved worst-witness prediction and verifies inputs again
after reading. It does not change the running study or execute another solve.
Commit 5910220 passed both hosted Windows and Linux checks, including the new
iteration tests.

## Larger proposal-step comparison

The runner now accepts explicit validated `--trusts` values. The matched
follow-up replaces `[0.01, 0.001, 0.0001]` with `[0.1, 0.01, 0.001]`, retaining
six local iterations, three proposals per iteration, the same eight exact
backoffs, derivative step, source poses, controls, scene geometry, witnesses,
sample clocks, solver version, physical limits and export checks. This changes
proposal size, not the allowed motion or penetration limits. The numerical
proposal and acceptance modules are unchanged; 28 focused tests pass again.

Request field/hash comparisons verify the matched configuration before reading
results. The larger-trust request is
`a7bdef9ad5d0d6c91f0ec9f32de5bebadf9526749653aaad27d835d693f29faa`;
the comparison record is `reports/hand-norm-trust-matched-configuration-v1.json`.

```powershell
.venv/Scripts/python.exe -u scripts/study_hand_norm_proposal.py reports/scene-pair-witness-epigraph-v1 reports/scene-pair-hand-norm-larger-trust-v1 --iterations 6 --trusts .1 .01 .001
```

The larger-trust experiment completed. Its six accepted fixed-witness peaks
were 20.897778, 20.838088, 20.817434, 20.782150, 20.760885 and 20.749525 mm.
Both exported GLBs reproduce exactly, preserve frozen keys and pass the original
four motion categories at all 148 times. Fresh hand geometry still fails:

| Candidate | Failing hand times / 43 | Peak penetration (mm) |
| --- | ---: | ---: |
| Original donor | 17 | 20.932800 |
| Six steps, smaller trust range | 16 | 20.873814 |
| Six steps, larger trust range | 17 | 20.791931 |

Against the smaller-trust candidate, sample 69 fails again. Twenty-two
directional observations worsen, by up to 3.444154 mm; the greatest per-time
peak increase is 2.924551 mm. Against the original donor, 23 directional
observations worsen by up to 2.864957 mm, with no newly failing time. The lower
global peak is not a uniform contact improvement. No Studio replacement or
quality approval follows.

Bound completed evidence:

- Larger-trust result: `a42a617a4995e89297c3b476682a6eaf2d31697448abc4f10908b8e7d8970f29`.
- Geometry: `bf834916df71a1a566407e25517df6e7e44f0c3df048354b32261ca2d0c28017`.
- Decoded audit: `067ff754b019fa0d23474f0b68e32407d31b49d1323e5afb950792088d98151a`.
- Actor A: `28c01507ce0b4d063676e6a65583ad4a8633dc6c578d3fe4d3838cd61da5ee3d`.
- Actor B: `f5cda40f1f24dec5d030175b894d8ec37bdc521e39c00df57fd1403c043e4d2a`.
- Smaller-trust comparison: `reports/hand-contact-sections-v3/smaller-trust-comparison.json`, SHA-256 `8b53acfce89e9eb5b9d435945204f34a1ee4da15a13273cf6b77d5785f2f2f3d`.

## Actual contact inspection and fixed witness envelopes

`scripts/inspect_hand_contact.py` reads a completed norm study, verifies its
bound inputs and outputs, loads serialized candidate GLBs and saved actor
placements, and replays the deepest recorded vertices at selected times. It
finds nearest target triangles, reports interpolated skin influences, and draws
three actual surface-plane sections through each deepest point. It also replays
every fixed witness in the objective's direction order, comparing against the
initial model. This is a diagnostic of existing observations, not a new complete
collision screen. It requires the existing development dependencies and Pillow.

```powershell
.venv/Scripts/python.exe scripts/inspect_hand_contact.py reports/scene-pair-hand-norm-larger-trust-v1 reports/hand-contact-sections-v3 --samples 69 77 81
```

All six deepest distances at these three times reproduce to 1e-10 m. At sample
69, source influences are 99.7% and 94.2% LeftForeArm; nearest target influences
are 98.8% and 99.7% LeftForeArm. Later sample 77/81 contacts have LeftHand as
their strongest source and target influence (source weights 59.2%-94.2%). These
weights describe deformation controls, not precise anatomy. The sections show
substantial intersecting surfaces around the late contacts; adding finger
controls alone is not supported as the next remedy by this evidence.

The fixed-witness replay identifies 437 individual observations whose final
signed depth exceeds max(5 mm, its own initial signed depth) by more than 1e-8 m.
At sample 69, the maximum fixed depth grows from 5.381383 to 7.062145 mm even as
the global peak falls. Many regressions are already visible to modeled contacts:
improving only the worst depth leaves these unconstrained. Missing witnesses or
surrogate error can still matter elsewhere. Empty witness times are recorded
explicitly with zero count and null peaks, never as clearance.

Diagnostic result: `reports/hand-contact-sections-v3/result.json`, SHA-256
`a5bc38defd2a9cccae2209d7a24092ab9337d9feb009ce1140554fbede75d650`.
Witness comparison: `345b9e39229a6e76a88dabf54ab599cf0b6b5e295b5d85af75f6f96fa1ea40e5`.
Images and character payloads stay local and ignored.

The next matched experiment adds `--preserve-witness-envelope`. Each original
signed witness gets a fixed ceiling of max(5 mm, initial signed depth) + 1e-8 m.
The explicit numerical slack is 0.00001 mm. Copied ceilings remain fixed for the
whole solve, enter local proposals and are checked on every exact backoff; they
are never rebased after an accepted step. Existing motion, domain, export and
fresh geometry gates remain unchanged. This is a surrogate regression bound,
not permission for intersections or evidence of full-body clearance. It can
limit available correction directions and does not prove general infeasibility.

Eight new tests cover exact rejection/backoff of a lower-peak proposal that
worsens a previously safe contact, preservation across later local models,
caller mutation, signed depths, malformed references and changed populations.
All 36 focused checks and all 786 minimal public Python tests pass.

```powershell
.venv/Scripts/python.exe -u scripts/study_hand_norm_proposal.py reports/scene-pair-witness-epigraph-v1 reports/scene-pair-hand-witness-envelope-v1 --iterations 6 --trusts .1 .01 .001 --preserve-witness-envelope
```

The envelope study uses the same original donor, six-iteration limit, three
proposal radii and eight backoffs. Its first iteration accepted no proposal;
all 24 exact trials had a negative constraint margin. The solver stage stopped
early and retained the donor. This finite local failure is not a proof that the
problem has no solution. The completed fresh mesh audit reproduces the donor
exactly: both candidate GLB hashes match the donor, all 43 two-direction depths
match, and 17 times still fail with a 20.932800 mm peak. Original motion checks
pass over all 148 times. No candidate replaces Studio.

The local models predict only about 0.000013 mm peak reduction under the added
per-witness limits. All 24 actual backoffs fail a constraint; increasing the
iteration budget cannot change this study's early stop. This is evidence against
continuing the same local formulation unchanged, not evidence of general
infeasibility or permission to weaken the original study's acceptance gates.

Completed envelope result: `dd1ff1b603abf6d58075ca557f787ce7a468752fb73d64c3936e86a13b327867`.
Geometry: `0de5059470998ae0d5ba7e827117d81ff3a5cb8b095d5f288986c70b4d0aa6b9`.
Envelope: `83559a7ec671f0d5707522e4c38bd0fd04ea1284e41f0c2758a3e3f9cdba291e`.
All workers for this comparison are terminal. No model training or held-out
prompts are used; all 14 capabilities stay unapproved.
