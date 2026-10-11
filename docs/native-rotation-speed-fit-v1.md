# Authored speed limits in native scene fitting

`SpeedLimitedSceneProblem` adds the author's local joint-speed limits to the
existing native scene solver. It first performs the necessary-condition
[preflight](temporal-rotation-bounds-v1.md), then retains every original scene
constraint and appends speed residuals for every neighboring key on each
selected rotation track. Original clocks, frozen keys, edit caps, contact goals
and existing source-relative motion bounds remain in force.

The existing optimizer can use this problem directly. Each proposed export must
be checked with its `decoded` method. That method reads the fresh GLB, checks
original edit/static/frozen-key preservation, and calculates rotation speeds
using separate normalized-quaternion relative-angle arithmetic. The model uses
SciPy rotation arithmetic; output checking does not reuse that angle decoder.
Every rate and native time is retained in `last_speed_output_audit`. A violated
edit/payload contract raises an error; a speed violation remains an optimization
residual and prevents a passing result. Failed exports stay available for review.

These are local-key geodesic speeds in degrees per second, without an extra speed
acceptance allowance or invented anatomical limit. They do not establish
instantaneous speed throughout glTF interpolation, physically plausible joint
dynamics, whole-surface collision freedom, engine fidelity or animation quality.
Scene fitting remains bounded and may fail even after preflight does not exclude
the request. Studio route/UI integration is pending.

The 15 new regression cases include identity, tiny angles, half-turns and
quaternion sign/length changes; invalid clocks and values; fresh serialized
output that disagrees with submitted controls; hard edit-audit rejection; and
a complete fixture fit with unchanged contact conditions, native clocks and
source bytes. The fixture deliberately isolates a rotation track from mesh
deformation, so its fit does not prove simultaneous full-body contact correction.
Both CPU workflows include these tests; execution results remain pending.
