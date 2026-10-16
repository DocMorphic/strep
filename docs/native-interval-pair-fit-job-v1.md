# Reusable paired native contact/surface fitting

`scripts/native_interval_pair_fit_job.py` turns the source-zero paired fitting
experiment into a recipe-driven offline command. It uses supplied native rigs,
contacts, geometry and explicit edit permissions. It does not generate prompts,
select an animation or grant motion-quality approval. It is a backend component;
Studio integration and full release validation remain pending.

Run through an owned resource-guarded worker in the pinned CPU environment:

```text
python scripts/native_interval_pair_fit_job.py recipe.json fresh-output
```

The recipe uses schema `strep-native-interval-pair-fit-v1` and contains:

- `contacts` and `geometry`: each a relative or absolute `path` and exact
  lowercase `sha256` for an original source declaration.
- `actors`: exactly the two original actor IDs. Each has pinned `request` and
  zero `controls` files, plus a contiguous list of existing `active_keys`.
- `surface_samples`: sorted unique indices in the original geometry clock.
  Surface derivatives must use exact existing quaternion keys.
- `surface_seed`: an explicit integer seed for source mesh queries. The job
  saves the before/after query states and restores the caller's generator state.
- `trust`, `difference_step`, `contact_reserve_m` and `maximum_nonzeros`:
  explicit bounded proposal settings. The complete combined sparse model must
  fit its budget; no rows or columns are truncated.

Source hashes, actor IDs and zero seeds are validated before fitting. Output
must be fresh and separate from immutable input results. Actor IDs cannot
escape the output directory. Source rigs, poses, original rate caps, root and
boundary contracts remain bound through the existing interval model. New edit
permissions must be declared in the actor requests; they are not inferred from
an action name.

All original native and floor-protection rows remain hard. The contact reserve
tightens only authored **position** norms; relative-speed norms retain their
own units and caps. Fixed surface guides are proposal objectives. If no source
surface witnesses exist, the job runs a contact-only proposal and does not
infer geometry clearance.

The job saves its source arrays, layouts, original caps/scales, complete affine
system/Jacobian, surface rows, query states, solver output and implementation
snapshot. A returned solver direction is saved **before** the full hard-row
postcheck, so a rejected iterate remains diagnosable. Only a passing affine
proposal is exported. Actual coupled contacts are then measured on the export;
full decoded native/floor/mesh validation remains a separate required stage.
Every output keeps `original_selected=true` and quality/release approval false.

Fifteen source tests exercise hash and zero-epoch rejection, actor-path safety,
bounded settings, contact row units, complete original native-cap retention,
unchanged source files, query-generator restoration, rejection of a forced
infeasible iterate even with a `Solved` label, and a forced feasible export
remaining unselected pending independent validation. Solver injection in the
last two cases tests the caller's gate, not numerical solver capability; the
separate full job case uses the actual solver.

All 15 pass locally in 73.06 seconds. The guarded run completes in 89.375
seconds including admission, peaks at 155,557,888 process-tree bytes, and
independently replays all 90 recorded resource observations. The guard stays at
512 MiB for these small fixtures, plus the unchanged 600-MiB free-memory floor.
Larger paired matrix studies retain the 1-GiB profile. These source tests do not
establish animation quality, engine playback, held-out coverage or human review.

The next development case adds explicitly selected finger controls to the
existing high-five source. The source inspection finds all 24 finger joints per
actor have compatible LINEAR tracks on the original wrist clock. Complete world
rate caps and scales replay exactly against the original saved baseline at the
same uniform clock and bins. Local finger motion and world-joint motion are
measured separately; local near-static tracks do not imply zero world-rate
headroom. No source bounds or model weights are changed by this inspection.

