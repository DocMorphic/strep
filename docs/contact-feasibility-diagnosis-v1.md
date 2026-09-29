# Distinguish incompatible requests from failed fitting

The retained crawl-11 stationary hand pin cannot satisfy the current native body-change screen and pin tolerance together. At frame 50, a conservative skin bound requires **at least 0.536499 m of joint displacement from the raw reference**, while the body screen permits 0.22 m. Against the limb reference, the bound is 0.491526 m. Increasing iterations cannot resolve this conflict without changing the request or an explicit acceptance requirement.

This is a limit on the edit's difference from its reference pose at the same frame. It is not a limit on how far a character may travel, run or reach in a generated animation. Neither the authored request nor the existing benchmark thresholds have been changed.

## Acceleration-aware timing diagnostic

The old endpoint check only compares distance, speed and available time. `contact_rate_feasibility.py` additionally relaxes the full quarter-frame point trajectory to three linear programs, one per coordinate. It includes every pin sample and the original speed/acceleration stencils, including those crossing phase boundaries. Samples strictly outside the edit window retain the existing 1-micrometre position budget. Decoded endpoint samples are not assumed identical merely because native endpoint poses are held.

Componentwise bounds are a relaxation of the actual vector limits, and free point trajectories omit skeleton, skin, collision, support and force constraints. No conflict therefore does not establish feasibility. The test expands each inequality by 1e-12 m for conservative arithmetic; it does not change any animation acceptance tolerance.

The implementation uses the existing SciPy installation. Its [official HiGHS interface documentation](https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs.html) distinguishes solver status, primal residuals and inequality marginals. A solver status alone is not accepted as a conflict certificate here.

For inequalities `A z <= b`, coordinate bound `|z| <= B` and nonnegative multipliers `y`, a feasible solution must satisfy `-B ||Aᵀy||₁ <= yᵀb`. The implementation recomputes the strict contradiction `yᵀb + B ||Aᵀy||₁ < 0` using exact rational arithmetic on the recorded binary64 data. This explicitly charges stationarity error instead of pretending the solver's multipliers satisfy exact cancellation. The finite coordinate bound follows from preserved source samples, boundary acceleration and complete speed coverage; missing coverage is rejected.

All eight retained cases were evaluated on their original requests and rate limits. All **24 component programs** returned zero minimum common violation, with maximum independently recomputed witness row violation 1.78e-15 m. No timing conflict was proved. This gives no basis to automatically alter their timing or to declare the original coupled animation problem feasible.

Use `scripts/study_contact_rate_feasibility.py --help` for the read-only runner. Inputs, method snapshots, decoded tracks, sparse constraint matrices, multipliers, exact certificate results and failed statuses are retained. The measured eight-case run is under ignored `reports/contact-rate-feasibility-v1/`.

## Skin reach bound explains crawling

For a material vertex, linear blend skinning gives `v = sum w_j (R_j q_j + t_j)`. With nonnegative weights, joint displacement at most `D`, and rotation operator norm at most `K`, each vertex coordinate lies within `D sum w_j + K sum w_j ||q_j||₁` of the weighted reference joint origins. The L1 lever bound permits arbitrary orientations and is deliberately conservative. The diagnostic adds the 5 mm pin tolerance and a 1-micrometre arithmetic reserve.

`contact_pose_reachability.py` evaluates this bound with exact rational sums. Its stated rotation norm assumption is 1.02, a conservative allowance around rigid rotations; it does not cover arbitrarily scaled or malformed bone matrices. The result concerns native-frame pin and body-displacement checks, not a new guarantee about exported interpolation.

The public `contact_pose_preflight.py` combines this calculation with saved raw/limb references and bound stationary pins, and prints a concrete conflict explanation. Across the original eight cases, it reproduces **316 frame/reference calculations**:

| Case | Proved conflict with current pose screen |
| --- | --- |
| Crawl 11 | Raw-reference frames 50–56 and limb-reference frames 50–55: 13 frame/reference pairs. Worst lower bounds 53.649906 cm raw and 49.152640 cm limb, both at frame 50. |
| Wave 11/22, crawl 22, kick 11/22, jump/landing 11/22 | No conflict proved by this conservative bound. |

This explains why crawl-11's restart could improve its hand pin while still showing a roughly 59 cm joint displacement and failing the 22 cm body screen. The smaller pin error did not resolve the incompatible requirements. Kicking remains unresolved: its worst bound is only 15.678320 cm, so this diagnostic does not exclude a solution within the current screen.

Example on an existing saved edit:

```powershell
.venv\Scripts\python.exe scripts/contact_pose_preflight.py `
  --source reports/contact-jobs/MY_JOB/source-take `
  --spec reports/contact-jobs/MY_JOB/checked-plan/bound-contact-spec.json `
  --output reports/MY_NEW_POSE_PREFLIGHT.json
```

Review the target, interval or source motion when the requirements conflict. The tools never alter them, widen thresholds or approve a candidate automatically. Integrating this explanation into Studio's saved checks is next; the current timing-check UI has not yet gained these diagnostics.

## Verification and limits

Twenty-four focused tests pass, including an acceleration conflict that passes the old distance/speed bound, exact certificate replay, phase-boundary stencils, multiple conflicting pins, translation, missing rate coverage, invalid data and 50 constructed rigid-skin candidates that must not be rejected. Input/artifact hashes and all recorded certificates were independently rechecked. The public pose preflight matches every recorded frame/reference row. Evidence remains under ignored `reports/contact-pose-reachability-v1/`.

No animation, model, training data or dependency was changed or acquired. No new engine playback, browser rendering or human review is claimed. Original failed fits remain preserved. These diagnoses change the next action for crawl-11; they do not approve any release capability or justify dropping difficult action families.


A [full-distance skin bound](contact-pose-sphere-v1.md) now proves kick-11 also conflicts with the current native edit screen: frame 50 requires at least 26.519804 cm versus the 22 cm budget. Exact outward rational bounds verify two new frame/reference conflicts; all 316 retained calculations were replayed, with no motion or acceptance changes. Twenty focused bound tests pass. The already-running body-constraint experiment remains frozen; its result will be retained, then the stronger certificate should enter Studio preflight. No further iteration-only retries are justified for this request.
