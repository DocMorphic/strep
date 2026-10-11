# Rotation-speed feasibility before editing

`scripts/temporal_rotation_bounds.py` assesses every neighboring key and joint
before an editor attempts to change motion. The author supplies a rotation-edit
cap at each key and, optionally, a maximum joint speed in degrees per second.
No physiological threshold or project release gate is supplied by default.

For original neighboring rotations separated by angle `a`, edit caps `c0`, `c1`
and elapsed time `dt`, the minimum possible average geodesic speed is at least
`max(0, a - c0 - c1) / dt`. This follows from the triangle inequality on SO(3).
The implementation subtracts a small numerical reserve before comparison. It
validates proper rotations, explicitly records projection of tolerated matrix
drift, retains the complete lower-bound array and reports an incompatible
interval witness for each affected joint. Original matrices remain unchanged.

For example, a 150-degree change in 0.1 seconds with 20- and 30-degree edit caps
still needs at least approximately 1,000 degrees per second. An author's
900-degree-per-second limit cannot be met under those caps. The editor should
report the conflicting interval rather than imply that fitting will solve it.

This is a necessary-condition calculation, exposed as a reusable
module. Non-exclusion
does not prove that one trajectory can satisfy every key simultaneously, or
that interpolation, contacts, anatomy, forces and engine behavior are valid.
The captured crawl/get-up replay remains a separate pending experiment.

The 26 synthetic regression cases cover achievable bounds, contradictory
author limits, protected endpoints, complete populations, coordinate-basis
invariance, half-turns, declared projection and invalid inputs. They are added
to both the broad source inventory and focused Windows/Linux CPU workflow.
The [focused run](https://github.com/DocMorphic/strep/actions/runs/38150882494)
at commit `5073eda` passes all 288 selected checks on each operating system,
including all 26 new cases, without skips or failures. Linux takes 14.29 seconds
and Windows 32.85 seconds. These are synthetic source checks, not captured-motion
or realism approval.

`scripts/native_rotation_speed_preflight.py` also assesses validated native
scene-edit permissions. Limits explicitly select actor/joint pairs, including
tracks with no editing permission. Every original neighboring key is retained
on that track's own clock. Frozen keys have zero allowance; editable keys use
the existing exported-rotation audit's norm cap and its 0.0001-degree
serialization allowance. Quaternion normalization follows the native decoder
and is reported. Boundary and protected-interpolation permissions are reused
from the validated editor.

The opt-in `SpeedPreflightSceneProblem` rejects incompatible requests before
the existing scene fitting population is initialized. Its exception retains
the complete diagnostic. A nonexcluded request initializes the existing scene
problem; this preflight-only class does **not** enforce the new absolute speed limit
on its output. Callers still need output verification and speed-constrained
fitting. Studio UI/route integration is pending. The additional 16 regression
cases use actual scene fixtures, including unchanged source bytes, protected
keys, boundary permissions and rejection before expensive initialization.

The first adapter CI attempt at `1c18f3c` passes 303 cases per operating system
and fails one test whose supposed missing-channel joint actually has a channel
in the fixture. The corrected test selects an existing joint without a rotation
channel and explicitly verifies that premise. The failed run and logs remain
preserved; no production behavior was relaxed to accommodate the fixture.

The [corrected focused run](https://github.com/DocMorphic/strep/actions/runs/38151278419)
at `c281fc9` passes all **304 checks on each operating system**, including all 16
adapter cases, without skips or failures. Linux takes 9.34 seconds and Windows
34.50 seconds. Exact committed source bytes and hosted logs are bound in the
local evidence record. No captured-motion, solver-output speed, live UI or
release approval follows from these fixture checks.

The separate [speed-constrained fitting implementation](native-rotation-speed-fit-v1.md)
now appends authored speed rows and verifies actual serialized output. The
preflight-only class described above retains its original diagnostic scope.
