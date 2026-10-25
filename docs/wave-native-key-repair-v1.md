# Native-key interpolation qualification and local repair failures

The existing native-key model predicts the saved wave accurately at the
previously missed collision time. That closes the representation gap for this
fixture, but the tested two-key repairs do not clear the collision. All nine
repair proposals remain rejected, including two for which the optimizer reports
success. No motion is promoted and no release criterion is changed.

## Saved-motion qualification

Use the rejected temporal wave from [the preceding study](wave-temporal-arm-v1.md)
at 1.8593750149011612 seconds. Its surrounding native keys are 55 and 56. Full
surface location metadata identifies all 35 proper-crossing pairs at this time
with dominant skin nodes 16 and 21, the right hand and head.

Construct `PartitionedAffineKeyPose` and `KeyPoseMap` on that candidate with
five-degree residual coordinates. These are additional proposal coordinates,
not a reset of the original edit allowances. The older 35-degree left-shoulder
edit remains part of the input; this qualification does not broaden the pose
model's own supported cap domain.

Three deterministic probes exercise nodes 14–18 at both keys. Export each as
a separate animation and compare all 3,273 vertices and complete node poses
at 36 times across the three affected native intervals. Native clocks,
geometry, original animations, unedited channels and keys are preserved.

- Maximum pose-matrix error: 8.882e-16.
- Maximum skin position error: 8.945e-16 m.
- For two probes, all 30 derivative columns are compared with central
  differences over every vertex; maximum absolute error is 1.614e-10 per
  normalized control coordinate.

This qualifies the model/export path on the observed fixture and probes. It
does not approve those probe motions, arbitrary rigs, or unobserved times.

## Two-key repair trials

Allow only nodes 14–16 at keys 55 and 56 to change. Preserve the left arm,
translations and every other key. Bound additional edits by five degrees,
total right-arm edits by 25 degrees relative to the immutable floor-corrected
source, and native-key correction speed by 40 degrees/second. Keep the 5 mm
floor limit. Each experiment uses up to three SLSQP rounds of 60 iterations;
complete triangle audits and strict limits decide selection after every round.

| Experiment | Target proper pairs by round | Serialized native bounds | Outcome |
| --- | --- | --- | --- |
| V1: reference directions, reserve on all angular rows | 29, 29, 26 | All fail | Reject |
| V2: reference directions, reserve only on editable angular rows | 37, 37, 37 | All pass | Reject: worse than 35 |
| V3: current-triangle directions, same corrected bounds | 35, 35, 35 | All pass | Reject: no count improvement |

Every discovered pair contributes all nine vertex-separation objective rows;
new proper pairs enter subsequent rounds. Directions are proposal guidance,
not acceptance tests. V3's last two solver success messages do not establish a
repair. These finite searches also do not prove that no feasible repair exists.

V1 incorrectly applied an extra fitting reserve to fixed neighboring keys.
Two fixed angular inequalities then had negative normalized gaps of about
-9.51e-8 and -1.35e-8, despite meeting the actual 25-degree acceptance limit.
Changing the editable keys cannot change these rows. V2 applies the reserve
only where the solver can edit a key; immutable neighbors retain the original
acceptance caps. No source values or acceptance tolerances were relaxed.
The original V1 experiment and its failures remain intact.

Independent serialization confirms V1's rejected proposals reach about 8.66
degrees of residual edit and 259.78 degrees/second of native correction speed.
V2 and V3 stay within the declared bounds, reaching about 1.33321 degrees of
residual edit and 39.9961 degrees/second. The short time support constrains
how much additional motion can be introduced, but these observations do not
prove that speed is the only obstacle.

## Evidence and scope

The diagnostic exports select no proposal: their tracks equal the rejected
temporal input. The project's original remains selected. Across the affected
interval, 13 of 14 assessed geometry times still fail; 121 dense observations
retain floor, angular and correction-rate results. None of these exports is
an accepted full-clip repair.

Ignored development-checkout reports retain:

- `reports/wave-native-key-map-v1/`: probe exports, complete skin observations,
  derivative comparisons and surface locations.
- `reports/wave-native-key-repair-v1/`, `v2/` and `v3/`: exact requests, all
  proposals, separation directions, bound records and decoded interval checks.
- `reports/wave-native-key-replay-v1/`: independent serialization of all six
  V1/V2 proposals, original and residual limit checks, target surface flag
  replay, unchanged selected-track checks, and dense floor/angular replay.
- `reports/wave-native-key-replay-v2/`: the same checks for all three V3
  proposals, plus fresh complete before/after geometry at all 14 interval times.

Six guarded workers complete, with 550 resource observations replayed.
Production code is unchanged; no fresh production regression-suite or hosted
CI result is claimed. There is no engine, semantic, animator or release approval.

## Next experiment

Widen the editable time support to ten native keys around this same failure,
while retaining the five-degree residual, 25-degree total and 40-degree/second
limits. Keep the left arm and translations fixed. Audit every newly affected
interval and preserve failures. This is a new experiment, not an inference
that a wider window must work. Action-preservation and resting-pose constraints,
other clip failures, broader action/rig/object/partner studies, and developer
and animator reviews remain required by the full project goal.
