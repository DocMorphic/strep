# Oriented contact fitting and real engine playback

2026-09-26. Work continues under the single project-wide goal. The release
contract is not complete. No model training, new motion generation or held-out
evaluation was performed in this study.

## Oriented scene solve

`support_contact_v6.py` adds actual skinned surface-normal targets and sampled
oriented-box clearance to v5's cubic edit controls. The frozen fixtures are in
`reports/scene-fit-fixtures-v3`; the outputs are in `reports/scene-fitting-v6`.
Actor transforms are converted into the actor's native frame. Explicit world
normals drive the high-five; the corrected anatomical box grips derive normals
from their unique box faces. Object trajectories remain fixed.

The clearance objective samples the whole surface at a fixed stride and includes
vertices near the box in the prepared motions. Its collision audit independently
evaluates all skin vertices. Neither operation establishes triangle-level,
continuous, partner or self-collision safety. Surface normals do not constrain
full wrist twist, fingers, joint limits or weight-bearing mechanics.

| Existing source | Peak point error | Peak skin-vertex box depth | Peak normal error | Result |
|---|---:|---:|---:|---|
| Box seed 11 | Left 3.91 cm; right 4.31 cm | 2.94 mm | Left 13.65°; right 12.34° | Failed point/support/pose checks |
| Box seed 22 | Left 5.19 cm; right 8.97 cm | 5.24 mm | Left 16.27°; right 23.85° | Failed point/orientation/support/pose checks |
| High-five seed 11 | Each world target 3.37 cm; palms 5.92 cm apart | Not measured for partner | 18.76° per world normal; palms oppose with 36.63° error | Failed contact/orientation/pose/speed checks |

Box penetration improves from v5's 6.42/10.08 cm, and high-five normal error from
78.95°, but point fitting regresses. The 3 cm point and provisional 15° normal
screens were not relaxed. None of these candidates is promoted to the default
editor. Existing hand slide/gap diagnostics can also conflict with intended
moving-object targets; their flags are retained and need interpretation rather
than deletion. Both high-five actors reuse the same native take, so this is not
independent partner-generation evidence.

Four exported actors preserve original raw motion, root XZ, root/finger rotations
within the existing numerical tolerance, bone lengths and hard correction
budgets. All eight raw/candidate GLBs validate with zero errors and warnings.
The actual GLB skin contact positions agree with the independent scene audit.
The full Python suite passes 150 tests, with four upstream Torch deprecation
warnings. Tests now include oriented geometry, coordinate transforms, explicit
world-normal auditing and invalid-normal rejection.

The initial v6 runner inherited v5 prose incorrectly saying it did not solve
orientation. `report-amendment.json` records that prose correction and the added
post-run normal audit, with original report hashes. Raw motion and the frozen
solver snapshot are unchanged. Future v6 runs automatically save normal audits
and include their failures in the aggregate status. Studio shows all three
source/candidate pairs with the independent orientation diagnostics.

## Godot import and playback

The official portable Windows Godot 4.7.2 build was downloaded from
[Godot's release](https://github.com/godotengine/godot-builds/releases/tag/4.7.2-stable)
and checked against the release asset SHA-256. The acquisition record is
`.cache/godot/4.7.2-stable/acquisition.json`; no system installation or PATH change
was made. Godot is a reference integration, not an exclusive engine requirement.

`reports/godot-import-v1/verification.json` records actual runtime GLB imports,
AnimationPlayer seeks and mesh inspection for the two attached-box exports and
one high-five actor. All 480 source frames were checked. Each imported mesh
retains 77 bones, 18,056 vertices and eight influences. Maximum joint position
error is 0.000000313 m, rotation matrix element error 0.000000654 and skin-weight
difference 0.0000153. Animated box transforms agree within 0.000000164.

`reports/godot-playback-v3/verification.json` then checks actual forward playback
at one-frame and 17-frame advances, including restart. Two authored grasp/release
sidecars dispatch in order exactly once; a separate synthetic test covers
frame-zero, middle and final-sample markers. Coarse steps dispatch on the update
that crosses the event, with up to 0.5 s delay at this deliberately coarse rate.
At 30 Hz the two authored event times match exactly within serialization
precision. Silent preview seeking emits no marker.

Two failed engine experiments remain available:

* `godot-playback-v1`: `seek(seconds, true)` dispatched a release marker during
  scrubbing. The adapter now explicitly uses the documented
  [`update_only` argument](https://docs.godotengine.org/en/stable/classes/class_animationplayer.html#class-animationplayer-method-seek).
* `godot-playback-v2`: native root deltas became zero on the final moving interval
  at the original clip endpoint. The adapter explicitly holds the last sample
  for one frame. A 180-sample clip therefore lasts six seconds, rather than ending
  exactly at its last sample time. The original GLB is unchanged; both durations
  are recorded. The test checks the terminal hold produces no further root drift.

With those fixes, extracted Hips translation deltas match source samples within
7.46e-9 m and rotation deltas within 5.58e-8 radians, including coarse updates.
This follows Godot's
[root-motion track interface](https://docs.godotengine.org/en/stable/classes/class_animationmixer.html#class-animationmixer-property-root-motion-track).
It does not verify CharacterBody movement, applying deltas to attached objects,
physics, blending, reverse/loop playback, other rigs or GPU skin rendering.
Headless import/playback fidelity does not approve the motion's realism.

## Use and reproduce

Studio Scenes offers **Godot adapter · ZIP** beside the two attached-box scene
packs. The adapter ZIP includes its instructions and engine verification. Its
served bytes match the local SHA-256. The browser displays the v6 frame-60 box
candidate and failure diagnostics without console errors. The instructions are
also in `integrations/godot/README.md`.

From the project directory, choose fresh output folders for each experiment:

```powershell
.venv\Scripts\python.exe scripts/setup_godot_audit.py
.venv\Scripts\python.exe scripts/run_godot_import_audit.py --output reports/godot-import-repeat
.venv\Scripts\python.exe scripts/run_godot_playback_audit.py --output reports/godot-playback-repeat
.venv\Scripts\python.exe scripts/run_scene_fit.py reports/scene-fit-fixtures-v3/high-five.json reports/scene-fit-fixtures-v3/box-seed-11.json reports/scene-fit-fixtures-v3/box-seed-22.json --solver-version 6 --output reports/oriented-scene-repeat
.venv\Scripts\python.exe scripts/verify_scene_fit.py reports/oriented-scene-repeat
node scripts/validate_scene_exports.mjs reports/oriented-scene-repeat
```

Next: resolve the competing point/orientation/clearance constraints with explicit
reachability checks and coordinated two-hand/object fitting; then add partner
collision and feasible Kimodo constraint conditioning. Retargeting, broader clip
editing/styles, held-out actions/objects/rigs, offline distribution and independent
animator cleanup-time evaluation remain part of the same release goal.
