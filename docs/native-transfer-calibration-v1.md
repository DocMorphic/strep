# Bounded reference calibration after native rig transfer

`scripts/native_transfer_calibration.py` creates a separate native transfer from
the original source clip and a bounded revision of the target's reference-axis
profile. This is a model-free, whole-clip correction option. It can change start
and end poses; transitions and loop boundaries must be checked again. It does
not change the existing scene editor's frozen endpoints or edit permissions.

## Inputs and protected intent

Start with a completed, verified `native_transfer_scene.py` comparison. A recipe
binds that comparison's `result.json` SHA256 and declares each editable actor's
mapped rotation roles, angular limits, optional root-offset radius and maximum
joint displacement. Actors without permission remain unchanged. World points,
object geometry and pose tracks, partner targets, vertex correspondences,
placements, contact times, reductions and limits remain exact.

```json
{
  "schema": "strep-native-transfer-calibration-v1",
  "comparison": {"path": "comparison", "sha256": "<result.json SHA256>"},
  "actors": {
    "A": {
      "role_rotations_degrees": {"LeftArm": 15, "LeftForeArm": 15},
      "maximum_root_offset_m": 0,
      "maximum_joint_displacement_m": 0.06
    }
  },
  "search": {"evaluations": 210, "calls": 1800, "seconds": 120, "starts": 7}
}
```

Run with the installed CPU dependencies:

```powershell
python scripts/native_transfer_calibration.py calibration.json separate-output
```

The comparison path resolves relative to the recipe. Output must be fresh and
outside the comparison. Existing target geometry, skin and animations survive;
the retransfer appends the source clip and selects its index explicitly. The
original scene remains selected. No checkpoint is sampled, modified or trained.

## Conditional rejection, search and readback

Before fitting, exact rational component and sphere bounds check whether a fixed
target is reachable under the declared joint-displacement limit and stated
rotation-norm/arithmetic assumptions. Incoming contacts against an editable
partner are included. Both editable sides are explicitly uncertified. A verified
conflict saves a portable receipt and skips optimization and export. No conflict
does not establish feasibility.

Reference-rotation vectors and the optional constant rig-world root offset use
radial bounded coordinates. Limits cannot exceed 45 degrees per role, 0.22 m
root offset or 0.22 m joint displacement. Native transfer restrictions still
apply: explicit humanoid mappings, rigid unit-scale references and supported
LINEAR source channels. Whole planned populations reject on size limits rather
than being truncated.

Up to seven deterministic starting poses share one total evaluation, objective
call and time budget. Alternative seeds address the weak gradient of a straight
arm when shortening reach. The bounded least-squares search is local; exhaustion
is retained and is not a global impossibility proof. Search aims 0.1% inside
contact limits to provide serialization margin. Final acceptance uses the
unchanged authored limits on the actual exported GLB.

Position checks use every common native/frame/quarter contact time. Hold speed
checks retain all twelve existing frame populations, including object-relative
errors. All target joint origins stay within the author displacement budget.
Velocity and acceleration limits for positions and rotations remain derived
from the original transferred clip at 120 Hz, in four bins, with the existing
fixed tolerance. A constant profile change does not guarantee those checks pass
for a moving articulated clip; exported results are independently measured.

## Evidence integrity and scope

The output includes the complete portable comparison, original recipe and
implementation snapshots, reach witnesses, bounded controls/search receipts,
new profiles/transfers, unchanged contact intent, common-clock observations,
frame audits and decoded displacement/rate measurements. `verify(output)`
reconstructs the expected profiles, checks the native source/target snapshots,
replays transfer fidelity and every measurement, and rejects rehashed changes
to contacts, placements, objects, controls, profiles, observations or approval
flags. Both successful and rejected outputs replay after relocation.

Point-contact success is separate from geometry, surface orientation, engine
playback, dynamics and human quality review. The calibration receipt deliberately
leaves those flags false. Generated triangle patches are software fixtures;
they are not anatomical hands, opposing palms or realistic box grasps. Production
rigs, held-out motions and timed developer/animator cleanup remain open.

## Development measurements

The small-scale moving fixture transfers a 19-joint rig to an independently
generated target at 1.005 scale, retaining a moving root, box, partner and exact
0.0853725 s foot touch. A single-start trial reduced errors but failed the 2 mm
contact limit. A multi-start trial reached the limit before export but retained
a 3 nm serialized excess. Both failed trials remain saved. The inward-search
trial passes the original sampled point contacts, with maximum error 1.9981 mm,
maximum hold slip 1.081 mm/s and maximum joint displacement 28.253 mm against
the unchanged 60 mm author cap; all four source-rate populations pass.

The 1.3-scale target remains a conditional reach conflict under the same cap.
Its targets and limits are not widened. This method handles small reference
calibration corrections; it does not solve arbitrary proportion changes or
general scene-aware animation.

The saved candidate also passes an actual CPU/headless Godot study. Two owned
engine processes save and reload two native actor Animation resources per run
and query 392 clock times each, including every common calibration position
time. The original transferred scene retains its contact failure; the calibrated
scene passes the same imported contact checks. Both runs pass imported bone,
raw-skin and object fidelity under the existing limits. Maximum pose component
error is 4.15e-7 and maximum skin position error is 5.07e-7 m. Both processes
exit zero with clean logs; the original inputs and archived methods remain
unchanged. Engine evidence stays a separate receipt and does not turn the
calibration's geometry, surface or quality flags into approvals.

Local engine receipt: `reports/native-transfer-calibration-engine-v1/result.json`,
SHA256 `9c33778f61477d6ad33e83e359dc750181af86c8c2148601c25c9298cf9884f8`.
Generated payloads stay outside the public repository. No live Studio/browser,
rendering, GPU, production anatomical asset query, new model sampling/training
or human review was performed.

The 33 regression cases cover exported contacts/rates, conditional reach
rejection, both editable partners, profile/FK agreement, bounded controls,
preserved target clips, complete clocks, portable replay, malformed inputs,
rehashed payloads/approval flags and shared search budgets. The initial run
passed 32 cases; one invalid-NaN setup failed because the normal JSON writer
correctly refused the input. After correcting that test's external-input writer,
all twelve parameters of that function pass a focused rerun against an immutable
generated comparison. The other 21 test function cases are unchanged and had
already passed. No expensive optimization or engine study was repeated for the
test setup correction. This is 33 passing cases across attempts, with zero skips,
not a claim that the full hosted CI workflow has finished.

Source validation receipt SHA256:
`d805fa656cc0eb293a4998986cb5b3defaaf4cc9532fa8949f54c39a4866316a`.
The parsed CI proof adds only this Python suite and preserves all other workflow
fields, dependency pins, environments, permissions, matrices and time budgets;
receipt SHA256 `0674b50235a143b896a89f451164416b93ffffcbaa97f85c1c2dd4791cc27b00`.
