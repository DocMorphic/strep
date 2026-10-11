# Root-fixed kick correction: retained failure and storage comparison

The first correction attempt on the existing Kenney kick keeps the root path
and clip endpoints fixed. It removes root translation from the earlier declared
permissions and retains nine body rotation tracks, 27 control components,
30-degree track bounds and a 22-cm all-joint displacement bound. The original
source-rate caps and their 1e-5 tolerance remain unchanged. These are development
edit-preservation bounds, not anatomical or style calibration.

The surface-vector solver uses minimum-envelope guidance, two primary iterations,
a 0.02 trust fraction and three allowed decoded-restoration steps. Complete
geometry always determines acceptance: all 1,029 triangle-referenced vertices
at all 2,017 declared times, with the original Y=0 / 5-mm floor screen. There
are no invented support, point-contact or gameplay targets.

The run completes within its unchanged 900-second execution limit; its last
execution observation is 429.282 seconds. Its 436 resource observations replay.
Both iterations finish with **no accepted step**. The final zero-control proposal
passes the original point/motion conditions and retains the root pose exactly,
but fails floor clearance at **234 / 2,017 times**, peaking at **49.727615 mm**.
The original source remains selected; no animation is approved or promoted.
The final root comparison covers all 120 original keys; the separate paired
study below checks root preservation at all 2,017 declared floor times.

Ten changed exports complete geometry checks. Every one fails original motion
conditions and the floor screen. The strongest apparent depth change is only
about **6.8 nanometres**, which is not useful clearance improvement. The first
proposal solve returns `AlmostSolved`; its minimum-norm phase reports
`InsufficientProgress`. Decoded restoration reports `PrimalInfeasible` for its
local tightened model. The second proposal solve reports `InsufficientProgress`.
These statuses do not prove that the full correction problem is infeasible.

## Same controls, two existing storage modes

A separate controlled comparison re-exports the original zero controls and
the largest/smallest already evaluated proposal fractions with the existing
`unit` and `source-scale` quaternion storage policies. It runs no optimizer,
changes no control, cap, rig, target or clock, and makes no selection decision.
Each output is decoded and assessed against the original 108,117 native
conditions. Every triangle-referenced vertex is also queried at all 2,017 floor
times; this plane query does not replace the complete geometry audit.

| Controls | Storage | Native failed conditions | Maximum normalized excess | Floor failed times |
| --- | --- | ---: | ---: | ---: |
| Original zero | Unit | 0 | 0 | 234 |
| Original zero | Source-scale | 0 | 0 | 234 |
| Largest proposal | Unit | 72 | 0.0000725964 | 234 |
| Largest proposal | Source-scale | 92 | 0.0000460910 | 234 |
| Smallest proposal | Unit | 25 | 0.00000283304 | 234 |
| Smallest proposal | Source-scale | 1 | 0.0000114550 | 234 |

Source-scale preserves source quaternion length before Float32 storage instead
of normalizing the original quaternion before multiplication. Changing storage
changes the measured native failures, but **neither mode passes the changed
proposals**. Fewer failures can coexist with a larger worst excess. Both modes
produce the same failed peak floor depth at each compared control value and
retain the root pose exactly. This does not justify switching the default mode,
loosening limits or claiming that storage explains the failure to correct motion.
All 138 comparison resource observations replay with archived bindings intact.

## Diagnostic population and actual skin witness

The first separate vector diagnostic checks the eleven exports with completed
probe geometry receipts. It additionally checks joint displacement at the
expanded geometry clock, rather than only at the producer's original uniform
motion clock. Its 1,951,587 combined rows therefore must not be described as the
exact original acceptance population. It reproduces recorded merit values and
reports 235 position-acceleration and 355 angular-acceleration failures across
the ten changed probes; these are repeated per-probe observations. There are no
reported position-speed or angular-speed failures. Its geometry figures are
producer receipt summaries, not an independent geometry requery.

The subsequent exact-row verifier rejects this accounting and then a row-order
mismatch. The producer's mixed NumPy indexing orders displacement rows by joint;
the diagnostic initially orders them by time. Version four corrects the clock
and ordering and matches every freshly reconstructed producer residual to
1e-10 relative/absolute tolerance: **108,117 original conditions per export,
1,189,287 across eleven exports**. Only the original zero-control export passes.
The acceleration failure counts above remain unchanged. This shares the original
sampler, edit layout and cap builder; it is not independent motion certification.
All 617 resource observations replay. Failed verifier outputs remain retained;
the first diagnostic's 85-observation resource trace remains valid for its
actual, broader diagnostic scope.

