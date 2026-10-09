# Guarded native contact repair

`scripts/guarded_pose_restoration.py` adds small, independently replayed repair
steps to the native pose diagnostic. The original clip, scene, model and budgets
remain saved. This experiment repairs a single native pose with fixed adjacent
candidate keys; it does not produce an approved animation.

The proposal uses all original point, actual triangle-normal, complete skin/prop,
floor, three-reference displacement, neighboring added-speed and rotation-norm
inequalities from [direct pose restoration](scene-pose-restoration-v1.md).
Controls are normalized by their original rotation/root bounds. A bounded
linearized SLSQP subproblem proposes a direction; eight backoffs replay the full
nonlinear population. Unaccepted proposals cannot replace the retained pose,
including when a budget expires. Rejected and retained poses, audits, controls
and hashes are saved separately.

Two explicit search policies retain the same final acceptance thresholds:

- `rowwise` preserves passing rows and prevents any failed row from worsening.
- `merit` preserves every passing row and every edit-budget/floor row. Only
  already-failed point, normal and prop rows may trade error. The complete maximum
  normalized violation must not increase and squared violation must decrease.
  Rows that become feasible remain protected at subsequent steps.

The merit policy can retain an increased error in an already-failed contact;
that contact still fails its original threshold. It does not approve that error,
widen the threshold or permit increased edit-budget violations. The exact
Boolean tradeoff mask and normalization are recorded in the protocol and result.
The strict policy remains the default.

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/my-fresh-guarded-study --frame 72 --iterations 60 --trust .03 --seconds 300 --failure-policy merit
```

Use the unchanged owned-process resource guard for heavy runs: 3600 seconds,
7 GiB process-tree RSS and at least 600 MiB available system memory. The shared
worker lock covers source loading, preflight, fitting and publication. Original
inputs, method sources, native skeleton definitions and Python/NumPy/SciPy/Torch
versions are bound; definitions are also archived. Final independent NumPy skin
replay, original-input and method hashes are checked before publication.
The command needs acquired native assets and a completed local V17 study; those
third-party payloads and bulky outputs are excluded from the public repository.

## Derivatives retain the complete population

`sparse_pose_jacobian.py` evaluates all 18,056 vertices before selecting active
dependencies. It retains every maximum/minimum tie, all contact vertices and
normal triangles, and all original body rows. Backpropagation uses the selected
vertices with all eight influences. Full nonlinear proposal replay still uses
the original complete skin and constraints.

Synthetic derivative comparisons cover global/native-joint groups, boxes,
spheres, cylinders and duplicated-vertex ties. At both actual source poses, all
values and derivatives match the dense path exactly in the recorded computation.
The frame-72 dependency set has 72 vertices, but timings are 6.469 seconds dense
versus 5.328 sparse. The reduction in backpropagated vertices does not imply a
similar reduction in total runtime; body derivatives still cost time.

## Actual results

The preceding grouped direct solve completes its supervisor in 1222.25 seconds
with 638,877,696 bytes peak process-tree RSS. Both poses stop at their explicit
600-second solve limits. Neither passes: vertex depths are 9.151 / 2.550 mm;
hand errors are 8.001/10.988 and 10.537/24.787 mm. They remain in
`reports/box-lift-pose-restoration-v4/`.

The strict guarded study completes in 53 seconds with 638,255,104 bytes peak tree
RSS. Frame 72 retains three steps, preserves both working hand-target passes and
reduces vertex depth from 25.715 to 25.053 mm. Frame 98 retains its seed.
Both stop with no further guarded improvement and remain failed. An archived
frame-72 backoff improves complete maximum/squared violation while worsening a
failed normal by about 0.0000035 degrees; frame 98 has similarly improving
backoffs that worsen its already-failed right contact. These measured rejections
motivate the explicitly masked merit policy, without changing any final limit.

The merit study completes in 91.75 seconds with 652,402,688 bytes peak tree RSS.
It retains seven / one steps; both stop with no further guarded improvement:

| Measurement | Frame 72 | Frame 98 | Original limit |
| --- | --- | --- | --- |
| Left/right hand error | 4.985 / 4.921 mm | 4.932 / 5.527 mm | 4.99 mm working target |
| Left/right normal error | 23.969 / 8.203 degrees | 19.433 / 15.916 degrees | 10 degrees |
| Prop vertex depth | 24.677 mm | 14.486 mm | No physical penetration |
| Maximum raw-relative joint displacement | 198.860 mm | 221.637 mm | 220 mm |
| Added speed to fixed neighbors | 0.557 / 0.610 m/s | 0.163 / 0.269 m/s | 1.5 m/s |
| Minimum floor vertex Y | 2.484 mm | 2.434 mm | 2 mm |

Rotation/root budgets pass both poses. Limb/previous reference results agree to
rounding. Both maximum/squared violation scores improve and every originally
passing and nontradeoff inequality stays protected. Frame 98's right contact
worsens from 5.085 to 5.527 mm and remains explicitly failed. Neither result is
accepted as a feasible grasp or usable animation.

Local evidence is in `reports/box-lift-guarded-restoration-v1/` and `-v2/`,
including every replayed proposal and native metadata/runtime bindings. There is
no new model sampling, training, held-out release evaluation, engine import,
human review or cleanup-time result. No full-clip temporal basis, protected
support/slide, between-key, triangle/volume, anatomy, balance or dynamics
certificate is inferred from the pose checks.

A separate NumPy replayer checks complete skin vertex prop-depth/floor results
for all 118 saved pose records, including seeds/finals and rejected backoffs.
It rechecks all input, archived-method, native-definition, protocol, audit and
pose hashes, and verifies all eleven retained decisions against the complete
recorded inequalities and the declared masks. Agreement tolerances check
arithmetic replay; they do not grant physical acceptance allowances.

One hundred and one distinct focused checks pass in a fresh source copy without
vendor payloads. The 58 model-free checks also pass using the separate runtime
without Torch. The CI manifest declares 404 model-free Python modules and 39
Node suites; the four Python shards contain 101 modules each. Native lifecycle
and derivative checks run in the separate CPU Torch jobs.
The preceding hosted CPU jobs failed because the older finger-budget test read
downloaded skeleton definitions. Its fixture now supplies the complete 38 finger
names inside a 77-joint synthetic rig, uses a fixed generator seed and accounts
only for double-precision roundoff in its norm assertion. Production budgets
are unchanged; actual acquired metadata remains checked by study preflight.
Hosted verification of the new batch is pending, not reported as green.

The next repair needs more accurate nonlinear protection of hand targets and a
coordinated contact window. The whole-project goal still includes arbitrary
actions, object/partner interaction, editing/style, rig transfer, transitions,
engine delivery and human validation. All fourteen release capabilities remain
unapproved.
