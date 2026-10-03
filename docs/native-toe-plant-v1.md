# Explicit additional foot rotations for planting

The experimental extra-rotation planting job lets an author permit named
animated joints below a support foot and bound each joint's cumulative local
rotation relative to the source. This addresses the protected toe influences
measured in the earlier articulation report. More freedom is a hypothesis to
test, not evidence that a correction will pass or look better.

The existing leg-only job and Studio path retain their original contract.
`scripts/native_support_permissions.py`, `scripts/native_toe_plant.py` and
`scripts/native_toe_plant_job.py` implement a separate, explicit CLI path.
An extended-contract result is labeled as such and never represented as an
original leg-only preservation pass.

## Permission contract

The `strep-native-support-rotation-permissions-v1` document binds the source
GLB and original support draft by SHA-256. Each listed support must already
exist in that draft. Its nonempty rotation list names distinct integer skin
node IDs below that foot and supplies an angle limit from 0.0001 to 45 degrees.
Root, unrelated nodes, existing leg-chain nodes, missing/static rotation
channels, unknown fields, duplicate declarations and mismatched native clocks
are rejected. Additional rotations currently need the original leg clock;
shorter/helper-bone or non-LINEAR tracks are not silently resampled or added.

For example, with node IDs obtained from the supplied source rig:

```json
{
  "schema": "strep-native-support-rotation-permissions-v1",
  "source_sha256": "<source GLB SHA-256>",
  "draft_sha256": "<original support draft SHA-256>",
  "supports": [
    {
      "id": "left-stance",
      "rotations": [{"node": 54, "maximum_angle_degrees": 2.0}]
    }
  ]
}
```

Each new node varies only interior keys of that support's original edit
window. Boundary/outside keys, all translations/root tracks, unrelated
rotations, channel clocks/modes/duration and static rig/mesh/image payloads
stay protected. Component boxes include the authored rotation ball; radial
constraints independently reject excessive box corners. The final extra-angle
audit uses the same 0.0001-degree serialization tolerance as existing leg
screens; the decoded proposal model still requires its strict angle rows.
Bounds apply cumulatively from the original source, not separately to each
optimization step or warm start.

The model inherits original uniform 120 Hz rates, all four source bins,
tolerance, affected descendants, authored support/edit limits and all twelve
fixed frame clocks. It adds explicit extra-angle rows and corresponding
derivative dependencies. Source caps are never rebuilt around a proposal.
Native skin is the existing validated/normalized rig-loader representation;
actual imported binding weights remain an independent engine measurement.

## Proposal, import and selection

```powershell
.venv/Scripts/python.exe scripts/native_toe_plant_job.py source.glb base.glb draft.json public-policy.json permissions.json reports/fresh-toe-fit --seed prior-proposal.glb --search-policy stricter-policy.json --iterations 16 --trust .001
```

The optional search policy must bind the same source/base/draft and may only
tighten anchor/speed limits. It cannot weaken the public policy. Every proposed
step is exported and independently decoded in raw and shadow-native form.
Requests archive inputs/method hashes, policies, permissions, runtime versions
and the fixed clock contract; controls, rejected probes and original source
audits remain available.

Normal execution performs an actual headless Godot import even for a failed
native proposal, preserving useful negative evidence. Selection requires
passing raw/shadow model rows, original serialized audits and the combined
legacy plus all twelve imported contact clocks. An already satisfactory native
input remains exact. Failed imports or changed inputs/methods produce terminal
failure and retain the saved input snapshot. No failed engine run selects a
correction. `--native-diagnostic-only` skips import and **always retains the
input**, including when native conditions pass.

Engine validation measures AnimationPlayer poses and imported skin bindings
through CPU reconstruction. It does not certify fresh GPU appearance, real
SOMA-native NPZ conversion, body/object collision, dynamics, semantic stance
labels, human realism, training admission or release quality. These remain
separate requirements.

## Validation and measured study

The final focused checks cover permission binding, invalid nodes/clocks/
bounds, exact original caps/clock populations, native frozen/root/translation
preservation, cumulative radial bounds, colored/full finite differences, raw/
shadow scalar decoding, real diagnostic jobs, input retention, failed import
and permission mutation. Existing leg, frame, foot, skin/contact and round-trip
checks run alongside the new tests. All 166 focused model-free checks pass,
including 34 new fixtures. Both CI platforms include the new suite. Existing
production source files and the default Studio path remain unchanged.

The real-rig study under `reports/native-toe-roll-v1/` uses the same female
run/roll/stand source, original warm seed, original support draft, sixteen
iterations and .001 radian trust as the completed leg-only frame study. The
public 1 mm anchor / 5 mm/s speed limits and separate 4.99 mm/s search target
remain unchanged. The only additional edit permissions are source/draft-bound
two-degree rotations of nodes 54 and 59 during their original edit windows.
The old contract and new contract are kept distinct.

| Sixteen-iteration variant | Native left/right anchor (mm) | Native left/right speed (mm/s) | Original failed rate rows: speed/acceleration/angular speed/angular acceleration | Worst imported frame speed (mm/s) |
| --- | --- | --- | --- | --- |
| Historical leg-only frames | 1.141046 / 1.211663 | 6.105352 / 8.142963 | 28 / 21 / 4 / 9 | 8.206508 |
| Explicit extra toe rotations | 1.067320 / 1.093633 | 5.766828 / 9.238813 | 24 / 27 / 4 / 26 | 9.290800 |

The extra-toe search improves both native anchors and left-foot speed, but
regresses right-foot speed and several rate-failure counts. Its maximum
normalized raw/shadow deficit is .8818832723, versus .8073194880 for the prior
leg-only search. More variables do not guarantee a better bounded nonlinear
search, causal proof, feasibility or animator quality. Toe changes reach only
.024810/.194924 degrees, below both authored two-degree limits; this does not
justify relaxing the original motion-rate or contact limits.

Support/edit bounds, extra-angle bounds and authored clearance pass. Native
contact/rates and combined imported contacts still fail. Actual headless Godot
adds 612 source/proposal pose observations across two 65-bone, three-surface
scenes. Every imported speed clock fails for each foot; worst left/right frame
speeds are 5.864405/9.290800 mm/s. The input remains selected. Repeated source
observations and this single development clip are not new held-out coverage.

Two separate generated six-bone fixtures test the normal engine-checked path.
One retains an already passing input without optimization. The second contains
analytic toe yaw, original angular peaks and an authored constant-stance warm
seed. Its baseline fails contact; the changed seed passes raw/shadow, original
rate/support/contact and actual imported clocks, and is selected after import
without an optimization step. This verifies changed-asset selection, not that
the fitter solved a human action or that a learned model improved. Fixture
observations are reported separately from real-rig motion evidence.

The initial regression expectations included an exact matrix comparison that
differed by 3.33e-16 when an unchanged toe channel was explicitly sampled, and a
purported passing fixture whose authored plane was above its foot. The fixtures
now use the existing proxy/scalar numerical comparison tolerance and an explicit
compatible plane. Original source caps and independent acceptance gates remain
unchanged. Receipt: `reports/native-toe-validation-v1/verification.json`.

The full project scope includes arbitrary humanoid actions, scene/partner
contacts, meaningful character controls, editable assets and engine exports.
This experimental foot path does not replace broader action/phase, rig,
interaction, human cleanup and learned-model evaluation. Original release
requirements and the single project-wide goal remain unchanged.
