# Protecting the initial repair direction

The previous point-preserving proposals improve collision merit while their
smaller backoffs worsen already-failed right-thumb displacement rows. The
optional `--tangent-guard` now constrains the initial direction of every passing
or nontradeoff row inside a nonlinear proposal. It also rejects a retained
backoff whose recorded first-order preservation check fails. The original full
nonlinear retention checks still apply; no final tolerance is relaxed.

At each outer iteration, the source controls, complete slacks/Jacobian, exact
protected-row identities and preservation caps are saved in the fit result.
The tangent proposal adds a normalized 0.000001 search margin to those caps;
retained tangent checks use the exact original preservation caps. Failed
normal/object rows remain explicitly eligible for merit tradeoffs. Newly passing
rows become protected at the next iteration. The default leaves this search
restriction disabled, and enabling it with a linear proposal is rejected before
worker acquisition.

This restriction is conservative. A finite endpoint may pass the nonlinear
checks while the tangent rule rejects it. A synthetic fixture demonstrates that
case and shows that smaller steps along the same direction worsen the protected
budget. Another fixture verifies that the constrained solve can use another
control and retain an improving step. Neither a tangent plane nor these fixtures
certifies a complete nonlinear path, temporal smoothness or physical motion.

## Unchanged native comparison

`reports/box-lift-guarded-restoration-v8/` retains the original V17 source, frame
98, point-preserving merit mask, contact-feasible proposal, point search margin
0.00001, trust box 0.03, 50 inner iterations and 300-second pose budget. It adds
the tangent guard. The unchanged owned-process global guard remains 3600 seconds,
7 GiB tree RSS and at least 600 MiB available RAM.

The supervisor completes in 314.047 seconds with 681,086,976 bytes peak tree RSS.
The pose solve stops at its time/measurement budget after 300.390 seconds and
retains one checked half-step. The first inner solve hit its iteration limit;
the next was still evaluating unretained queries when the budget expired.
The pose pipeline is explicitly `interrupted_resource_guard`, not feasible.

| Measurement | Original pose | Retained pose | Original limit |
| --- | --- | --- | --- |
| Left/right point error | 4.427 / 5.085 mm | 4.455 / 4.916 mm | 4.99 mm working target |
| Left/right normal error | 19.876 / 15.945 degrees | 19.684 / 17.209 degrees | 10 degrees |
| Prop vertex depth | 15.437 mm | 13.566 mm | No physical penetration |
| Maximum raw-relative displacement | 222.107 mm | 222.107 mm | 220 mm |
| Added speed to fixed neighbors | 0.160 / 0.243 m/s | 0.228 / 0.454 m/s | 1.5 m/s |
| Minimum floor vertex Y | 2.022 mm | 2.012 mm | 2 mm |

Both point targets now pass, including the previously failed right hand. Every
originally passing and nontradeoff row stays protected; rotation/root budgets
pass. Both normals, prop penetration and raw-relative displacement still fail.
Right-hand normal error worsens under the declared failed-normal tradeoff.
The raw-displacement change is only about 0.000070 mm and does not resolve its
failure. This is one improved native pose, not a successful grasp or animation.

A separate NumPy replay verifies all 306 saved pose records, original/archive/
output/diagnostic hashes, full native vertex floor/prop-depth, hand points and
triangle normals, all three reference body populations and fixed-neighbor added
speeds. It verifies the retained decision and recomputes each tangent decision
from the recorded complete Jacobian/controls. That tangent calculation is a
replay of recorded derivatives, not an independent derivative certificate.
The existing dense/sparse native preflight and synthetic derivative checks
remain separate evidence.

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/my-fresh-tangent-study --frame 98 --failure-policy merit --point-policy preserve --proposal nonlinear --row-chunk 16 --solve-iterations 50 --seconds 300 --point-proposal feasible --point-headroom 0.00001 --tangent-guard
```

## Scope and next work

The fresh source copy without vendor payloads passes 168 distinct focused checks;
88 also pass without Torch. The model-free CI inventory remains 405 Python
modules and 39 Node suites. Hosted verification of this newer batch remains
pending. Raw study evidence and acquired model/character payloads stay excluded
from the public source repository.

Next, preserve this accepted point correction while requiring the failed body
budget to be restored, then coordinate the contact window and replay complete
temporal and geometry checks. The current scene-guided generation preparation
checks source contact and orientation before sampling; these failed poses are
not assumed to be valid guides. A new sampling comparison requires explicit
source-target qualification and retained baseline provenance.

No new model generation/training, full-clip correction, support/slide,
between-key/triangle-volume, rig transfer, engine import, anatomy/dynamics,
human rating or cleanup approval is inferred. The full arbitrary-action,
scene/partner, editing/style, rig/transition/export and human-validation goal
remains active; all fourteen release capabilities remain unapproved.