The retained full-mesh witness at 0.7333333492279053 seconds is vertex 391,
weighted entirely to **LeftFoot, node 52**. An initial static permission probe
mistakenly selects the right leg. Neither its hip-only nor hip/knee/foot/toe
variant can move that left-foot witness, and both local solves fail without a
changed pose. That failed probe is retained; it is not an infeasibility claim
about the left leg or the complete motion.

The corrected static probe uses the actual left-foot influences. Its hip-only
attempt reduces depth to about 4.500086 mm but moves a joint by 303.026 mm,
exceeding the original 220-mm bound, and is rejected. With the hip, knee, foot
and toe permitted, the local solve passes its sampled static conditions:
**4.5-mm depth, 185.338-mm maximum joint displacement**, with edits of
3.606 / 9.078 / 0.942 / 0.916 degrees respectively. All unselected local
transforms remain identical; root reconstruction error is below 2.23e-16.
All 63 resource observations replay. This is a single pose, with no temporal
source-rate, engine, support, semantic or human-quality approval. The next
screen maps this direction into explicit native clip clocks and rechecks the
original caps and complete declared geometry population before any further fit.

## Static direction through native clip storage

The follow-up adds the three measured left knee/foot/toe rotation permissions,
retaining all nine earlier body permissions, 30-degree track bounds, a 220-mm
all-joint bound and frozen root/endpoints. It maps the passing pose direction
into the existing middle edit knot, then separately into an added knot at the
problem frame. The first mapping compensates for its knot weight at that frame;
the second uses the static direction directly. No optimizer runs in this screen.

Both actual serialized clips preserve unpermitted tracks, frozen keys and static
payloads. Their original source-cap arrays match byte-for-byte. Each is decoded
against **108,471 native conditions** (the extra 354 rows are the three added
track bounds), and receives complete **2,017-time / 1,029-vertex / 1,604-face**
declared geometry evaluation. The 94 resource observations replay.

| Edit clock | Controls | Failed native rows | Floor failed times | Peak floor depth | Maximum joint displacement |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original middle knot | 36 | 2,022 | 83 | 9.994 mm | 498.206 mm |
| Added peak knot | 72 | 68 | 110 | 7.505 mm | 185.338 mm |

Both root paths remain exact at every declared geometry time. The original
middle knot produces 497 failed displacement rows and 1,525 failed rate rows.
The added peak knot passes the displacement bound but fails 48 position-speed,
six position-acceleration, nine angular-speed and five angular-acceleration rows.
Neither passes the original motion and floor conditions; the original animation
remains selected. A passing static pose therefore does not become a passing clip
merely through interpolation. The next bounded pilot will try to restore the
added-knot proposal's native constraints while retaining its complete geometry
checks. Any intermediate model improvement still requires actual decoded
acceptance and later engine, support, semantic and review evidence.

The first restoration pilot stops before solving because of a strict
preview/decoder surface disagreement near the final Float32 key. That failed
run is retained. The [endpoint sampling correction](native-endpoint-sampling-v1.md)
fixes the batch preview without changing the asset or tolerance; its corrected
restoration rerun is a separate record, with no inherited motion approval.
That rerun completes but its local 0.02-trust affine model returns
`PrimalInfeasible`, producing no direction or new clip. All 198 resource
observations replay. The frozen-model row-group diagnostic remains locally
infeasible when all native rows stay hard and only the floor guards become soft.
Its counterfactual with soft rate rows produces a direction but predicts 149
native failures, and is never exported. All 204 diagnostic resource observations
replay. Actual clip acceptance and source caps remain unchanged.

Local records are under `reports/kenney-kick-root-fixed-fit-v1`,
`reports/kenney-kick-proposal-diagnostics-v1` through `v4`,
`reports/kenney-kick-storage-comparison-v1`, and
`reports/kenney-kick-pose-permissions-v1` / `v2`, and
`reports/kenney-kick-pose-to-clip-v1`. Acquired and generated payloads
remain excluded from public Git. No model weights, training admission, held-out
fixtures, release gates or capability approvals change.

The [contact and rig workflow at e7aced8](https://github.com/DocMorphic/strep/actions/runs/38166713174)
passes **552 Python checks per OS** on both Windows and Linux: 485 contact/rig,
35 lineage and 32 game-package checks, plus the offline editor suite. These
software outcomes verify the new encoding audit and existing authoring contracts;
they do not approve the failed correction above. See the preceding
[seven-action export/encoding study](kenney-native-export-v1.md).
