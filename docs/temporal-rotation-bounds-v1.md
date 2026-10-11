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

This is a necessary-condition calculation, currently exposed as a reusable
module. It is not yet connected to the Studio editing workflow. Non-exclusion
does not prove that one trajectory can satisfy every key simultaneously, or
that interpolation, contacts, anatomy, forces and engine behavior are valid.
The captured crawl/get-up replay remains a separate pending experiment.

The 26 synthetic regression cases cover achievable bounds, contradictory
author limits, protected endpoints, complete populations, coordinate-basis
invariance, half-turns, declared projection and invalid inputs. They are added
to both the broad source inventory and focused Windows/Linux CPU workflow;
execution results will be recorded after CI completes.
