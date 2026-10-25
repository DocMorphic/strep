# Time-varying arm repair: measured interpolation failures

The sequential repair clears 11 of 17 control poses, but the serialized clip
still fails geometry at 11 of 33 assessed times. It also deviates from the
intended sparse correction schedule by up to 2.89451 mm, exceeding this
experiment's declared 1 mm limit. The candidate is retained as failed evidence;
it does not replace the original or confer release approval.

## Method

Continue from the explicitly expanded-cap diagnostic in
[the shoulder study](wave-shoulder-temporal-v1.md). Use its immutable
floor-corrected source and trial 58 seed. At 17 evenly spaced times, fit local
rotation edits for nodes 14–18. Root translations remain fixed; caps are
25, 25, 25, 35 and 25 degrees. Both clip endpoints are editable for this study.

The first pose starts from the previous constant edit; subsequent poses start
from the preceding selected edit. Limit each joint's neighboring rotation-vector
change to 8 degrees, with a 1e-4 relative fitting reserve. This limits correction
changes, not the character's total angular velocity or anatomical joint range.

Each pose receives up to three SLSQP rounds of 60 iterations. Every discovered
pair contributes nine reference-axis vertex separation objective terms; the
floor and edit limits are hard constraints. Newly detected proper pairs enter
later rounds. After each round, rerun the complete triangle audit and strict
declared bounds. Bounded proposals with fewer proper pairs, then fewer new
pairs, may seed the diagnostic schedule even when still failing. This selection
is not acceptance: all new or remaining proper crossings reject a complete repair.
Solver success flags never override the measured post-fit results.

Interpolate the 17 correction vectors onto all 120 existing native keys, then
export and reload the GLB. The exporter preserves its existing-key contract;
it does not insert the off-key control times or promise the desired correction
function between saved keys. Check complete source and candidate triangles at
the 17 control times and their 16 midpoints. Separately assess decoded floor,
angular limits, correction rate and intended-schedule skin deviation at 4,737
native/eighth-interval/960 Hz observations.

## Results

| Check | Observation | Decision |
| --- | --- | --- |
| Selected control bounds | All 17 satisfy floor, rotation and neighboring-edit limits | Pass for these controls |
| Selected control geometry | Six failed poses: indices 0, 6, 10, 11, 13, 14 | Fail |
| Serialized geometry | 11 of 33 times fail; 273 introduced pair observations | Fail |
| Decoded floor | Maximum 4.821543 mm; limit 5 mm | Pass on dense sample set |
| Decoded rotation edits | All within declared caps | Pass on dense sample set |
| Decoded correction rate | Maximum 32.274489 degrees/s; diagnostic limit 40 | Pass on dense sample set |
| Intended-schedule skin deviation | Maximum 2.894510 mm; diagnostic limit 1 mm | Fail |

At 1.8593750149011612 seconds, between two selected controls with zero proper
pairs, the exported candidate has 35 proper pairs, all new relative to the
source at that time. This directly disproves inferring interval clearance from
the two control poses. The source itself has 53 proper pairs at that time;
reduced counts do not excuse introducing different collisions.

The largest schedule deviation occurs near 3.222916666666667 seconds, an
off-key control time. Resampling a piecewise correction onto the native clock,
then interpolating the resulting quaternion products, is not generally the
same operation as applying that correction to the source at each observation.
The study measures their combined difference; it does not isolate each cause.
The discrepancy is separate from the exporter's key-level round-trip check.

A complete-triangle orthographic comparison of four times was inspected.
The candidate visibly holds the resting arm farther from the torso. Static
projections can hide intersections and cannot establish natural movement, but
this observation reinforces the need for explicit action/resting-pose
preservation before choosing a repair. No human quality rating was entered.

## Verification and limits

Local ignored reports in the development checkout retain:

- `reports/wave-temporal-arm-v1/`: frozen request, guarded worker, all attempted
  and selected poses, separation rows, complete audits, schedule and candidate.
- `reports/wave-temporal-arm-replay-v1/`: independent reconstruction of every
  selected control, strict bound checks, hash/decision replay for all 33
  serialized geometry records, and fresh complete geometry replay at indices
  0, 16 and 32. It also contains dense decoded observations and `comparison.png`.
- `published-verification.json`: a separate replay of recorded dense maxima,
  decisions, failure counts and resource receipts. This last replay does not
  recompute geometry. Both workers completed; 344 resource observations replay.

Full geometry was not checked at every dense time, and the continuous interval
is not certified. There is no engine, contact-intent, action-semantic, animator,
cleanup-time or release approval. Production solver code is unchanged; no new
production regression-suite pass is claimed.

## Next implementation step

Fit the actual native-key interpolation at explicit failing interior times,
rather than optimize independent pose controls and assume their resampling
preserves constraints. Reuse the existing `native_key_pose_map.py` machinery
after qualifying it against this rig and export path. Couple both bracketing
keys, constrain their neighboring corrections, and recheck all affected
intervals for newly introduced pairs. Begin with the 1.859375-second witness.

Include resting-arm and action-preservation targets in later repair selection;
increasing angular freedom alone does not establish professional motion.
Broader action, rig, object, partner, transition and review requirements remain
unchanged under the single project goal.