At commit `d966978`, [hosted focused run 38893122451](https://github.com/DocMorphic/strep/actions/runs/38893122451)
passes all 15 cases on Ubuntu (10.73 seconds) and Windows (74.24 seconds).
Inventories now list 528 Python modules and 45 Node suites, with 92 Python
modules and five Node suites in the contact/rig subset. This remains focused
source verification, not full-inventory or animation-quality approval.

The source-only finger inspection independently replays the complete original
rate caps/scales for both actors. It uses 477 samples at 120 Hz and the identical
four source bins. All 24 finger joints per actor have existing compatible
LINEAR channels on the 120-key wrist clock. Maximum observed local finger speed
is 33.210447 degrees/s for A and 66.596863 for B; maximum world-joint speed is
563.217710 and 820.943799 degrees/s respectively. These are source observations,
not anatomical limits. The inspection guard completes in 34.406 seconds at
125,771,776 bytes, with all 36 resource observations replayed.

The expanded development fit declares shoulder, upper arm, forearm, wrist and
the first two joints of each right-hand finger: nodes 40–45, 48–49, 53–54,
58–59 and 63–64 for this supplied SOMA rig. These IDs are not a universal rig
mapping. Every declared rotation permission is 10 degrees; the original 50-mm
joint displacement bound, world-rate bounds, source epoch, roots and frozen
endpoints remain in force. Eight active native keys (56–63) per actor give
672 controls under the existing 768-control budget. Five contact-near geometry
times remain the initial selected comparison population.

Compared with the earlier arm-only fit, this changes the edit permissions,
window and local trust radius (0.2 versus 0.1). It is explicitly not an isolated
finger ablation. No old native matrix is reused. The new source surface model
retains all 29,378 rows and has 1,246,068 analytic nonzeros; every canonical
source vertex still agrees with the native decoder to 6.661338e-16 metres.
The rebuilt system contains 693,420 norm rows and 2,941,970 nonzeros, with
660,002 native rows, three coupled contacts and 4,034 floor-protection rows in
its 664,039-row hard prefix. Clarabel reports `Solved` after 53 iterations and
the full affine postcheck passes. The guarded job completes in 660.781 seconds
at a 955,412,480-byte peak, with all 650 resource observations replayed.

The exported candidate meets all three authored 30-mm contacts at 29.530898,
11.275910 and 29.764394 mm. The 29.5-mm search reserve is an affine target;
actual authored acceptance stays 30 mm. Independent actor A validation finds
49 native failures, so the candidate is rejected despite the solver's success.
All 309,831 original source native vectors/caps/scales replay exactly; 20,170
new finger edit rows are separately declared. Actor A preserves its original
floor bounds at all 2,017 times but retains all physical floor failures. Its
guard completes in 152.672 seconds at 274,800,640 bytes with 152 observations
replayed. Actor B has 44 native failures and preserves all original floor
bounds while retaining the physical floor failures. Its guard completes in
140.156 seconds at 272,584,704 bytes, with 140 observations replayed. Rebuilt
source references match all 619,662 original native vectors/caps/scales; the
40,340 additional rotation-edit rows correspond to the declared finger
permissions. Every decoded rotation-edit and joint-displacement row passes.

| Actor | Position speed | Position acceleration | World angular speed | World angular acceleration |
| --- | ---: | ---: | ---: | ---: |
| A | 2 | 14 | 5 | 28 |
| B | 2 | 12 | 7 | 23 |

All 93 native failures are original speed/acceleration limits. The counts above
come from complete saved residual replay and structural row attribution, not
from a selected witness subset. They are source-reference limits, not calibrated
anatomical thresholds.

The separate scene stage replays all 660,002 saved native rows and every cached
mesh vertex against the actual exports, freshly rechecks coupled contacts, and
calls the unchanged direct geometry evaluator. Geometry is explicitly measured
**diagnostically despite native failure**. The qualification condition still
requires zero native failures, so these measurements cannot approve the clip.
This guard completes in 89.328 seconds at 307,367,936 bytes; all 90 resource
observations replay.

The five-time geometry comparison improves 19 measurements, regresses six and
leaves ten unchanged. The largest directional depth decreases from 20.590680 to
15.727350 mm, still above the 5-mm screen. Four intersection counts increase;
at 2.033333302 seconds A-inside-B peak depth increases from 7.778888 to
7.948739 mm and the count of A vertices deeper than 5 mm increases from 18 to 32.
Both actors also retain all 2,017 physical floor failures. The candidate remains
rejected and the original remains selected. This study does not establish a
quality benefit from finger articulation alone.

Next, distinguish continuous-preview errors from stored-export effects and
attempt bounded nonlinear rate restoration using the measured current motion
while retaining the original reference caps, layouts and source assets. A
recentered proposal must not treat the failed candidate as a new source. Surface
objectives also need to account for the remaining intersection regressions;
neither a successful solver status nor better maximum depth proves acceptance.
