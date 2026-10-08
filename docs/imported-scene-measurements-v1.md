# Imported-skin contact and vertex diagnostics

The synchronized scene audit now has an optional imported-skin measurement
stage. It reads actual Godot surface weights, joint palettes, inverse binds,
positions and triangle indices. Existing `ImportedSceneSkin` correspondence
checks require complete source vertex functions and triangle populations before
any measured contact is used. Bone/slot/vertex ordering can change; missing or
altered skin functions and topology reject the measurement.

```powershell
python scripts/run_scene_playback.py reports/scene-preview-v1 reports/my-imported-measurements --rate-hz 120 --scene-id lift-box-seed-11 --scene-id high-five-seed-11 --measure-skin --floor-y-m 0 --penetration-limit-m 0.005
```

Use a fresh output directory and the existing local engine/dependencies. This
command runs no model, edits no clip and downloads no assets. CLI output names
pose fidelity and point-contact success separately. A clean import can still
produce failed contact measurements.

## Measurement contract

- Preserve the dense shared clock, actual stored keys and exact timestamp
  protocol from the synchronized import audit.
- Reconstruct every source vertex with all raw imported influences. Do not
  normalize quantized engine weights or substitute nearest animated vertices.
  Apply authored placement after the raw-weight skin sum.
- Measure surface-vertex or named joint/offset effectors against authored world
  points, imported moving object poses, or the other actor's actual skin/joint
  on the same clock. Keep the original point tolerance and exact interval
  boundaries. Report first valid interval time, nearest sampled time, errors
  and the full contact tracks.
- Report area-weighted source-winding surface-normal diagnostics against an
  authored direction, an opposing partner normal, or an unambiguous inward
  primitive surface normal. Missing/degenerate/ambiguous normals remain
  unavailable. The 15-degree diagnostic remains provisional.
- Query every actor vertex against the explicitly declared floor and every
  analytic box, sphere or cylinder at every sample. Save maximum depths,
  source vertex/time witnesses and counts over the declared diagnostic limit.
  Object basis projection onto a rigid rotation is measured and bounded by the
  existing object pose screen.
- Retain unsupported authored distributed regions and tangent requirements as
  unmeasured, never silently pass them. Save small numeric observation archives
  alongside the raw imported poses/bindings and implementation snapshots.

Complete vertex queries are **not** complete triangle/object collision queries.
These measurements cannot certify object containment, partner body collision,
self-collision, continuous motion, GPU rendering, forces, attachment, natural
motion or release acceptance. Existing full-triangle/volume evaluators remain
separate required work.

## Actual engine results

Four development scenes were reimported with complete skin observations:
2585 actor poses and 1407 object poses, all 18,056 vertices and eight influences
per actor. Every imported skin matched its expected bind function and all
36,108 source triangles, with reported globally reversed engine winding.
Maximum bind-function coefficient discrepancy was about `1.02e-14`.

| Scene | Point samples | Maximum contact error | Maximum floor depth | Result |
|---|---:|---|---:|---|
| Original box lift, seed 11 | 11 per hand | Left 549.465 mm; right 497.652 mm | 8.997 mm | Both 30 mm point constraints fail; floor screen fails |
| Original high-five, seed 11 | 1 per contact | Each world target 289.596 mm; hand-to-hand 533.735 mm | 6.234 mm per actor | All three 30 mm constraints fail; floor screens fail |
| Corrected V16 reference, seed 7103 | 19 | 0.986473 mm | 0 | Unchanged 1 mm point constraint passes |
| Corrected V16 reference, seed 7104 | 19 | 0.937494 mm | 0 | Unchanged 1 mm point constraint passes |

The lift's palm-normal diagnostics are 147.675/161.295 degrees; the high-five's
opposing-palm error is 84.166 degrees. Reference normal errors are 7.223/4.135
degrees. No sampled actor vertex enters the box in these three object scenes;
that does not prove their triangle interiors or enclosed volume avoid it.

Maximum imported-versus-source whole-skin displacement ranges from 0.095163 to
0.138701 mm. Both high-five actors and both reference clips exceed the earlier
native scene engine's 0.1 mm whole-skin comparison screen. That screen is not
widened or declared passed: matching the expected quantized import function
does not establish exact original-weight skin fidelity.

The longer scene receipt retains its frozen executor. Its final CLI line was
subsequently clarified to separate pose/contact results; an exact byte
substitution verifies that this revision changes only that terminal summary,
not the measured code or saved observations. Reference measurements use the
current executor. No existing evidence was rebound to edited inputs.

The model-free integration subset passed 118 tests; the broader local suite
passed 153, including actual object-rotation checks. The native-frame scene
runner still passes four source/candidate imports. Model-free CI now declares
396 Python modules in four equal shards and 37 Node scripts per operating
system.

## Remaining work

Bind these observations to the full-triangle and partner-volume checks rather
than treating vertex screens as collision approval. Resolve the whole-skin
comparison failures, then complete and evaluate a longer constrained lift when
system memory permits. None of these fixtures demonstrates a natural lift or
high-five, independent animator approval, held-out coverage or measured cleanup
time. All fourteen release capabilities remain unapproved; the project-wide
goal stays active.
