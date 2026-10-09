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

The current runner additionally defaults to `--point-policy preserve`, protecting
even failed hand-distance rows. The point tradeoffs measured in the historical
V2/V4 studies now require explicit `--point-policy tradeoff`. See
[point-preserving repair](point-preserving-repair-v1.md) for the new comparison
and complete named-row diagnostics. The original grasp thresholds remain fixed.

The merit policy can retain an increased error in an already-failed contact;
that contact still fails its original threshold. It does not approve that error,
widen the threshold or permit increased edit-budget violations. The exact
Boolean tradeoff mask and normalization are recorded in the protocol and result.
The strict policy remains the default.

```powershell
.venv/Scripts/python.exe scripts/guarded_pose_restoration.py reports/box-lift-authored-height-v1 reports/my-fresh-guarded-study --frame 72 --iterations 60 --trust .03 --seconds 300 --failure-policy merit --point-policy tradeoff
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

## Nonlinear proposal comparison

The optional `--proposal nonlinear` mode evaluates the complete original
inequalities and their current derivatives inside each bounded proposal solve.
This accounts for the curvature of hand-target balls instead of constraining
only their tangent approximation. The default remains the archived linear
proposal. Both modes use the same full-population replay and retention policy;
no proposal solver status can approve a pose.

Each distinct inner query is saved with its pose, independent audit, parameters,
complete inequalities and hashes. Inner queries are marked unretained. Only a
backoff that passes the original retention checks can replace the current pose.
Time or measurement expiry retains the last accepted pose, even when an inner
candidate looks better. `--solve-iterations` explicitly bounds each proposal
solve, and the shared elapsed-time and measurement budgets cover its queries.

A synthetic circular target boundary demonstrates a tangent proposal stall and
a successful nonlinear repair without losing the passing boundary constraint.
Additional checks verify inner-query budget expiry retains the seed, changed
derivative populations fail, and invalid options never acquire a worker.
The fresh no-vendor source copy passes 136 distinct focused checks; 63 also pass
without Torch. These checks do not establish native grasp feasibility.

The actual comparison uses the same two source frames, masked merit policy,
30 outer steps, 10 inner iterations and 300 seconds per pose under the unchanged
global resource guard. The first nonlinear run in
`reports/box-lift-guarded-restoration-v3/` fails at 295.375 seconds when an
unwrapped SciPy constraint callback queries beyond a normalized control bound.
The original error and pipeline remain failed. A separate NumPy replay verifies
all 68 partial pose records and the two retained decisions, with last retained
box depth 22.136 mm. There is no final result or frame-98 result for that attempt.

The repaired nonlinear callback clips its search queries to the declared trust
box and global controls before measurement, recording each clipped request.
The final replay still uses exact original inequalities. A regression fixture
forces a callback just past the bound and proves that measurement, derivatives
and retained controls stay inside the original bound. This changes proposal
handling, not contact or edit-budget acceptance limits.

Optional `--row-chunk 16` groups exact derivative rows into bounded batches;
all original rows and vertex dependencies remain present. [PyTorch documents
batched vector-Jacobian products](https://docs.pytorch.org/docs/stable/generated/torch.autograd.grad.html)
as experimental, so no speed improvement is assumed without measurement.
Fixtures compare every row to scalar backward, including maximum/minimum ties,
and compare the integrated sparse path to dense derivatives for all three
primitive types and both constraint grouping modes. The default scalar path
remains available. The chunk cap limits derivative batching, not total memory;
the unchanged process-tree resource guard still applies.

The bounded callback and chunked retry is preserved separately in
`reports/box-lift-guarded-restoration-v4/`. Its supervisor completes in 232.14
seconds with 666,415,104 bytes peak process-tree RSS. Pose solve times are
121.266 / 93.375 seconds, retaining five / four steps before both stop with no
guarded improvement. Dense/chunked initial derivative timings are
6.031 / 1.453 seconds at frame 72 and 5.906 / 0.813 seconds at frame 98. All
initial values and Jacobian entries match exactly in these recorded computations.
These timings compare the combined sparse/batched path to dense scalar backward;
they do not isolate batching alone or establish a full-clip speedup.

| Measurement | Frame 72 | Frame 98 |
| --- | --- | --- |
| Left/right hand error | 4.755 / 4.989 mm | 4.944 / 11.144 mm |
| Left/right normal error | 23.831 / 8.886 degrees | 19.505 / 17.327 degrees |
| Prop vertex depth | 21.365 mm | 11.124 mm |
| Maximum raw-relative joint displacement | 193.859 mm | 219.680 mm |
| Added speed to fixed neighbors | 0.574 / 0.787 m/s | 0.531 / 0.456 m/s |
| Minimum floor vertex Y | 5.277 mm | 7.121 mm |

Both poses retain every originally passing row and every protected edit/floor
row. Rotation/root limits pass. Frame 98's displacement now passes 220 mm, but
its already-failed right hand worsens from 5.085 to 11.144 mm under the explicitly
declared merit tradeoff. Neither pose passes the original grasp checks; neither
is a usable animation. This regression prevents describing the lower collision
depth as a successful interaction repair.

A separate NumPy replay checks all 280 saved retry pose records, all nine retained
decisions, all original/archive/protocol/audit/pose bindings, and complete native
vertex floor/prop-depth. Every distinct inner query is verified as unretained.
No full-clip, between-key, triangle/volume, imported rig, engine or human approval
is inferred. The earlier failed partial study remains intact.

The next proposal should protect even failed hand-distance rows from increasing,
diagnose which original limits stall the repair, and coordinate the contact
window. The whole-project goal and all fourteen unapproved capabilities remain
unchanged. The preceding published batch's hosted native CPU jobs pass on both
Windows and Ubuntu; its complete workflow and this newer batch are not yet
reported as green.
