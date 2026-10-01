# Per-joint peak guards for contact-rate fitting

The [unguarded continuation](contact-rate-continuation-v1.md) reduced its scalar
objective but worsened angular-speed peaks and several failure counts. This
matched experiment starts from the same `contact-rate-path-v1` clips and retains
the same 36 controls per actor, 120-iteration limit, original joint-angle
references, contact target and geometry audit.

## Separate original acceptance from non-regression

For each rate kind and joint, compute its positive peak excess over the original
per-time/bin cap, including the unchanged 1e-5 cap comparison tolerance. Freeze
that peak from the starting serialized clip. The candidate must not increase
it by more than a 1e-7 numerical allowance in the corresponding rate unit.
Already-passing joints retain their original caps rather than being forced to
match a lower arbitrary source rate. This prevents another joint's improvement
or a lower aggregate score from hiding a larger peak on this joint.

This guard does **not** redefine release success around the starting clip.
Original cap tests still run independently. A passing guard can retain existing
violations, and failure counts can increase while peaks stay bounded. Counts,
individual peaks and original-cap results remain separate outputs.

## Proposal-only inward margins

Fit the same weighted positive-excess objective, but require an additional
1 micrometre of hand-plane clearance in the double-precision proposal. Actual
float32 acceptance retains the existing 0.45 mm auxiliary clearance. The
authored contact and full-mesh collision tolerance remain unchanged.

For each positive rate-excess peak, also tighten the proposal guard inward by
the smaller of 10% of that deficit or 1e-4 times its objective scale. Already
passing joints get no additional rate reserve. Scales remain 1 m/s, 10 m/s²,
3 rad/s and 100 rad/s². These reserves are numerical planning choices, not
physical realism thresholds or certified rounding-error bounds.

The starting clip must pass the actual guards; it need not satisfy these new
inward proposal reserves. Only a serialized feasible reduction in the weighted
rate objective may be selected. Full proposed controls and every attempted
backoff are retained even if the source clip is ultimately kept unchanged.

After export, independently decode and recheck the per-joint peak guards,
original arm/finger limits, clocks, untouched channels, protected/outside poses,
contact surfaces, all 53 inter-actor mesh samples, floor depth and original rate
caps. No continuous collision, self-collision, engine or human-quality approval
follows from a proposal pass.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_peak_guarded_contact.py reports/contact-rate-path-v1 reports/<fresh-guarded-fit>
```

The local provenance chain and separately acquired character are required.
The previous experiments, model checkpoint and reserved held-out prompts remain
unchanged.


## Equivalent explicit-time constraint experiment

The first guard formulation gives SLSQP each joint's maximum across time. Its
worst-time index can switch as controls change. Both actors fail to find an
acceptable step: actor A terminates after 96 iterations with a positive
directional derivative for line search, and actor B reaches the 120-iteration
limit. Every tested serialized backoff is rejected. Both selected GLBs remain
byte-identical to the input; the repeated mesh passes are not new motion progress.

A matched follow-up exposes the inequality at every relevant time and joint
instead of taking the maximum inside the constraint function. For a fixed
per-joint ceiling, requiring every sample to stay below it is equivalent to
requiring the maximum to stay below it. Tests verify this equality and retain
both constraint branches when the worst time switches. This changes the solver
formulation, not the accepted envelopes or reserves.

Proposal rows cover the subtree affected by the three arm controls. Unaffected
joints are omitted from the optimization rows because the local controls cannot
change their world transforms. Serialized acceptance and independent decoding
still check **every** joint. The tests explicitly reject a regression in an
omitted column through the full acceptance guard.

```powershell
.venv/Scripts/python.exe scripts/study_sample_guarded_contact.py reports/contact-rate-path-v1 reports/<fresh-sample-guarded-fit>
```

The failed aggregate formulation remains at `reports/peak-guarded-contact-v1`:
4,475 bound inputs, 95 methods and 60 outputs, all rehashed without mismatch.
Its result SHA-256 is
`64d70cbc5cb7257aa27af808391bf8e8e5d774ef1c4706cbd9831996aff8f519`.


## Explicit-time results and absolute-peak limitation

Both actors reach the 120-iteration limit; convergence is not claimed. Both
full-strength serialized proposals are accepted by the excess-peak guards.
The weighted objectives decrease from 0.08155325 to 0.07747246 (actor A) and
0.07761605 to 0.06714228 (actor B). All 53 sampled inter-actor mesh checks pass,
with zero crossings and vertex penetration. Contact separation is 1.00002449 mm;
original edit budgets, clocks, protected poses and untouched channels pass.
The auxiliary 0.45 mm hand planes pass; the stricter 0.5 mm comparison fails.

Original motion acceptance still fails in every group:

| Rate group | Failing rows | Maximum cap excess |
| --- | ---: | ---: |
| Position speed | 137 | 0.416848 m/s |
| Position acceleration | 292 | 63.453464 m/s² |
| Angular speed | 1,420 | 2.206540 rad/s |
| Angular acceleration | 278 | 229.019708 rad/s² |

**A passing excess guard does not guarantee that absolute rate peaks decrease.**
The reference caps vary with time. Moving a rate peak into a larger-cap bin can
reduce excess while increasing the actual physical rate. A separate read-only
comparison over the same uniform audit interval finds increased absolute angular
acceleration peaks in 25 joints of actor A and six of actor B. Maximum increases
are 21.286555 rad/s² at A's LeftHandIndex1 and 16.729657 rad/s² at B's LeftForeArm.
No joint's absolute peak increases in the other three rate groups.

The counterexample is covered by a unit test: source rates [10, 6] and caps [8, 1]
have peak excess 5; candidate rates [11, 5] have peak excess 4 but absolute peak 11
instead of 10. Next, constrain absolute per-joint peaks alongside excess peaks;
neither replaces original motion acceptance. No such new fit is claimed here.
These observations cover the saved audit interval, not the entire clip.

```powershell
.venv/Scripts/python.exe scripts/diagnose_native_absolute_rates.py reports/sample-guarded-contact-v1 reports/<fresh-absolute-rate-diagnostic>
```

The explicit-time fit binds 4,475 inputs, 96 methods and 60 outputs. Its result
SHA-256 is `202e635747f42cbd565d8ab50e77921c5241a4118522ed6d27e91b40931c1921`.
The absolute comparison binds 4,632 inputs, 98 methods and two outputs; result
SHA-256 `aaaec315cea50809144ac1837be765b0d1afd76430b3fb4b97f027a2fd12ffa9`.
The independent turnaround diagnosis binds 4,632 inputs, 97 methods and two
outputs; result SHA-256
`d2ba6145f0219d4e00d104dc03d4718928d3711976a093e5223cb850fd5ba1bb`.

A fourth comparison version is packaged locally at
`reports/native-contact-review-v3/viewer.html`. All eight copied GLBs pass offline
format/loader checks with zero errors or warnings. This does not verify browser
rendering, game-engine playback, human motion quality or continuous collision
freedom. The full model-free Python suite passes 1,071 tests. No candidate is
selected for Studio; no training or reserved held-out evaluation occurred.
